package app.adblocker.vpn

import android.app.Notification
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.core.app.NotificationCompat
import app.adblocker.AdBlockerApp
import app.adblocker.R
import app.adblocker.data.BlocklistRepository
import app.adblocker.data.Settings
import app.adblocker.data.Stats
import app.adblocker.ui.MainActivity
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * 端末内に擬似 VPN を立て、`10.215.173.2:53` 宛 DNS クエリだけを捕捉して
 * - ブロックリスト一致 → NXDOMAIN を即返す
 * - 非一致 → 設定された upstream DNS (既定: 1.1.1.1) に転送して応答を返す
 *
 * 他のトラフィックには一切触れず、ルートは DNS 専用 (`10.215.173.2/32`) のみ。
 */
class AdBlockVpnService : VpnService() {

    private var vpnInterface: ParcelFileDescriptor? = null
    private val running = AtomicBoolean(false)

    private lateinit var settings: Settings
    private lateinit var blocklist: BlocklistRepository
    private lateinit var stats: Stats

    private val forwarder = Executors.newFixedThreadPool(4) { r ->
        Thread(r, "dns-forward").apply { isDaemon = true }
    }
    private var workerThread: Thread? = null

    override fun onCreate() {
        super.onCreate()
        val app = applicationContext as AdBlockerApp
        settings = app.settings
        blocklist = app.blocklist
        stats = app.stats
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopVpn()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                broadcastState(false)
                return START_NOT_STICKY
            }
            else -> startVpn()
        }
        return START_STICKY
    }

    override fun onRevoke() {
        // ユーザーが別の VPN を起動した、または OS が剥奪
        stopVpn()
        stopSelf()
        broadcastState(false)
        super.onRevoke()
    }

    override fun onDestroy() {
        stopVpn()
        forwarder.shutdownNow()
        super.onDestroy()
    }

    private fun startVpn() {
        if (running.get()) return
        try {
            val builder = Builder()
                .setSession(getString(R.string.app_name))
                .addAddress(VPN_LOCAL_ADDR, 32)
                .addDnsServer(VPN_DNS_ADDR)
                .addRoute(VPN_DNS_ADDR, 32)
                .setMtu(1500)
                .setBlocking(true)
            builder.setConfigureIntent(
                PendingIntent.getActivity(
                    this, 0,
                    Intent(this, MainActivity::class.java),
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
            )
            val pfd = builder.establish() ?: error("Failed to establish VPN interface")
            vpnInterface = pfd
            running.set(true)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                startForeground(
                    AdBlockerApp.NOTIFICATION_ID_VPN,
                    buildNotification(),
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
                )
            } else {
                startForeground(AdBlockerApp.NOTIFICATION_ID_VPN, buildNotification())
            }
            broadcastState(true)

            workerThread = Thread({ runLoop(pfd) }, "vpn-loop").also { it.start() }
        } catch (t: Throwable) {
            Log.e(TAG, "startVpn failed", t)
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
            broadcastState(false)
        }
    }

    private fun stopVpn() {
        if (!running.compareAndSet(true, false)) return
        try {
            vpnInterface?.close()
        } catch (_: IOException) {
        }
        vpnInterface = null
        workerThread?.interrupt()
        workerThread = null
        stats.persist()
    }

    private fun runLoop(pfd: ParcelFileDescriptor) {
        val input = FileInputStream(pfd.fileDescriptor)
        val output = FileOutputStream(pfd.fileDescriptor)
        val buf = ByteArray(32 * 1024)
        try {
            while (running.get() && !Thread.currentThread().isInterrupted) {
                val n = try {
                    input.read(buf)
                } catch (e: IOException) {
                    if (running.get()) Log.w(TAG, "tun read error", e)
                    break
                }
                if (n <= 0) continue
                handleInbound(buf, n, output)
            }
        } finally {
            try {
                input.close()
            } catch (_: IOException) {
            }
            try {
                output.close()
            } catch (_: IOException) {
            }
        }
    }

    /** tun から読んだ生 IP パケットを処理。DNS でなければ捨てる (route 設定上ほぼ来ない)。 */
    private fun handleInbound(buf: ByteArray, length: Int, output: FileOutputStream) {
        if (length < 28) return // IPv4(20) + UDP(8) 未満
        if (IpPacket.version(buf) != 4) return
        if (IpPacket.protocol(buf) != IpPacket.PROTO_UDP) return
        val ihl = IpPacket.ihlBytes(buf)
        if (IpPacket.udpDstPort(buf, ihl) != 53) return

        val dnsOffset = IpPacket.udpPayloadOffset(ihl)
        val dnsLength = IpPacket.udpPayloadLength(buf, ihl)
        if (dnsOffset + dnsLength > length) return

        val domain = DnsPacket.firstQuestionName(buf, dnsOffset, dnsLength)
        if (domain != null && blocklist.isBlocked(domain)) {
            stats.recordQuery(domain, blocked = true)
            val response = DnsPacket.buildNxDomainResponse(buf, dnsOffset, dnsLength) ?: return
            val reply = IpPacket.buildReply(buf, length, response)
            synchronized(output) {
                try {
                    output.write(reply)
                } catch (e: IOException) {
                    Log.w(TAG, "Failed to write blocked reply", e)
                }
            }
            return
        }
        if (domain != null) stats.recordQuery(domain, blocked = false)
        forwardUpstream(buf.copyOf(length), length, output)
    }

    /** 非ブロックドメインのクエリを upstream DNS に転送し、応答を tun に書き戻す。 */
    private fun forwardUpstream(
        packet: ByteArray,
        length: Int,
        output: FileOutputStream
    ) {
        forwarder.execute {
            val ihl = IpPacket.ihlBytes(packet)
            val dnsOffset = IpPacket.udpPayloadOffset(ihl)
            val dnsLength = IpPacket.udpPayloadLength(packet, ihl)
            val query = ByteArray(dnsLength)
            System.arraycopy(packet, dnsOffset, query, 0, dnsLength)

            val response = queryUpstream(query) ?: return@execute
            val reply = IpPacket.buildReply(packet, length, response)
            synchronized(output) {
                try {
                    output.write(reply)
                } catch (e: IOException) {
                    if (running.get()) Log.w(TAG, "Failed to write upstream reply", e)
                }
            }
        }
    }

    private fun queryUpstream(query: ByteArray): ByteArray? {
        val servers = listOf(settings.upstreamDns, settings.upstreamDnsFallback)
        for (server in servers) {
            try {
                DatagramSocket().use { socket ->
                    if (!protect(socket)) {
                        Log.w(TAG, "protect(socket) failed for $server")
                        return@use
                    }
                    socket.soTimeout = 5_000
                    val addr = InetSocketAddress(InetAddress.getByName(server), 53)
                    socket.send(DatagramPacket(query, query.size, addr))
                    val buf = ByteArray(2048)
                    val packet = DatagramPacket(buf, buf.size)
                    socket.receive(packet)
                    return buf.copyOf(packet.length)
                }
            } catch (t: Throwable) {
                Log.w(TAG, "upstream $server failed: ${t.message}")
            }
        }
        return null
    }

    private fun buildNotification(): Notification {
        val tap = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val stopIntent = Intent(this, AdBlockVpnService::class.java).setAction(ACTION_STOP)
        val stop = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            PendingIntent.getForegroundService(
                this, 1, stopIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        } else {
            PendingIntent.getService(
                this, 1, stopIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        }
        return NotificationCompat.Builder(this, AdBlockerApp.CHANNEL_ID_VPN)
            .setSmallIcon(R.drawable.ic_shield)
            .setContentTitle(getString(R.string.notification_active_title))
            .setContentText(getString(R.string.notification_active_text))
            .setOngoing(true)
            .setContentIntent(tap)
            .addAction(0, getString(R.string.action_stop), stop)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }

    private fun broadcastState(active: Boolean) {
        sendBroadcast(
            Intent(ACTION_STATE_CHANGED)
                .setPackage(packageName)
                .putExtra(EXTRA_ACTIVE, active)
        )
    }

    companion object {
        private const val TAG = "AdBlockVpn"

        const val ACTION_STOP = "app.adblocker.action.STOP"
        const val ACTION_STATE_CHANGED = "app.adblocker.action.STATE_CHANGED"
        const val EXTRA_ACTIVE = "active"

        // RFC 1918 内の任意のローカルアドレス
        private const val VPN_LOCAL_ADDR = "10.215.173.1"
        private const val VPN_DNS_ADDR = "10.215.173.2"

        fun stopIntent(context: Context): Intent =
            Intent(context, AdBlockVpnService::class.java).setAction(ACTION_STOP)
    }
}

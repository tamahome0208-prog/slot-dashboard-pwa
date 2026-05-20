package app.adblocker

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import app.adblocker.data.BlocklistRepository
import app.adblocker.data.Settings
import app.adblocker.data.Stats

class AdBlockerApp : Application() {

    lateinit var settings: Settings
        private set
    lateinit var stats: Stats
        private set
    lateinit var blocklist: BlocklistRepository
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        settings = Settings(this)
        stats = Stats(this)
        blocklist = BlocklistRepository(this, settings)
        createNotificationChannel()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID_VPN,
                getString(R.string.notification_channel_vpn),
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = getString(R.string.notification_channel_vpn_desc)
                setShowBadge(false)
            }
            getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    companion object {
        const val CHANNEL_ID_VPN = "vpn_status"
        const val NOTIFICATION_ID_VPN = 1001

        private lateinit var instance: AdBlockerApp
        fun get(): AdBlockerApp = instance
    }
}

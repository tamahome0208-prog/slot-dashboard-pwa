package app.adblocker.vpn

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.net.VpnService
import app.adblocker.AdBlockerApp

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val app = context.applicationContext as AdBlockerApp
        if (!app.settings.startOnBoot) return
        // 既に VPN 許可済みなら prepare() は null を返す。null でない (＝ダイアログ必要)
        // 場合は、Activity を立ち上げないと許可できないため、起動時は諦める。
        if (VpnService.prepare(context) != null) return
        val svc = Intent(context, AdBlockVpnService::class.java)
        context.startForegroundService(svc)
    }
}

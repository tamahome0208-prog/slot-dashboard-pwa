package app.adblocker.data

import android.content.Context
import android.content.SharedPreferences

class Settings(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("adblocker_settings", Context.MODE_PRIVATE)

    var upstreamDns: String
        get() = prefs.getString(KEY_UPSTREAM_DNS, DEFAULT_UPSTREAM_DNS) ?: DEFAULT_UPSTREAM_DNS
        set(value) = prefs.edit().putString(KEY_UPSTREAM_DNS, value).apply()

    var upstreamDnsFallback: String
        get() = prefs.getString(KEY_UPSTREAM_DNS_FALLBACK, DEFAULT_UPSTREAM_DNS_FALLBACK)
            ?: DEFAULT_UPSTREAM_DNS_FALLBACK
        set(value) = prefs.edit().putString(KEY_UPSTREAM_DNS_FALLBACK, value).apply()

    var startOnBoot: Boolean
        get() = prefs.getBoolean(KEY_START_ON_BOOT, false)
        set(value) = prefs.edit().putBoolean(KEY_START_ON_BOOT, value).apply()

    /** ユーザー独自のブロックドメイン (1行1ドメイン) */
    var customBlockedDomains: Set<String>
        get() = prefs.getStringSet(KEY_CUSTOM_BLOCKED, emptySet()) ?: emptySet()
        set(value) = prefs.edit().putStringSet(KEY_CUSTOM_BLOCKED, value).apply()

    /** ユーザーが許可したドメイン (ブロックリストより優先) */
    var allowedDomains: Set<String>
        get() = prefs.getStringSet(KEY_ALLOWED, emptySet()) ?: emptySet()
        set(value) = prefs.edit().putStringSet(KEY_ALLOWED, value).apply()

    /** 有効な外部ブロックリスト URL */
    var enabledRemoteLists: Set<String>
        get() = prefs.getStringSet(KEY_REMOTE_LISTS, DEFAULT_REMOTE_LISTS) ?: DEFAULT_REMOTE_LISTS
        set(value) = prefs.edit().putStringSet(KEY_REMOTE_LISTS, value).apply()

    companion object {
        private const val KEY_UPSTREAM_DNS = "upstream_dns"
        private const val KEY_UPSTREAM_DNS_FALLBACK = "upstream_dns_fallback"
        private const val KEY_START_ON_BOOT = "start_on_boot"
        private const val KEY_CUSTOM_BLOCKED = "custom_blocked"
        private const val KEY_ALLOWED = "allowed"
        private const val KEY_REMOTE_LISTS = "remote_lists"

        const val DEFAULT_UPSTREAM_DNS = "1.1.1.1"
        const val DEFAULT_UPSTREAM_DNS_FALLBACK = "1.0.0.1"

        val DEFAULT_REMOTE_LISTS: Set<String> = setOf(
            // StevenBlack の hosts (広告 + マルウェア)。同期は手動。
            "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
        )
    }
}

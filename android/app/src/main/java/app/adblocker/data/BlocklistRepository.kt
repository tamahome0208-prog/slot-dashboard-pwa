package app.adblocker.data

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.util.Collections

/**
 * ホストファイル形式 (`0.0.0.0 ads.example.com` または `ads.example.com` のみ) を
 * ロードして、メモリ上のドメイン集合として保持する。
 *
 * 起動時に bundled `assets/blocklist.txt` と、ダウンロード済みリモートリストを
 * マージする。`allowedDomains` (ホワイトリスト) は除外する。
 */
class BlocklistRepository(
    private val context: Context,
    private val settings: Settings
) {

    @Volatile
    private var blockedSet: Set<String> = emptySet()

    @Volatile
    private var allowedSet: Set<String> = emptySet()

    val size: Int get() = blockedSet.size

    init {
        // 初期ロードは軽量に同期で。リモートリストは別途 reload() で取り込む。
        blockedSet = readBundled() + settings.customBlockedDomains.normalize()
        allowedSet = settings.allowedDomains.normalize()
    }

    /** ドメインがブロック対象か判定。サブドメインも親ドメインがブロックされていれば対象。 */
    fun isBlocked(domain: String): Boolean {
        val d = domain.lowercase().trimEnd('.')
        if (d.isEmpty()) return false
        if (matches(d, allowedSet)) return false
        return matches(d, blockedSet)
    }

    private fun matches(domain: String, set: Set<String>): Boolean {
        if (set.isEmpty()) return false
        if (set.contains(domain)) return true
        var i = domain.indexOf('.')
        while (i != -1 && i < domain.length - 1) {
            val parent = domain.substring(i + 1)
            if (set.contains(parent)) return true
            i = domain.indexOf('.', i + 1)
        }
        return false
    }

    /** カスタム/許可リストの変更を即時反映 */
    fun refreshUserLists() {
        val bundled = readBundled()
        val downloaded = readDownloaded()
        blockedSet = (bundled + downloaded + settings.customBlockedDomains.normalize())
            .toSet()
        allowedSet = settings.allowedDomains.normalize()
    }

    /** リモートのホストファイルをダウンロードしてキャッシュし、メモリへ反映 */
    suspend fun downloadRemoteLists(): DownloadResult = withContext(Dispatchers.IO) {
        val urls = settings.enabledRemoteLists
        var entries = 0
        var failures = 0
        for (url in urls) {
            try {
                val bytes = httpGet(url)
                val file = cacheFileFor(url)
                file.parentFile?.mkdirs()
                file.writeBytes(bytes)
                entries += parseHostsLines(file.readLines()).size
            } catch (t: Throwable) {
                Log.w(TAG, "Failed to download $url", t)
                failures++
            }
        }
        refreshUserLists()
        DownloadResult(urls.size, failures, blockedSet.size)
    }

    private fun httpGet(urlString: String): ByteArray {
        val conn = (URL(urlString).openConnection() as HttpURLConnection).apply {
            connectTimeout = 15_000
            readTimeout = 30_000
            requestMethod = "GET"
            instanceFollowRedirects = true
            setRequestProperty("User-Agent", "AdBlocker-Android/0.1")
        }
        try {
            val code = conn.responseCode
            if (code !in 200..299) error("HTTP $code for $urlString")
            return conn.inputStream.use { it.readBytes() }
        } finally {
            conn.disconnect()
        }
    }

    private fun readBundled(): Set<String> {
        return try {
            context.assets.open("blocklist.txt").use { input ->
                val reader = BufferedReader(InputStreamReader(input))
                parseHostsLines(reader.readLines())
            }
        } catch (t: Throwable) {
            Log.w(TAG, "No bundled blocklist", t)
            emptySet()
        }
    }

    private fun readDownloaded(): Set<String> {
        val dir = File(context.filesDir, "blocklists")
        if (!dir.isDirectory) return emptySet()
        val result = HashSet<String>(50_000)
        dir.listFiles()?.forEach { f ->
            try {
                result.addAll(parseHostsLines(f.readLines()))
            } catch (t: Throwable) {
                Log.w(TAG, "Failed to read ${f.name}", t)
            }
        }
        return Collections.unmodifiableSet(result)
    }

    private fun cacheFileFor(url: String): File {
        val name = url.hashCode().toString(16) + ".hosts"
        return File(File(context.filesDir, "blocklists"), name)
    }

    data class DownloadResult(val totalSources: Int, val failures: Int, val totalDomains: Int)

    private fun Set<String>.normalize(): Set<String> =
        this.asSequence().map { it.lowercase().trim().trimEnd('.') }
            .filter { it.isNotEmpty() }.toSet()

    companion object {
        private const val TAG = "BlocklistRepo"

        /**
         * hosts ファイル形式の各行をドメインに変換する。
         * - `#` 以降はコメント
         * - `0.0.0.0 ads.example.com` / `127.0.0.1 ads.example.com` / `ads.example.com` を受け入れる
         * - `localhost` / `broadcasthost` などローカル名は除外
         */
        fun parseHostsLines(lines: List<String>): Set<String> {
            val out = HashSet<String>(lines.size)
            for (raw in lines) {
                val noComment = raw.substringBefore('#').trim()
                if (noComment.isEmpty()) continue
                val parts = noComment.split(Regex("\\s+"))
                val domain = when (parts.size) {
                    1 -> parts[0]
                    else -> parts[1]
                }.lowercase().trimEnd('.')
                if (!isValidDomain(domain)) continue
                out.add(domain)
            }
            return out
        }

        private val LOCAL_NAMES = setOf(
            "localhost", "localhost.localdomain", "local", "broadcasthost",
            "ip6-localhost", "ip6-loopback", "ip6-localnet", "ip6-mcastprefix",
            "ip6-allnodes", "ip6-allrouters", "ip6-allhosts"
        )

        private val DOMAIN_REGEX =
            Regex("^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z]{2,63}$")

        private fun isValidDomain(d: String): Boolean {
            if (d.isEmpty() || d.length > 253) return false
            if (d in LOCAL_NAMES) return false
            return DOMAIN_REGEX.matches(d)
        }
    }
}

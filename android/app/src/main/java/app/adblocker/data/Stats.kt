package app.adblocker.data

import android.content.Context
import android.content.SharedPreferences
import java.util.ArrayDeque
import java.util.concurrent.atomic.AtomicLong

class Stats(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("adblocker_stats", Context.MODE_PRIVATE)

    private val totalQueries = AtomicLong(prefs.getLong(KEY_TOTAL, 0))
    private val blockedQueries = AtomicLong(prefs.getLong(KEY_BLOCKED, 0))

    private val recentLock = Any()
    private val recent: ArrayDeque<Entry> = ArrayDeque(RECENT_CAPACITY)

    fun recordQuery(domain: String, blocked: Boolean) {
        totalQueries.incrementAndGet()
        if (blocked) blockedQueries.incrementAndGet()
        synchronized(recentLock) {
            if (recent.size >= RECENT_CAPACITY) recent.pollFirst()
            recent.addLast(Entry(System.currentTimeMillis(), domain, blocked))
        }
    }

    fun snapshot(): Snapshot {
        val recentCopy = synchronized(recentLock) { recent.toList() }
        return Snapshot(totalQueries.get(), blockedQueries.get(), recentCopy.asReversed())
    }

    fun persist() {
        prefs.edit()
            .putLong(KEY_TOTAL, totalQueries.get())
            .putLong(KEY_BLOCKED, blockedQueries.get())
            .apply()
    }

    fun reset() {
        totalQueries.set(0)
        blockedQueries.set(0)
        synchronized(recentLock) { recent.clear() }
        prefs.edit().clear().apply()
    }

    data class Entry(val timestamp: Long, val domain: String, val blocked: Boolean)

    data class Snapshot(
        val total: Long,
        val blocked: Long,
        val recent: List<Entry>
    )

    companion object {
        private const val KEY_TOTAL = "total"
        private const val KEY_BLOCKED = "blocked"
        private const val RECENT_CAPACITY = 200
    }
}

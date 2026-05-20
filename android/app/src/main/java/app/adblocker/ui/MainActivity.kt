package app.adblocker.ui

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.VpnService
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import app.adblocker.AdBlockerApp
import app.adblocker.R
import app.adblocker.data.Stats
import app.adblocker.databinding.ActivityMainBinding
import app.adblocker.vpn.AdBlockVpnService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.DateFormat
import java.util.Date

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val app: AdBlockerApp by lazy { application as AdBlockerApp }
    private val handler = Handler(Looper.getMainLooper())
    private var vpnActive = false

    private val prepareLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == RESULT_OK) {
                startVpnService()
            } else {
                binding.toggle.isChecked = false
                snackbar(getString(R.string.toast_vpn_permission_denied))
            }
        }

    private val notificationsLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { /* no-op */ }

    private val stateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action != AdBlockVpnService.ACTION_STATE_CHANGED) return
            val active = intent.getBooleanExtra(AdBlockVpnService.EXTRA_ACTIVE, false)
            updateActive(active)
        }
    }

    private val refreshRunnable = object : Runnable {
        override fun run() {
            refreshStats()
            handler.postDelayed(this, 1_000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        binding.toggle.setOnCheckedChangeListener { _, checked ->
            if (checked) prepareAndStart() else stopVpnService()
        }
        binding.btnBlocklist.setOnClickListener {
            startActivity(Intent(this, BlocklistActivity::class.java))
        }
        binding.btnRefreshLists.setOnClickListener { refreshRemoteLists() }
        binding.btnResetStats.setOnClickListener {
            app.stats.reset()
            refreshStats()
        }

        binding.blocklistSizeValue.text = formatNumber(app.blocklist.size.toLong())

        ensureNotificationPermission()
    }

    override fun onResume() {
        super.onResume()
        ContextCompat.registerReceiver(
            this, stateReceiver,
            IntentFilter(AdBlockVpnService.ACTION_STATE_CHANGED),
            ContextCompat.RECEIVER_NOT_EXPORTED
        )
        refreshStats()
        handler.post(refreshRunnable)
    }

    override fun onPause() {
        super.onPause()
        unregisterReceiver(stateReceiver)
        handler.removeCallbacks(refreshRunnable)
    }

    private fun ensureNotificationPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        if (ActivityCompat.checkSelfPermission(
                this, Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            notificationsLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    private fun prepareAndStart() {
        val intent = VpnService.prepare(this)
        if (intent != null) {
            prepareLauncher.launch(intent)
        } else {
            startVpnService()
        }
    }

    private fun startVpnService() {
        val intent = Intent(this, AdBlockVpnService::class.java)
        ContextCompat.startForegroundService(this, intent)
    }

    private fun stopVpnService() {
        startService(AdBlockVpnService.stopIntent(this))
    }

    private fun updateActive(active: Boolean) {
        vpnActive = active
        binding.toggle.setOnCheckedChangeListener(null)
        binding.toggle.isChecked = active
        binding.toggle.setOnCheckedChangeListener { _, checked ->
            if (checked) prepareAndStart() else stopVpnService()
        }
        binding.statusText.text = getString(
            if (active) R.string.status_active else R.string.status_inactive
        )
    }

    private fun refreshStats() {
        val snap = app.stats.snapshot()
        binding.totalValue.text = formatNumber(snap.total)
        binding.blockedValue.text = formatNumber(snap.blocked)
        val ratio = if (snap.total == 0L) 0 else (snap.blocked * 100 / snap.total).toInt()
        binding.blockedRatioValue.text = getString(R.string.percent_format, ratio)
        binding.recentList.text = formatRecent(snap.recent)
    }

    private fun formatRecent(entries: List<Stats.Entry>): CharSequence {
        if (entries.isEmpty()) return getString(R.string.recent_empty)
        val df = DateFormat.getTimeInstance(DateFormat.MEDIUM)
        return entries.take(50).joinToString("\n") { e ->
            val mark = if (e.blocked) "✕" else "✓"
            "$mark  ${df.format(Date(e.timestamp))}  ${e.domain}"
        }
    }

    private fun formatNumber(n: Long): String = "%,d".format(n)

    private fun refreshRemoteLists() {
        binding.btnRefreshLists.isEnabled = false
        binding.btnRefreshLists.text = getString(R.string.action_downloading)
        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) { app.blocklist.downloadRemoteLists() }
            binding.btnRefreshLists.isEnabled = true
            binding.btnRefreshLists.text = getString(R.string.action_refresh_lists)
            binding.blocklistSizeValue.text = formatNumber(app.blocklist.size.toLong())
            val msg = if (result.failures == 0) {
                getString(R.string.toast_lists_updated, result.totalDomains)
            } else {
                getString(R.string.toast_lists_partial, result.failures, result.totalSources)
            }
            snackbar(msg)
        }
    }

    private fun snackbar(text: String) {
        com.google.android.material.snackbar.Snackbar
            .make(binding.root, text, com.google.android.material.snackbar.Snackbar.LENGTH_SHORT)
            .show()
    }
}

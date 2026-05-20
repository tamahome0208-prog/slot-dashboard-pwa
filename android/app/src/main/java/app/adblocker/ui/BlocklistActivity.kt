package app.adblocker.ui

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import app.adblocker.AdBlockerApp
import app.adblocker.R
import app.adblocker.databinding.ActivityBlocklistBinding

class BlocklistActivity : AppCompatActivity() {

    private lateinit var binding: ActivityBlocklistBinding
    private val app: AdBlockerApp by lazy { application as AdBlockerApp }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBlocklistBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        binding.startOnBoot.isChecked = app.settings.startOnBoot
        binding.startOnBoot.setOnCheckedChangeListener { _, v ->
            app.settings.startOnBoot = v
        }

        binding.upstreamDns.setText(app.settings.upstreamDns)
        binding.upstreamDnsFallback.setText(app.settings.upstreamDnsFallback)

        binding.blockedEditor.setText(app.settings.customBlockedDomains.sorted().joinToString("\n"))
        binding.allowedEditor.setText(app.settings.allowedDomains.sorted().joinToString("\n"))

        binding.btnSave.setOnClickListener {
            app.settings.upstreamDns = binding.upstreamDns.text.toString().trim()
                .ifEmpty { "1.1.1.1" }
            app.settings.upstreamDnsFallback = binding.upstreamDnsFallback.text.toString().trim()
                .ifEmpty { "1.0.0.1" }
            app.settings.customBlockedDomains = binding.blockedEditor.text.toString()
                .splitToDomains()
            app.settings.allowedDomains = binding.allowedEditor.text.toString()
                .splitToDomains()
            app.blocklist.refreshUserLists()
            finish()
        }
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    private fun String.splitToDomains(): Set<String> = this.lineSequence()
        .map { it.substringBefore('#').trim().lowercase().trimEnd('.') }
        .filter { it.isNotEmpty() }
        .toSet()
}

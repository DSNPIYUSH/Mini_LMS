package com.subjectbank.app.ui

import android.content.Intent
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.subjectbank.app.R
import com.subjectbank.app.SubjectBankApp
import com.subjectbank.app.api.ApiClient
import com.subjectbank.app.api.SubjectItem
import com.subjectbank.app.databinding.ActivityMainBinding
import com.subjectbank.app.databinding.DialogCreateSubjectBinding
import com.subjectbank.app.databinding.DialogServerUrlBinding
import com.subjectbank.app.ui.adapters.SubjectAdapter
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var subjectAdapter: SubjectAdapter
    private var allSubjects: List<SubjectItem> = emptyList()

    private val loginLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            updateAdminState()
            loadSubjects()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setSupportActionBar(binding.toolbar)

        setupRecyclerView()
        setupListeners()
        updateAdminState()
        checkAuthStatus()
        loadSubjects()
    }

    override fun onResume() {
        super.onResume()
        updateAdminState()
        loadSubjects()
    }

    private fun setupRecyclerView() {
        subjectAdapter = SubjectAdapter(
            subjects = emptyList(),
            isAdmin = SubjectBankApp.instance.prefs.isAdmin,
            onSubjectClick = { subject ->
                openSubjectDetail(subject)
            },
            onDeleteClick = { subject ->
                confirmDeleteSubject(subject)
            }
        )

        binding.rvSubjects.apply {
            layoutManager = LinearLayoutManager(this@MainActivity)
            adapter = subjectAdapter
        }
    }

    private fun setupListeners() {
        binding.swipeRefresh.setOnRefreshListener {
            loadSubjects()
        }

        binding.fabNewSubject.setOnClickListener {
            showCreateSubjectDialog()
        }

        binding.etSearch.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                filterSubjects(s?.toString()?.trim() ?: "")
            }
            override fun afterTextChanged(s: Editable?) {}
        })
    }

    private fun updateAdminState() {
        val isAdmin = SubjectBankApp.instance.prefs.isAdmin
        val username = SubjectBankApp.instance.prefs.username

        binding.fabNewSubject.visibility = if (isAdmin) View.VISIBLE else View.GONE

        if (isAdmin) {
            binding.toolbar.subtitle = "Admin Mode ($username) • MongoDB"
        } else {
            binding.toolbar.subtitle = "Viewer Mode • Direct DB Vault"
        }

        subjectAdapter.updateData(allSubjects, isAdmin)
        invalidateOptionsMenu()
    }

    private fun checkAuthStatus() {
        lifecycleScope.launch {
            try {
                val apiService = ApiClient.getService(this@MainActivity)
                val response = apiService.getAuthStatus()
                if (response.success) {
                    val prefs = SubjectBankApp.instance.prefs
                    prefs.isAdmin = response.isAdmin
                    prefs.username = response.username ?: ""
                    updateAdminState()
                }
            } catch (_: Exception) {
                // Ignore initial connection errors
            }
        }
    }

    private fun loadSubjects() {
        binding.progressBar.visibility = View.VISIBLE
        binding.emptyView.visibility = View.GONE

        lifecycleScope.launch {
            try {
                val apiService = ApiClient.getService(this@MainActivity)
                val response = apiService.getSubjects()
                binding.progressBar.visibility = View.GONE
                binding.swipeRefresh.isRefreshing = false

                if (response.success) {
                    allSubjects = response.subjects ?: emptyList()
                    val query = binding.etSearch.text?.toString()?.trim() ?: ""
                    filterSubjects(query)

                    // Also sync admin status returned by backend
                    if (response.isAdmin != SubjectBankApp.instance.prefs.isAdmin) {
                        SubjectBankApp.instance.prefs.isAdmin = response.isAdmin
                        updateAdminState()
                    }
                } else {
                    Toast.makeText(this@MainActivity, response.error ?: "Failed to load subjects", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                binding.progressBar.visibility = View.GONE
                binding.swipeRefresh.isRefreshing = false
                val msg = e.localizedMessage ?: e.message ?: "Connection failed"
                Toast.makeText(this@MainActivity, "Server Error: $msg\n(Check Server URL in Settings)", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun filterSubjects(query: String) {
        val filtered = if (query.isEmpty()) {
            allSubjects
        } else {
            allSubjects.filter {
                it.name.contains(query, ignoreCase = true) ||
                (it.description ?: "").contains(query, ignoreCase = true)
            }
        }

        subjectAdapter.updateData(filtered, SubjectBankApp.instance.prefs.isAdmin)
        binding.emptyView.visibility = if (filtered.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun openSubjectDetail(subject: SubjectItem) {
        val intent = Intent(this, SubjectDetailActivity::class.java).apply {
            putExtra(SubjectDetailActivity.EXTRA_SUBJECT_NAME, subject.name)
            putStringArrayListExtra(SubjectDetailActivity.EXTRA_FOLDERS, ArrayList(subject.folders ?: emptyList()))
        }
        startActivity(intent)
    }

    private fun showCreateSubjectDialog() {
        val dialogBinding = DialogCreateSubjectBinding.inflate(LayoutInflater.from(this))

        MaterialAlertDialogBuilder(this)
            .setView(dialogBinding.root)
            .setPositiveButton("Create") { _, _ ->
                val name = dialogBinding.etSubjectName.text?.toString()?.trim() ?: ""
                val desc = dialogBinding.etSubjectDesc.text?.toString()?.trim() ?: ""
                if (name.isNotEmpty()) {
                    createSubject(name, desc)
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun createSubject(name: String, desc: String) {
        lifecycleScope.launch {
            try {
                val apiService = ApiClient.getService(this@MainActivity)
                val response = apiService.createSubject(name, desc)
                if (response.success) {
                    Toast.makeText(this@MainActivity, "Subject created!", Toast.LENGTH_SHORT).show()
                    loadSubjects()
                } else {
                    Toast.makeText(this@MainActivity, response.error ?: "Failed to create subject", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "Error: ${e.localizedMessage ?: e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun confirmDeleteSubject(subject: SubjectItem) {
        MaterialAlertDialogBuilder(this)
            .setTitle("Delete Subject")
            .setMessage("Are you sure you want to delete '${subject.name}' and all its folders & documents?")
            .setPositiveButton("Delete") { _, _ ->
                deleteSubject(subject.name)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun deleteSubject(name: String) {
        lifecycleScope.launch {
            try {
                val apiService = ApiClient.getService(this@MainActivity)
                val response = apiService.deleteSubject(name)
                if (response.success) {
                    Toast.makeText(this@MainActivity, "Subject deleted", Toast.LENGTH_SHORT).show()
                    loadSubjects()
                } else {
                    Toast.makeText(this@MainActivity, response.error ?: "Failed to delete", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "Error: ${e.localizedMessage ?: e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun showServerSettingsDialog() {
        val dialogBinding = DialogServerUrlBinding.inflate(LayoutInflater.from(this))
        val currentUrl = SubjectBankApp.instance.prefs.serverUrl
        dialogBinding.etServerUrl.setText(currentUrl)

        dialogBinding.btnPresetEmulator.setOnClickListener {
            dialogBinding.etServerUrl.setText("http://10.0.2.2:8000/")
        }
        dialogBinding.btnPresetLocalhost.setOnClickListener {
            dialogBinding.etServerUrl.setText("http://127.0.0.1:8000/")
        }

        MaterialAlertDialogBuilder(this)
            .setView(dialogBinding.root)
            .setPositiveButton("Save") { _, _ ->
                val newUrl = dialogBinding.etServerUrl.text?.toString()?.trim() ?: ""
                if (newUrl.isNotEmpty()) {
                    SubjectBankApp.instance.prefs.serverUrl = newUrl
                    ApiClient.resetClient()
                    Toast.makeText(this, "Server URL updated!", Toast.LENGTH_SHORT).show()
                    loadSubjects()
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    override fun onCreateOptionsMenu(menu: Menu?): Boolean {
        menuInflater.inflate(R.menu.menu_main, menu)
        val authItem = menu?.findItem(R.id.action_auth)
        if (SubjectBankApp.instance.prefs.isAdmin) {
            authItem?.title = "Log Out"
        } else {
            authItem?.title = "Admin Login"
        }
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_server -> {
                showServerSettingsDialog()
                true
            }
            R.id.action_auth -> {
                if (SubjectBankApp.instance.prefs.isAdmin) {
                    logoutAdmin()
                } else {
                    val intent = Intent(this, LoginActivity::class.java)
                    loginLauncher.launch(intent)
                }
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun logoutAdmin() {
        lifecycleScope.launch {
            try {
                val apiService = ApiClient.getService(this@MainActivity)
                apiService.logout()
            } catch (_: Exception) {}

            SubjectBankApp.instance.prefs.clearAuth()
            ApiClient.resetClient()
            updateAdminState()
            loadSubjects()
            Toast.makeText(this@MainActivity, "Logged out. Back to Viewer Mode.", Toast.LENGTH_SHORT).show()
        }
    }
}

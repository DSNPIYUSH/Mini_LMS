package com.subjectbank.app.ui

import android.content.DialogInterface
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.android.material.button.MaterialButton
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.subjectbank.app.R
import com.subjectbank.app.SubjectBankApp
import com.subjectbank.app.api.ApiClient
import com.subjectbank.app.api.DocumentItem
import com.subjectbank.app.databinding.ActivitySubjectDetailBinding
import com.subjectbank.app.databinding.DialogCreateFolderBinding
import com.subjectbank.app.databinding.DialogUploadDocumentBinding
import com.subjectbank.app.ui.adapters.DocumentAdapter
import com.subjectbank.app.utils.FileUtils
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody

class SubjectDetailActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySubjectDetailBinding
    private lateinit var documentAdapter: DocumentAdapter

    private var subjectName: String = ""
    private var foldersList: MutableList<String> = mutableListOf()
    private var selectedFolder: String? = null
    private var allDocuments: List<DocumentItem> = emptyList()

    private var pendingUploadUri: Uri? = null

    private val filePickerLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null) {
            pendingUploadUri = uri
            showUploadDialog(uri)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySubjectDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)

        subjectName = intent.getStringExtra(EXTRA_SUBJECT_NAME) ?: "Subject"
        val initialFolders = intent.getStringArrayListExtra(EXTRA_FOLDERS) ?: arrayListOf()
        foldersList = initialFolders.toMutableList()

        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = subjectName

        binding.toolbar.setNavigationOnClickListener {
            finish()
        }

        setupRecyclerView()
        setupListeners()
        updateAdminControls()
        loadDocuments()
    }

    override fun onResume() {
        super.onResume()
        updateAdminControls()
    }

    private fun updateAdminControls() {
        val isAdmin = SubjectBankApp.instance.prefs.isAdmin
        binding.fabUpload.visibility = if (isAdmin) View.VISIBLE else View.GONE
        binding.btnAddFolder.visibility = if (isAdmin) View.VISIBLE else View.GONE
        invalidateOptionsMenu()
    }

    private fun setupRecyclerView() {
        documentAdapter = DocumentAdapter(
            documents = emptyList(),
            isAdmin = SubjectBankApp.instance.prefs.isAdmin,
            onDocClick = { doc ->
                openDocumentViewer(doc)
            },
            onDeleteClick = { doc ->
                confirmDeleteDocument(doc)
            }
        )

        binding.rvDocuments.apply {
            layoutManager = LinearLayoutManager(this@SubjectDetailActivity)
            adapter = documentAdapter
        }
    }

    private fun setupListeners() {
        binding.swipeRefresh.setOnRefreshListener {
            loadDocuments()
        }

        binding.btnAddFolder.setOnClickListener {
            showCreateFolderDialog()
        }

        binding.fabUpload.setOnClickListener {
            filePickerLauncher.launch("*/*")
        }
    }

    private fun populateFolderChips() {
        // Keep the "+ Folder" button, recreate chips before it
        binding.folderChipsContainer.removeAllViews()

        // 1. "All Folders" Chip
        val allBtn = MaterialButton(this, null, com.google.android.material.R.attr.materialButtonOutlinedStyle).apply {
            text = getString(R.string.all_folders)
            textSize = 12f
            isSelected = (selectedFolder == null)
            val stroke = if (selectedFolder == null) 2 else 1
            strokeWidth = (stroke * resources.displayMetrics.density).toInt()
            setOnClickListener {
                selectedFolder = null
                filterDocuments()
                populateFolderChips()
            }
        }
        binding.folderChipsContainer.addView(allBtn)

        // 2. Chips for each folder
        foldersList.forEach { folderName ->
            val folderBtn = MaterialButton(this, null, com.google.android.material.R.attr.materialButtonOutlinedStyle).apply {
                text = folderName
                textSize = 12f
                isSelected = (selectedFolder == folderName)
                val stroke = if (selectedFolder == folderName) 2 else 1
                strokeWidth = (stroke * resources.displayMetrics.density).toInt()
                setOnClickListener {
                    selectedFolder = folderName
                    filterDocuments()
                    populateFolderChips()
                }
                setOnLongClickListener {
                    if (SubjectBankApp.instance.prefs.isAdmin) {
                        confirmDeleteFolder(folderName)
                        true
                    } else false
                }
            }
            binding.folderChipsContainer.addView(folderBtn)
        }

        // 3. "+ New Folder" button
        if (SubjectBankApp.instance.prefs.isAdmin) {
            val addFolderBtn = MaterialButton(this, null, com.google.android.material.R.attr.materialButtonTonalStyle).apply {
                text = getString(R.string.new_folder)
                textSize = 12f
                setOnClickListener {
                    showCreateFolderDialog()
                }
            }
            binding.folderChipsContainer.addView(addFolderBtn)
        }
    }

    private fun loadDocuments() {
        binding.progressBar.visibility = View.VISIBLE
        binding.emptyView.visibility = View.GONE

        lifecycleScope.launch {
            try {
                val apiService = ApiClient.getService(this@SubjectDetailActivity)
                val response = apiService.getDocuments(subject = subjectName)
                binding.progressBar.visibility = View.GONE
                binding.swipeRefresh.isRefreshing = false

                if (response.success) {
                    allDocuments = response.documents ?: emptyList()
                    supportActionBar?.subtitle = "${foldersList.size} folders • ${allDocuments.size} docs"
                    populateFolderChips()
                    filterDocuments()
                } else {
                    Toast.makeText(this@SubjectDetailActivity, response.error ?: "Failed to load documents", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                binding.progressBar.visibility = View.GONE
                binding.swipeRefresh.isRefreshing = false
                Toast.makeText(this@SubjectDetailActivity, "Network error: ${e.localizedMessage ?: e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun filterDocuments() {
        val filtered = if (selectedFolder == null) {
            allDocuments
        } else {
            allDocuments.filter { it.folder.equals(selectedFolder, ignoreCase = true) }
        }

        documentAdapter.updateData(filtered, SubjectBankApp.instance.prefs.isAdmin)
        binding.emptyView.visibility = if (filtered.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun openDocumentViewer(doc: DocumentItem) {
        val intent = Intent(this, DocumentViewerActivity::class.java).apply {
            putExtra(DocumentViewerActivity.EXTRA_FILE_ID, doc.id)
            putExtra(DocumentViewerActivity.EXTRA_DOC_TITLE, doc.title)
            putExtra(DocumentViewerActivity.EXTRA_DOC_FILENAME, doc.filename)
            putExtra(DocumentViewerActivity.EXTRA_DOC_CATEGORY, doc.category)
        }
        startActivity(intent)
    }

    private fun showCreateFolderDialog() {
        val dialogBinding = DialogCreateFolderBinding.inflate(LayoutInflater.from(this))

        MaterialAlertDialogBuilder(this)
            .setView(dialogBinding.root)
            .setPositiveButton("Create") { _, _ ->
                val folderName = dialogBinding.etFolderName.text?.toString()?.trim() ?: ""
                if (folderName.isNotEmpty()) {
                    createFolder(folderName)
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun createFolder(folderName: String) {
        lifecycleScope.launch {
            try {
                val apiService = ApiClient.getService(this@SubjectDetailActivity)
                val response = apiService.createFolder(subject = subjectName, folderName = folderName)
                if (response.success) {
                    if (!foldersList.contains(folderName)) {
                        foldersList.add(folderName)
                    }
                    selectedFolder = folderName
                    populateFolderChips()
                    loadDocuments()
                    Toast.makeText(this@SubjectDetailActivity, "Folder created!", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@SubjectDetailActivity, response.error ?: "Failed to create folder", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@SubjectDetailActivity, "Error: ${e.localizedMessage ?: e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun confirmDeleteFolder(folderName: String) {
        MaterialAlertDialogBuilder(this)
            .setTitle("Delete Folder")
            .setMessage("Are you sure you want to delete folder '$folderName' and its documents?")
            .setPositiveButton("Delete") { _, _ ->
                deleteFolder(folderName)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun deleteFolder(folderName: String) {
        lifecycleScope.launch {
            try {
                val apiService = ApiClient.getService(this@SubjectDetailActivity)
                val response = apiService.deleteFolder(subject = subjectName, folderName = folderName)
                if (response.success) {
                    foldersList.remove(folderName)
                    if (selectedFolder == folderName) selectedFolder = null
                    populateFolderChips()
                    loadDocuments()
                    Toast.makeText(this@SubjectDetailActivity, "Folder deleted", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@SubjectDetailActivity, response.error ?: "Failed to delete folder", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@SubjectDetailActivity, "Error: ${e.localizedMessage ?: e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun showUploadDialog(uri: Uri) {
        val dialogBinding = DialogUploadDocumentBinding.inflate(LayoutInflater.from(this))
        val fileName = FileUtils.getFileName(this, uri)
        val fileSize = FileUtils.getFileSize(this, uri)

        dialogBinding.tvPickedFileName.text = fileName
        dialogBinding.tvPickedFileSize.text = FileUtils.formatFileSize(fileSize)
        dialogBinding.etDocTitle.setText(fileName)

        // Setup folder choices
        val choices = if (foldersList.isEmpty()) listOf("General") else foldersList
        val adapter = ArrayAdapter(this, android.R.layout.simple_dropdown_item_1line, choices)
        dialogBinding.actvFolder.setAdapter(adapter)
        val initialFolder = selectedFolder ?: choices.first()
        dialogBinding.actvFolder.setText(initialFolder, false)

        MaterialAlertDialogBuilder(this)
            .setView(dialogBinding.root)
            .setPositiveButton("Upload") { _, _ ->
                val title = dialogBinding.etDocTitle.text?.toString()?.trim() ?: fileName
                val folder = dialogBinding.actvFolder.text?.toString()?.trim() ?: "General"
                val tags = dialogBinding.etDocTags.text?.toString()?.trim() ?: ""
                uploadFile(uri, title, folder, tags)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun uploadFile(uri: Uri, title: String, folder: String, tags: String) {
        binding.progressBar.visibility = View.VISIBLE

        lifecycleScope.launch {
            try {
                val filePart = FileUtils.uriToMultipartBodyPart(this@SubjectDetailActivity, uri, "file")
                val titlePart = title.toRequestBody("text/plain".toMediaTypeOrNull())
                val subjectPart = subjectName.toRequestBody("text/plain".toMediaTypeOrNull())
                val folderPart = folder.toRequestBody("text/plain".toMediaTypeOrNull())
                val tagsPart = tags.toRequestBody("text/plain".toMediaTypeOrNull())

                val apiService = ApiClient.getService(this@SubjectDetailActivity)
                val response = apiService.uploadDocument(filePart, titlePart, subjectPart, folderPart, tagsPart)

                binding.progressBar.visibility = View.GONE
                if (response.success) {
                    Toast.makeText(this@SubjectDetailActivity, "Document uploaded to MongoDB!", Toast.LENGTH_SHORT).show()
                    loadDocuments()
                } else {
                    Toast.makeText(this@SubjectDetailActivity, response.error ?: "Upload failed", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                binding.progressBar.visibility = View.GONE
                Toast.makeText(this@SubjectDetailActivity, "Upload error: ${e.localizedMessage ?: e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun confirmDeleteDocument(doc: DocumentItem) {
        MaterialAlertDialogBuilder(this)
            .setTitle("Delete Document")
            .setMessage("Are you sure you want to delete '${doc.title ?: doc.filename}' from MongoDB?")
            .setPositiveButton("Delete") { _, _ ->
                deleteDocument(doc.id)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun deleteDocument(docId: String) {
        lifecycleScope.launch {
            try {
                val apiService = ApiClient.getService(this@SubjectDetailActivity)
                val response = apiService.deleteDocument(docId)
                if (response.success) {
                    Toast.makeText(this@SubjectDetailActivity, "Document deleted", Toast.LENGTH_SHORT).show()
                    loadDocuments()
                } else {
                    Toast.makeText(this@SubjectDetailActivity, response.error ?: "Failed to delete document", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@SubjectDetailActivity, "Error: ${e.localizedMessage ?: e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onCreateOptionsMenu(menu: Menu?): Boolean {
        menuInflater.inflate(R.menu.menu_subject_detail, menu)
        val deleteItem = menu?.findItem(R.id.action_delete_subject)
        deleteItem?.isVisible = SubjectBankApp.instance.prefs.isAdmin
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_delete_subject -> {
                confirmDeleteSubject()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun confirmDeleteSubject() {
        MaterialAlertDialogBuilder(this)
            .setTitle("Delete Subject")
            .setMessage("Delete '$subjectName' and all documents inside it?")
            .setPositiveButton("Delete") { _, _ ->
                deleteSubject()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun deleteSubject() {
        lifecycleScope.launch {
            try {
                val apiService = ApiClient.getService(this@SubjectDetailActivity)
                val response = apiService.deleteSubject(subjectName)
                if (response.success) {
                    Toast.makeText(this@SubjectDetailActivity, "Subject deleted", Toast.LENGTH_SHORT).show()
                    finish()
                } else {
                    Toast.makeText(this@SubjectDetailActivity, response.error ?: "Failed to delete", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@SubjectDetailActivity, "Error: ${e.localizedMessage ?: e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    companion object {
        const val EXTRA_SUBJECT_NAME = "extra_subject_name"
        const val EXTRA_FOLDERS = "extra_folders"
    }
}

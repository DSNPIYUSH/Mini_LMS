package com.subjectbank.app.ui

import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.PagerSnapHelper
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.subjectbank.app.R
import com.subjectbank.app.SubjectBankApp
import com.subjectbank.app.api.ApiClient
import com.subjectbank.app.api.SlideItem
import com.subjectbank.app.databinding.ActivityDocumentViewerBinding
import com.subjectbank.app.ui.adapters.SlideAdapter
import kotlinx.coroutines.launch

class DocumentViewerActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDocumentViewerBinding
    private var fileId: String = ""
    private var docTitle: String = ""
    private var docFilename: String = ""
    private var docCategory: String = ""
    private var slideList: List<SlideItem> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDocumentViewerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        fileId = intent.getStringExtra(EXTRA_FILE_ID) ?: ""
        docTitle = intent.getStringExtra(EXTRA_DOC_TITLE) ?: ""
        docFilename = intent.getStringExtra(EXTRA_DOC_FILENAME) ?: ""
        docCategory = intent.getStringExtra(EXTRA_DOC_CATEGORY) ?: ""

        supportActionBar?.title = docTitle.ifBlank { docFilename }
        supportActionBar?.subtitle = docFilename

        binding.toolbar.setNavigationOnClickListener {
            finish()
        }

        binding.btnDownloadAnyway.setOnClickListener {
            startDownload()
        }

        setupWebView()
        loadDocumentPreview()
    }

    private fun setupWebView() {
        val settings = binding.webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.loadWithOverviewMode = true
        settings.useWideViewPort = true
        settings.builtInZoomControls = true
        settings.displayZoomControls = false
        binding.webView.setBackgroundColor(0xFFFFFFFF.toInt())
        binding.webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    private fun loadDocumentPreview() {
        if (fileId.isEmpty()) {
            showError("Invalid document identifier.")
            return
        }

        binding.progressBar.visibility = View.VISIBLE
        binding.webView.visibility = View.GONE
        binding.ivImagePreview.visibility = View.GONE
        binding.pptxContainer.visibility = View.GONE
        binding.errorContainer.visibility = View.GONE

        lifecycleScope.launch {
            try {
                val apiService = ApiClient.getService(this@DocumentViewerActivity)
                val response = apiService.getPreviewContent(fileId)
                binding.progressBar.visibility = View.GONE

                if (!response.success && response.type != "docx" && response.type != "pptx") {
                    showError(response.error ?: "Unable to preview document.")
                    return@launch
                }

                when (response.type) {
                    "docx" -> {
                        renderDocxHtml(response.html ?: "<p>No content extracted.</p>")
                    }
                    "pptx" -> {
                        renderPptxSlides(response.slides ?: emptyList())
                    }
                    "image" -> {
                        val serverUrl = SubjectBankApp.instance.prefs.serverUrl
                        val imageUrl = "${serverUrl.trimEnd('/')}/documents/$fileId/view/"
                        renderImage(imageUrl)
                    }
                    "pdf" -> {
                        val serverUrl = SubjectBankApp.instance.prefs.serverUrl
                        val pdfUrl = "${serverUrl.trimEnd('/')}/documents/$fileId/view/"
                        renderPdf(pdfUrl)
                    }
                    else -> {
                        // Fallback check category
                        if (docFilename.endsWith(".pdf", ignoreCase = true)) {
                            val serverUrl = SubjectBankApp.instance.prefs.serverUrl
                            renderPdf("${serverUrl.trimEnd('/')}/documents/$fileId/view/")
                        } else {
                            showError("Preview not supported for this file format.")
                        }
                    }
                }
            } catch (e: Exception) {
                binding.progressBar.visibility = View.GONE
                showError("Error loading preview: ${e.localizedMessage ?: e.message}")
            }
        }
    }

    private fun renderDocxHtml(rawHtml: String) {
        binding.webView.visibility = View.VISIBLE

        // Wrap inside pure white A4 styled paper container
        val styledHtml = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
                <style>
                    body {
                        margin: 0;
                        padding: 20px 16px;
                        background-color: #ffffff !important;
                        color: #0f172a !important;
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                        line-height: 1.6;
                        font-size: 15px;
                        word-wrap: break-word;
                    }
                    h1, h2, h3, h4, h5, h6 {
                        color: #0f172a !important;
                        margin-top: 1.2em;
                        margin-bottom: 0.5em;
                        font-weight: 700;
                    }
                    h1 { font-size: 1.5em; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; }
                    h2 { font-size: 1.3em; }
                    h3 { font-size: 1.15em; }
                    p { margin: 0.8em 0; color: #1e293b !important; }
                    table {
                        border-collapse: collapse;
                        width: 100%;
                        margin: 16px 0;
                        font-size: 13px;
                    }
                    th, td {
                        border: 1px solid #cbd5e1;
                        padding: 8px 10px;
                        text-align: left;
                        color: #0f172a !important;
                    }
                    th { background-color: #f1f5f9; font-weight: 600; }
                    img { max-width: 100%; height: auto; border-radius: 6px; }
                    ul, ol { padding-left: 24px; color: #1e293b !important; }
                    li { margin-bottom: 6px; }
                </style>
            </head>
            <body>
                $rawHtml
            </body>
            </html>
        """.trimIndent()

        binding.webView.loadDataWithBaseURL(null, styledHtml, "text/html", "UTF-8", null)
    }

    private fun renderPptxSlides(slides: List<SlideItem>) {
        if (slides.isEmpty()) {
            showError("No slides found in this presentation.")
            return
        }

        slideList = slides
        binding.pptxContainer.visibility = View.VISIBLE

        val adapter = SlideAdapter(slides)
        val layoutManager = LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false)
        binding.rvSlides.layoutManager = layoutManager
        binding.rvSlides.adapter = adapter

        val snapHelper = PagerSnapHelper()
        binding.rvSlides.onFlingListener = null
        snapHelper.attachToRecyclerView(binding.rvSlides)

        fun updateCounter(pos: Int) {
            binding.tvSlideCounter.text = "Slide ${pos + 1} of ${slides.size}"
            binding.btnPrevSlide.isEnabled = pos > 0
            binding.btnNextSlide.isEnabled = pos < slides.size - 1
        }

        updateCounter(0)

        binding.rvSlides.addOnScrollListener(object : RecyclerView.OnScrollListener() {
            override fun onScrollStateChanged(recyclerView: RecyclerView, newState: Int) {
                if (newState == RecyclerView.SCROLL_STATE_IDLE) {
                    val view = snapHelper.findSnapView(layoutManager)
                    if (view != null) {
                        val pos = layoutManager.getPosition(view)
                        updateCounter(pos)
                    }
                }
            }
        })

        binding.btnPrevSlide.setOnClickListener {
            val view = snapHelper.findSnapView(layoutManager)
            if (view != null) {
                val current = layoutManager.getPosition(view)
                if (current > 0) {
                    binding.rvSlides.smoothScrollToPosition(current - 1)
                }
            }
        }

        binding.btnNextSlide.setOnClickListener {
            val view = snapHelper.findSnapView(layoutManager)
            if (view != null) {
                val current = layoutManager.getPosition(view)
                if (current < slides.size - 1) {
                    binding.rvSlides.smoothScrollToPosition(current + 1)
                }
            }
        }
    }

    private fun renderImage(url: String) {
        binding.ivImagePreview.visibility = View.VISIBLE
        Glide.with(this)
            .load(url)
            .into(binding.ivImagePreview)
    }

    private fun renderPdf(pdfUrl: String) {
        binding.webView.visibility = View.VISIBLE
        // Load PDF directly or via PDF.js viewer
        val viewerUrl = "https://docs.google.com/viewer?embedded=true&url=${Uri.encode(pdfUrl)}"
        binding.webView.loadUrl(pdfUrl)
    }

    private fun showError(message: String) {
        binding.errorContainer.visibility = View.VISIBLE
        binding.tvErrorMessage.text = message
    }

    private fun startDownload() {
        if (fileId.isEmpty()) return
        val serverUrl = SubjectBankApp.instance.prefs.serverUrl
        val downloadUrl = "${serverUrl.trimEnd('/')}/documents/$fileId/download/"

        try {
            val request = DownloadManager.Request(Uri.parse(downloadUrl))
                .setTitle(docTitle.ifBlank { docFilename })
                .setDescription("Downloading academic document from Subject Bank")
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, docFilename)
                .setAllowedOverMetered(true)
                .setAllowedOverRoaming(true)

            val manager = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            manager.enqueue(request)
            Toast.makeText(this, "Download started for $docFilename", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            // Fallback to browser intent
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(downloadUrl))
            startActivity(intent)
        }
    }

    override fun onCreateOptionsMenu(menu: Menu?): Boolean {
        menuInflater.inflate(R.menu.menu_document_viewer, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_download -> {
                startDownload()
                true
            }
            R.id.action_open_browser -> {
                val serverUrl = SubjectBankApp.instance.prefs.serverUrl
                val url = "${serverUrl.trimEnd('/')}/documents/$fileId/view/"
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                startActivity(intent)
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    companion object {
        const val EXTRA_FILE_ID = "extra_file_id"
        const val EXTRA_DOC_TITLE = "extra_doc_title"
        const val EXTRA_DOC_FILENAME = "extra_doc_filename"
        const val EXTRA_DOC_CATEGORY = "extra_doc_category"
    }
}

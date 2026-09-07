package com.subjectbank.app.ui.adapters

import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.subjectbank.app.api.DocumentItem
import com.subjectbank.app.databinding.ItemDocumentBinding

class DocumentAdapter(
    private var documents: List<DocumentItem>,
    private var isAdmin: Boolean,
    private val onDocClick: (DocumentItem) -> Unit,
    private val onDeleteClick: (DocumentItem) -> Unit
) : RecyclerView.Adapter<DocumentAdapter.DocumentViewHolder>() {

    fun updateData(newDocs: List<DocumentItem>, adminState: Boolean) {
        documents = newDocs
        isAdmin = adminState
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): DocumentViewHolder {
        val binding = ItemDocumentBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return DocumentViewHolder(binding)
    }

    override fun onBindViewHolder(holder: DocumentViewHolder, position: Int) {
        holder.bind(documents[position])
    }

    override fun getItemCount(): Int = documents.size

    inner class DocumentViewHolder(private val binding: ItemDocumentBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(doc: DocumentItem) {
            val title = doc.title?.ifBlank { doc.filename } ?: doc.filename
            binding.tvDocTitle.text = title

            val folder = doc.folder?.ifBlank { "General" } ?: "General"
            binding.tvFolderTag.text = "📁 $folder"

            val dateStr = doc.uploadDate?.take(10) ?: "Recently"
            binding.tvDocMeta.text = "${doc.sizeFormatted} • $dateStr"

            // Category badge styling
            val cat = (doc.category ?: "other").lowercase()
            val badgeText = when {
                cat == "pdf" || doc.filename.endsWith(".pdf", ignoreCase = true) -> "PDF"
                cat == "word" || doc.filename.endsWith(".docx", ignoreCase = true) -> "DOCX"
                cat == "presentation" || doc.filename.endsWith(".pptx", ignoreCase = true) -> "PPTX"
                cat == "image" || doc.filename.matches(Regex(".*\\.(png|jpg|jpeg|gif|webp)$", RegexOption.IGNORE_CASE)) -> "IMG"
                else -> "FILE"
            }

            val badgeColor = when (badgeText) {
                "PDF" -> Color.parseColor("#EF4444")
                "DOCX" -> Color.parseColor("#2563EB")
                "PPTX" -> Color.parseColor("#EA580C")
                "IMG" -> Color.parseColor("#10B981")
                else -> Color.parseColor("#64748B")
            }

            binding.tvCategoryBadge.text = badgeText
            val bg = binding.tvCategoryBadge.background?.mutate() as? GradientDrawable
            bg?.setColor(badgeColor)

            binding.btnDeleteDoc.visibility = if (isAdmin) View.VISIBLE else View.GONE
            binding.btnDeleteDoc.setOnClickListener {
                onDeleteClick(doc)
            }

            binding.root.setOnClickListener {
                onDocClick(doc)
            }
        }
    }
}

package com.subjectbank.app.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.subjectbank.app.api.SubjectItem
import com.subjectbank.app.databinding.ItemSubjectBinding

class SubjectAdapter(
    private var subjects: List<SubjectItem>,
    private var isAdmin: Boolean,
    private val onSubjectClick: (SubjectItem) -> Unit,
    private val onDeleteClick: (SubjectItem) -> Unit
) : RecyclerView.Adapter<SubjectAdapter.SubjectViewHolder>() {

    fun updateData(newSubjects: List<SubjectItem>, adminState: Boolean) {
        subjects = newSubjects
        isAdmin = adminState
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): SubjectViewHolder {
        val binding = ItemSubjectBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return SubjectViewHolder(binding)
    }

    override fun onBindViewHolder(holder: SubjectViewHolder, position: Int) {
        holder.bind(subjects[position])
    }

    override fun getItemCount(): Int = subjects.size

    inner class SubjectViewHolder(private val binding: ItemSubjectBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(subject: SubjectItem) {
            binding.tvSubjectName.text = subject.name
            binding.tvSubjectDescription.text = subject.description?.ifBlank { "No description provided." } ?: "No description provided."

            val folderCount = subject.folders?.size ?: 0
            binding.tvFolderCount.text = "📁 $folderCount ${if (folderCount == 1) "folder" else "folders"}"
            binding.tvDocCount.text = "📄 ${subject.docCount} docs (${subject.totalSizeStr})"

            binding.btnDeleteSubject.visibility = if (isAdmin) View.VISIBLE else View.GONE
            binding.btnDeleteSubject.setOnClickListener {
                onDeleteClick(subject)
            }

            binding.root.setOnClickListener {
                onSubjectClick(subject)
            }
        }
    }
}

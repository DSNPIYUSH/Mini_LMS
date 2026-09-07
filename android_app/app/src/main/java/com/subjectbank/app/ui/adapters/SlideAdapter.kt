package com.subjectbank.app.ui.adapters

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.subjectbank.app.api.SlideItem
import com.subjectbank.app.databinding.ItemSlideBinding

class SlideAdapter(
    private var slides: List<SlideItem>
) : RecyclerView.Adapter<SlideAdapter.SlideViewHolder>() {

    fun updateSlides(newSlides: List<SlideItem>) {
        slides = newSlides
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): SlideViewHolder {
        val binding = ItemSlideBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return SlideViewHolder(binding)
    }

    override fun onBindViewHolder(holder: SlideViewHolder, position: Int) {
        holder.bind(slides[position])
    }

    override fun getItemCount(): Int = slides.size

    inner class SlideViewHolder(private val binding: ItemSlideBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(slide: SlideItem) {
            binding.tvSlideTitle.text = slide.title ?: "Slide ${slide.slideNumber}"

            val builder = StringBuilder()
            slide.content?.forEach { paragraphGroup ->
                paragraphGroup.forEach { p ->
                    val indent = "  ".repeat(p.level)
                    builder.append("$indent• ${p.text}\n")
                }
            }

            if (slide.tables?.isNotEmpty() == true) {
                builder.append("\n[Table Data]:\n")
                slide.tables.forEach { row ->
                    builder.append(row.joinToString(" | ")).append("\n")
                }
            }

            binding.tvSlideBody.text = if (builder.isNotBlank()) {
                builder.toString().trim()
            } else {
                "(No text content on this slide)"
            }
        }
    }
}

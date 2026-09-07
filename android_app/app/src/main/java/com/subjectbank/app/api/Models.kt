package com.subjectbank.app.api

import com.google.gson.annotations.SerializedName

data class SubjectItem(
    @SerializedName("name") val name: String,
    @SerializedName("description") val description: String? = null,
    @SerializedName("created_at") val createdAt: String? = null,
    @SerializedName("folders") val folders: List<String>? = emptyList(),
    @SerializedName("doc_count") val docCount: Int = 0,
    @SerializedName("total_size_str") val totalSizeStr: String = "0 B"
)

data class DocumentItem(
    @SerializedName("id") val id: String,
    @SerializedName("filename") val filename: String,
    @SerializedName("title") val title: String? = null,
    @SerializedName("subject") val subject: String? = null,
    @SerializedName("folder") val folder: String? = null,
    @SerializedName("category") val category: String? = null,
    @SerializedName("length") val length: Long = 0,
    @SerializedName("size_formatted") val sizeFormatted: String = "0 B",
    @SerializedName("upload_date") val uploadDate: String? = null,
    @SerializedName("tags") val tags: List<String>? = emptyList()
)

data class Stats(
    @SerializedName("total_documents") val totalDocuments: Int = 0,
    @SerializedName("total_size_formatted") val totalSizeFormatted: String = "0 B",
    @SerializedName("total_subjects") val totalSubjects: Int = 0
)

data class SubjectsResponse(
    @SerializedName("success") val success: Boolean = false,
    @SerializedName("subjects") val subjects: List<SubjectItem>? = emptyList(),
    @SerializedName("stats") val stats: Stats? = null,
    @SerializedName("is_admin") val isAdmin: Boolean = false,
    @SerializedName("error") val error: String? = null
)

data class DocumentsResponse(
    @SerializedName("success") val success: Boolean = false,
    @SerializedName("count") val count: Int = 0,
    @SerializedName("documents") val documents: List<DocumentItem>? = emptyList(),
    @SerializedName("stats") val stats: Stats? = null,
    @SerializedName("is_admin") val isAdmin: Boolean = false,
    @SerializedName("error") val error: String? = null
)

data class AuthResponse(
    @SerializedName("success") val success: Boolean = false,
    @SerializedName("is_authenticated") val isAuthenticated: Boolean = false,
    @SerializedName("is_admin") val isAdmin: Boolean = false,
    @SerializedName("username") val username: String? = null,
    @SerializedName("message") val message: String? = null,
    @SerializedName("error") val error: String? = null
)

data class ApiResponse(
    @SerializedName("success") val success: Boolean = false,
    @SerializedName("message") val message: String? = null,
    @SerializedName("error") val error: String? = null,
    @SerializedName("id") val id: String? = null
)

data class PreviewResponse(
    @SerializedName("success") val success: Boolean = false,
    @SerializedName("type") val type: String? = null,
    @SerializedName("url") val url: String? = null,
    @SerializedName("title") val title: String? = null,
    @SerializedName("filename") val filename: String? = null,
    @SerializedName("html") val html: String? = null,
    @SerializedName("slides") val slides: List<SlideItem>? = emptyList(),
    @SerializedName("download_url") val downloadUrl: String? = null,
    @SerializedName("error") val error: String? = null
)

data class SlideItem(
    @SerializedName("slide_number") val slideNumber: Int = 0,
    @SerializedName("title") val title: String? = null,
    @SerializedName("content") val content: List<List<SlideParagraph>>? = emptyList(),
    @SerializedName("images") val images: List<String>? = emptyList(),
    @SerializedName("tables") val tables: List<List<String>>? = emptyList()
)

data class SlideParagraph(
    @SerializedName("text") val text: String = "",
    @SerializedName("level") val level: Int = 0
)

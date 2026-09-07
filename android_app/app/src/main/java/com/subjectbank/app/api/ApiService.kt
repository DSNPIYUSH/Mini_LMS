package com.subjectbank.app.api

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.*

interface ApiService {

    // Authentication APIs
    @POST("api/auth/login/")
    suspend fun login(@Body credentials: Map<String, String>): AuthResponse

    @GET("api/auth/status/")
    suspend fun getAuthStatus(): AuthResponse

    @POST("api/auth/logout/")
    suspend fun logout(): ApiResponse

    // Subject & Folder APIs
    @GET("api/subjects/")
    suspend fun getSubjects(): SubjectsResponse

    @FormUrlEncoded
    @POST("api/subjects/create/")
    suspend fun createSubject(
        @Field("name") name: String,
        @Field("description") description: String
    ): ApiResponse

    @POST("api/subjects/{subjectName}/delete/")
    suspend fun deleteSubject(
        @Path("subjectName") subjectName: String
    ): ApiResponse

    @FormUrlEncoded
    @POST("api/folders/create/")
    suspend fun createFolder(
        @Field("subject") subject: String,
        @Field("folder_name") folderName: String
    ): ApiResponse

    @FormUrlEncoded
    @POST("api/folders/delete/")
    suspend fun deleteFolder(
        @Field("subject") subject: String,
        @Field("folder_name") folderName: String
    ): ApiResponse

    // Document APIs
    @GET("api/documents/")
    suspend fun getDocuments(
        @Query("q") query: String? = null,
        @Query("subject") subject: String? = null,
        @Query("folder") folder: String? = null,
        @Query("category") category: String? = null
    ): DocumentsResponse

    @Multipart
    @POST("api/documents/upload/")
    suspend fun uploadDocument(
        @Part file: MultipartBody.Part,
        @Part("title") title: RequestBody,
        @Part("subject") subject: RequestBody,
        @Part("folder") folder: RequestBody,
        @Part("tags") tags: RequestBody
    ): ApiResponse

    @POST("api/documents/{fileId}/delete/")
    suspend fun deleteDocument(
        @Path("fileId") fileId: String
    ): ApiResponse

    @GET("api/documents/{fileId}/preview-content/")
    suspend fun getPreviewContent(
        @Path("fileId") fileId: String
    ): PreviewResponse
}

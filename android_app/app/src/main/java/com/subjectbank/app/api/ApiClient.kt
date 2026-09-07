package com.subjectbank.app.api

import android.content.Context
import com.subjectbank.app.utils.PreferenceHelper
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

class MemoryCookieJar : CookieJar {
    private val cookieStore = mutableMapOf<String, MutableList<Cookie>>()

    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        val host = url.host
        val existing = cookieStore.getOrPut(host) { mutableListOf() }
        cookies.forEach { cookie ->
            existing.removeAll { it.name == cookie.name }
            existing.add(cookie)
        }
    }

    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        return cookieStore[url.host] ?: emptyList()
    }

    fun clear() {
        cookieStore.clear()
    }
}

object ApiClient {

    private var retrofit: Retrofit? = null
    private var apiService: ApiService? = null
    private var currentBaseUrl: String? = null
    val cookieJar = MemoryCookieJar()

    fun getService(context: Context): ApiService {
        val prefs = PreferenceHelper(context)
        val baseUrl = prefs.serverUrl

        if (apiService == null || currentBaseUrl != baseUrl) {
            currentBaseUrl = baseUrl

            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }

            val okHttpClient = OkHttpClient.Builder()
                .cookieJar(cookieJar)
                .addInterceptor(logging)
                .connectTimeout(20, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .build()

            retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()

            apiService = retrofit?.create(ApiService::class.java)
        }

        return apiService!!
    }

    fun resetClient() {
        retrofit = null
        apiService = null
        currentBaseUrl = null
        cookieJar.clear()
    }
}

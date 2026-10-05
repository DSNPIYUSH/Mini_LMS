package com.subjectbank.app.utils

import android.content.Context
import android.content.SharedPreferences

class PreferenceHelper(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)

    var serverUrl: String
        get() {
            var url = prefs.getString(KEY_SERVER_URL, DEFAULT_SERVER_URL) ?: DEFAULT_SERVER_URL
            if (!url.endsWith("/")) {
                url += "/"
            }
            return url
        }
        set(value) {
            var url = value.trim()
            if (!url.endsWith("/")) {
                url += "/"
            }
            prefs.edit().putString(KEY_SERVER_URL, url).apply()
        }

    var isAdmin: Boolean
        get() = prefs.getBoolean(KEY_IS_ADMIN, false)
        set(value) = prefs.edit().putBoolean(KEY_IS_ADMIN, value).apply()

    var isAuthenticated: Boolean
        get() = prefs.getBoolean(KEY_IS_AUTHENTICATED, false)
        set(value) = prefs.edit().putBoolean(KEY_IS_AUTHENTICATED, value).apply()

    var role: String
        get() = prefs.getString(KEY_ROLE, ROLE_USER) ?: ROLE_USER
        set(value) = prefs.edit().putString(KEY_ROLE, value).apply()

    var username: String
        get() = prefs.getString(KEY_USERNAME, "") ?: ""
        set(value) = prefs.edit().putString(KEY_USERNAME, value).apply()

    fun clearAuth() {
        prefs.edit()
            .putBoolean(KEY_IS_ADMIN, false)
            .putBoolean(KEY_IS_AUTHENTICATED, false)
            .putString(KEY_ROLE, ROLE_USER)
            .putString(KEY_USERNAME, "")
            .apply()
    }

    companion object {
        private const val PREF_NAME = "subject_bank_prefs"
        private const val KEY_SERVER_URL = "server_url"
        private const val KEY_IS_ADMIN = "is_admin"
        private const val KEY_IS_AUTHENTICATED = "is_authenticated"
        private const val KEY_ROLE = "role"
        private const val KEY_USERNAME = "username"
        const val ROLE_ADMIN = "admin"
        const val ROLE_USER = "user"
        const val DEFAULT_SERVER_URL = "http://10.0.2.2:8000/"
    }
}

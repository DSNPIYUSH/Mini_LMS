package com.subjectbank.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.subjectbank.app.SubjectBankApp
import com.subjectbank.app.api.ApiClient
import com.subjectbank.app.databinding.ActivityLoginBinding
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.toolbar.setNavigationOnClickListener {
            finish()
        }

        binding.btnLogin.setOnClickListener {
            performLogin()
        }
    }

    private fun performLogin() {
        val username = binding.etUsername.text?.toString()?.trim() ?: ""
        val password = binding.etPassword.text?.toString()?.trim() ?: ""

        if (username.isEmpty()) {
            binding.tilUsername.error = "Username is required"
            return
        } else {
            binding.tilUsername.error = null
        }

        if (password.isEmpty()) {
            binding.tilPassword.error = "Password is required"
            return
        } else {
            binding.tilPassword.error = null
        }

        binding.loginProgress.visibility = View.VISIBLE
        binding.btnLogin.isEnabled = false
        binding.tvLoginError.visibility = View.GONE

        lifecycleScope.launch {
            try {
                val apiService = ApiClient.getService(this@LoginActivity)
                val credentials = mapOf("username" to username, "password" to password)
                val response = apiService.login(credentials)

                binding.loginProgress.visibility = View.GONE
                binding.btnLogin.isEnabled = true

                if (response.success) {
                    val prefs = SubjectBankApp.instance.prefs
                    prefs.isAdmin = response.isAdmin
                    prefs.isAuthenticated = true
                    prefs.role = response.role ?: if (response.isAdmin) "admin" else "user"
                    prefs.username = response.username ?: username

                    val label = if (response.isAdmin) "Admin" else "User"
                    Toast.makeText(this@LoginActivity, "Logged in as $label!", Toast.LENGTH_SHORT).show()
                    setResult(RESULT_OK)
                    finish()
                } else {
                    binding.tvLoginError.text = response.error ?: "Invalid credentials"
                    binding.tvLoginError.visibility = View.VISIBLE
                }
            } catch (e: Exception) {
                binding.loginProgress.visibility = View.GONE
                binding.btnLogin.isEnabled = true
                binding.tvLoginError.text = "Connection error: ${e.localizedMessage ?: e.message}"
                binding.tvLoginError.visibility = View.VISIBLE
            }
        }
    }
}

package com.subjectbank.app

import android.app.Application
import com.subjectbank.app.utils.PreferenceHelper

class SubjectBankApp : Application() {

    lateinit var prefs: PreferenceHelper
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        prefs = PreferenceHelper(this)
    }

    companion object {
        lateinit var instance: SubjectBankApp
            private set
    }
}

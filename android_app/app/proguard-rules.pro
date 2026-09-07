# ProGuard / R8 rules for Subject Bank Android App
-keepattributes *Annotation*
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}
-keep class com.subjectbank.app.api.** { *; }

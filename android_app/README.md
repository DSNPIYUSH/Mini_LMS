# Subject Bank - Android Application

This directory contains the complete native Android project for the **Subject Bank** platform, built with **Kotlin**, **Material 3**, **Retrofit**, and **OkHttp**.

---

## 📱 Features

1. **Subject-First & Folder-First Navigation**:
   - Browse academic subjects with folder count, document count, and storage size metrics.
   - Tap any subject to access its folders and documents with interactive filter chips.
   - Real-time search bar to find subjects and documents.

2. **In-App Pure White Document Viewer**:
   - **Word (`.docx`)**: Converted into clean HTML and displayed on a white reading surface.
   - **PowerPoint (`.pptx`)**: Rendered as an interactive slide carousel with slide counter, next/previous controls, and content bullet points.
   - **PDF & Images**: High-definition native viewing.
   - Download or share files directly to Android's Download manager.

3. **Admin Controls & Management**:
   - Secure Admin Login dialog with persistent session cookie handling.
   - Create new Subjects and Folders on the fly.
   - Upload documents directly from your Android phone using Android's file picker (`ACTION_GET_CONTENT`).
   - Delete documents, folders, or subjects with safety confirmation prompts.

4. **Configurable Server Address**:
   - Built-in **Server Settings** dialog to easily switch between Android Emulator (`http://10.0.2.2:8000`), local Wi-Fi IP (`http://192.168.X.X:8000`), or a production domain without modifying code.

---

## 🚀 How to Run in Android Studio

### Prerequisites
- [Android Studio](https://developer.android.com/studio) (Hedgehog, Iguana, Jellyfish, Koala, Ladybug or newer)
- Android SDK 24+ (Android 7.0 to 14+)

### Steps
1. **Open the Project**:
   - Launch Android Studio.
   - Select **Open...** and browse to `subject bank/android_app`.
   - Wait for Gradle sync to complete.

2. **Ensure the Django Backend is Running**:
   - In the root `subject bank` folder, start the server:
     ```powershell
     .\venv\Scripts\python manage.py runserver 0.0.0.0:8000
     ```
     *(Note: Using `0.0.0.0:8000` allows both emulators and phones on your Wi-Fi to connect!)*

3. **Run on Emulator or Physical Device**:
   - In Android Studio, click the green **Run** button (or press `Shift + F10`).
   - **On Android Emulator**: The default server URL `http://10.0.2.2:8000/` will connect directly to your PC's localhost.
   - **On a Physical Android Device**:
     1. Connect your phone to the same Wi-Fi network as your PC.
     2. Find your PC's local IP address (run `ipconfig` in PowerShell, e.g. `192.168.1.50`).
     3. Open the app on your phone, tap the **Settings icon (⚙️)** in the top right, and set the server URL to:
        ```
        http://192.168.1.50:8000/
        ```
     4. Tap **Save**. The app will immediately fetch and display your subjects!

---

## 🌐 Instant Testing via Progressive Web App (PWA)

You can also install and run the app directly on your Android phone **right now without building an APK**:
1. Run the Django server on your PC:
   ```powershell
   .\venv\Scripts\python manage.py runserver 0.0.0.0:8000
   ```
2. On your Android phone, open **Google Chrome** and visit:
   ```
   http://<YOUR_PC_IP>:8000/
   ```
3. Chrome will prompt **"Add Subject Bank to Home screen"** or tap Chrome's three dots menu $\to$ **"Install app"**.
4. The app will install onto your Android home screen with its own icon and launch full-screen like a native app.

# 📚 Subject Bank - Centralized Course Materials Repository

https://mini-lms-sdx6.onrender.com/

A lightweight document management platform where files (PDFs, PPTs, Word documents, images) are stored **directly inside MongoDB using GridFS**, structured hierarchically by **Subject → Folders → Documents**.

The platform features strict role-based access control (RBAC): **Administrators** manage courses, structure folders, and upload materials, while **Viewers** can browse and read documents directly inside their browser or mobile app without downloading files locally.

Most of the android studio is done by using vibe coding
---

## 🌟 Key Features

1. **Hierarchical Academic Structure**:
   - Organized intuitively for students and faculty: **Subject** (e.g., *Cloud Computing*) → **Folders** (e.g., *Syllabus*, *Unit 1 - Architecture*, *Lab Manuals*) → **Documents**.
   - Built-in breadcrumb navigation (`All Subjects > Cloud Computing > Unit 1`).
2. **Role-Based Access Control (RBAC)**:
   - **Viewer (Public)**: Browse subjects, navigate folders, search materials, and view documents live. Administrative actions (upload, edit, delete) are hidden, and unauthorized API requests return `403 Forbidden`.
   - **Administrator**: Dedicated login portal (`/login/`) to create subjects, manage folders, upload documents, and delete obsolete materials.
3. **Universal In-Browser Live Previews (Zero Downloads Required)**:
   - **Word Documents (`.docx`)**: Formatted as clean A4 reading pages with support for tables, images, and typography.
   - **PowerPoint Presentations (`.pptx`)**: Interactive presentation canvas with slide thumbnails, next/previous buttons, and keyboard controls (`←`, `→`).
   - **PDFs & Images**: High-performance embedded native viewers.
4. **Database-Level Storage with MongoDB GridFS**:
   - Completely eliminates disk file storage dependencies. Files are split into 255 KB binary chunks and stored directly across MongoDB collections (`fs.files` and `fs.chunks`).

---

## 🛠️ Tech Stack

- **Backend**: Python, Django / Django REST Framework
- **Database**: MongoDB (via GridFS for binary assets)
- **Mobile Client**: Native Android (Kotlin, AndroidX, Material 3, Coroutines)
- **Networking**: Retrofit 2, OkHttp 3 (with session-based auth handling)
- **Web Frontend**: HTML5, Modern CSS / Tailwind, JavaScript, PWA Manifest

---

## 🔐 Configuration & Environment

Create a `.env` file in the project root:

```env
DEBUG=True
SECRET_KEY=your_django_secret_key
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=subject_bank
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_secure_password
```

Apply database migrations and initialize credentials:

```bash
# Windows (PowerShell)
.\venv\Scripts\activate
python manage.py migrate
python set_admin.py
```

*Or create a superuser interactively:*
```bash
python manage.py createsuperuser
```

---

## 🏃 Running the Application

### Option 1: Quick Launcher (Windows)
Double-click **`run_server.bat`** in the project root. It will boot the server and launch `http://127.0.0.1:8000/` automatically.

### Option 2: Terminal / CLI
```bash
# Activate your virtual environment and start the development server
python manage.py runserver 0.0.0.0:8000
```
*(Binding to `0.0.0.0` allows devices on your local Wi-Fi, such as your physical Android phone, to connect.)*

---

## 📱 Native Android Application

The project includes a companion native Android client located in the [`android_app/`](android_app/) directory:

- **UI & Architecture**: Built with Kotlin and Google Material 3 components.
- **Networking & Auth**: Retrofit 2 paired with OkHttp 3, maintaining persistent Django session cookies (`sessionid`, `csrftoken`).
- **File Uploads**: Modern Android Activity Result API (`ActivityResultContracts.GetContent`) for streaming uploads to the backend.
- **In-App Previews**: Dedicated viewer activities for Word documents, slide decks, PDFs, and graphics.
- **Flexible Endpoints**: In-app endpoint configuration dialog to toggle seamlessly between:
  - Android Emulator: `http://10.0.2.2:8000`
  - Physical Device (LAN): `http://<YOUR_LOCAL_IP>:8000`

### Setup in Android Studio
1. Open Android Studio → **Open** → Select the `android_app` directory.
2. Ensure `android:usesCleartextTraffic="true"` is present in `AndroidManifest.xml` for local HTTP testing.
3. Sync Gradle and run the project on an emulator or connected physical device.

> **PWA Alternative**: You can also use the web app as a Progressive Web App on mobile by navigating to `http://<YOUR_LOCAL_IP>:8000/` in Chrome and selecting **Add to Home Screen**.

---

## 🧪 Automated Testing

To test authentication restrictions, API responses, GridFS uploads, live preview endpoints, and document deletion:

```bash
python test_system.py
```

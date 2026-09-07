# 📚 Subject Bank - Centralized Course Materials Repository

A document management web application where files (PDFs, PPTs, Word documents, images) are stored **directly inside MongoDB using GridFS**, organized hierarchically by **Subject → Folders → Documents**.

Features role-based access control where **only the Administrator can create folders and upload files**, while **viewers can browse and read documents live in their browser without downloading**.

---

## 🌟 Key Features

1. **Subject & Folder First Architecture**:
   - Organized intuitively for students and teachers: **Subject** (e.g. *Cloud Computing*) → **Folders** (e.g. *Syllabus*, *Unit 1 - Architecture*, *Lab Manuals*) → **Documents**.
   - Breadcrumb navigation (`All Subjects > Cloud Computing > Unit 1`).
2. **Role-Based Access Control**:
   - **Viewer (Public)**: Can browse subjects, open folders, search, and view all documents. No upload or delete buttons are visible, and API calls from non-admins are rejected (`403 Forbidden`).
   - **Administrator**: Dedicated login portal (`/login/`) to create new subjects, add folders, upload documents into specific folders, and delete materials.
3. **Universal In-Browser Live Viewer (Zero Downloads Needed)**:
   - **Word Documents (`.docx`)**: Rendered as **pure white A4 document pages** with high-contrast dark text, tables, and images.
   - **PowerPoint Slides (`.pptx`)**: Interactive presentation canvas with slide thumbnails, next/prev controls, and keyboard navigation (`←`, `→`).
   - **PDFs & Images**: Embedded PDF viewer and image viewer.
4. **Direct Database Storage with MongoDB GridFS**:
   - Zero local folder or disk drive storage. Files are broken into 255 KB chunks stored directly in MongoDB (`fs.files` and `fs.chunks`).

---

## 🔐 Admin Credentials

- **Login URL**: [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)
- **Username**: `admin`
- **Password**: `admin123`

---

## 🏃 How to Run the Application

### Option 1: 1-Click Launcher (Windows)
Double-click **`run_server.bat`** in the project folder. It will launch the server and open your browser automatically at `http://127.0.0.1:8000/`.

### Option 2: Terminal
```powershell
cd "c:\Users\dsnpi\OneDrive\Desktop\subject bank"
.\venv\Scripts\python manage.py runserver 127.0.0.1:8000
```

---

## 📱 Android Application

The project includes a complete native Android application in the [`android_app/`](android_app/) directory:
- **Language & Framework**: Kotlin, AndroidX, Google Material 3.
- **Networking**: Retrofit 2 + OkHttp 3 with persistent session cookies for Django authentication.
- **In-App Document Viewer**: Pure white reading mode for Word (`.docx`), interactive slide carousel for PowerPoint (`.pptx`), and embedded viewers for PDF & Images.
- **Admin Management**: Mobile login, file picker (`ACTION_GET_CONTENT`) for uploading docs to MongoDB, and folder/subject creation.
- **Custom Server Address**: In-app settings dialog to easily switch between Android Emulator (`10.0.2.2:8000`) or local Wi-Fi IP (`192.168.X.X:8000`).

To open in Android Studio:
1. Open Android Studio → **Open** → Select `subject bank/android_app`.
2. Run on emulator or connected phone!

You can also install the **Progressive Web App (PWA)** immediately on any Android phone by visiting `http://<your-pc-ip>:8000/` in Chrome and tapping **Add to Home screen**.

---

## 🧪 Automated Tests

To test the entire backend pipeline (viewer restrictions, mobile JSON auth, admin login, folder creation, uploads, live viewing, and deletion):

```powershell
.\venv\Scripts\python test_system.py
```


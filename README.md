# 📚 Subject Bank - Centralized Course Materials Repository

https://mini-lms-sdx6.onrender.com/

A lightweight document management platform where files (PDFs, PPTs, Word documents, images) are stored **directly inside MongoDB using GridFS**, structured hierarchically by **Subject → Folders → Documents**.

The platform features strict role-based access control (RBAC) with **password-only authentication (no two-factor/OTP step)**. There is exactly **one administrator profile**, which manages courses, structure folders, uploads materials, and creates user accounts. Every other account is a **regular user** that can sign in on its own login page and browse, preview, and download materials with **zero administrative control**. **Login is required to view anything** — anonymous visitors are redirected to the login page.

Most of the android studio is done by using vibe coding
---

## 🌟 Key Features

1. **Hierarchical Academic Structure**:
   - Organized intuitively for students and faculty: **Subject** (e.g., *Cloud Computing*) → **Folders** (e.g., *Syllabus*, *Unit 1 - Architecture*, *Lab Manuals*) → **Documents**.
   - Built-in breadcrumb navigation (`All Subjects > Cloud Computing > Unit 1`).
2. **Role-Based Access Control (RBAC)**:
   - **Administrator (single profile)**: Dedicated login portal at `/login/` (staff accounts only). Creates subjects, manages folders, uploads documents, deletes obsolete materials, and **creates/deletes regular user accounts** from the **👥 Users** button in the header.
   - **Regular User**: Dedicated login portal at `/user-login/` (non-staff accounts only). Browse subjects, navigate folders, search materials, and view documents live in the browser or mobile app. No admin controls are rendered and every admin endpoint returns `403 Forbidden`.
   - **Anonymous**: Redirected to `/user-login/` from the homepage and blocked from all content and API endpoints (`403`). Only `/health/` stays public.
   - **Password-only**: Two-factor authentication has been removed — one username + password POST signs you straight in.
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

> SMS/Twilio/Fast2SMS variables (`ADMIN_PHONE_NUMBER`, `SMS_PROVIDER`, `TWILIO_*`, `FAST2SMS_API_KEY`) are no longer used — two-factor authentication has been removed.

Apply database migrations and initialize credentials:

```bash
# Windows (PowerShell)
.\venv\Scripts\activate
python manage.py migrate
python set_admin.py
```

`set_admin.py` provisions **exactly one** administrator from `ADMIN_USERNAME` / `ADMIN_PASSWORD` and automatically **demotes any other staff account** to a regular user, so the admin profile stays unique.

*Or create a superuser interactively:*
```bash
python manage.py createsuperuser
```

### Creating User Accounts

Regular user accounts are **created from the web UI** by the administrator:

1. Sign in at `/login/`.
2. Click the **👥 Users** button in the header.
3. Enter a username and password, then click **Create User**.

Each account can also be disabled/enabled, have its password reset, or be deleted. New accounts are always regular users — they can never be granted admin rights, and the administrator profile itself cannot be deleted or deactivated.

Regular users sign in at **`/user-login/`**.

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

To test anonymous restrictions, admin vs. user permissions, single-admin protection, user management, API responses, GridFS uploads, live preview endpoints, and document deletion:

```bash
python test_system.py
```

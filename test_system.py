import os
import io
import json
import django
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'subject_bank.settings')
django.setup()

from django.test import Client
from documents import mongo
from docx import Document

ADMIN_USER = 'testadmin'
ADMIN_PASS = 'testpass123'
USER_NAME = 'teststudent'
USER_PASS = 'studentpass123'


def run_tests():
    print("=== STARTING ROLE-BASED ACCESS (NO 2FA), SUBJECT HIERARCHY & AI TUTOR TESTS ===")

    from django.contrib.auth import get_user_model
    User = get_user_model()

    anonymous_client = Client()
    admin_client = Client()
    user_client = Client()

    # Fresh fixtures
    User.objects.filter(username__in=[ADMIN_USER, USER_NAME]).delete()

    test_admin = User.objects.create_superuser(ADMIN_USER, 'test@example.com', ADMIN_PASS)
    test_user = User.objects.create_user(USER_NAME, 'student@example.com', USER_PASS)
    test_user.is_staff = False
    test_user.is_superuser = False
    test_user.save()

    # 1. Anonymous visitors are blocked everywhere
    print("\n--- 1. Testing Anonymous (Unauthenticated) Restrictions ---")
    r_home = anonymous_client.get('/')
    assert r_home.status_code == 302, f"Expected redirect to login, got {r_home.status_code}"
    assert '/user-login/' in r_home.url, f"Expected redirect to user login, got {r_home.url}"

    r_login_page = anonymous_client.get(r_home.url)
    assert r_login_page.status_code == 200
    assert 'User Login' in r_login_page.content.decode('utf-8')
    assert 'name="next" value="/"' in r_login_page.content.decode('utf-8')
    print("  [OK] Login page preserves the requested page for post-login redirect")

    r_subjects_fail = anonymous_client.get('/api/subjects/')
    assert r_subjects_fail.status_code == 403
    print("  [OK] Anonymous visitors redirected from homepage and blocked from /api/subjects/")

    r_docs_fail = anonymous_client.get('/api/documents/')
    assert r_docs_fail.status_code == 403
    print("  [OK] Anonymous visitors blocked from /api/documents/")

    r_upload_fail = anonymous_client.post('/api/documents/upload/', {'title': 'Hacker Note'})
    assert r_upload_fail.status_code == 403
    assert r_upload_fail.json()['success'] is False
    print("  [OK] Anonymous visitor blocked from uploading documents (403 Forbidden)")

    r_create_subj_fail = anonymous_client.post('/api/subjects/create/', {'name': 'Hacker Subject'})
    assert r_create_subj_fail.status_code == 403
    print("  [OK] Anonymous visitor blocked from creating subjects (403 Forbidden)")

    r_create_folder_fail = anonymous_client.post('/api/folders/create/', {'subject': 'Cloud Computing', 'folder_name': 'Hacker Folder'})
    assert r_create_folder_fail.status_code == 403
    print("  [OK] Anonymous visitor blocked from creating folders (403 Forbidden)")

    r_ai_fail = anonymous_client.get('/api/ai/status/')
    assert r_ai_fail.status_code == 403
    print("  [OK] Anonymous visitor blocked from the AI tutor API (403 Forbidden)")

    r_users_fail = anonymous_client.get('/api/users/')
    assert r_users_fail.status_code == 403
    print("  [OK] Anonymous visitor blocked from user management (403 Forbidden)")

    # 2. No two-factor step: one POST logs the admin straight in
    print("\n--- 2. Testing Admin Login (single step, no OTP) ---")
    login_res = admin_client.post('/login/', {'username': ADMIN_USER, 'password': ADMIN_PASS})
    assert login_res.status_code == 302, f"Expected redirect after login, got {login_res.status_code}"
    assert login_res.url == '/', f"Expected redirect to '/', got {login_res.url}"
    assert '_auth_user_id' in admin_client.session
    assert 'otp_code' not in admin_client.session
    print("  [OK] Admin authenticated with a single password step (no OTP / no 2FA)")

    r_otp_route = admin_client.get('/verify-otp/')
    assert r_otp_route.status_code == 404
    print("  [OK] /verify-otp/ route no longer exists (404)")

    r_admin_home = admin_client.get('/')
    assert r_admin_home.status_code == 200
    admin_html = r_admin_home.content.decode('utf-8')
    assert 'Logout' in admin_html
    assert 'openUserManagerModal' in admin_html
    assert 'New Subject' in admin_html
    print("  [OK] Admin console renders admin-only controls + user manager")

    r_bad_login = Client().post('/login/', {'username': ADMIN_USER, 'password': 'wrong-pass'})
    assert r_bad_login.status_code == 200
    assert 'Invalid username or password' in r_bad_login.content.decode('utf-8')
    print("  [OK] Bad admin password rejected without OTP step")

    # 3. Regular user login: allowed on the user page, refused on the admin page
    print("\n--- 3. Testing User Login (no admin control) ---")
    r_user_on_admin_page = Client().post('/login/', {'username': USER_NAME, 'password': USER_PASS})
    assert r_user_on_admin_page.status_code == 200
    assert 'not an administrator' in r_user_on_admin_page.content.decode('utf-8')
    print("  [OK] Regular user cannot sign in through the admin login page")

    r_admin_on_user_page = Client().post('/user-login/', {'username': ADMIN_USER, 'password': ADMIN_PASS})
    assert r_admin_on_user_page.status_code == 200
    assert 'must sign in from the admin login page' in r_admin_on_user_page.content.decode('utf-8')
    print("  [OK] Admin cannot sign in through the user login page")

    user_login_res = user_client.post('/user-login/', {'username': USER_NAME, 'password': USER_PASS})
    assert user_login_res.status_code == 302
    assert user_login_res.url == '/'

    open_redirect = Client().post('/user-login/', {'username': USER_NAME, 'password': USER_PASS,
                                                  'next': 'https://evil.example.com/steal'})
    assert open_redirect.status_code == 302
    assert open_redirect.url == '/'
    print("  [OK] Off-site 'next' redirect targets are ignored")

    r_user_home = user_client.get('/')
    assert r_user_home.status_code == 200
    user_html = r_user_home.content.decode('utf-8')
    assert 'Logout' in user_html
    assert 'openUserManagerModal' not in user_html
    assert 'openCreateSubjectModal()' not in user_html
    assert 'openUploadModal()' not in user_html
    print("  [OK] User console renders with NO admin controls (no subject/folder/upload/user manager)")

    r_user_subjects = user_client.post('/api/subjects/create/', {'name': 'User Subject'})
    assert r_user_subjects.status_code == 403
    r_user_upload = user_client.post('/api/documents/upload/', {'title': 'User Note'})
    assert r_user_upload.status_code == 403
    r_user_folder = user_client.post('/api/folders/create/', {'subject': 'X', 'folder_name': 'Y'})
    assert r_user_folder.status_code == 403
    r_user_users = user_client.get('/api/users/')
    assert r_user_users.status_code == 403
    print("  [OK] User blocked from subject/folder creation, uploads and user management (403 Forbidden)")

    # 4. Admin creates user accounts from the web UI
    print("\n--- 4. Testing Admin User Management ---")
    r_list = admin_client.get('/api/users/')
    assert r_list.status_code == 200
    listed = r_list.json()['users']
    assert any(u['username'] == ADMIN_USER and u['is_admin'] for u in listed)
    assert any(u['username'] == USER_NAME and not u['is_admin'] for u in listed)
    print("  [OK] Admin listed accounts and roles correctly")

    new_user_name = 'testcreated'
    User.objects.filter(username=new_user_name).delete()
    r_create = admin_client.post('/api/users/create/', {'username': new_user_name, 'password': 'createdpass123'})
    assert r_create.status_code == 201, f"Expected 201, got {r_create.status_code}: {r_create.content}"
    created = r_create.json()['user']
    assert created['is_admin'] is False
    print("  [OK] Admin created a regular (non-admin) user account")

    r_dup = admin_client.post('/api/users/create/', {'username': new_user_name, 'password': 'createdpass123'})
    assert r_dup.status_code == 400
    print("  [OK] Duplicate username rejected")

    r_weak = admin_client.post('/api/users/create/', {'username': 'weakling', 'password': '123'})
    assert r_weak.status_code == 400
    print("  [OK] Weak password rejected by Django password validation")

    new_client = Client()
    r_new_login = new_client.post('/user-login/', {'username': new_user_name, 'password': 'createdpass123'})
    assert r_new_login.status_code == 302
    print("  [OK] Newly created user can log in on the user login page")

    created_id = created['id']

    r_toggle = admin_client.post(f'/api/users/{created_id}/toggle-active/')
    assert r_toggle.status_code == 200
    disabled_client = Client()
    r_disabled_login = disabled_client.post('/user-login/', {'username': new_user_name, 'password': 'createdpass123'})
    assert r_disabled_login.status_code == 200
    assert 'Invalid username or password' in r_disabled_login.content.decode('utf-8')
    admin_client.post(f'/api/users/{created_id}/toggle-active/')
    print("  [OK] Admin disabled/re-enabled the account and login was blocked while disabled")

    r_reset = admin_client.post(f'/api/users/{created_id}/password/', json.dumps({'password': 'newpass456'}),
                                content_type='application/json')
    assert r_reset.status_code == 200
    reset_client = Client()
    assert reset_client.post('/user-login/', {'username': new_user_name, 'password': 'newpass456'}).status_code == 302
    print("  [OK] Admin reset the user password and the new one works")

    # 5. Single admin profile is protected
    print("\n--- 5. Testing Single-Admin Protection ---")
    admin_id = next(u['id'] for u in admin_client.get('/api/users/').json()['users'] if u['is_admin'])
    r_del_admin = admin_client.post(f'/api/users/{admin_id}/delete/')
    assert r_del_admin.status_code == 400
    assert 'administrator profile cannot be removed' in r_del_admin.json()['error']
    print("  [OK] Administrator profile cannot be deleted")

    r_toggle_admin = admin_client.post(f'/api/users/{admin_id}/toggle-active/')
    assert r_toggle_admin.status_code == 400
    assert 'cannot be deactivated' in r_toggle_admin.json()['error']
    print("  [OK] Administrator profile cannot be deactivated")

    r_del_self = admin_client.post(f'/api/users/{admin_id}/delete/')
    assert r_del_self.status_code == 400
    assert User.objects.filter(username=ADMIN_USER).exists()
    print("  [OK] Administrator profile survives every delete attempt")

    r_del_user = admin_client.post(f'/api/users/{created_id}/delete/')
    assert r_del_user.status_code == 200
    assert not User.objects.filter(username=new_user_name).exists()
    print("  [OK] Admin deleted a regular user account")

    r_staff_promote = admin_client.post('/api/users/create/', {'username': 'sneaky', 'password': 'createdpass123', 'is_staff': '1'})
    assert r_staff_promote.status_code == 201
    assert User.objects.get(username='sneaky').is_staff is False
    admin_client.post(f'/api/users/{User.objects.get(username="sneaky").id}/delete/')
    print("  [OK] New accounts can never be created with admin rights")

    # 6. Admin creates Subject & Folder
    print("\n--- 6. Testing Subject & Folder Creation by Admin ---")
    subj_name = "Cloud Computing Core"
    admin_client.post(f'/api/subjects/{subj_name}/delete/')

    r_subj = admin_client.post('/api/subjects/create/', {
        'name': subj_name,
        'description': 'Virtualization, Cloud Storage, and Distributed Systems'
    })
    assert r_subj.status_code == 200
    print(f"  [OK] Admin created subject '{subj_name}'")

    folder_name = "Unit 1 - Cloud Architecture"
    r_folder = admin_client.post('/api/folders/create/', {
        'subject': subj_name,
        'folder_name': folder_name
    })
    assert r_folder.status_code == 200
    print(f"  [OK] Admin created folder '{folder_name}' in '{subj_name}'")

    # 7. Admin uploads material
    print("\n--- 7. Testing Admin File Upload into Specific Subject & Folder ---")
    from docx import Document as DocxDocument
    doc = DocxDocument()
    doc.add_heading('Cloud Architecture Overview', 0)
    doc.add_paragraph('Infrastructure as a Service (IaaS), Platform as a Service (PaaS), and Software as a Service (SaaS).')
    buf = io.BytesIO()
    doc.save(buf)

    file_upload = SimpleUploadedFile("Cloud_Lecture1.docx", buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    r_upload = admin_client.post('/api/documents/upload/', {
        'file': file_upload,
        'title': 'Lecture 1: Cloud Service Models',
        'subject': subj_name,
        'folder': folder_name,
        'tags': 'cloud,iaas,paas,saas'
    })
    assert r_upload.status_code == 200
    doc_id = r_upload.json()['id']
    print(f"  [OK] Admin uploaded Word doc into '{subj_name} / {folder_name}' -> ID: {doc_id}")

    print("\n--- 7b. Testing Multi-File Batch Upload by Admin ---")
    file1 = SimpleUploadedFile("Notes_Part1.txt", b"First set of notes on Cloud.", content_type="text/plain")
    file2 = SimpleUploadedFile("Notes_Part2.txt", b"Second set of notes on Cloud.", content_type="text/plain")
    file3 = SimpleUploadedFile("Notes_Part3.txt", b"Third set of notes on Cloud.", content_type="text/plain")

    r_multi = admin_client.post('/api/documents/upload/', {
        'files': [file1, file2, file3],
        'subject': subj_name,
        'folder': folder_name,
        'tags': 'batch,notes'
    })
    assert r_multi.status_code == 200
    multi_res = r_multi.json()
    assert multi_res['success'] == True
    assert multi_res['count'] == 3
    assert len(multi_res['ids']) == 3
    print(f"  [OK] Admin batch-uploaded 3 files at once -> IDs: {multi_res['ids']}")

    for fid in multi_res['ids']:
        admin_client.post(f'/api/documents/{fid}/delete/')

    # 8. Logged-in user browses and previews
    print("\n--- 8. Testing User Browsing & Previewing Documents ---")
    r_docs = user_client.get(f'/api/documents/?subject={subj_name}&folder={folder_name}')
    assert r_docs.status_code == 200
    docs_data = r_docs.json()
    assert docs_data['count'] >= 1
    assert docs_data['is_admin'] is False
    print(f"  [OK] User found {docs_data['count']} document(s) in '{subj_name} / {folder_name}'")

    r_prev = user_client.get(f'/api/documents/{doc_id}/preview-content/')
    assert r_prev.status_code == 200
    prev_data = r_prev.json()
    assert prev_data['type'] == 'docx'
    assert 'Cloud Architecture' in prev_data['html']
    print("  [OK] User previewed the Word document live in-browser")

    r_stream = user_client.get(f'/documents/{doc_id}/view/')
    assert r_stream.status_code == 200
    print("  [OK] User streamed the document inline")

    anon_stream = anonymous_client.get(f'/documents/{doc_id}/view/')
    assert anon_stream.status_code == 302
    print("  [OK] Anonymous visitors cannot stream documents (redirected to login)")

    r_user_delete = user_client.post(f'/api/documents/{doc_id}/delete/')
    assert r_user_delete.status_code == 403
    print("  [OK] User blocked from deleting documents")

    # 9. Admin deletion + logout
    print("\n--- 9. Testing Admin Deletion & Logout ---")
    r_del = admin_client.post(f'/api/documents/{doc_id}/delete/')
    assert r_del.status_code == 200
    print("  [OK] Admin successfully deleted document from MongoDB GridFS")

    admin_client.post(f'/api/subjects/{subj_name}/delete/')
    print(f"  [OK] Admin cleaned up test subject '{subj_name}'")

    r_logout = admin_client.get('/logout/')
    assert r_logout.status_code == 302
    assert '_auth_user_id' not in admin_client.session
    assert '/user-login/' in r_logout.url
    print("  [OK] Logout cleared the session and redirected to the user login page")

    # 10. REST auth APIs (no OTP step)
    print("\n--- 10. Testing Mobile/REST JSON Auth APIs ---")
    mobile_client = Client()
    r_status = mobile_client.get('/api/auth/status/')
    assert r_status.json()['is_authenticated'] == False
    assert r_status.json()['is_admin'] == False
    print("  [OK] Anonymous /api/auth/status/ reported correctly")

    r_mob_login = mobile_client.post('/api/auth/login/', {'username': ADMIN_USER, 'password': ADMIN_PASS},
                                     content_type='application/json')
    assert r_mob_login.status_code == 200, r_mob_login.content
    mob_login = r_mob_login.json()
    assert mob_login['success'] is True
    assert mob_login['is_admin'] is True
    assert mob_login['role'] == 'admin'
    assert '_auth_user_id' in mobile_client.session
    print("  [OK] Mobile admin login completed in ONE step (no OTP)")

    r_mob_status = mobile_client.get('/api/auth/status/')
    assert r_mob_status.json()['is_admin'] == True
    r_mob_logout = mobile_client.post('/api/auth/logout/')
    assert r_mob_logout.status_code == 200
    print("  [OK] Mobile admin status + logout verified")

    r_mob_user = Client().post('/api/auth/login/', {'username': USER_NAME, 'password': USER_PASS},
                               content_type='application/json')
    assert r_mob_user.status_code == 200
    assert r_mob_user.json()['is_admin'] is False
    assert r_mob_user.json()['role'] == 'user'
    print("  [OK] Mobile user login works and reports role 'user'")

    r_role_mismatch = Client().post('/api/auth/login/', {'username': USER_NAME, 'password': USER_PASS, 'role': 'admin'},
                                    content_type='application/json')
    assert r_role_mismatch.status_code == 403
    r_role_mismatch2 = Client().post('/api/auth/login/', {'username': ADMIN_USER, 'password': ADMIN_PASS, 'role': 'user'},
                                     content_type='application/json')
    assert r_role_mismatch2.status_code == 403
    print("  [OK] role= guard rejects cross-role logins")

    r_mob_bad = Client().post('/api/auth/login/', {'username': ADMIN_USER, 'password': 'nope'},
                              content_type='application/json')
    assert r_mob_bad.status_code == 401
    print("  [OK] Mobile API rejects invalid credentials with 401")

    r_otp_api = Client().post('/api/auth/verify-otp/', {'otp': '123456'}, content_type='application/json')
    assert r_otp_api.status_code == 404
    r_resend_api = Client().post('/api/auth/resend-otp/', content_type='application/json')
    assert r_resend_api.status_code == 404
    print("  [OK] /api/auth/verify-otp/ and /api/auth/resend-otp/ removed (404)")

    # 11. Health endpoint & cache
    print("\n--- 11. Testing Health Endpoint & Caching Speed ---")
    import time
    t0 = time.perf_counter()
    r_health = anonymous_client.get('/health/')
    t_health = (time.perf_counter() - t0) * 1000
    assert r_health.status_code == 200
    assert r_health.content == b"OK"
    print(f"  [OK] /health/ returned 200 OK in {t_health:.2f}ms (public, no login required)")

    t0 = time.perf_counter()
    s1 = mongo.get_all_subjects_with_stats()
    t1 = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    s2 = mongo.get_all_subjects_with_stats()
    t2 = (time.perf_counter() - t0) * 1000
    print(f"  [OK] First load: {t1:.2f}ms, RAM Cached load: {t2:.2f}ms (Instant!)")
    assert len(s1) == len(s2)

    # 12. Gemini AI assistant (requires login)
    print("\n--- 12. Testing Gemini AI Academic Tutor APIs ---")
    r_ai_status = user_client.get('/api/ai/status/')
    assert r_ai_status.status_code == 200
    ai_status_json = r_ai_status.json()
    assert ai_status_json.get('success') is True
    assert 'configured' in ai_status_json
    print(f"  [OK] /api/ai/status/ returned model={ai_status_json.get('model')}, configured={ai_status_json.get('configured')}")

    r_ai_bad = user_client.post('/api/ai/chat/', {}, content_type='application/json')
    assert r_ai_bad.status_code == 400
    print("  [OK] /api/ai/chat/ correctly validated empty prompt requirement (400 Bad Request)")

    r_ai_chat = user_client.post('/api/ai/chat/', {
        'prompt': 'What are the core properties of relational databases?',
        'action': 'explain'
    }, content_type='application/json')
    assert r_ai_chat.status_code == 200
    ai_chat_json = r_ai_chat.json()
    assert 'response' in ai_chat_json
    print(f"  [OK] /api/ai/chat/ returned valid structured response (configured={ai_chat_json.get('configured')})")

    # Cleanup
    User.objects.filter(username__in=[ADMIN_USER, USER_NAME]).delete()
    print("\n  [OK] Cleaned up temporary test accounts")

    print("\n=== ALL ROLE-BASED ACCESS, SUBJECT HIERARCHY, SPEED & AI TUTOR TESTS PASSED! ===")


if __name__ == '__main__':
    run_tests()

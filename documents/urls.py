from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("", views.index_view, name="index"),
    path("health/", views.health_check_view, name="health_check"),
    path("login/", views.login_view, name="admin_login"),
    path("user-login/", views.user_login_view, name="user_login"),
    path("logout/", views.logout_view, name="logout"),
    path("manifest.json", views.pwa_manifest_view, name="pwa_manifest"),
    
    # Mobile / REST Auth APIs (no two-factor step)
    path("api/auth/login/", views.api_auth_login_view, name="api_auth_login"),
    path("api/auth/status/", views.api_auth_status_view, name="api_auth_status"),
    path("api/auth/logout/", views.api_auth_logout_view, name="api_auth_logout"),
    
    # Admin-only user management (single admin profile, regular users have no admin control)
    path("api/users/", views.api_users_view, name="api_users"),
    path("api/users/create/", views.api_create_user_view, name="api_create_user"),
    path("api/users/<int:user_id>/delete/", views.api_delete_user_view, name="api_delete_user"),
    path("api/users/<int:user_id>/password/", views.api_reset_user_password_view, name="api_reset_user_password"),
    path("api/users/<int:user_id>/toggle-active/", views.api_toggle_user_active_view, name="api_toggle_user_active"),
    
    # Subject & Folder APIs
    path("api/subjects/", views.api_subjects_view, name="api_subjects"),
    path("api/subjects/create/", views.api_create_subject_view, name="api_create_subject"),
    path("api/subjects/<str:subject_name>/delete/", views.api_delete_subject_view, name="api_delete_subject"),
    path("api/folders/create/", views.api_create_folder_view, name="api_create_folder"),
    path("api/folders/delete/", views.api_delete_folder_view, name="api_delete_folder"),
    
    # Document APIs
    path("api/documents/", views.api_documents_view, name="api_documents"),
    path("api/documents/upload/", views.api_upload_view, name="api_upload"),
    path("api/documents/<str:file_id>/delete/", views.api_delete_view, name="api_delete"),
    path("api/documents/<str:file_id>/preview-content/", views.api_preview_content_view, name="api_preview_content"),
    
    # Gemini AI Assistant APIs
    path("api/ai/status/", views.api_ai_status_view, name="api_ai_status"),
    path("api/ai/chat/", views.api_ai_chat_view, name="api_ai_chat"),
    
    # Direct streaming
    path("documents/<str:file_id>/view/", views.view_file_inline_view, name="view_file"),
    path("documents/<str:file_id>/download/", views.download_file_view, name="download_file"),
]

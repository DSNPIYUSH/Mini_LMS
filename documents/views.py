import io
import json
import base64
import mammoth
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse, Http404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.http import urlencode, url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from . import mongo
from . import gemini_service

# ================= ACCESS CONTROL HELPERS =================

ROLE_ADMIN = "admin"
ROLE_USER = "user"

def user_role(user):
    """Return 'admin' for the single staff profile, 'user' for everyone else."""
    return ROLE_ADMIN if (user and user.is_authenticated and user.is_staff) else ROLE_USER


def safe_next(request, default="/"):
    """Only follow same-site relative redirect targets."""
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return target
    return default


def require_login_page(view_func):
    """Redirect anonymous HTML visitors to the login page."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{reverse('documents:user_login')}?{query}")
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def require_login_api(view_func):
    """Return 403 for anonymous JSON/REST callers."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                "success": False,
                "error": "Unauthorized. Please log in to continue."
            }, status=403)
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def require_admin_api(view_func):
    """Only the single admin profile may perform this action."""
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_staff):
            return JsonResponse({
                "success": False,
                "error": "Access denied. Administrator privileges are required."
            }, status=403)
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def _request_data(request):
    """Read fields from either a JSON body or a standard form POST."""
    if request.content_type and "application/json" in request.content_type and request.body:
        try:
            return json.loads(request.body.decode("utf-8") or "{}")
        except Exception:
            return {}
    return request.POST


# ================= AUTHENTICATION VIEWS (NO TWO-FACTOR) =================

def login_view(request):
    """Admin-only login for the single administrator profile."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("/")

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is None:
            error = "Invalid username or password. Please try again."
        elif not user.is_staff:
            error = "This account is not an administrator. Please use the user login page."
        else:
            auth_login(request, user)
            return redirect(safe_next(request))

    return render(request, "documents/login.html", {
        "error": error,
        "next": safe_next(request, default="")
    })


def user_login_view(request):
    """Login page for regular users. No administrative controls are granted."""
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect("/")

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is None:
            error = "Invalid username or password. Please try again."
        elif user.is_staff:
            error = "Administrators must sign in from the admin login page."
        else:
            auth_login(request, user)
            return redirect(safe_next(request))

    return render(request, "documents/user_login.html", {
        "error": error,
        "next": safe_next(request, default="")
    })


def logout_view(request):
    auth_logout(request)
    return redirect(reverse("documents:user_login"))


@csrf_exempt
def api_auth_login_view(request):
    """
    Mobile/REST login. Optional 'role' field decides which account type is expected:
      role="admin" -> only the single staff profile may log in
      role="user"  -> only non-staff accounts may log in
    When 'role' is omitted either account type is accepted and the real role returned.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)

    data = _request_data(request)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    expected_role = (data.get("role") or "").strip().lower()

    if expected_role not in ("", ROLE_ADMIN, ROLE_USER):
        return JsonResponse({"success": False, "error": "Role must be either 'admin' or 'user'."}, status=400)

    if not username or not password:
        return JsonResponse({"success": False, "error": "Username and password are required"}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"success": False, "error": "Invalid username or password"}, status=401)

    role = user_role(user)
    if expected_role and role != expected_role:
        if role == ROLE_ADMIN:
            return JsonResponse({"success": False, "error": "Administrators must sign in from the admin login page."}, status=403)
        return JsonResponse({"success": False, "error": "This is an administrator account. Use the admin login page."}, status=403)

    auth_login(request, user)
    return JsonResponse({
        "success": True,
        "is_authenticated": True,
        "is_admin": role == ROLE_ADMIN,
        "role": role,
        "username": user.username,
        "message": f"Login successful. Welcome, {user.username}."
    })


def api_auth_status_view(request):
    is_auth = request.user.is_authenticated
    role = user_role(request.user) if is_auth else ""
    return JsonResponse({
        "success": True,
        "is_authenticated": is_auth,
        "is_admin": is_auth and request.user.is_staff,
        "role": role,
        "username": request.user.username if is_auth else ""
    })


@csrf_exempt
def api_auth_logout_view(request):
    auth_logout(request)
    return JsonResponse({"success": True, "message": "Successfully logged out"})


# ================= ADMIN: USER MANAGEMENT (SINGLE-ADMIN ENFORCED) =================

def _serialize_account(user, request):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_staff,
        "is_active": user.is_active,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "is_self": request.user.is_authenticated and user.id == request.user.id,
    }


@csrf_exempt
@require_admin_api
def api_users_view(request):
    User = get_user_model()
    accounts = [
        _serialize_account(u, request)
        for u in User.objects.all().order_by("is_staff", "username")
    ]
    return JsonResponse({
        "success": True,
        "users": accounts,
        "admin_username": next((u["username"] for u in accounts if u["is_admin"]), ""),
    })


@csrf_exempt
@require_admin_api
def api_create_user_view(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)

    data = _request_data(request)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()

    if not username or not password:
        return JsonResponse({"success": False, "error": "Username and password are required"}, status=400)

    User = get_user_model()
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({"success": False, "error": f"The username '{username}' is already taken."}, status=400)

    try:
        validate_password(password)
    except ValidationError as exc:
        return JsonResponse({"success": False, "error": " ".join(exc.messages)}, status=400)

    # Regular accounts only: the app is locked to exactly one administrator profile.
    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_staff = False
    user.is_superuser = False
    user.save()

    return JsonResponse({
        "success": True,
        "message": f"User '{username}' created successfully.",
        "user": _serialize_account(user, request)
    }, status=201)


@csrf_exempt
@require_admin_api
def api_delete_user_view(request, user_id):
    if request.method not in ["POST", "DELETE"]:
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)

    if user.is_staff:
        return JsonResponse({"success": False, "error": "The administrator profile cannot be removed."}, status=400)
    if request.user.is_authenticated and user.id == request.user.id:
        return JsonResponse({"success": False, "error": "You cannot delete the account you are signed in with."}, status=400)

    username = user.username
    user.delete()
    return JsonResponse({"success": True, "message": f"User '{username}' deleted."})


@csrf_exempt
@require_admin_api
def api_reset_user_password_view(request, user_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)

    data = _request_data(request)
    password = data.get("password") or ""
    if not password:
        return JsonResponse({"success": False, "error": "New password is required"}, status=400)

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)

    try:
        validate_password(password)
    except ValidationError as exc:
        return JsonResponse({"success": False, "error": " ".join(exc.messages)}, status=400)

    user.set_password(password)
    user.save()
    return JsonResponse({"success": True, "message": f"Password updated for '{user.username}'."})


@csrf_exempt
@require_admin_api
def api_toggle_user_active_view(request, user_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)

    if user.is_staff:
        return JsonResponse({"success": False, "error": "The administrator profile cannot be deactivated."}, status=400)
    if request.user.is_authenticated and user.id == request.user.id:
        return JsonResponse({"success": False, "error": "You cannot deactivate the account you are signed in with."}, status=400)

    user.is_active = not user.is_active
    user.save()
    state = "activated" if user.is_active else "deactivated"
    return JsonResponse({"success": True, "message": f"User '{user.username}' {state}."})

def pwa_manifest_view(request):
    manifest = {
        "name": "Subject Bank - Academic Vault",
        "short_name": "SubjectBank",
        "description": "Store and preview PDF, PPT, Word, and Image documents stored in MongoDB.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#4f46e5",
        "icons": [
            {
                "src": "/static/documents/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/documents/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }
    return JsonResponse(manifest)

def health_check_view(request):
    """Ultra-fast keep-alive endpoint for cron-job.org / UptimeRobot to keep Render awake 24/7."""
    return HttpResponse("OK", content_type="text/plain", status=200)


# ================= PAGE VIEWS =================

@require_login_page
def index_view(request):
    stats = mongo.get_stats()
    subjects = mongo.get_all_subjects_with_stats()
    return render(request, "documents/index.html", {
        "stats": stats,
        "subjects": subjects,
        "is_admin": request.user.is_staff,
        "username": request.user.username,
    })

# ================= SUBJECT & FOLDER API =================

@require_login_api
def api_subjects_view(request):
    subjects = mongo.get_all_subjects_with_stats()
    stats = mongo.get_stats()
    return JsonResponse({
        "success": True,
        "subjects": subjects,
        "stats": stats,
        "is_admin": request.user.is_staff
    })

@csrf_exempt
@require_admin_api
def api_create_subject_view(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)
        
    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()
    
    try:
        mongo.create_subject(name=name, description=description)
        return JsonResponse({"success": True, "message": f"Subject '{name}' created successfully!"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

@csrf_exempt
@require_admin_api
def api_delete_subject_view(request, subject_name):
    if request.method not in ["POST", "DELETE"]:
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)
        
    try:
        mongo.delete_subject(subject_name)
        return JsonResponse({"success": True, "message": f"Subject '{subject_name}' deleted."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

@csrf_exempt
@require_admin_api
def api_create_folder_view(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)
        
    subject = request.POST.get("subject", "").strip()
    folder_name = request.POST.get("folder_name", "").strip()
    
    try:
        mongo.create_folder(subject_name=subject, folder_name=folder_name)
        return JsonResponse({"success": True, "message": f"Folder '{folder_name}' created in '{subject}'!"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

@csrf_exempt
@require_admin_api
def api_delete_folder_view(request):
    if request.method not in ["POST", "DELETE"]:
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)
        
    subject = request.POST.get("subject", "").strip()
    folder_name = request.POST.get("folder_name", "").strip()
    
    try:
        mongo.delete_folder(subject_name=subject, folder_name=folder_name)
        return JsonResponse({"success": True, "message": f"Folder '{folder_name}' deleted from '{subject}'."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

# ================= DOCUMENT API =================

@require_login_api
def api_documents_view(request):
    query = request.GET.get("q", "").strip()
    subject = request.GET.get("subject", "").strip()
    folder = request.GET.get("folder", "").strip()
    category = request.GET.get("category", "").strip()
    
    docs = mongo.list_documents(query=query, subject=subject, folder=folder, category=category)
    stats = mongo.get_stats()
    
    return JsonResponse({
        "success": True,
        "count": len(docs),
        "documents": docs,
        "stats": stats,
        "is_admin": request.user.is_staff
    })

@csrf_exempt
@require_admin_api
def api_upload_view(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)
    
    # Support both single file ('file') and multiple files ('files' or 'file' multiple times)
    files = request.FILES.getlist("files")
    if not files:
        files = request.FILES.getlist("file")
        
    if not files:
        return JsonResponse({"success": False, "error": "No file(s) selected for upload"}, status=400)
    
    subject = request.POST.get("subject", "").strip() or "General"
    folder = request.POST.get("folder", "").strip() or "General"
    tags = request.POST.get("tags", "")
    batch_title = request.POST.get("title", "").strip()
    
    saved_ids = []
    saved_names = []
    
    try:
        for idx, file_obj in enumerate(files):
            # If a single file and a title was given, use it. Otherwise use the file's original name.
            if len(files) == 1 and batch_title:
                doc_title = batch_title
            elif batch_title and len(files) > 1:
                # If a batch prefix was provided, format as "Prefix - Filename"
                doc_title = f"{batch_title} - {file_obj.name}"
            else:
                doc_title = file_obj.name
                
            file_id = mongo.save_document(
                file_obj=file_obj,
                title=doc_title,
                subject=subject,
                folder=folder,
                tags=tags
            )
            saved_ids.append(file_id)
            saved_names.append(file_obj.name)
            
        mongo.invalidate_cache()
        
        msg = f"Successfully stored {len(saved_ids)} document(s) in {subject} / {folder}!"
        return JsonResponse({
            "success": True,
            "count": len(saved_ids),
            "id": saved_ids[0] if saved_ids else None,
            "ids": saved_ids,
            "filenames": saved_names,
            "message": msg,
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@csrf_exempt
@require_admin_api
def api_delete_view(request, file_id):
    if request.method not in ["POST", "DELETE"]:
        return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)
        
    deleted = mongo.delete_document(file_id)
    if deleted:
        return JsonResponse({"success": True, "message": "Document deleted from MongoDB"})
    else:
        return JsonResponse({"success": False, "error": "Document not found or could not be deleted"}, status=404)

# ================= STREAMING & PREVIEWS =================

def _stream_gridfs_file(grid_out, chunk_size=256 * 1024):
    while True:
        chunk = grid_out.read(chunk_size)
        if not chunk:
            break
        yield chunk

@require_login_page
def view_file_inline_view(request, file_id):
    grid_out = mongo.get_document(file_id)
    if not grid_out:
        raise Http404("Document not found")
        
    content_type = getattr(grid_out, 'contentType', None) or getattr(grid_out, 'content_type', 'application/octet-stream')
    filename = grid_out.filename or "document"
    
    response = StreamingHttpResponse(
        _stream_gridfs_file(grid_out),
        content_type=content_type
    )
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    response["Content-Length"] = grid_out.length
    return response

@require_login_page
def download_file_view(request, file_id):
    grid_out = mongo.get_document(file_id)
    if not grid_out:
        raise Http404("Document not found")
        
    content_type = getattr(grid_out, 'contentType', None) or getattr(grid_out, 'content_type', 'application/octet-stream')
    filename = grid_out.filename or "document"
    
    response = StreamingHttpResponse(
        _stream_gridfs_file(grid_out),
        content_type=content_type
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Length"] = grid_out.length
    return response

def _extract_pptx_slides(file_bytes):
    prs = Presentation(io.BytesIO(file_bytes))
    slides_data = []
    
    for idx, slide in enumerate(prs.slides, 1):
        slide_info = {
            "slide_number": idx,
            "title": "",
            "content": [],
            "images": [],
            "tables": []
        }
        
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text.strip()
                if not text:
                    continue
                if shape == slide.shapes.title:
                    slide_info["title"] = text
                else:
                    paragraphs = []
                    for p in shape.text_frame.paragraphs:
                        p_text = p.text.strip()
                        if p_text:
                            paragraphs.append({
                                "text": p_text,
                                "level": p.level
                            })
                    if paragraphs:
                        slide_info["content"].append(paragraphs)
                        
            if shape.has_table:
                table_data = []
                for row in shape.table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(row_data)
                slide_info["tables"].append(table_data)
                
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                img_bytes = shape.image.blob
                ct = shape.image.content_type
                b64 = base64.b64encode(img_bytes).decode('utf-8')
                slide_info["images"].append(f"data:{ct};base64,{b64}")
                
        if not slide_info["title"]:
            slide_info["title"] = f"Slide {idx}"
            
        slides_data.append(slide_info)
    return slides_data

@require_login_api
def api_preview_content_view(request, file_id):
    grid_out = mongo.get_document(file_id)
    if not grid_out:
        return JsonResponse({"success": False, "error": "Document not found"}, status=404)
        
    filename = (grid_out.filename or "").lower()
    title = getattr(grid_out, "title", grid_out.filename)
    category = getattr(grid_out, "category", "other")
    
    view_url = f"/documents/{file_id}/view/"
    download_url = f"/documents/{file_id}/download/"

    if category == "pdf" or filename.endswith(".pdf"):
        return JsonResponse({
            "success": True,
            "type": "pdf",
            "url": view_url,
            "title": title,
            "filename": grid_out.filename,
            "id": file_id
        })
        
    if category == "image" or filename.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
        return JsonResponse({
            "success": True,
            "type": "image",
            "url": view_url,
            "title": title,
            "filename": grid_out.filename,
            "id": file_id
        })

    # Read binary bytes from GridFS
    file_bytes = grid_out.read()

    # Word Documents
    if filename.endswith(".docx"):
        try:
            result = mammoth.convert_to_html(io.BytesIO(file_bytes))
            return JsonResponse({
                "success": True,
                "type": "docx",
                "html": result.value,
                "title": title,
                "filename": grid_out.filename,
                "id": file_id
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "type": "unsupported",
                "error": f"Error parsing Word document: {str(e)}",
                "download_url": download_url,
                "id": file_id
            })

    # PowerPoint Presentations
    if filename.endswith(".pptx"):
        try:
            slides = _extract_pptx_slides(file_bytes)
            return JsonResponse({
                "success": True,
                "type": "pptx",
                "slides": slides,
                "title": title,
                "filename": grid_out.filename,
                "id": file_id
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "type": "unsupported",
                "error": f"Error parsing presentation: {str(e)}",
                "download_url": download_url,
                "id": file_id
            })

    # Plain text / code files
    if filename.endswith((".txt", ".md", ".csv", ".json", ".log", ".py", ".js", ".html")):
        try:
            text_content = file_bytes.decode('utf-8', errors='replace')
            return JsonResponse({
                "success": True,
                "type": "text",
                "text": text_content,
                "title": title,
                "filename": grid_out.filename,
                "id": file_id
            })
        except Exception:
            pass

    return JsonResponse({
        "success": False,
        "type": "unsupported",
        "error": "This file format cannot be parsed directly in the browser.",
        "download_url": download_url,
        "title": title,
        "filename": grid_out.filename,
        "id": file_id
    })


# ================= GEMINI AI ACADEMIC TUTOR VIEWS =================

@require_login_api
def api_ai_status_view(request):
    """
    Returns whether the Gemini API key is configured and active.
    """
    configured = gemini_service.is_gemini_configured()
    return JsonResponse({
        "success": True,
        "configured": configured,
        "model": gemini_service.get_effective_model()
    })

@csrf_exempt
@require_login_api
def api_ai_chat_view(request):
    """
    AI Academic Tutor query handler. Supports general questions or
    document-grounded questions/summaries/quizzes/explanations.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)

    try:
        if request.content_type and "application/json" in request.content_type:
            data = json.loads(request.body.decode("utf-8") or "{}")
        else:
            data = request.POST

        prompt = (data.get("prompt") or "").strip()
        file_id = data.get("file_id") or None
        action = data.get("action") or None

        if not prompt and not action:
            return JsonResponse({"success": False, "error": "Prompt or action is required."}, status=400)

        result = gemini_service.ask_gemini(prompt=prompt, file_id=file_id, action=action)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e),
            "response": f"### ⚠️ AI Processing Error\n\n`{str(e)}`"
        }, status=500)


import io
import json
import base64
import mammoth
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse, Http404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.views.decorators.csrf import csrf_exempt
from . import mongo

# ================= AUTHENTICATION VIEWS =================

def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("/")
        
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_staff:
                auth_login(request, user)
                return redirect("/")
            else:
                error = "Access denied. Only administrators can log into the management console."
        else:
            error = "Invalid username or password. Please try again."
            
    return render(request, "documents/login.html", {"error": error})

def logout_view(request):
    auth_logout(request)
    return redirect("/")

@csrf_exempt
def api_auth_login_view(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)
    
    username = ""
    password = ""
    
    # Support both JSON body and standard Form POST
    if request.content_type == "application/json" and request.body:
        try:
            body_data = json.loads(request.body)
            username = body_data.get("username", "").strip()
            password = body_data.get("password", "").strip()
        except Exception:
            pass
    
    if not username:
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        
    if not username or not password:
        return JsonResponse({"success": False, "error": "Username and password are required"}, status=400)
        
    user = authenticate(request, username=username, password=password)
    if user is not None:
        if user.is_staff:
            auth_login(request, user)
            return JsonResponse({
                "success": True,
                "is_authenticated": True,
                "is_admin": True,
                "username": user.username,
                "message": f"Welcome, {user.username}!"
            })
        else:
            return JsonResponse({
                "success": False, 
                "error": "Access denied. Only administrators have management privileges."
            }, status=403)
    else:
        return JsonResponse({"success": False, "error": "Invalid username or password"}, status=401)

def api_auth_status_view(request):
    is_auth = request.user.is_authenticated
    is_staff = is_auth and request.user.is_staff
    return JsonResponse({
        "success": True,
        "is_authenticated": is_auth,
        "is_admin": is_staff,
        "username": request.user.username if is_auth else ""
    })

@csrf_exempt
def api_auth_logout_view(request):
    auth_logout(request)
    return JsonResponse({"success": True, "message": "Successfully logged out"})

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


# ================= PAGE VIEWS =================

def index_view(request):
    stats = mongo.get_stats()
    subjects = mongo.get_all_subjects_with_stats()
    return render(request, "documents/index.html", {
        "stats": stats,
        "subjects": subjects,
        "is_admin": request.user.is_authenticated and request.user.is_staff
    })

# ================= SUBJECT & FOLDER API =================

def api_subjects_view(request):
    subjects = mongo.get_all_subjects_with_stats()
    stats = mongo.get_stats()
    return JsonResponse({
        "success": True,
        "subjects": subjects,
        "stats": stats,
        "is_admin": request.user.is_authenticated and request.user.is_staff
    })

@csrf_exempt
def api_create_subject_view(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({"success": False, "error": "Unauthorized. Only administrators can create subjects."}, status=403)
        
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
def api_delete_subject_view(request, subject_name):
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({"success": False, "error": "Unauthorized. Only administrators can delete subjects."}, status=403)
        
    if request.method not in ["POST", "DELETE"]:
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)
        
    try:
        mongo.delete_subject(subject_name)
        return JsonResponse({"success": True, "message": f"Subject '{subject_name}' deleted."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

@csrf_exempt
def api_create_folder_view(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({"success": False, "error": "Unauthorized. Only administrators can create folders."}, status=403)
        
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
def api_delete_folder_view(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({"success": False, "error": "Unauthorized. Only administrators can delete folders."}, status=403)
        
    if request.method not in ["POST", "DELETE"]:
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)
        
    subject = request.POST.get("subject", "").strip()
    folder_name = request.POST.get("folder_name", "").strip()
    
    try:
        mongo.delete_folder(subject_name=subject, folder_name=folder_name)
        return JsonResponse({"success": True, "message": f"Folder '{folder_name}' deleted."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

# ================= DOCUMENT API =================

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
        "is_admin": request.user.is_authenticated and request.user.is_staff
    })

@csrf_exempt
def api_upload_view(request):
    # Enforce Admin Check
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({
            "success": False, 
            "error": "Access Denied: Only authenticated administrators can upload documents."
        }, status=403)
    
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)
    
    file_obj = request.FILES.get("file")
    if not file_obj:
        return JsonResponse({"success": False, "error": "No file uploaded"}, status=400)
    
    title = request.POST.get("title", "").strip() or file_obj.name
    subject = request.POST.get("subject", "").strip() or "General"
    folder = request.POST.get("folder", "").strip() or "General"
    tags = request.POST.get("tags", "")
    
    try:
        file_id = mongo.save_document(
            file_obj=file_obj,
            title=title,
            subject=subject,
            folder=folder,
            tags=tags
        )
        return JsonResponse({
            "success": True,
            "id": file_id,
            "message": f"Successfully stored '{file_obj.name}' in {subject} / {folder}!",
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@csrf_exempt
def api_delete_view(request, file_id):
    # Enforce Admin Check
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({
            "success": False, 
            "error": "Access Denied: Only authenticated administrators can delete documents."
        }, status=403)

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
            "filename": grid_out.filename
        })
        
    if category == "image" or filename.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
        return JsonResponse({
            "success": True,
            "type": "image",
            "url": view_url,
            "title": title,
            "filename": grid_out.filename
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
                "filename": grid_out.filename
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "type": "unsupported",
                "error": f"Error parsing Word document: {str(e)}",
                "download_url": download_url
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
                "filename": grid_out.filename
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "type": "unsupported",
                "error": f"Error parsing presentation: {str(e)}",
                "download_url": download_url
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
                "filename": grid_out.filename
            })
        except Exception:
            pass

    return JsonResponse({
        "success": False,
        "type": "unsupported",
        "error": "This file format cannot be parsed directly in the browser.",
        "download_url": download_url,
        "title": title,
        "filename": grid_out.filename
    })

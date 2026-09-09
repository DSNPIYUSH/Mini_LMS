import os
import io
from google import genai
from google.genai import types
from docx import Document
from pptx import Presentation
import mammoth
from . import mongo

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

def get_api_key():
    return os.getenv("GEMINI_API_KEY", "").strip()

def is_gemini_configured():
    return bool(get_api_key())

def get_client():
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[Gemini Service] Error creating client: {e}")
        return None

def extract_document_context(file_id):
    """
    Extracts text or binary part from a document stored in MongoDB GridFS.
    Returns: (payload, is_multimodal_part, doc_meta)
    """
    if not file_id:
        return None, False, None
        
    try:
        grid_out = mongo.get_document(file_id)
        if not grid_out:
            return None, False, None
            
        filename = (grid_out.filename or "").lower()
        title = getattr(grid_out, "title", grid_out.filename)
        subject = getattr(grid_out, "subject", "General")
        folder = getattr(grid_out, "folder", "General")
        category = getattr(grid_out, "category", "other")
        
        doc_meta = {
            "id": file_id,
            "filename": grid_out.filename,
            "title": title,
            "subject": subject,
            "folder": folder,
            "category": category,
        }
        
        file_bytes = grid_out.read()
        
        # 1. PDF - native multimodal input to Gemini
        if category == "pdf" or filename.endswith(".pdf"):
            part = types.Part.from_bytes(data=file_bytes, mime_type="application/pdf")
            return part, True, doc_meta
            
        # 2. Images - native multimodal input
        if category == "image" or filename.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            content_type = getattr(grid_out, "contentType", "image/png")
            if "image" not in content_type:
                content_type = "image/png"
            part = types.Part.from_bytes(data=file_bytes, mime_type=content_type)
            return part, True, doc_meta
            
        # 3. Word DOCX - extract text
        if filename.endswith(".docx"):
            try:
                raw_text = mammoth.extract_raw_text(io.BytesIO(file_bytes)).value
                if raw_text.strip():
                    return raw_text, False, doc_meta
            except Exception:
                pass
            try:
                doc = Document(io.BytesIO(file_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                return "\n\n".join(paragraphs), False, doc_meta
            except Exception as e:
                return f"[Extracted document filename: {grid_out.filename}]", False, doc_meta

        # 4. PowerPoint PPTX - extract slide texts
        if filename.endswith(".pptx"):
            try:
                prs = Presentation(io.BytesIO(file_bytes))
                slides_text = []
                for idx, slide in enumerate(prs.slides, 1):
                    slide_lines = []
                    for shape in slide.shapes:
                        if shape.has_text_frame and shape.text.strip():
                            slide_lines.append(shape.text.strip())
                    if slide_lines:
                        slides_text.append(f"--- Slide {idx} ---\n" + "\n".join(slide_lines))
                return "\n\n".join(slides_text), False, doc_meta
            except Exception:
                return f"[Presentation: {grid_out.filename}]", False, doc_meta

        # 5. Plain text & code
        if filename.endswith((".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".log")):
            return file_bytes.decode("utf-8", errors="ignore"), False, doc_meta
            
        return f"[Document: {grid_out.filename}]", False, doc_meta
        
    except Exception as e:
        print(f"[Gemini Service] Error extracting document context: {e}")
        return None, False, None

def ask_gemini(prompt="", file_id=None, action=None):
    """
    Sends a query to Gemini model with optional document context.
    Actions supported: 'summarize', 'quiz', 'explain', or freeform 'chat'.
    """
    client = get_client()
    if not client:
        return {
            "success": False,
            "configured": False,
            "response": (
                "### ⚠️ Gemini API Key Required\n\n"
                "To enable AI study features, add your **GEMINI_API_KEY**:\n"
                "1. Get a 100% free key in 30 seconds from [Google AI Studio](https://aistudio.google.com/apikey).\n"
                "2. Add `GEMINI_API_KEY=your_key_here` to your `.env` file (local) or Render Dashboard **Environment** tab.\n"
                "3. Restart the server and your AI tutor will be live!"
            )
        }

    # Extract context if file_id is provided
    doc_payload, is_binary_part, doc_meta = extract_document_context(file_id)
    
    # Define action prompts
    if action == "summarize":
        user_instruction = (
            "Please analyze this study material and generate a comprehensive, high-yield academic study summary.\n"
            "Format your response with clear Markdown headers and bullet points:\n"
            "- **📌 Overview & Primary Goals**\n"
            "- **🔑 Key Concepts & Definitions**\n"
            "- **📝 Essential Takeaways & Formulas**\n"
            "- **💡 High-Yield Exam Tips & Common Mistakes**"
        )
    elif action == "quiz":
        user_instruction = (
            "Based directly on this study material, generate a 5-question review practice quiz to test understanding.\n"
            "Include a mix of multiple-choice questions and conceptual questions.\n"
            "For each question, provide 4 distinct answer choices (A, B, C, D) and then a clear explanation of why the correct answer is right."
        )
    elif action == "explain":
        user_instruction = (
            "Explain the main concepts and topics in this study material as if teaching a passionate student.\n"
            "Break down difficult ideas into simple, intuitive concepts, use clear real-world analogies, and provide step-by-step walkthroughs."
        )
    else:
        user_instruction = prompt.strip() if prompt else "Hello! How can you help me study this material?"

    system_prompt = (
        "You are the Subject Bank AI Academic Tutor, an expert educational mentor for university and college students. "
        "Your goal is to provide crystal-clear, structured, accurate, and encouraging academic explanations. "
        "Use GitHub-flavored Markdown, bullet points, headers, and code/math blocks when appropriate. "
        "If answering questions about a provided document, prioritize the document's facts and content."
    )

    contents = []
    
    # Add document context
    if doc_payload is not None:
        if is_binary_part:
            contents.append(doc_payload)
            contents.append(f"Document Title: {doc_meta.get('title', 'Unknown')}\nSubject: {doc_meta.get('subject')}\n\nTask: {user_instruction}")
        else:
            # Text context (truncate if extremely long to maintain fast latency)
            truncated_text = doc_payload[:60000] if len(doc_payload) > 60000 else doc_payload
            context_prompt = (
                f"### Academic Document Context:\n"
                f"- **Title**: {doc_meta.get('title')}\n"
                f"- **Subject**: {doc_meta.get('subject')} / {doc_meta.get('folder')}\n\n"
                f"```text\n{truncated_text}\n```\n\n"
                f"### User Question / Request:\n{user_instruction}"
            )
            contents.append(context_prompt)
    else:
        contents.append(user_instruction)

    model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            )
        )
        
        return {
            "success": True,
            "configured": True,
            "response": response.text,
            "model": model_name,
            "doc_title": doc_meta.get("title") if doc_meta else None
        }
    except Exception as e:
        print(f"[Gemini Service Error]: {e}")
        return {
            "success": False,
            "configured": True,
            "error": str(e),
            "response": f"### ⚠️ AI Processing Error\n\nCould not generate response from Gemini: `{str(e)}`"
        }

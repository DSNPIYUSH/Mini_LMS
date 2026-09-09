import os
import io
import base64
from google import genai
from google.genai import types
from docx import Document
from pptx import Presentation
import mammoth
from . import mongo

DEFAULT_MODEL = "gemini-3.6-flash"

def get_effective_model():
    """
    Returns the target model, automatically upgrading legacy models (e.g. 2.5/2.0/1.5)
    to the latest supported gemini-3.6-flash / gemini-3.7-flash.
    """
    m = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip()
    if not m or any(legacy in m for legacy in ["gemini-2.5", "gemini-2.0", "gemini-1.5"]):
        return "gemini-3.6-flash"
    return m

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
    Returns: (payload, is_multimodal_part, doc_meta, raw_bytes, mime_type)
    """
    if not file_id:
        return None, False, None, None, None
        
    try:
        grid_out = mongo.get_document(file_id)
        if not grid_out:
            return None, False, None, None, None
            
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
            return part, True, doc_meta, file_bytes, "application/pdf"
            
        # 2. Images - native multimodal input
        if category == "image" or filename.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            content_type = getattr(grid_out, "contentType", "image/png")
            if "image" not in content_type:
                content_type = "image/png"
            part = types.Part.from_bytes(data=file_bytes, mime_type=content_type)
            return part, True, doc_meta, file_bytes, content_type
            
        # 3. Word DOCX - extract text
        if filename.endswith(".docx"):
            try:
                raw_text = mammoth.extract_raw_text(io.BytesIO(file_bytes)).value
                if raw_text.strip():
                    return raw_text, False, doc_meta, None, None
            except Exception:
                pass
            try:
                doc = Document(io.BytesIO(file_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                return "\n\n".join(paragraphs), False, doc_meta, None, None
            except Exception as e:
                return f"[Extracted document filename: {grid_out.filename}]", False, doc_meta, None, None

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
                return "\n\n".join(slides_text), False, doc_meta, None, None
            except Exception:
                return f"[Presentation: {grid_out.filename}]", False, doc_meta, None, None

        # 5. Plain text & code
        if filename.endswith((".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".log")):
            return file_bytes.decode("utf-8", errors="ignore"), False, doc_meta, None, None
            
        return f"[Document: {grid_out.filename}]", False, doc_meta, None, None
        
    except Exception as e:
        print(f"[Gemini Service] Error extracting document context: {e}")
        return None, False, None, None, None

def _extract_interaction_text(interaction):
    """
    Safely extracts response string from an Interaction object across different schemas.
    """
    if hasattr(interaction, "output_text") and interaction.output_text:
        return interaction.output_text
    if hasattr(interaction, "outputs") and interaction.outputs:
        for out in reversed(interaction.outputs):
            if hasattr(out, "text") and out.text:
                return out.text
    if hasattr(interaction, "steps") and interaction.steps:
        for step in reversed(interaction.steps):
            if hasattr(step, "content") and step.content:
                for c in step.content:
                    if hasattr(c, "text") and c.text:
                        return c.text
    return str(interaction)

def ask_gemini(prompt="", file_id=None, action=None):
    """
    Sends a query to Gemini model with optional document context.
    Uses Google's recommended Interactions API and gemini-3.6-flash / gemini-3.7-flash.
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
    doc_payload, is_binary_part, doc_meta, raw_bytes, mime_type = extract_document_context(file_id)
    
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

    models_to_try = [get_effective_model()]
    for fallback_model in ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite"]:
        if fallback_model not in models_to_try:
            models_to_try.append(fallback_model)

    last_error = None

    for target_model in models_to_try:
        # Method 1: Try Interactions API (Google's recommended way for Gemini 3.x)
        if hasattr(client, "interactions"):
            try:
                if doc_payload is not None:
                    if is_binary_part and raw_bytes:
                        b64_data = base64.b64encode(raw_bytes).decode("utf-8")
                        input_payload = [
                            {"type": "text", "text": f"Document Title: {doc_meta.get('title')}\nSubject: {doc_meta.get('subject')}\n\nTask: {user_instruction}"},
                            {"type": "file" if "pdf" in (mime_type or "") else "image", "data": b64_data, "mime_type": mime_type}
                        ]
                    else:
                        truncated_text = doc_payload[:60000] if len(doc_payload) > 60000 else doc_payload
                        input_payload = (
                            f"### Academic Document Context:\n"
                            f"- **Title**: {doc_meta.get('title')}\n"
                            f"- **Subject**: {doc_meta.get('subject')} / {doc_meta.get('folder')}\n\n"
                            f"```text\n{truncated_text}\n```\n\n"
                            f"### User Question / Request:\n{user_instruction}"
                        )
                else:
                    input_payload = user_instruction

                interaction = client.interactions.create(
                    model=target_model,
                    input=input_payload,
                    system_instruction=system_prompt,
                )
                
                resp_text = _extract_interaction_text(interaction)
                if resp_text:
                    return {
                        "success": True,
                        "configured": True,
                        "response": resp_text,
                        "model": target_model,
                        "doc_title": doc_meta.get("title") if doc_meta else None
                    }
            except Exception as e_interact:
                print(f"[Gemini Interactions API with {target_model}]: {e_interact}")
                last_error = e_interact

        # Method 2: Fallback to generate_content API with GenerateContentConfig
        try:
            contents = []
            if doc_payload is not None:
                if is_binary_part:
                    contents.append(doc_payload)
                    contents.append(f"Document Title: {doc_meta.get('title', 'Unknown')}\nSubject: {doc_meta.get('subject')}\n\nTask: {user_instruction}")
                else:
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

            response = client.models.generate_content(
                model=target_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                )
            )

            if response and response.text:
                return {
                    "success": True,
                    "configured": True,
                    "response": response.text,
                    "model": target_model,
                    "doc_title": doc_meta.get("title") if doc_meta else None
                }
        except Exception as e_gen:
            print(f"[Gemini generate_content with {target_model}]: {e_gen}")
            last_error = e_gen

    return {
        "success": False,
        "configured": True,
        "error": str(last_error),
        "response": f"### ⚠️ AI Processing Error\n\nCould not generate response from Gemini: `{str(last_error)}`"
    }


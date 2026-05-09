from database import get_database
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_database, ChatSession, Message
from file_processor import process_file
from ai_service import get_ai_response, transcribe_audio
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# ─── Schemas ───────────────────────────────────────────────
class NewSession(BaseModel):
    title: str = "New Chat"
    username: str

class ChatMessage(BaseModel):
    session_id: int
    message: str

# ─── Routes ────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse("../frontend/index.html")

# Create new chat session
@app.post("/sessions")
def create_session(data: NewSession):
    db = get_database(data.username)
    session = ChatSession(title=data.title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

# Get all sessions
@app.get("/sessions")
def get_sessions(username: str):
    db = get_database(username)
    return db.query(ChatSession).all()
    # return db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()

# Delete session
@app.delete("/sessions/{session_id}")
def delete_session(session_id: int, username: str):
    db = get_database(username)

    db.query(Message).filter(
        Message.session_id == session_id
    ).delete()

    db.query(ChatSession).filter(
        ChatSession.id == session_id
    ).delete()

    db.commit()

    return {"message": "Deleted"}

# Get messages for a session
@app.get("/sessions/{session_id}/messages")
def get_messages(session_id: int, username: str):
    db = get_database(username)

    return db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at).all()

@app.post("/chat")
async def chat(
    username: str = Form(...),
    session_id: int = Form(...),
    message: str = Form(""),
    file: Optional[UploadFile] = File(None),
):
    db = get_database(username)

    file_data = None
    file_label = ""

    # Process uploaded file
    if file:
        file_bytes = await file.read()

        processed = process_file(
            file_bytes,
            file.filename,
            file.content_type
        )

        if processed["type"] == "audio":
            transcript = transcribe_audio(
                file_bytes,
                file.filename
            )

            file_data = {
                "type": "text",
                "content": f"Audio transcript:\n{transcript}",
                "label": "Audio"
            }

        elif processed["type"] == "unsupported":
            return {
                "response": f"Sorry, `.{file.filename.split('.')[-1]}` files are not supported yet."
            }

        else:
            file_data = processed

        file_label = f" [Attached: {file.filename}]"

    # Save user message
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=message + file_label,
        file_content=file_data["content"]
        if file_data and file_data["type"] != "image"
        else None
    )

    db.add(user_msg)
    db.commit()

    # Get history
    history = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at).all()

    # Build messages
    # Only inject file_content into the LAST message.
    # Re-sending huge file dumps in every history message wastes tokens badly.
    messages = []
    recent = history[-6:]

    for i, m in enumerate(recent):
        is_last = (i == len(recent) - 1)
        msg_content = m.content

        if is_last and m.file_content:
            truncated = m.file_content[:4000]
            if len(m.file_content) > 4000:
                truncated += "\n\n[...file truncated to save tokens...]"
            msg_content = f"{m.content}\n\n[File contents below]\n{truncated}"

        messages.append({
            "role": m.role,
            "content": msg_content
        })

    # AI response
    ai_response = get_ai_response(
        messages,
        file_data if file_data and file_data.get("type") == "image" else None
    )

    # Save AI response
    ai_msg = Message(
        session_id=session_id,
        role="assistant",
        content=ai_response,
        file_content=None
    )

    db.add(ai_msg)

    # Auto title
    if len(history) == 1:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()

        title = message or (
            file.filename if file else "New Chat"
        )

        session.title = (
            title[:40] + "..."
            if len(title) > 40
            else title
        )

    db.commit()

    return {"response": ai_response}
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import json

from app.db.database import get_db
from app.models.models import User, Conversation, Message
from app.schemas.schemas import (
    ChatRequest, ChatResponse, 
    Conversation as ConversationSchema,
    ConversationWithMessages,
    Message as MessageSchema
)
from app.services.rag_service import RAGService
from app.services.gemini_service import GeminiService
from app.utils.dependencies import get_current_active_user

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat_with_rag(
    chat_request: ChatRequest,
    mode: Optional[str] = Query("rag", regex="^(rag|general)$"),  # mode controls RAG or General Chat
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Send a message and get AI response; mode controls RAG vs General chat
    """
    rag_service = RAGService()
    gemini_service = GeminiService()

    # Get or create conversation
    if chat_request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == chat_request.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        conversation_title = chat_request.message[:50]
        if len(chat_request.message) > 50:
            conversation_title += "..."
        conversation = Conversation(
            user_id=current_user.id,
            title=conversation_title
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=chat_request.message
    )
    db.add(user_message)
    db.commit()

    try:
        if mode == "general":
            # General chat mode via Gemini API
            response_text = await gemini_service.generate_general_response(chat_request.message)
            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=response_text,
                sources=None,
                relevance_score=None
            )
            db.add(assistant_message)
            conversation.updated_at = assistant_message.created_at
            db.commit()

            return ChatResponse(
                message=response_text,
                conversation_id=conversation.id,
                sources=[],
                context_used=False,
                chunks_retrieved=0
            )
        else:
            # RAG chat mode
            rag_response = await rag_service.generate_rag_response(
                chat_request.message, 
                current_user.id
            )

            sources_json = None
            if rag_response.get("sources"):
                simplified_sources = []
                for source in rag_response["sources"][:5]:
                    simplified_sources.append({
                        "filename": source.get("filename"),
                        "document_id": source.get("document_id"),
                        "similarity_score": round(source.get("similarity_score", 0), 3),
                        "preview": source.get("chunk_preview", "")[:200]
                    })
                sources_json = json.dumps(simplified_sources)

            relevance_score = None
            if rag_response.get("chunks_retrieved", 0) > 0:
                if rag_response.get("sources"):
                    scores = [s.get("similarity_score", 0) for s in rag_response["sources"][:3]]
                    relevance_score = sum(scores) / len(scores) if scores else 0

            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=rag_response["response"],
                sources=sources_json,
                relevance_score=relevance_score
            )
            db.add(assistant_message)
            conversation.updated_at = assistant_message.created_at
            db.commit()

            return ChatResponse(
                message=rag_response["response"],
                conversation_id=conversation.id,
                sources=rag_response.get("sources", []),
                context_used=rag_response.get("context_used", False),
                chunks_retrieved=rag_response.get("chunks_retrieved", 0)
            )

    except Exception as e:
        error_message = f"❌ Sorry, I encountered an error: {str(e)}"
        error_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=error_message
        )
        db.add(error_msg)
        db.commit()
        return ChatResponse(
            message=error_message,
            conversation_id=conversation.id,
            sources=[],
            context_used=False,
            chunks_retrieved=0
        )


@router.get("/conversations", response_model=List[ConversationSchema])
async def get_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return conversations


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageSchema])
async def get_conversation_messages(
    conversation_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    # Parse JSON sources for each message
    for message in messages:
        if message.sources:
            try:
                message.sources = json.loads(message.sources)
            except:
                message.sources = []
        else:
            message.sources = []
    return messages


@router.get("/stats")
async def get_chat_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    total_conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).count()

    total_messages = db.query(Message).join(Conversation).filter(
        Conversation.user_id == current_user.id
    ).count()

    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)

    recent_conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.created_at >= week_ago
    ).count()

    return {
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "recent_conversations": recent_conversations,
        "user_id": current_user.id
    }

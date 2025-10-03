from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import Document as DocumentSchema, FileUploadResponse, DocumentStats
from app.services.document_service import DocumentService
from app.utils.dependencies import get_current_active_user

router = APIRouter()

@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a new document for RAG processing"""
    document_service = DocumentService(db)
    document = await document_service.upload_and_process_document(file, current_user)

    return FileUploadResponse(
        message=f"Document '{file.filename}' uploaded successfully and is being processed",
        document=document
    )

@router.get("/", response_model=List[DocumentSchema])
async def get_documents(
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of documents to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user documents with pagination"""
    document_service = DocumentService(db)
    return document_service.get_user_documents(current_user.id, skip=skip, limit=limit)

@router.get("/stats", response_model=DocumentStats)
async def get_document_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get document statistics for the current user"""
    document_service = DocumentService(db)
    stats = document_service.get_document_stats(current_user.id)
    return DocumentStats(**stats)

@router.get("/{document_id}", response_model=DocumentSchema)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific document"""
    document_service = DocumentService(db)
    document = document_service.get_document_by_id(document_id, current_user.id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return document

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a document and remove from RAG knowledge base"""
    document_service = DocumentService(db)
    success = document_service.delete_document(document_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or could not be deleted"
        )

    return {"message": "Document deleted successfully and removed from knowledge base"}

@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Reprocess a document (useful if processing failed)"""
    document_service = DocumentService(db)
    document = document_service.get_document_by_id(document_id, current_user.id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if document.processing_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is already being processed"
        )

    # Reset status and reprocess
    document.processing_status = "pending"
    db.commit()

    # Process asynchronously
    import asyncio
    asyncio.create_task(document_service._process_document_async(document))

    return {"message": "Document reprocessing started"}

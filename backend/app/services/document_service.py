import os
import hashlib
import asyncio
import aiofiles
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status

from app.models.models import Document, User
from app.core.config import settings
from app.services.rag_service import RAGService


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.rag_service = RAGService()

    async def upload_and_process_document(self, file: UploadFile, user: User) -> Document:
        """Upload and process document with RAG integration"""
        await self._validate_file(file)

        content = await file.read()
        await file.seek(0)

        file_hash = hashlib.md5(content).hexdigest()
        file_extension = file.filename.split('.')[-1].lower()
        unique_filename = f"{user.id}_{file_hash}.{file_extension}"

        user_upload_dir = os.path.join(settings.upload_path, str(user.id))
        os.makedirs(user_upload_dir, exist_ok=True)

        file_path = os.path.join(user_upload_dir, unique_filename)

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        document_type = "image" if file_extension in ['png', 'jpg', 'jpeg'] else "text"

        db_document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=len(content),
            file_type=file_extension,
            document_type=document_type,
            user_id=user.id,
            processing_status="pending"
        )
        self.db.add(db_document)
        self.db.commit()
        self.db.refresh(db_document)

        asyncio.create_task(self._process_document_async(db_document))

        return db_document

    async def _validate_file(self, file: UploadFile):
        """Validate uploaded file"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in settings.allowed_file_types_list:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Supported types: {', '.join(settings.allowed_file_types_list)}"
            )

        content = await file.read()
        await file.seek(0)

        if len(content) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
            )

    async def _process_document_async(self, document: Document):
        """Process document with RAG service"""
        try:
            success = await self.rag_service.process_document(document, self.db)
            if not success:
                print(f"❌ Failed to process document {document.id}")
            else:
                print(f"✅ Successfully processed document {document.id}")
        except Exception as e:
            print(f"❌ Error processing document {document.id}: {str(e)}")
            document.processing_status = "failed"
            self.db.commit()

    def get_user_documents(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Document]:
        """Get documents for a user with pagination"""
        return (
            self.db.query(Document)
            .filter(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_document_by_id(self, document_id: int, user_id: int) -> Optional[Document]:
        """Get a specific document by ID for a user"""
        return (
            self.db.query(Document)
            .filter(Document.id == document_id, Document.user_id == user_id)
            .first()
        )

    def delete_document(self, document_id: int, user_id: int) -> bool:
        """Delete a document and remove from vector store"""
        document = self.get_document_by_id(document_id, user_id)

        if not document:
            return False

        try:
            self.rag_service.delete_document_from_vector_store(document_id, user_id)

            if os.path.exists(document.file_path):
                os.remove(document.file_path)

            self.db.delete(document)
            self.db.commit()
            return True

        except Exception as e:
            print(f"❌ Error deleting document {document_id}: {str(e)}")
            self.db.rollback()
            return False

    def get_document_stats(self, user_id: int) -> dict:
        """Get user document statistics"""
        try:
            total_docs = self.db.query(Document).filter(Document.user_id == user_id).count()
            completed_docs = self.db.query(Document).filter(
                Document.user_id == user_id,
                Document.processing_status == "completed"
            ).count()

            docs = self.db.query(Document).filter(Document.user_id == user_id).all()
            file_types = {}
            for doc in docs:
                file_types[doc.file_type] = file_types.get(doc.file_type, 0) + 1

            return {
                "total_documents": total_docs,
                "processed_documents": completed_docs,
                "file_types": file_types,
                "vector_stats": self.rag_service.get_collection_stats(user_id)
            }

        except Exception as e:
            print(f"❌ Error getting document stats: {str(e)}")
            return {"error": str(e)}

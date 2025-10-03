import os
import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime

# RAG and LLM imports
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import google.generativeai as genai

# Document processing imports
import PyPDF2
import docx
from PIL import Image
import pytesseract
import cv2

from app.core.config import settings
from app.models.models import Document, DocumentChunk
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        # Initialize Gemini API
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            try:
                #self.gemini_model = genai.GenerativeModel(settings.gemini_model_name)
                self.gemini_model = genai.GenerativeModel("gemini-2.5-flash")

                logger.info(f"✅ Gemini API initialized with model {settings.gemini_model_name}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Gemini model: {e}")
                self.gemini_model = None
        else:
            self.gemini_model = None
            logger.warning("⚠️ No Gemini API key provided")

        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(settings.embedding_model)
            logger.info(f"✅ Embedding model loaded: {settings.embedding_model}")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise

        # Initialize text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=settings.vector_store_path,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Configure OCR
        if settings.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path

    def get_user_collection(self, user_id: int):
        """Get or create ChromaDB collection for user"""
        collection_name = f"user_{user_id}_documents"
        try:
            collection = self.chroma_client.get_collection(collection_name)
        except:
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"user_id": user_id}
            )
            logger.info(f"✅ Created new collection: {collection_name}")
        return collection

    async def extract_text_from_file(self, file_path: str, file_type: str) -> str:
        """Extract text from various file types including images"""
        try:
            if file_type.lower() == 'pdf':
                return await self._extract_pdf_text(file_path)
            elif file_type.lower() == 'docx':
                return await self._extract_docx_text(file_path)
            elif file_type.lower() == 'txt':
                return await self._extract_txt_text(file_path)
            elif file_type.lower() in ['png', 'jpg', 'jpeg']:
                return await self._extract_image_text(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            logger.error(f"❌ Text extraction failed for {file_path}: {e}")
            return ""

    async def _extract_pdf_text(self, file_path: str) -> str:
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if not text.strip():
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(file_path, poppler_path=settings.poppler_path)
                    for i, image in enumerate(images):
                        ocr_text = pytesseract.image_to_string(image)
                        text += f"\n--- Page {i+1} ---\n{ocr_text}"
                except Exception as ocr_error:
                    logger.warning(f"⚠️ OCR fallback failed: {ocr_error}")
        except Exception as e:
            logger.error(f"❌ PDF extraction failed: {e}")
        return text.strip()

    async def _extract_docx_text(self, file_path: str) -> str:
        text = ""
        try:
            doc = docx.Document(file_path)
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
        except Exception as e:
            logger.error(f"❌ DOCX extraction failed: {e}")
        return text.strip()

    async def _extract_txt_text(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    return file.read()
            except Exception as e:
                logger.error(f"❌ TXT extraction failed: {e}")
                return ""

    async def _extract_image_text(self, file_path: str) -> str:
        try:
            image = cv2.imread(file_path)
            if image is None:
                pil_image = Image.open(file_path)
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(thresh, config='--psm 6')
            logger.info(f"✅ OCR extracted {len(text)} characters from image")
            return text.strip()
        except Exception as e:
            logger.error(f"❌ Image OCR failed: {e}")
            return ""

    async def process_document(self, document: Document, db: Session) -> bool:
        logger.info(f"🔄 Processing document: {document.original_filename}")
        try:
            document.processing_status = "processing"
            db.commit()
            extracted_text = await self.extract_text_from_file(document.file_path, document.file_type)
            if not extracted_text.strip():
                document.processing_status = "failed"
                db.commit()
                logger.warning(f"⚠️ No text extracted from {document.original_filename}")
                return False
            document.extracted_text = extracted_text
            chunks = self.text_splitter.split_text(extracted_text)
            logger.info(f"📄 Created {len(chunks)} chunks from document")
            collection = self.get_user_collection(document.user_id)
            chunk_ids, embeddings, metadatas, documents_text = [], [], [], []
            for i, chunk in enumerate(chunks):
                chunk_id = f"doc_{document.id}_chunk_{i}"
                chunk_ids.append(chunk_id)
                embedding = self.embedding_model.encode(chunk).tolist()
                embeddings.append(embedding)
                documents_text.append(chunk)
                metadatas.append({
                    "document_id": document.id,
                    "chunk_index": i,
                    "filename": document.original_filename,
                    "file_type": document.file_type,
                    "created_at": datetime.now().isoformat()
                })
                db_chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_text=chunk,
                    chunk_index=i,
                    embedding=embedding[:50],  # Store first 50 dims for reference
                    metadata={"chunk_id": chunk_id}
                )
                db.add(db_chunk)
            collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
            document.processing_status = "completed"
            db.commit()
            logger.info(f"✅ Successfully processed {document.original_filename}")
            return True
        except Exception as e:
            logger.error(f"❌ Document processing failed: {e}")
            document.processing_status = "failed"
            db.commit()
            return False

    def retrieve_relevant_chunks(self, query: str, user_id: int, n_results: int = 5) -> List[Dict[str, Any]]:
        try:
            collection = self.get_user_collection(user_id)
            count = collection.count()
            if count == 0:
                logger.info("📭 No documents in user collection")
                return []
            query_embedding = self.embedding_model.encode(query).tolist()
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, count),
                include=["documents", "metadatas", "distances"]
            )
            relevant_chunks = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    relevant_chunks.append({
                        "text": doc,
                        "metadata": metadata,
                        "similarity_score": 1 / (1 + distance),  # Convert distance to similarity
                        "rank": i + 1
                    })
            logger.info(f"🔍 Retrieved {len(relevant_chunks)} relevant chunks")
            return relevant_chunks
        except Exception as e:
            logger.error(f"❌ Retrieval failed: {e}")
            return []

    def _is_context_low_quality(self, relevant_chunks):
        if not relevant_chunks:
            return True
        avg_score = sum(chunk["similarity_score"] for chunk in relevant_chunks) / len(relevant_chunks)
        return avg_score < 0.3

    async def generate_rag_response(self, query: str, user_id: int) -> Dict[str, Any]:
        try:
            if not self.gemini_model:
                return {
                    "response": "❌ Gemini API not configured. Please set GEMINI_API_KEY.",
                    "sources": [],
                    "error": "No API key"
                }
            relevant_chunks = self.retrieve_relevant_chunks(query, user_id)
            if not relevant_chunks or self._is_context_low_quality(relevant_chunks):
                response = self.gemini_model.generate_content(query)
                return {
                    "response": response.text,
                    "sources": [],
                    "context_used": False
                }
            context_parts = []
            sources = []
            for chunk in relevant_chunks[:5]:
                context_parts.append(f"Source: {chunk['metadata']['filename']}\n{chunk['text']}")
                sources.append({
                    "filename": chunk['metadata']['filename'],
                    "document_id": chunk['metadata']['document_id'],
                    "similarity_score": chunk['similarity_score'],
                    "chunk_preview": chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text']
                })
            context = "\n\n".join(context_parts)
            rag_prompt = f"""You are a helpful AI assistant that answers questions based on the provided context from the user's documents.

Context from uploaded documents:
{context}

User Question: {query}

Instructions:
- Answer the question based ONLY on the information provided in the context above
- If the answer cannot be found in the context, clearly state that you don't have that information in the uploaded documents
- Be specific and cite which document(s) you're referencing when possible
- Provide a comprehensive but concise answer
- If multiple documents contain relevant information, synthesize the information appropriately

Answer:"""
            response = self.gemini_model.generate_content(rag_prompt)
            return {
                "response": response.text,
                "sources": sources,
                "context_used": True,
                "chunks_retrieved": len(relevant_chunks)
            }
        except Exception as e:
            logger.error(f"❌ RAG response generation failed: {e}", exc_info=True)
            return {
                "response": f"❌ Sorry, I encountered an error while generating the response: {str(e)}",
                "sources": [],
                "error": str(e)
            }

    def delete_document_from_vector_store(self, document_id: int, user_id: int):
        try:
            collection = self.get_user_collection(user_id)
            results = collection.get(
                where={"document_id": document_id},
                include=["metadatas"]
            )
            if results['ids']:
                collection.delete(ids=results['ids'])
                logger.info(f"🗑️ Deleted {len(results['ids'])} chunks for document {document_id}")
        except Exception as e:
            logger.error(f"❌ Failed to delete document from vector store: {e}")

    def get_collection_stats(self, user_id: int) -> Dict[str, Any]:
        try:
            collection = self.get_user_collection(user_id)
            count = collection.count()
            if count > 0:
                sample = collection.get(limit=min(100, count), include=["metadatas"])
                doc_ids = set()
                file_types = {}
                for metadata in sample['metadatas']:
                    doc_ids.add(metadata.get('document_id'))
                    file_type = metadata.get('file_type', 'unknown')
                    file_types[file_type] = file_types.get(file_type, 0) + 1
                return {
                    "total_chunks": count,
                    "total_documents": len(doc_ids),
                    "file_types": file_types,
                    "collection_name": f"user_{user_id}_documents"
                }
            else:
                return {
                    "total_chunks": 0,
                    "total_documents": 0,
                    "file_types": {},
                    "collection_name": f"user_{user_id}_documents"
                }
        except Exception as e:
            logger.error(f"❌ Failed to get collection stats: {e}")
            return {"error": str(e)}

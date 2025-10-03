# 🤖 AI RAG Chatbot - Complete Python + React Project

A comprehensive, production-ready AI-powered chatbot with Retrieval-Augmented Generation (RAG) capabilities. This project combines a **Python FastAPI backend** with a **React frontend**, featuring Gemini API integration, multi-format document processing, and real-time chat with knowledge base integration.

## ✨ Complete Tech Stack

### 🐍 **Python Backend (FastAPI)**
- **FastAPI** - Modern, async web framework
- **ChromaDB** - Vector database for RAG
- **Sentence Transformers** - Document embeddings
- **Google Gemini API** - AI response generation
- **MySQL** - Database with separate connection fields
- **JWT Authentication** - Secure user management
- **OCR Processing** - Extract text from images
- **Docker** - Containerized deployment

### ⚛️ **React Frontend (JSX Components)**
- **React 18** - Modern React with hooks
- **Tailwind CSS** - Utility-first styling
- **React Router** - Client-side routing
- **Axios** - HTTP client for API calls
- **Hot Toast** - Notification system
- **Responsive Design** - Mobile-first approach

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- **Gemini API Key** from Google AI Studio

### 1. Setup Environment
```bash
# Clone/extract the project
cd ai-rag-chatbot-complete-python-react

# Configure backend environment
cp backend/.env.example backend/.env

# Edit backend/.env and add your API key:
GEMINI_API_KEY=your-gemini-api-key-here
SECRET_KEY=your-secure-secret-key-here
```

### 2. Launch with Docker
```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 4. First Steps
1. **Register** a new account at http://localhost:3000/register
2. **Upload documents** in Knowledge Base (PDF, DOCX, TXT, Images)
3. **Wait for processing** (documents are indexed automatically)
4. **Start chatting** and ask questions about your documents

## 📁 Project Structure

```
ai-rag-chatbot-complete-python-react/
├── 🐍 backend/                     # Python FastAPI Backend
│   ├── app/
│   │   ├── core/                   # Configuration & security
│   │   │   ├── config.py          # Settings with separate DB fields
│   │   │   └── security.py        # JWT & password hashing
│   │   ├── api/endpoints/          # API routes
│   │   │   ├── auth.py            # Registration & login
│   │   │   ├── documents.py       # File upload & management
│   │   │   └── chat.py            # RAG chat with history
│   │   ├── models/                 # SQLAlchemy models
│   │   ├── schemas/                # Pydantic schemas
│   │   ├── services/               # Business logic
│   │   │   ├── rag_service.py     # Complete RAG pipeline
│   │   │   └── document_service.py # Document processing
│   │   └── db/                     # Database configuration
│   ├── main.py                     # FastAPI application
│   ├── requirements.txt            # Python dependencies
│   ├── init_db.py                  # Database initialization
│   └── Dockerfile                  # Backend container
├── ⚛️ frontend/                     # React Frontend
│   ├── src/
│   │   ├── components/             # Reusable components
│   │   │   ├── Layout.jsx         # Navigation & sidebar
│   │   │   └── LoadingSpinner.jsx # Loading states
│   │   ├── pages/                  # Main application pages
│   │   │   ├── Login.jsx          # User authentication
│   │   │   ├── Register.jsx       # Account creation
│   │   │   ├── Dashboard.jsx      # Main overview
│   │   │   ├── KnowledgeBase.jsx  # File management
│   │   │   └── Chat.jsx           # RAG chat interface
│   │   ├── contexts/               # React contexts
│   │   │   └── AuthContext.jsx    # Authentication state
│   │   ├── services/               # API integration
│   │   │   └── apiService.js      # HTTP client
│   │   ├── App.jsx                 # Main app component
│   │   ├── index.jsx               # React entry point
│   │   └── index.css               # Tailwind styles
│   ├── package.json                # Node dependencies
│   ├── Dockerfile                  # Frontend container
│   └── nginx.conf                  # Production web server
├── docker-compose.yml              # Multi-service orchestration
├── .gitignore                      # Version control
└── README.md                       # This documentation
```

## 🎯 Key Features

### 🧠 **Advanced RAG Pipeline**
- **Multi-format Processing**: PDF, DOCX, TXT, Images with OCR
- **Text Chunking**: Intelligent document segmentation
- **Vector Embeddings**: Sentence Transformers for semantic search
- **ChromaDB Integration**: Persistent vector storage
- **Context Retrieval**: Similarity-based chunk selection
- **Gemini Generation**: AI responses with document context

### 🔐 **Complete Authentication**
- **User Registration**: Email validation & secure passwords
- **JWT Tokens**: Stateless authentication
- **Password Security**: bcrypt hashing with salt
- **Session Management**: Token refresh & logout
- **User Isolation**: Complete data separation

### 📄 **Document Management**
- **Drag-and-Drop Upload**: Intuitive file interface
- **Multi-format Support**: PDF, DOCX, TXT, PNG, JPG, JPEG
- **OCR Processing**: Extract text from images
- **Real-time Status**: Live processing updates
- **File Operations**: View, delete, reprocess documents
- **Statistics Dashboard**: Track knowledge base growth

### 💬 **Intelligent Chat**
- **RAG-Powered Responses**: Context-aware AI answers
- **Source Attribution**: Document references with similarity scores
- **Chat History**: Persistent conversation storage
- **Real-time Interface**: Live message updates
- **Mobile Responsive**: Optimized for all devices
- **Context Indicators**: Show when knowledge base is used

## ⚙️ Configuration

### Backend Environment Variables (`.env`)
```env
# Database (Separate fields as requested)
DBHOST=localhost
DBPORT=3306
DBNAME=rag_chatbot
DBUSER=app_user
DBPASSWORD=app_password123

# Security
SECRET_KEY=your-super-secure-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# File Processing
MAX_FILE_SIZE_MB=25
ALLOWED_FILE_TYPES=pdf,txt,docx,png,jpg,jpeg
```

### Frontend Environment Variables (`.env`)
```env
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_APP_NAME=AI RAG Chatbot
REACT_APP_VERSION=2.0.0
```

## 🔧 Development

### Local Development Setup

#### Backend Development
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python init_db.py

# Run development server
python main.py
```

#### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start development server
npm start
```

### Database Management
```bash
# Initialize database tables
cd backend
python init_db.py

# Check database connection
python -c "from app.db.database import engine; print(engine.execute('SELECT 1').fetchone())"
```

## 📊 API Documentation

### Authentication Endpoints
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/token` - Login (JWT)
- `GET /api/v1/auth/me` - Current user info

### Document Management
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents/` - List documents
- `DELETE /api/v1/documents/{id}` - Delete document
- `GET /api/v1/documents/stats` - Statistics

### RAG Chat
- `POST /api/v1/chat/` - Send message (RAG-powered)
- `GET /api/v1/chat/conversations` - List conversations
- `GET /api/v1/chat/conversations/{id}/messages` - Chat history
- `DELETE /api/v1/chat/conversations/{id}` - Delete conversation

**Interactive Docs**: http://localhost:8000/docs

## 🐳 Production Deployment

### Docker Production
```bash
# Set production environment
export GEMINI_API_KEY=your-production-key
export SECRET_KEY=your-production-secret

# Deploy with compose
docker-compose -f docker-compose.yml up -d

# Scale services if needed
docker-compose up -d --scale backend=2
```

### Manual Deployment
```bash
# Backend
cd backend
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

# Frontend
cd frontend
npm run build
# Serve build/ with Nginx/Apache
```

## 🧪 Testing

### Health Checks
```bash
# Backend health
curl http://localhost:8000/health

# Frontend health
curl http://localhost:3000

# Database connection
curl http://localhost:8000/admin
```

### API Testing
```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "email": "test@example.com", "password": "test123"}'

# Upload document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

## 🔍 Troubleshooting

### Common Issues

#### Backend Issues
```bash
# Check backend logs
docker-compose logs backend

# Database connection issues
docker-compose exec mysql mysql -u app_user -p rag_chatbot

# Python dependency issues
pip install --upgrade -r requirements.txt
```

#### Frontend Issues
```bash
# Check frontend logs
docker-compose logs frontend

# Node dependency issues
rm -rf node_modules package-lock.json
npm install

# Build issues
npm run build
```

#### Vector Database Issues
```bash
# Check ChromaDB directory
ls -la backend/vector_stores/

# Reset vector database
rm -rf backend/vector_stores/*
# Reprocess documents through UI
```

## 🎯 Usage Guide

### 1. **Upload Documents**
   - Navigate to Knowledge Base
   - Drag and drop files or click to browse
   - Supported: PDF, DOCX, TXT, PNG, JPG (max 25MB)
   - Wait for processing to complete

### 2. **Chat with Your Documents**
   - Go to Chat page
   - Ask questions about your uploaded content
   - View source attributions and similarity scores
   - Access conversation history in sidebar

### 3. **Example Questions**
   - "What are the key points in my documents?"
   - "Summarize the information about [specific topic]"
   - "Find details about [concept] in my files"
   - "What does document X say about Y?"

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **Google Gemini API** for AI capabilities
- **ChromaDB** for vector database
- **FastAPI** for backend framework
- **React** for frontend framework
- **Tailwind CSS** for styling
- **Sentence Transformers** for embeddings

---

**🚀 Ready to deploy your AI-powered knowledge base!**

**Built with Python FastAPI + React + Gemini API + ChromaDB**

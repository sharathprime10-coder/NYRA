# NYRA - Premium Knowledge Assistant

NYRA is a state-of-the-art, AI-powered knowledge assistant featuring a highly interactive 3D glassmorphism UI, Retrieval-Augmented Generation (RAG), and Model Context Protocol (MCP) capabilities. 

## 🚀 Features
- **Intelligent Chat Interface:** Powered by LangGraph and Gemini for advanced reasoning and contextual understanding.
- **Document Management & RAG:** Upload PDFs and documents to seamlessly query and extract insights using ChromaDB and pgvector.
- **Model Context Protocol (MCP):** Connects to external tools and databases dynamically.
- **Voice Assistant Integration:** Next-gen interactive AI voice capabilities.
- **Secure Authentication:** Google OAuth 2.0 and JWT-based secure user sessions.
- **Premium UI/UX:** Built with React, Framer Motion, and Tailwind CSS for a stunning, responsive, and glassmorphism-inspired design.

## 🛠 Tech Stack

### Frontend
- **Framework:** React 18 with Vite
- **Styling:** Tailwind CSS + Custom CSS (Glassmorphism, 3D effects)
- **Animations:** Framer Motion
- **Authentication:** Google OAuth (`@react-oauth/google`)
- **API Client:** Axios
- **Routing:** React Router DOM

### Backend
- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL (with `pgvector` for vector embeddings)
- **ORM:** SQLAlchemy with Alembic for migrations
- **AI/ML:** LangChain, LangGraph, Google GenAI (Gemini)
- **Vector Store:** ChromaDB / pgvector
- **Security:** Passlib (Argon2), Python-Jose (JWT)

## 📦 Local Development Setup

### 1. Database (PostgreSQL & Redis)
Ensure Docker is installed and running.
```bash
cd backend
docker-compose up -d
```

### 2. Backend Setup
Create a virtual environment and install dependencies:
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Set up your `.env` file in the `backend/` directory:
```env
DATABASE_URL=postgresql://nyra_user:nyra_password@localhost:5432/nyra_db
JWT_SECRET=your_super_secret_jwt_key
GOOGLE_CLIENT_ID=your_google_client_id
GEMINI_API_KEY=your_gemini_api_key
```

Run database migrations and start the server:
```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

Set up your `.env` file in the `frontend/` directory:
```env
VITE_GOOGLE_CLIENT_ID=your_google_client_id
VITE_API_URL=http://localhost:8000
```

Start the Vite development server:
```bash
npm run dev
```

## 🚀 Deployment Guide
- **Frontend:** Designed to be deployed on **Vercel**. Ensure environment variables are set in the Vercel dashboard.
- **Backend:** Designed for platforms like **Render**, **Railway**, or **AWS/GCP**. Requires a managed PostgreSQL database with `pgvector` support (e.g., Supabase, Neon.tech).
- **Database:** Migrate local Docker PostgreSQL to a managed cloud database and update the `DATABASE_URL`.

## 🛡 Security Notes
- NEVER commit `.env` files.
- Keep `JWT_SECRET` and `GEMINI_API_KEY` secure and rotate them if compromised.
- Ensure Google OAuth Authorized JavaScript Origins strictly match your production domain.

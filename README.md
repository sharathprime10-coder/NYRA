# NYRA - Premium Agentic Knowledge Assistant

[![CI Pipeline](https://github.com/your-org/app_chatbot/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/app_chatbot/actions/workflows/ci.yml)

NYRA is a state-of-the-art, AI-powered knowledge assistant featuring a highly interactive 3D glassmorphism UI, Retrieval-Augmented Generation (RAG), and Model Context Protocol (MCP) capabilities. 

![demo](docs/demo.gif)

## Architecture

NYRA uses a modern React frontend and a FastAPI Python backend powered by LangGraph to route intelligent agent interactions.

```mermaid
flowchart TD
    subgraph Client["🖥️ Client — React 19 + Vite"]
        direction TB
        UI["Chat / KnowledgeBase /Voice UI"]
        AuthCtx["AuthContext — JWT in localStorage"]
        Axios["Axios client + auth interceptor"]
        UI --> AuthCtx
        UI --> Axios
    end

    subgraph API["🚪 API Layer — FastAPI"]
        direction TB
        CORS["CORS Middleware"]
        Rate["slowapi Rate Limiter"]
        AuthVerif["JWT / Google OAuth Verification"]
        CORS --> Rate
        Rate --> AuthVerif
    end

    Axios --> CORS

    subgraph Endpoints["📡 Endpoints"]
        direction LR
        EpAuth["/api/auth — signup, login, google, me"]
        EpDocs["/api/documents — upload, list, delete"]
        EpChat["/api/chat — send message, history"]
    end
    
    AuthVerif --> Endpoints

    subgraph Storage["💾 Persistent Storage"]
        direction LR
        PG[("PostgreSQL<br>users, sessions, messages, documents")]
        Disk[("Local disk<br>uploaded_docs/")]
    end

    subgraph Retrieval["📚 Retrieval Layer"]
        direction TB
        Embed["Gemini Embeddings"]
        Chroma[("ChromaDB<br>nyra_knowledge_base")]
        Embed --> Chroma
    end

    subgraph Tools["🛠️ Tool Layer"]
        direction LR
        MCP["MCP filesystem server<br>uploaded_docs access"]
        Calc["calculator"]
        Web["DuckDuckGo web_search"]
        RAG["rag_tool"]
    end

    subgraph LangGraph["🧠 LangGraph Multi-Agent Orchestrator"]
        direction TB
        Supervisor["Supervisor Node<br>routes: researcher | writer"]
        Researcher["Researcher Node<br>tool-calling agent"]
        Writer["Writer Node<br>drafts final answer"]
        Critic["Critic Node<br>hallucination / quality check"]
        Checkpoint[("SQLite Checkpointer<br>nyra_checkpoints.db")]
        
        Supervisor -- route --> Researcher
        Supervisor -- route --> Writer
        Researcher --> Writer
        Writer -- route --> Critic
        Critic -- revise --> Writer
        
        Supervisor <--> Checkpoint
        Researcher <--> Checkpoint
    end

    subgraph LLM["☁️ LLM Provider Cascade — with fallback"]
        direction LR
        Groq["Groq — Llama 3.3 70B / 3.18B"]
        GeminiLLM["Google Gemini 3.6 Flash"]
        Nvidia["NVIDIA Nemotron — optional"]
        
        Groq -. fallback .-> GeminiLLM
        GeminiLLM -. fallback .-> Nvidia
    end

    %% Cross-layer connections
    EpAuth --> PG
    EpDocs --> PG
    EpDocs --> Disk
    EpDocs -- background task --> Embed
    
    EpChat --> Supervisor
    Critic -- approved --> EpChat
    
    Researcher --> Tools
    RAG --> Chroma
    MCP -. reads .-> Disk
    
    LangGraph --> LLM
```

## Features
- **Intelligent Chat Interface:** Powered by LangGraph and Gemini for advanced reasoning and contextual understanding.
- **Document Management & RAG:** Upload PDFs and documents to seamlessly query and extract insights using ChromaDB and pgvector.
- **Model Context Protocol (MCP):** Connects to external tools dynamically via multi-server registration.
  - **Scoped Filesystem Server:** Safely reads user-uploaded documents, strictly scoped to `./uploaded_docs/{user_id}` to guarantee data isolation.
  - **Notes Server:** A custom-built MCP server that allows the agent to save and retrieve markdown bookmarks and notes per conversation.
- **Voice Assistant Integration:** Next-gen interactive AI voice capabilities.
- **Secure Authentication:** Google OAuth 2.0 and JWT-based secure user sessions.
- **Premium UI/UX:** Built with React, Framer Motion, and Tailwind CSS for a stunning, responsive, and glassmorphism-inspired design.

## Tech Stack

### Frontend
- **Framework:** React 18 with Vite
- **Styling:** Tailwind CSS + Custom CSS (Glassmorphism, 3D effects)
- **Animations:** Framer Motion
- **Authentication:** Google OAuth (`@react-oauth/google`)
- **API Client:** Axios (with custom error boundary interceptors)
- **Routing:** React Router DOM

### Backend
- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL (with `pgvector` for vector embeddings)
- **ORM:** SQLAlchemy with Alembic for migrations
- **AI/ML:** LangChain, LangGraph, Google GenAI (Gemini)
- **Vector Store:** ChromaDB / pgvector
- **Security:** Passlib (Argon2), Python-Jose (JWT)
- **Observability:** Python JSON Logger, Sentry (Optional)

## Local Development Setup

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

## Testing & CI

NYRA uses GitHub Actions for continuous integration. Security (Bandit/Safety), linting (Ruff/Oxlint), code formatting (Black), and unit tests (Pytest) are enforced on every PR to `main`.

To run tests locally:
```bash
# Run backend tests
cd backend
pytest tests/

# Run frontend linting & checks
cd frontend
npm run lint
npm run build
```

## Deployment Guide
- **Frontend:** Designed to be deployed on **Vercel**. Ensure environment variables are set in the Vercel dashboard.
- **Backend:** Designed for platforms like **Render**, **Railway**, or **AWS/GCP**. Requires a managed PostgreSQL database with `pgvector` support (e.g., Supabase, Neon.tech).
- **Database:** Migrate local Docker PostgreSQL to a managed cloud database and update the `DATABASE_URL`.

## Known Limitations
- **Cost-Optimization:** Multi-provider fallback cascade is currently active; Groq and Gemini models are heavily utilized which can scale rapidly in cost during intensive agentic loops.
- **Sentry Integration:** The client and server have DSN ingestion logic enabled, but error reporting will be a no-op until `SENTRY_DSN` is populated.

## Security Notes
- See `SECURITY.md` for vulnerability reporting guidelines.
- NEVER commit `.env` files.
- Keep `JWT_SECRET` and `GEMINI_API_KEY` secure and rotate them if compromised.
- Ensure Google OAuth Authorized JavaScript Origins strictly match your production domain.

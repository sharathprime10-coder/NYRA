# NYRA - Premium Agentic Knowledge Assistant

[![CI Pipeline](https://github.com/sharathprime10-coder/NYRA/actions/workflows/ci.yml/badge.svg)](https://github.com/sharathprime10-coder/NYRA/actions/workflows/ci.yml)

NYRA is a state-of-the-art, AI-powered knowledge assistant featuring a highly interactive 3D glassmorphism UI, Retrieval-Augmented Generation (RAG), and Model Context Protocol (MCP) capabilities. 

![demo](docs/demo.gif)

## Architecture

NYRA uses a modern React frontend and a FastAPI Python backend powered by LangGraph to route intelligent agent interactions.

```mermaid
flowchart TD
    %% Styling
    linkStyle default stroke-width:3px

    %% Client Layer
    Client(["💻 React 19 + Vite UI<br/>(Chat / KnowledgeBase / Voice)"])

    %% API Layer
    subgraph API ["🚪 FastAPI Gateway"]
        direction LR
        Auth["🔑 /api/auth"]
        Docs["📄 /api/documents"]
        Chat["💬 /api/chat"]
    end

    Client ===> API

    %% Storage Layer
    subgraph Storage ["💾 Data Layer"]
        direction LR
        PG[("PostgreSQL<br/>(Users & Sessions)")]
        Disk[("Local Disk<br/>(Files)")]
        Chroma[("ChromaDB<br/>(Embeddings)")]
        State[("SQLite<br/>(Checkpoints)")]
    end

    Auth --> PG
    Docs --> Disk

    %% Agent Layer
    subgraph Orchestrator ["🧠 LangGraph Multi-Agent Orchestrator"]
        direction TB
        Supervisor{"Supervisor Node"}
        Researcher["🔍 Researcher Node"]
        Writer["✍️ Writer Node"]
        Critic{"⚖️ Critic Node"}
        
        Supervisor -->|routes| Researcher & Writer
        Researcher -->|context| Writer
        Writer -->|draft| Critic
        Critic -->|revise| Writer
    end

    Chat ===> Supervisor
    Critic ===>|approved| Chat

    Supervisor -.-> State
    Researcher -.-> State

    %% Tools & LLM Layer
    subgraph Services ["🛠️ Tools & Intelligence"]
        direction LR
        RAG["📚 RAG Pipeline"]
        MCP["🗂️ MCP Server"]
        Search["🌐 Web Search"]
        LLM["☁️ LLM Cascade<br/>(Gemini → Groq)"]
    end

    Docs -.->|background task| RAG
    Researcher ===> RAG & MCP & Search
    
    Orchestrator ===> LLM
    
    RAG <==> Chroma
    MCP <==> Disk
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

### 1. Database (Supabase PostgreSQL & Redis)
NYRA is configured to use a managed Supabase PostgreSQL instance with `pgvector` enabled.
Ensure your `DATABASE_URL` in `.env` points to your Supabase instance.

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
- **Database:** Ensure you have a managed cloud database (like Supabase) with `pgvector` enabled and `DATABASE_URL` configured in your `.env`.

## Known Limitations
- **Cost-Optimization:** Multi-provider fallback cascade is currently active; Groq and Gemini models are heavily utilized which can scale rapidly in cost during intensive agentic loops.
- **Sentry Integration:** The client and server have DSN ingestion logic enabled, but error reporting will be a no-op until `SENTRY_DSN` is populated.

## Security Notes
- See `SECURITY.md` for vulnerability reporting guidelines.
- NEVER commit `.env` files.
- Keep `JWT_SECRET` and `GEMINI_API_KEY` secure and rotate them if compromised.
- Ensure Google OAuth Authorized JavaScript Origins strictly match your production domain.

# NYRA Architecture Plan

## Current Architecture Audit
- **Frontend Framework**: React 19, Vite, TailwindCSS (React Router, Lucide Icons, Framer Motion).
- **Backend Framework**: FastAPI with Python 3.12+.
- **Database**: SQLite (`nyra.db`, `nyra_checkpoints.db`) via SQLAlchemy with `Integer` primary keys.
- **Authentication**: JWT-based with `passlib` and basic User model (id, username, password_hash). Missing fine-grained scoping.
- **RAG & Documents**: PyPDF extraction, LangChain RecursiveCharacterTextSplitter, ChromaDB for vector storage. Basic document model (id, filename, user_id, status).
- **Agents & Orchestration**: LangGraph integrated with a `Supervisor -> Researcher -> Writer -> Critic` architecture.
- **MCP Integration**: An `MCPClient` is implemented which dynamically bridges to a standard filesystem server via stdio.

## Target Architecture (Product-Ready)
- **Database**: PostgreSQL with `pgvector` for embeddings and hybrid search. Alembic for migrations.
- **Data Models**: Use UUIDs. Entites: users, sessions, conversations, messages, documents, chunks, collections, embeddings, agent_runs, tool_calls, audit_logs.
- **LLM/Embeddings Abstraction**: `LLMProvider` and `EmbeddingProvider` interfaces (OpenAI, Anthropic, Gemini, Local) to prevent vendor lock-in.
- **Retrieval Engine**: Multi-query, query rewriting, reranking, and metadata filtering (user isolation).
- **Expanded Agents**: RAG Agent, Research Agent, Document Agent, Study Agent, Writer Agent, Critic Agent, Memory Agent.
- **MCP Servers**: First-party NYRA MCP servers (Knowledge, Conversation, Study, System) for standardized tool execution, with explicit tool policies and authorization.
- **Observability**: Trace IDs, latency, token usage, tool-call tracking, and LLM-as-a-judge evaluation frameworks.
- **Testing & Security**: Rigorous Pytest coverage, rate limiting (SlowAPI), robust API error handling.

## Migration Plan & Phasing
The transition will happen in phases, preserving the existing React UI completely. Since the baseline Multi-Agent architecture and MCP Client stub are already implemented, we will weave them into the new infrastructure.

1. **Phase 1 & 2**: Stand up PostgreSQL/Alembic. Migrate models to UUIDs. Overhaul Auth (secure hashing, logout invalidation).
2. **Phase 3 & 4 & 5**: Implement Chat, Document, and pgvector persistence. Ensure background processing for docs.
3. **Phase 6**: Upgrade the RAG pipeline with rewriting, reranking, and metadata filtering.
4. **Phase 7 & 8**: Solidify the LangGraph agents and create first-party MCP Servers for NYRA, replacing the generic tools with MCP-backed endpoints.
5. **Phase 9, 10, 11, 12**: Multi-agent recovery, memory, evaluation frameworks, and final hardening (rate limits, caching).

## Risks
- **Vector DB Migration**: Moving from ChromaDB to PostgreSQL+pgvector requires changes to how vectors and metadata are stored and queried.
- **State Complexity**: Moving to persistent PostgreSQL graph state (LangGraph checkpoints) requires careful typing.
- **Frontend Contract Breaking**: The API responses MUST remain compatible with the current React UI. We will use DTOs/Schemas to ensure backward compatibility.

## Assumptions
- The frontend UI will NOT be modified.
- Deployment infrastructure is not required (Local Docker-Compose only).
- We have the right to refactor the Python backend entirely as long as the API boundaries remain stable for the frontend.

## Dependencies
- `psycopg2-binary`, `alembic`, `pgvector` for DB.
- `langgraph`, `langchain` for orchestration.
- `mcp` SDK for the server/client architecture.
- `docker` for local PostgreSQL/Redis standing.

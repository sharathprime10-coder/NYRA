# Contributing to NYRA

First off, thank you for considering contributing to NYRA! 

## Local Development Setup

1. **Clone the repository** and install dependencies for both the frontend (Node 20+) and backend (Python 3.11+).
2. **Backend**: 
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```
3. **Frontend**:
   ```bash
   cd frontend
   npm ci
   ```

## Pull Request Process

1. Ensure any changes to the backend pass the automated test suite. Run `pytest tests/` in the `backend/` directory.
2. Ensure Python code is formatted with Black (`black .`) and passes Ruff linting (`ruff check .`).
3. Ensure React code passes the frontend linter (`npm run lint`) and builds successfully (`npm run build`).
4. Our GitHub Actions CI pipeline will automatically run these checks on your PR. PRs with failing checks will not be merged.
5. Update the `README.md` with details of changes to the interface, this includes new environment variables, exposed ports, useful file locations, and container parameters.

## Scope of Contributions

Since this is an experimental/student project, we are primarily looking for:
- Bug fixes (especially UI state issues or RAG chunking bugs)
- CI/CD or testing infrastructure improvements
- Prompt/agent logic enhancements that strictly improve groundedness and reduce hallucination.

# Agent Leash

Agent Leash is a merchant-side safety layer for AI-agent commerce.

AI interprets intent; deterministic policy code authorizes money.

## Project structure

- `backend/`: FastAPI application and policy logic
- `frontend/`: Streamlit dashboard
- `tests/`: future test files

## Local setup

1. Create a virtual environment:
   python -m venv .venv
2. Activate it:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
3. Install dependencies:
   pip install -r requirements.txt
4. Start backend:
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
5. Start frontend:
   streamlit run frontend/app.py --server.port 8501

## Notes

- This is the initial runnable skeleton only.
- Real payment processing and AI logic are not implemented yet.
- Secrets must be stored in environment variables and never checked into Git.

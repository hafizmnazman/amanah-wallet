"""The agent wallet's API server.

    cd backend && uvicorn app.main:app --port 8000
"""

from app.agentwallet.api import create_app

app = create_app()

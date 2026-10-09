# SIH25104 Language-Agnostic Institutional Chatbot

This project is a FastAPI backend and plain HTML/CSS/JavaScript chat interface for a language-agnostic institutional chatbot. Users can ask questions in English, Hindi, Hinglish, or code-mixed text and receive an answer with the detected language, sources, and confidence. The current Phase 5 implementation uses the configured dummy AI service.

## Setup

Create and activate a Python virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

On Windows PowerShell, activate it with:

```powershell
venv\Scripts\Activate.ps1
```

Install the pinned dependencies:

```bash
pip install -r requirements.txt
```

Create the local environment file from the template:

```bash
cp .env.example .env
```

On Windows, copy `.env.example` to `.env` using the equivalent file-copy command. Keep `.env` local and never commit it.

## Run the application

From the repository root, start the development server:

```bash
uvicorn backend.main:app --reload
```

The application will be available at:

- API documentation: http://127.0.0.1:8000/docs
- Chat frontend: http://127.0.0.1:8000/app/
- Backend status: http://127.0.0.1:8000/

The frontend can also be opened directly from `file://`; in that case it uses `http://127.0.0.1:8000` as its API base URL.

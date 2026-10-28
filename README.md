# CrimeVision AI

A runnable starter implementation of a multimodal forensic evidence workspace. It includes case management, evidence uploads, asynchronous-style analysis endpoints, an evidence timeline, Groq-backed chat (optional), PDF report generation, and a React dashboard.

> AI outputs are decision-support only. Do not treat them as verified forensic conclusions. Model integrations require model weights/API credentials and must be independently validated before operational use.

## Requirements
- Python 3.10+
- Node.js 18+
- Optional: Groq API key for AI chat
- Optional model weights/dependencies for computer vision and transcription

## Run backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows CMD; on macOS/Linux use: cp .env.example .env
python run.py
```
Backend runs at `http://127.0.0.1:5000`.

## Run frontend
In another terminal:
```bash
cd frontend
npm install
npm run dev
```
Open the URL shown by Vite. The frontend expects the backend at `http://127.0.0.1:5000`.

## Optional Groq chat
Set `GROQ_API_KEY` in `backend/.env`. The API uses the Groq OpenAI-compatible endpoint. If the key is missing, chat returns a helpful setup message rather than fake AI output.

## AI model integrations
The project includes modular, optional service hooks for RT-DETR, CLIP, BLIP, and Whisper. Install the relevant libraries and configure model IDs/weights before using them. For safety and reliability, this starter does not pretend a model ran when it is not configured; the analysis endpoint reports which capabilities are unavailable. Validate model outputs and preserve original evidence in any real deployment.

## API overview
- `GET /api/health`
- `GET/POST /api/cases`
- `GET/PUT/DELETE /api/cases/<case_id>`
- `POST /api/cases/<case_id>/evidence`
- `GET /api/cases/<case_id>/evidence`
- `POST /api/cases/<case_id>/analyze`
- `GET /api/cases/<case_id>/timeline`
- `POST /api/cases/<case_id>/chat`
- `POST /api/cases/<case_id>/report`

## Notes
- Uploaded originals are stored in `backend/uploads`; generated reports in `backend/reports`.
- SQLite database is created automatically.
- This is a functional starter project, not a validated forensic product or legal evidence system. Add authentication, authorization, audit review, malware scanning, retention policies, and deployment hardening before production use.

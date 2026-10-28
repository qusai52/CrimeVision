import os, uuid, hashlib, json
from pathlib import Path
from flask import Blueprint, request, send_file
from werkzeug.utils import secure_filename
from ..db import connect, ROOT
from ..services.ai import capabilities, groq_answer
from ..services.reporting import build_report

api = Blueprint("api", __name__)
UPLOADS = ROOT / "uploads"
REPORTS = ROOT / "reports"
UPLOADS.mkdir(exist_ok=True); REPORTS.mkdir(exist_ok=True)
ALLOWED = {".png",".jpg",".jpeg",".webp",".mp4",".mov",".avi",".wav",".mp3",".m4a",".txt",".pdf"}

def rowdict(row): return dict(row) if row else None

@api.get("/health")
def health():
    return {"status":"ok","service":"CrimeVision AI API","capabilities":capabilities()}

@api.get("/cases")
def list_cases():
    with connect() as c:
        cases = [dict(r) for r in c.execute("SELECT * FROM cases ORDER BY id DESC")]
        for case in cases:
            case["evidence_count"] = c.execute("SELECT COUNT(*) FROM evidence WHERE case_id=?", (case["id"],)).fetchone()[0]
        return {"cases": cases}

@api.post("/cases")
def create_case():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title: return {"error":"Case title is required."}, 400
    with connect() as c:
        cur = c.execute("INSERT INTO cases(title,description,status) VALUES(?,?,?)",
                        (title, data.get("description",""), data.get("status","Open")))
        case = dict(c.execute("SELECT * FROM cases WHERE id=?", (cur.lastrowid,)).fetchone())
    return {"case":case}, 201

@api.get("/cases/<int:case_id>")
def get_case(case_id):
    with connect() as c:
        case = c.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not case: return {"error":"Case not found."}, 404
        return {"case":dict(case),
                "evidence":[dict(r) for r in c.execute("SELECT id,case_id,original_name,media_type,size_bytes,sha256,uploaded_at FROM evidence WHERE case_id=? ORDER BY id DESC",(case_id,))],
                "events":[dict(r) for r in c.execute("SELECT * FROM events WHERE case_id=? ORDER BY timestamp,id",(case_id,))]}

@api.put("/cases/<int:case_id>")
def update_case(case_id):
    data=request.get_json(silent=True) or {}
    with connect() as c:
        if not c.execute("SELECT id FROM cases WHERE id=?",(case_id,)).fetchone(): return {"error":"Case not found."},404
        c.execute("UPDATE cases SET title=?, description=?, status=? WHERE id=?",
                  (data.get("title","Untitled case"),data.get("description",""),data.get("status","Open"),case_id))
        return {"case":dict(c.execute("SELECT * FROM cases WHERE id=?",(case_id,)).fetchone())}

@api.delete("/cases/<int:case_id>")
def delete_case(case_id):
    with connect() as c:
        c.execute("DELETE FROM cases WHERE id=?",(case_id,))
    return {"deleted":True}

@api.post("/cases/<int:case_id>/evidence")
def upload_evidence(case_id):
    f=request.files.get("file")
    if not f or not f.filename: return {"error":"Choose a file to upload."},400
    ext=Path(f.filename).suffix.lower()
    if ext not in ALLOWED: return {"error":f"Unsupported file type: {ext}"},415
    with connect() as c:
        if not c.execute("SELECT id FROM cases WHERE id=?",(case_id,)).fetchone(): return {"error":"Case not found."},404
    safe=secure_filename(f.filename) or "evidence"
    stored=f"{uuid.uuid4().hex}_{safe}"
    path=UPLOADS/stored
    digest=hashlib.sha256()
    size=0
    with path.open("wb") as out:
        while True:
            chunk=f.stream.read(1024*1024)
            if not chunk: break
            size += len(chunk); digest.update(chunk); out.write(chunk)
    media = "image" if ext in {".png",".jpg",".jpeg",".webp"} else "video" if ext in {".mp4",".mov",".avi"} else "audio" if ext in {".wav",".mp3",".m4a"} else "document"
    with connect() as c:
        cur=c.execute("INSERT INTO evidence(case_id,original_name,stored_name,media_type,size_bytes,sha256) VALUES(?,?,?,?,?,?)",
                       (case_id,safe,stored,media,size,digest.hexdigest()))
        ev=dict(c.execute("SELECT id,case_id,original_name,media_type,size_bytes,sha256,uploaded_at FROM evidence WHERE id=?",(cur.lastrowid,)).fetchone())
    return {"evidence":ev,"message":"Evidence stored. Model analysis must be configured before AI findings can be produced."},201

@api.get("/cases/<int:case_id>/evidence")
def list_evidence(case_id):
    with connect() as c:
        return {"evidence":[dict(r) for r in c.execute("SELECT id,case_id,original_name,media_type,size_bytes,sha256,uploaded_at FROM evidence WHERE case_id=? ORDER BY id DESC",(case_id,))]}

@api.post("/cases/<int:case_id>/analyze")
def analyze_case(case_id):
    with connect() as c:
        case=c.execute("SELECT id FROM cases WHERE id=?",(case_id,)).fetchone()
        if not case: return {"error":"Case not found."},404
        evidence=[dict(r) for r in c.execute("SELECT id,original_name,media_type FROM evidence WHERE case_id=?",(case_id,))]
        status=capabilities()
    return {"case_id":case_id,"status":"partial","message":"Evidence inventory checked. Model-specific inference is not enabled in this starter until model runtimes and weights are configured.","evidence_count":len(evidence),"capabilities":status,"events_created":0},200

@api.get("/cases/<int:case_id>/timeline")
def timeline(case_id):
    with connect() as c:
        return {"events":[dict(r) for r in c.execute("SELECT * FROM events WHERE case_id=? ORDER BY timestamp,id",(case_id,))]}

@api.post("/cases/<int:case_id>/events")
def add_event(case_id):
    data=request.get_json(silent=True) or {}
    if not (data.get("description") or "").strip(): return {"error":"Event description is required."},400
    with connect() as c:
        if not c.execute("SELECT id FROM cases WHERE id=?",(case_id,)).fetchone(): return {"error":"Case not found."},404
        cur=c.execute("INSERT INTO events(case_id,evidence_id,timestamp,description,source_type,confidence) VALUES(?,?,?,?,?,?)",
                       (case_id,data.get("evidence_id"),data.get("timestamp",""),data["description"],data.get("source_type","investigator"),data.get("confidence")))
        return {"event":dict(c.execute("SELECT * FROM events WHERE id=?",(cur.lastrowid,)).fetchone())},201

@api.post("/cases/<int:case_id>/chat")
def chat(case_id):
    data=request.get_json(silent=True) or {}; question=(data.get("message") or "").strip()
    if not question: return {"error":"Message is required."},400
    with connect() as c:
        case=c.execute("SELECT * FROM cases WHERE id=?",(case_id,)).fetchone()
        if not case: return {"error":"Case not found."},404
        evidence=[dict(r) for r in c.execute("SELECT id,original_name,media_type,size_bytes,sha256 FROM evidence WHERE case_id=?",(case_id,))]
        events=[dict(r) for r in c.execute("SELECT * FROM events WHERE case_id=?",(case_id,))]
        c.execute("INSERT INTO messages(case_id,role,content) VALUES(?,?,?)",(case_id,"user",question))
    context=json.dumps({"case":dict(case),"evidence":evidence,"events":events},ensure_ascii=False)
    try:
        answer=groq_answer(question,context)
    except Exception as e:
        answer=f"Groq request failed: {type(e).__name__}. Check API configuration and network, then retry."
    with connect() as c:
        c.execute("INSERT INTO messages(case_id,role,content) VALUES(?,?,?)",(case_id,"assistant",answer))
        history=[dict(r) for r in c.execute("SELECT id,role,content,created_at FROM messages WHERE case_id=? ORDER BY id",(case_id,))]
    return {"answer":answer,"history":history}

@api.get("/cases/<int:case_id>/chat")
def chat_history(case_id):
    with connect() as c:
        return {"history":[dict(r) for r in c.execute("SELECT id,role,content,created_at FROM messages WHERE case_id=? ORDER BY id",(case_id,))]}

@api.post("/cases/<int:case_id>/report")
def generate_report(case_id):
    with connect() as c:
        case=c.execute("SELECT * FROM cases WHERE id=?",(case_id,)).fetchone()
        if not case: return {"error":"Case not found."},404
        evidence=[dict(r) for r in c.execute("SELECT * FROM evidence WHERE case_id=?",(case_id,))]
        events=[dict(r) for r in c.execute("SELECT * FROM events WHERE case_id=? ORDER BY timestamp,id",(case_id,))]
        messages=[dict(r) for r in c.execute("SELECT * FROM messages WHERE case_id=?",(case_id,))]
    filename=f"crimevision_case_{case_id}_{uuid.uuid4().hex[:8]}.pdf"
    path=REPORTS/filename
    build_report(path,dict(case),evidence,events,messages)
    return {"report_url":f"/api/reports/{filename}","filename":filename}

@api.get("/reports/<path:filename>")
def download_report(filename):
    path=(REPORTS/filename).resolve()
    if path.parent != REPORTS.resolve() or not path.is_file(): return {"error":"Report not found."},404
    return send_file(path,as_attachment=True,download_name=path.name)

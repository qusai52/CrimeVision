from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from pathlib import Path
from xml.sax.saxutils import escape

def build_report(path, case, evidence, events, messages):
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    styles = getSampleStyleSheet()
    story = [Paragraph("CrimeVision AI — Forensic Analysis Report", styles["Title"]), Spacer(1, 12)]
    story += [Paragraph(f"<b>Case ID:</b> {case['id']}", styles["Normal"]),
              Paragraph(f"<b>Case:</b> {escape(case['title'])}", styles["Normal"]),
              Paragraph(f"<b>Description:</b> {escape(case['description'] or 'Not provided')}", styles["Normal"]),
              Paragraph(f"<b>Created:</b> {case['created_at']}", styles["Normal"]), Spacer(1, 14)]
    story.append(Paragraph("Evidence Inventory", styles["Heading2"]))
    rows = [["ID", "File", "Type", "Size (bytes)", "SHA-256"]]
    for e in evidence:
        rows.append([str(e["id"]), escape(e["original_name"][:35]), e["media_type"], str(e["size_bytes"]), e["sha256"][:18] + "…"])
    table = Table(rows, repeatRows=1, colWidths=[28, 120, 70, 60, 145])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1e293b")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.4,colors.grey),("FONTSIZE",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story += [table, Spacer(1, 14), Paragraph("Timeline / Recorded Events", styles["Heading2"])]
    if events:
        for ev in events:
            story.append(Paragraph(f"<b>{escape(ev['timestamp'] or 'Time unknown')}</b> — {escape(ev['description'])} (source: {escape(ev['source_type'])})", styles["BodyText"]))
            story.append(Spacer(1, 5))
    else:
        story.append(Paragraph("No events have been recorded. Analysis has not been performed or model integrations are not configured.", styles["BodyText"]))
    story += [Spacer(1, 16), Paragraph("Limitations and Review", styles["Heading2"]),
              Paragraph("This report includes uploaded evidence metadata and recorded application outputs. AI-generated interpretations require human verification. This starter application is not a certified forensic system.", styles["BodyText"])]
    doc.build(story)

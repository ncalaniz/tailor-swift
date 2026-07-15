# export.py — turns tailored resume text into downloadable Word (.docx) and PDF files.
import io
from turtle import st
import docx                 # installed as "python-docx"
from fpdf import FPDF       # installed as "fpdf2"
import store
import re
import json

def _contact():
    """Pull the header (name + contact line) from settings."""
    name = store.get_setting("name", "")
    bits = [store.get_setting("email", ""), store.get_setting("phone", ""),
            store.get_setting("location", ""), store.get_setting("linkedin", "")]
    return name, [b for b in bits if b]

def _is_rule(line):
    """True for leftover '---' style separator lines we want to drop."""
    return len(line) >= 3 and set(line) <= {"-", "*", "_"}

def _ascii(s):
    """Swap characters the PDF font can't handle for plain equivalents."""
    for bad, good in [("—", "-"), ("–", "-"), ("’", "'"), ("‘", "'"),
                      ("“", '"'), ("”", '"'), ("•", "-"), ("…", "...")]:
        s = s.replace(bad, good)
    return s

def _norm(s):
    """Lowercase + collapse whitespace, for tolerant matching."""
    return re.sub(r"\s+", " ", (s or "").lower()).strip()

def _dates_for_heading(heading):
    """Find the stored job inside this heading and return a formatted date range (or '')."""
    h = _norm(heading)
    # longest role first, so 'Sr. Manager...' wins over 'Manager...'
    for j in sorted(store.list_jobs(), key=lambda x: -len(x["role"] or "")):
        emp, role = _norm(j["employer"]), _norm(j["role"])
        if emp and emp in h and (not role or role in h):
            start = (j["start_date"] or "").strip()
            end = (j["end_date"] or "").strip()
            if start and end:
                return f"{start} \u2013 {end}"
            if start:
                return f"{start} \u2013 Present"
            return end
    return ""

def build_docx(tailored_text):
    """Turn the tailored text into a Word doc, returned as bytes."""
    doc = docx.Document()
    name, contact_parts = _contact()
    if name:
        doc.add_heading(name, level=0)
    for part in contact_parts:
        doc.add_paragraph(part)

    for raw in tailored_text.split("\n"):
        line = raw.strip()
        if not line or _is_rule(line):
            continue
        job_id = _job_tag(line)
        if job_id is not None:
            title, dates, loc = _job_heading_parts(job_id)
            if title:
                doc.add_heading(title + (f"   ({dates})" if dates else ""), level=2)
                if loc:
                    doc.add_paragraph(loc)
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:], level=2)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=1)
        elif line.startswith("- ") or line.startswith("* "):
            doc.add_paragraph(line[2:], style="List Bullet")
        else:
            doc.add_paragraph(line)

    edu = _education()
    if edu:
        doc.add_heading("Education", level=1)
        for e in edu:
            school = e.get("school", "")
            loc = e.get("location", "")
            degree = e.get("degree", "")
            year = e.get("year", "")
            doc.add_heading(school + (f" ({loc})" if loc else ""), level=2)
            line2 = degree + (f", {year}" if year else "")
            if line2.strip():
                doc.add_paragraph(line2)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

def _job_heading_parts(job_id):
    """Return (title_text, dates_text, location_text) for a job id."""
    for j in store.list_jobs():
        if j["id"] == job_id:
            title = f"{j['employer']} — {j['role']}"
            start = (j["start_date"] or "").strip()
            end = (j["end_date"] or "").strip()
            dates = f"{start or '?'} \u2013 {end or 'Present'}" if (start or end) else ""
            loc = (j["location"] or "").strip()
            return title, dates, loc
    return "", "", ""

def _job_tag(line):
    """If the line is a [[JOB:id]] tag, return the id (int); else None."""
    m = re.match(r"^\[\[JOB:(\d+)\]\]\s*$", line.strip())
    return int(m.group(1)) if m else None

def _education():
    """Return the stored education list (or empty)."""
    try:
        return json.loads(store.get_setting("education", "[]") or "[]")
    except Exception:
        return []

def _section_header(pdf, title):
    """Draw a section title with a horizontal rule under it."""
    pdf.set_font("Helvetica", "B", 15)
    pdf.multi_cell(0, 8, _ascii(title), new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(2)

def build_pdf(tailored_text):
    """Turn the tailored text into a PDF, returned as bytes."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    name, contact_parts = _contact()
    if name:
        pdf.set_font("Helvetica", "B", 20)
        pdf.multi_cell(0, 9, _ascii(name), new_x="LMARGIN", new_y="NEXT")
    if contact_parts:
        pdf.set_font("Helvetica", "", 10)
        for part in contact_parts:
            pdf.cell(0, 5, _ascii(part), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    drew_experience = False

    for raw in tailored_text.split("\n"):
        line = raw.strip()
        if not line:
            pdf.ln(2); continue
        if _is_rule(line):
            continue
        job_id = _job_tag(line)
        if job_id is not None:
            title, dates, loc = _job_heading_parts(job_id)
            if title:
                if not drew_experience:
                    pdf.ln(2)
                    _section_header(pdf, "Experience")
                    drew_experience = True
                pdf.ln(1)
                pdf.set_font("Helvetica", "B", 13)
                title_w = pdf.get_string_width(_ascii(title)) + 2
                pdf.cell(title_w, 7, _ascii(title))
                pdf.set_font("Helvetica", "", 11)
                pdf.cell(0, 7, _ascii(dates), align="R", new_x="LMARGIN", new_y="NEXT")
                if loc:
                    pdf.set_font("Helvetica", "I", 10)
                    pdf.cell(0, 5, _ascii(loc), align="R", new_x="LMARGIN", new_y="NEXT")
            continue
        if line.startswith("### "):   # fallback if a heading slips through
            pdf.set_font("Helvetica", "B", 13); pdf.multi_cell(0, 7, _ascii(line[4:]), new_x="LMARGIN", new_y="NEXT")
        elif line.startswith("## "):
            _section_header(pdf, line[3:])
        elif line.startswith("- ") or line.startswith("* "):
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 5.5, chr(149) + "  " + _ascii(line[2:]), new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 5.5, _ascii(line), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)
        
    edu = _education()
    if edu:
        pdf.ln(3)
        _section_header(pdf, "Education")
        for e in edu:
            school = e.get("school", "")
            degree = e.get("degree", "")
            loc = e.get("location", "")
            year = e.get("year", "")
            pdf.set_font("Helvetica", "B", 12)
            line1 = school + (f"   ({loc})" if loc else "")
            pdf.multi_cell(0, 6, _ascii(line1), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 11)
            line2 = degree + (f"   {year}" if year else "")
            if line2.strip():
                pdf.multi_cell(0, 6, _ascii(line2), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

    return bytes(pdf.output())

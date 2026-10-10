"""Export helpers: ICS calendar files, complaint letters, and PDF reports."""
import re
from datetime import datetime, timedelta, timezone

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:  # graceful degradation: text export only
    HAS_FPDF = False


# ---------- ICS calendar export ----------

def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _parse_date(value: str):
    """Best-effort date parsing for model-provided strings."""
    value = (value or "").strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", value)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    for fmt in ("%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def build_ics(key_dates: list[dict], title: str = "CivicLens deadlines") -> str:
    """Return ICS text with a reminder (1 day before) for each parseable date."""
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//CivicLens//Deadlines//EN", "CALSCALE:GREGORIAN",
    ]
    for idx, item in enumerate(key_dates or [], 1):
        dt = _parse_date(item.get("date", ""))
        if not dt:
            continue
        label = item.get("label") or "Deadline"
        stamp = dt.strftime("%Y%m%d")
        end = (dt + timedelta(days=1)).strftime("%Y%m%d")
        lines += [
            "BEGIN:VEVENT",
            f"UID:civiclens-{idx}-{stamp}@local",
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{stamp}",
            f"DTEND;VALUE=DATE:{end}",
            f"SUMMARY:{_ics_escape(label)}",
            f"DESCRIPTION:{_ics_escape(title)}",
            "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY",
            f"DESCRIPTION:{_ics_escape(label)}", "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


# ---------- Complaint letter ----------

def draft_letter(report: dict) -> str:
    """Formal complaint letter text from the issue report dict."""
    today = datetime.now().strftime("%d %B %Y")
    location = report.get("location") or "[location]"
    return (
        f"To,\n{report.get('authority') or 'The Commissioner, Municipal Corporation'}\n\n"
        f"Subject: {report.get('title') or 'Civic complaint'} — {report.get('severity', '')} "
        f"issue at {location}\n\n"
        f"Respected Sir/Madam,\n\n"
        f"I wish to report a civic issue of category \"{report.get('issue_type', 'General')}\" "
        f"with {report.get('severity', 'Minor').lower()} severity at the following location:\n"
        f"{location}\n\n"
        f"Description:\n{report.get('description', '')}\n\n"
        f"Urgency: {report.get('urgency', 'Medium')}.\n\n"
        "I request the concerned department to inspect the site and resolve this issue "
        "at the earliest. Kindly acknowledge this complaint and share a reference number.\n\n"
        "Thanking you,\n\n"
        "[Your name]\n[Address]\n[Contact number]\n\n"
        f"Date: {today}\n"
    )


# ---------- PDF report ----------

def _wrap(text: str, width: int = 88) -> list[str]:
    lines = []
    for para in (text or "").split("\n"):
        line = ""
        for word in para.split():
            if len(line) + len(word) + 1 > width:
                lines.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        lines.append(line)
    return lines


def report_sections(analysis: dict, letter: str | None = None, title: str = "CivicLens Report") -> list[str]:
    """Plain-text sections shared by the PDF and text exporters."""
    out = [title, ""]

    def add(label: str, content: str):
        out.append(label)
        out.extend(_wrap(content))
        out.append("")

    add("Category", f"{analysis.get('category', '')}  |  Urgency: {analysis.get('urgency', '')}")
    add("Summary", analysis.get("summary", ""))
    if analysis.get("key_details"):
        add("Key details", "\n".join(f"{k}: {v}" for k, v in analysis["key_details"].items()))
    if analysis.get("key_dates"):
        add("Key dates", "\n".join(f"{d.get('label')}: {d.get('date')}" for d in analysis["key_dates"]))
    if analysis.get("action_items"):
        add("Next steps", "\n".join(f"{i}. {item}" for i, item in enumerate(analysis["action_items"], 1)))
    if analysis.get("glossary"):
        add("Glossary", "\n".join(f"{k} - {v}" for k, v in analysis["glossary"].items()))
    if analysis.get("required_documents"):
        add("Documents to bring", "\n".join(f"- {d}" for d in analysis["required_documents"]))
    if letter:
        add("Draft complaint letter", letter)
    out.append("AI-generated guidance. Verify with official sources.")
    return out


def build_text(analysis: dict, letter: str | None = None) -> str:
    return "\n".join(report_sections(analysis, letter))


def find_unicode_font() -> str | None:
    """Locate a TTF with Indic/Unicode coverage for non-English exports."""
    import glob
    candidates = (
        glob.glob("/usr/share/fonts/**/NotoSans-Regular.ttf", recursive=True)
        + glob.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True)
        + glob.glob("/usr/share/fonts/**/LiberationSans-Regular.ttf", recursive=True)
        + glob.glob("/usr/share/fonts/**/*Sans-Regular.ttf", recursive=True)
    )
    for path in candidates:
        name = path.lower()
        # Prefer fonts with broad Latin+Unicode coverage; skip script-specific
        # fonts (a Devanagari-only font renders Latin text as missing glyphs).
        if not any(code in name for code in ("devanagari", "tamil", "kannada", "telugu",
                                             "lao", "khmer", "tai", "gothic", "cjk", "adwaita")):
            return path
    return candidates[0] if candidates else None


def build_pdf(analysis: dict, letter: str | None = None, title: str = "CivicLens Report") -> bytes:
    """PDF via fpdf2. Uses a system Unicode font when available so Hindi,
    Tamil, Kannada, Telugu, and Marathi summaries render correctly."""
    if not HAS_FPDF:
        raise RuntimeError("fpdf2 is not installed")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    font_path = find_unicode_font()
    if font_path:
        try:
            pdf.add_font("civic", "", font_path)
            pdf.set_font("civic", size=11)
        except RuntimeError:
            pdf.set_font("Courier", size=10)
    else:
        pdf.set_font("Courier", size=10)
    for line in report_sections(analysis, letter, title):
        if line.strip() and line == line.strip() and len(line) < 30 and not line.startswith(" "):
            pdf.set_font_size(13) if not line[0].isdigit() else pdf.set_font_size(11)
        pdf.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())

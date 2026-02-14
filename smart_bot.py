# smart_bot.py
import os
import re
import pdfplumber

# =========================
# Configuration
# =========================
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "Weekly Progress Reports")

HEADERS = {
    "completed": [
        "What did you do this week?",
        "What have you done this week?"
    ],
    "next": [
        "What are you going to do next week?",
        "Next week"
    ],
    "blockers": [
        "Blockers",
        "Blockers, things you want to flag, problems, etc."
    ]
}

STOP_HEADERS = [
    "Abstracts",
    "Abstract",
    "References",
    "Reference Article",
    "Summary",
    "What did you do and prove it",
    "Proof of Progress",
    "Visualization Validation"
]

ALL_HEADERS = sum(HEADERS.values(), [])

SECTION_ICONS = {
    "Completed": "✅",
    "In Progress": "🔄",
    "Blockers": "⚠️"
}

# =========================
# PDF Text Extraction
# =========================
def extract_text_from_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            pages = [p.extract_text() for p in pdf.pages if p.extract_text()]
            return "\n".join(pages)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""

# =========================
# Section Extraction
# =========================
def extract_section(text, header_keywords):
    for header in header_keywords:
        stop_headers = [h for h in (ALL_HEADERS + STOP_HEADERS) if h.lower() != header.lower()]
        stop_pattern = "|".join(r"^\s*" + re.escape(h) for h in stop_headers)
        pattern = r"^\s*" + re.escape(header) + r"\s*(.*?)" + r"(?=(" + stop_pattern + r")|\Z)"
        match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if not match:
            continue

        content = match.group(1).strip()
        lines = []

        for line in content.split("\n"):
            line = line.strip()
            # Skip empty or leftover header lines / email / week info
            if not line or re.search(r"things you want to flag|Week \d+|@\w+", line, re.I):
                continue
            # Remove bullets
            line = re.sub(r"^[•\-●]\s*", "", line)
            # Collapse internal spaces
            line = re.sub(r"\s+", " ", line)
            lines.append(line)

        # Smart merging
        merged = ""
        for l in lines:
            if merged:
                if merged[-1] in ".!?":
                    merged += " " + l
                else:
                    merged += ". " + l
            else:
                merged = l

        merged = merged.strip()
        if merged and merged[-1] not in ".!?":
            merged += "."

        return merged or "None"

    return "None"

# =========================
# Report Parsing
# =========================
def parse_report(file_path):
    text = extract_text_from_pdf(file_path)
    completed = extract_section(text, HEADERS["completed"])
    next_week = extract_section(text, HEADERS["next"])
    blockers = extract_section(text, HEADERS["blockers"])
    return completed, next_week, blockers

# =========================
# Latest Week Selection
# =========================
def get_latest_week_files():
    latest_week = -1
    week_files = []
    for file in os.listdir(REPORTS_DIR):
        match = re.search(r"Week(\d+)", file)
        if not match:
            continue
        week_num = int(match.group(1))
        if week_num > latest_week:
            latest_week = week_num
            week_files = [file]
        elif week_num == latest_week:
            week_files.append(file)
    return latest_week, week_files

# =========================
# Build Smart Summary
# =========================
def build_summary(latest_week, files):
    summary = f"*Week {latest_week} Progress Summary*\n\n"
    sections = {"Completed": [], "In Progress": [], "Blockers": []}

    for file in files:
        name_match = re.search(r"Week\d+-(.*)\.pdf", file)
        name = name_match.group(1) if name_match else file
        completed, next_week, blockers = parse_report(os.path.join(REPORTS_DIR, file))

        # Full updates for Completed and In Progress
        sections["Completed"].append(f"- *{name}*: {completed}")
        sections["In Progress"].append(f"- *{name}*: {next_week}")

        # Only include meaningful blockers
        blockers_clean = blockers.strip().lower()
        if not re.fullmatch(r"(none|no|na|n/a|no blockers)?\.?", blockers_clean):
            sections["Blockers"].append(f"- *{name}*: {blockers}")

    for section, items in sections.items():
        summary += f"{SECTION_ICONS.get(section,'')} {section}:\n"
        if items:
            summary += "\n".join(items)
        else:
            # Optional: indicate no blockers at all
            if section == "Blockers":
                summary += "• None"
            else:
                summary += "• None reported"
        summary += "\n\n"

    return summary.strip()


# bot.py

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


# =========================
# PDF Text Extraction
# =========================

def extract_text_from_pdf(file_path):
    """Extract raw text from a PDF."""
    try:
        with pdfplumber.open(file_path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n".join(pages)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""


# =========================
# Section Extraction
# =========================

def extract_section(text, header_keywords):
    """Extract section text based on header keywords, stops at next header or stop header."""
    for header in header_keywords:
        stop_headers = [
            h for h in (ALL_HEADERS + STOP_HEADERS)
            if h.lower() != header.lower()
        ]

        stop_pattern = "|".join(
            r"^\s*" + re.escape(h) for h in stop_headers
        )

        pattern = (
            r"^\s*" + re.escape(header) +
            r"\s*(.*?)" +
            r"(?=(" + stop_pattern + r")|\Z)"
        )

        match = re.search(
            pattern,
            text,
            flags=re.DOTALL | re.IGNORECASE | re.MULTILINE
        )

        if not match:
            continue

        content = match.group(1)

        # Remove leaked header suffix text (fix Blockers issue)
        for h in header_keywords:
            suffix = h.replace("Blockers", "").strip()
            if suffix:
                content = re.sub(
                    r"^\s*,?\s*" + re.escape(suffix),
                    "",
                    content,
                    flags=re.IGNORECASE
                )

        content = content.strip()

        # Normalize bullets and clean lines
        lines = []
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            line = line.lstrip("•-● ").strip()
            lines.append(line)

        if lines:
            return " • ".join(lines)

    return "None"


# =========================
# Report Parsing
# =========================

def parse_report(file_path):
    """Parse a single PDF report."""
    text = extract_text_from_pdf(file_path)

    completed = extract_section(text, HEADERS["completed"])
    next_week = extract_section(text, HEADERS["next"])
    blockers = extract_section(text, HEADERS["blockers"])

    return completed, next_week, blockers


# =========================
# File Selection
# =========================

def get_latest_week_files():
    """Return only the reports from the latest week."""
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
# Summary Builder
# =========================

def build_summary(latest_week, files):
    summary = f"*Week {latest_week} Progress Summary*\n\n"

    sections = {
        "Completed": [],
        "In Progress": [],
        "Blockers": []
    }

    for file in files:
        name_match = re.search(r"Week\d+-(.*)\.pdf", file)
        name = name_match.group(1) if name_match else file

        completed, next_week, blockers = parse_report(
            os.path.join(REPORTS_DIR, file)
        )

        sections["Completed"].append(f"- {name}: {completed}")
        sections["In Progress"].append(f"- {name}: {next_week}")
        sections["Blockers"].append(f"- {name}: {blockers}")

    for section, items in sections.items():
        if section == "Completed":
            summary += "✅ Completed:\n"
        elif section == "In Progress":
            summary += "🔄 In Progress:\n"
        else:
            summary += "⚠️ Blockers:\n"

        summary += "\n".join(items) + "\n\n"

    return summary


# =========================
# Entry point for Slack runner
# =========================

def main():
    """Call this from slack_runner.py"""
    latest_week, files = get_latest_week_files()
    if not files:
        return "No reports found for the latest week."

    return build_summary(latest_week, files)


# =========================
# local test
# =========================

if __name__ == "__main__":
    print(main())

"""Generate the hackathon deliverables with the same Gemini pipeline as the web app.

Usage (from the repo root): python submission/generate_submission.py
Writes submission/submission.txt and submission/anonymized_document.pdf.
Uses the pipeline in submission/app (the same code as the web app).
Requires GEMINI_API_KEY in the environment or submission/app/.env.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "app"))

from anonymizer import process_file  # noqa: E402

SOURCE = HERE.parent / "raw_data" / "document_to_anonymize.pdf"


def main():
    result = process_file(SOURCE.read_bytes(), "pdf")
    if result["engine"] != "gemini":
        sys.exit("Gemini unavailable: check GEMINI_API_KEY (refusing to write a rules-only submission).")
    (HERE / "submission.txt").write_text(result["censored"] + "\n", encoding="utf-8", newline="\n")
    (HERE / "anonymized_document.pdf").write_bytes(result["file"])
    print(f"Done: {result['count']} words censored with Gemini")


if __name__ == "__main__":
    main()

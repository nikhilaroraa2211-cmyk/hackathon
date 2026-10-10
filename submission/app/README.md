# Redactor – how the app works

Redactor is a small web app that censors personal and sensitive data in a document and gives you back **the same format** (PDF in → PDF out, Word in → Word out, TXT in → TXT out). Every sensitive word is replaced by a `*`.

## Quick start

```powershell
pip install -r submission/app/requirements.txt
copy submission\app\.env.example submission\app\.env   # then put your Gemini API key in it
python submission/app/server.py
```

Open <http://127.0.0.1:8000/>, then drag & drop a file or press **Upload from device**.

`.env` is git-ignored. Never commit your key.

## What happens to a file

```
Browser (static/)  ──POST /api/anonymize──▶  server.py  ──▶  anonymizer.py  ──▶  llm.py ──▶ Gemini API
        ◀── JSON: censored file (base64) + original/censored text + engine ──┘
```

1. **Upload** – `static/app.js` sends the file to `POST /api/anonymize`. `server.py` accepts only `.pdf`, `.docx` and `.txt`, up to 10 MB, and stores nothing.
2. **Extract text** – `anonymizer.py` reads the text of the file.
3. **Detect** – `llm.py` sends the text to Gemini with a system prompt (GDPR expert), one few-shot example, temperature 0 and a JSON-schema response. Gemini returns the exact strings that identify a person or are sensitive: names, IDs, contacts, IPs, passwords, dates of birth, financial and health data, and so on. It is told to keep section labels and non-personal content such as streets, monuments, fictional characters and product codes.
4. **Safety net** – `anonymizer.py` also always masks IP addresses, e-mails and digit runs split by spaces, whatever Gemini returns.
5. **Mask** – every occurrence of each detected string is hidden, one `*` per word (case and accent-insensitive).
6. **Return** – the file is rebuilt in its own format and shown next to the original in the UI, with a download button.

If Gemini is unavailable, the app falls back to built-in regex rules. The UI shows which engine was used.

## How each format is handled

| Format | Method | Result |
|---|---|---|
| **PDF** | Redacts **in place** with PyMuPDF | Layout, tables, fonts and images stay. The underlying text is removed, not just covered. Each hidden word gets a `*` drawn on a light grey bar, which closes the gaps between masked words. |
| **DOCX** | Edits the paragraphs and table cells with python-docx | Styles and tables stay. A paragraph that gets censored is rewritten into its first run, so mixed formatting inside that paragraph is lost. |
| **TXT** | Replaces the text directly | Plain text out. |

## Files

| File | Role |
|---|---|
| `server.py` | Local HTTP server (127.0.0.1:8000): serves `static/` and `POST /api/anonymize`. |
| `anonymizer.py` | Text extraction, term masking, regex fallback and per-format output. |
| `llm.py` | Gemini client: system prompt, few-shot example, key and model loading, retries. |
| `static/index.html`, `style.css`, `app.js` | The UI: drop zone, upload button, progress, side-by-side preview, download. |
| `requirements.txt` | `pymupdf`, `python-docx`. |
| `.env.example` | Template for `GEMINI_API_KEY` and `GEMINI_MODEL`. |

## Configuration

Set in `submission/app/.env` or in the environment:

- `GEMINI_API_KEY` – your key (required for Gemini detection).
- `GEMINI_MODEL` – defaults to `gemini-3.1-flash-lite` in the code. Use another model if yours is slow or out of quota.

## Limits

- The text is sent to the Gemini API, so the app is not fully offline. Nothing is stored by the app.
- Gemini is a language model, so the exact list of detected terms can vary slightly between runs.
- Scanned or image-only PDFs have no text layer and cannot be redacted.
- PyMuPDF is AGPL-licensed.

## Regenerating the hackathon submission

```powershell
python submission/generate_submission.py
```

This runs the same pipeline on `raw_data/document_to_anonymize.pdf` and writes `submission/submission.txt` and `submission/anonymized_document.pdf`. It refuses to write if Gemini is unavailable.

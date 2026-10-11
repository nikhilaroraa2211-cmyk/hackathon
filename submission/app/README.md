# Redactor – how the app works

Redactor is a small web app that censors personal and sensitive data in documents and images, then gives you back **the same format** (PDF in → PDF out, Word in → Word out, TXT in → TXT out). Text-based documents use `*` marks; images use solid black bars.

## Quick start

```powershell
pip install -r submission/app/requirements.txt
python submission/app/server.py
```

If no key is configured, starting the server in a terminal prompts for your Gemini API key without displaying or saving it. From the repository root, open <http://127.0.0.1:8000/>, then drag & drop a file or press **Upload from device**.

Alternatively, from `submission/app`, copy `.env.example` to `.env` and add your key there, or set `GEMINI_API_KEY` as an environment variable. `.env.example` is a public template: do not put a real key in it or commit your key. Hosted deployments should set the key in the host's private environment-variable settings.

## What happens to a file

```
Browser (static/)  ──POST /api/anonymize──▶  server.py  ──▶  anonymizer.py  ──▶  llm.py ──▶ Gemini API
        ◀── JSON: censored file (base64) + original/censored text + engine ──┘
```

1. **Upload** – `static/app.js` sends the file to `POST /api/anonymize`. `server.py` accepts only `.pdf`, `.docx`, `.txt`, `.png`, `.jpg` and `.jpeg`, up to 10 MB, and stores nothing.
2. **Extract text** – `anonymizer.py` reads the text of the file.
3. **Detect** – `llm.py` sends the text to Gemini with a system prompt (GDPR expert), one few-shot example, temperature 0 and a JSON-schema response. Gemini returns the exact strings that identify a person or are sensitive: names, IDs, contacts, IPs, passwords, dates of birth, financial and health data, and so on. It is told to keep section labels and non-personal content such as streets, monuments, fictional characters and product codes.
4. **Safety net** – local label and pattern rules run whether or not Gemini responds, so Gemini omissions do not skip obvious sensitive fields. Numeric dates, written month dates, standalone years, IP addresses, e-mails and digit runs split by spaces are also masked locally.
5. **Mask** – every occurrence of each detected string is hidden, one `*` per word (case and accent-insensitive).
6. **Return** – the file is rebuilt in its own format and shown next to the original in the UI, with a download button.

If Gemini is unavailable, the app falls back to built-in regex rules. The UI shows which engine was used.

## How each format is handled

| Format | Method | Result |
|---|---|---|
| **PDF** | Redacts **in place** with PyMuPDF | Layout, tables, fonts and images stay. The underlying text is removed, not just covered. Each hidden word gets a `*` drawn on a light grey bar, which closes the gaps between masked words. |
| **PNG / JPG** | Local OCR (RapidOCR) finds each word with exact boxes; the sensitive ones are painted black. Gemini vision adds faces, signatures, barcodes and QR codes. | The pixels are really overwritten. Tilted text gets axis-aligned boxes. No WebP/BMP. |
| **Scanned PDF** | Image-only pages are rendered, OCR'd and redacted; the image pixels under black bars are destroyed with PyMuPDF `apply_redactions`. | Text-layer content is redacted in place. |
| **DOCX** | Edits the paragraphs and table cells with python-docx | Styles and tables stay. A paragraph that gets censored is rewritten into its first run, so mixed formatting inside that paragraph is lost. |
| **TXT** | Replaces the text directly | Plain text out. |

## Files

| File | Role |
|---|---|
| `server.py` | Local HTTP server (127.0.0.1:8000): serves `static/` and `POST /api/anonymize`. |
| `anonymizer.py` | Text extraction, term masking, regex fallback and per-format output. |
| `llm.py` | Gemini client: system prompt, few-shot example, key and model loading, retries. |
| `static/index.html`, `style.css`, `app.js` | The UI: drop zone, upload button, progress, side-by-side preview, download. |
| `requirements.txt` | `pymupdf`, `python-docx`, `rapidocr`, `onnxruntime` (OCR runs locally; first image takes longer while models load). |
| `.env.example` | Template for `GEMINI_API_KEY` and `GEMINI_MODEL`. |

## Configuration

Set in `submission/app/.env` or in the environment:

- `GEMINI_API_KEY` – your key (required for Gemini detection).
- `GEMINI_MODEL` – defaults to `gemini-3.1-flash-lite` in the code. Use another model if yours is slow or out of quota.

## Choosing what to keep

Before uploading, the page has a **Keep visible** panel: tick categories (names and places, dates, numbers and IDs, e-mails, faces and signatures in images) and/or type specific words to keep (comma separated). The choice is sent in the `X-Keep` header as JSON (`{"categories": [...], "terms": [...]}`) and applied after detection, so a kept word is simply not censored. If a kept word sits inside a longer detected term, only the rest of the term is censored.

## Limits

- The text is sent to the Gemini API, so the app is not fully offline. Nothing is stored by the app.
- Gemini is a language model, so the exact list of detected terms can vary slightly between runs.
- OCR supports image-only and scanned PDFs. OCR can miss text, and boxes on tilted text are axis-aligned. Standalone WebP and BMP images are not supported.
- PyMuPDF is AGPL-licensed.

## Regenerating the hackathon submission

```powershell
python submission/generate_submission.py
```

This runs the same pipeline on `raw_data/document_to_anonymize.pdf` and writes `submission/submission.txt` and `submission/anonymized_document.pdf`. It refuses to write if Gemini is unavailable.

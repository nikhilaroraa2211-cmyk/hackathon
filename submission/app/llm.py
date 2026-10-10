"""Gemini-based detector of sensitive text spans (prompt-engineered, few-shot).

The API key is read from the GEMINI_API_KEY environment variable or app/.env
(git-ignored). It is never logged or sent to the browser.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent / ".env"
DEFAULT_MODEL = "gemini-3.1-flash-lite"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = """You are a privacy and data-protection (GDPR) expert. You receive a document \
(any language, mostly Portuguese) and must list every piece of text that identifies a person or is \
sensitive, so it can be censored.

MUST be listed:
- Names of people (full names AND every partial form that appears, e.g. "Maria Santos", "Maria", "João"), including doctors and relatives.
- Identifiers: reference/case numbers, tax IDs (NIF), ID card, passport, social security, insurance policy numbers, professional licence numbers.
- Contact data: addresses, phone numbers, emails, IP addresses (IPv4/IPv6), usernames, social-media handles and profile URLs.
- Credentials: passwords (including temporary ones), tokens, PINs.
- Identifiers written with spaces or separators between the characters (e.g. "2 4 6 8 1 3 5 7 9") must be returned exactly as written.
- Dates of birth, ages of people, and other dates that identify a person (not the generic document date unless it identifies the person).
- Financial data: card numbers with expiry/CVV, income, bank accounts, IBAN.
- Biometric IDs and physical data tied to the person: fingerprint/face IDs, height, weight, blood type, blood pressure readings.
- Special-category data: infection status such as HIV, genetic mutations/results, religion, marital status, sex/gender, substance-dependence treatment, family-member details, occupation and employer.
- Insurance plan names and policy numbers.
- Everything in a record about a specific person (e.g. a table row of employee data): employee/record IDs, city of residence, \
salary, and any health, sick-leave, disciplinary, criminal, immigration, union or sexual-orientation notes, including the \
words that describe them.

MUST NOT be listed (keep so the document stays meaningful):
- Section titles and field labels (e.g. "Nome:", "Telefone:").
- The organisation name, generic clinical text, routine diagnoses, exams and medications, symptoms, durations ("há 5 anos").
- Things that are not about a real, identifiable person: fictional or cartoon characters, monuments, streets, \
cities and countries mentioned as general geography, companies, product/batch/order codes, version numbers, coordinates, generic postal codes, \
generic date ranges and counters. If the document itself says a name is not a person, do not list it.

RULES:
1. Return each item EXACTLY as written in the document (same characters, accents, spacing), as short as possible but complete for that item (a whole phone number, a whole name).
2. Do not include the field label, only the value.
3. Be exhaustive: when unsure whether something identifies or exposes a person, include it.
4. Output only a JSON array of strings, no commentary."""

FEW_SHOT_INPUT = """Nome: Rui Almeida
Morada: Rua do Sol, 5, Porto
Telefone: +351 911 000 111
O paciente Rui, de 52 anos, é ateu e tem hipertensão. Contacto: rui.a@mail.com
Cartão de crédito: 5500 0000 0000 0004 (validade 01/30, CVV 999)
Médico: Dra. Sofia Lima, CRM 55555-PT
Exames: hemograma completo."""

FEW_SHOT_OUTPUT = json.dumps([
    "Rui Almeida", "Rua do Sol, 5, Porto", "+351 911 000 111", "Rui", "52 anos", "ateu",
    "rui.a@mail.com", "5500 0000 0000 0004", "01/30", "999", "Sofia Lima", "55555-PT",
], ensure_ascii=False)


def _load_key() -> tuple[str | None, str]:
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip('"\'')
    key = os.environ.get("GEMINI_API_KEY") or values.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL") or values.get("GEMINI_MODEL") or DEFAULT_MODEL
    return key, model


def is_configured() -> bool:
    return bool(_load_key()[0])


def detect_sensitive(text: str) -> list[str] | None:
    """Return the sensitive substrings found by Gemini, or None if unavailable."""
    key, model = _load_key()
    if not key or not text.strip():
        return None

    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {"role": "user", "parts": [{"text": FEW_SHOT_INPUT}]},
            {"role": "model", "parts": [{"text": FEW_SHOT_OUTPUT}]},
            {"role": "user", "parts": [{"text": text}]},
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
    }
    payload = _post(body, key, model)
    if payload is None:
        return None
    try:
        items = json.loads(payload["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, ValueError):
        return None
    return [s for s in items if isinstance(s, str) and s.strip()]


def _post(body: dict, key: str, model: str) -> dict | None:
    req = urllib.request.Request(
        ENDPOINT.format(model=model),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            return None
        except (OSError, TimeoutError, ValueError):
            return None
    return None


IMAGE_PROMPT = """You receive an IMAGE (document scan, photo or screenshot). Text is handled elsewhere: ignore all text. \
Find only the NON-TEXT items that identify a person: human faces, photos of people (ID photos, portraits), handwritten signatures, \
fingerprints, barcodes and QR codes. Return "text" = "[face]", "[signature]", "[fingerprint]" or "[code]" and "box_2d" = \
[ymin, xmin, ymax, xmax], integers normalised to 0-1000 relative to the full image, covering the whole item. \
If there are none, return an empty array. Output only a JSON array of objects, no commentary."""

IMAGE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING"},
            "box_2d": {"type": "ARRAY", "items": {"type": "INTEGER"}},
        },
        "required": ["text", "box_2d"],
    },
}


def detect_in_image(image: bytes, mime: str) -> list[dict] | None:
    """Return [{"text", "box"}] (box = ymin, xmin, ymax, xmax in 0-1000) or None if unavailable."""
    key, model = _load_key()
    if not key:
        return None
    body = {
        "systemInstruction": {"parts": [{"text": IMAGE_PROMPT}]},
        "contents": [{"role": "user", "parts": [
            {"inlineData": {"mimeType": mime, "data": base64.b64encode(image).decode()}},
            {"text": "Return the sensitive items with their boxes."},
        ]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                             "responseSchema": IMAGE_SCHEMA},
    }
    payload = _post(body, key, model)
    if payload is None:
        return None
    try:
        items = json.loads(payload["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, ValueError):
        return None
    out = []
    for it in items:
        box = it.get("box_2d") if isinstance(it, dict) else None
        if isinstance(box, list) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box):
            out.append({"text": str(it.get("text", "")), "box": [max(0, min(1000, v)) for v in box]})
    return out

# NOS Gen-AI Hackathon

Welcome to the official repository for the NOS Gen-AI Hackathon, part of the SCAILE initiative! In this repository, you will find essential resources including the official hackathon rules, code snippets, and examples designed to facilitate your development process. Additionally, we provide a baseline structure to guide you in addressing the proposed challenge effectively.

## 0. Problem Statement and Evaluation Criteria

For a complete description of the problem statement and the detailed evaluation criteria, refer to this [document](tutorials/problem_and_eval.md).

The document to be anonymized is located at [`raw_data/document_to_anonymize.pdf`](raw_data/document_to_anonymize.pdf).

## 1. Prerequisites
Before participating in the hackathon, please ensure that you meet the following prerequisites. Having the needed accounts and accesses will help streamline your development process and facilitate the use of necessary tools and APIs.

### 1.1. GitHub Account

Make sure you have an active GitHub account at [Create a GitHub Account](https://github.com/signup)

### 1.2. Google Account

You'll need an active Google account to access Google AI tools at [Create a Google Account](https://accounts.google.com/signup)

### 1.3. Set Up Your Google API Key

To generate your API key:

a. Go to [Google AI Studio](https://aistudio.google.com/) and log in with your Google account.  
b. Click on the **“Get API Key”** button.  
c. Select **“Create API key”** (or **“Criar chave de API”** if in Portuguese).  
d. A window will open where you’ll create an API key under a new project.  
e. **Important:** Save the generated API key in a safe place — you'll need it later!

## 2. Setup
In this section, we'll walk you through the essential setup steps needed to get started with your project. Follow these instructions carefully!

### 2.1. Git tutorial

If you're new to Git, it’s important to understand how to manage your code effectively. To help you get started, we have provided a Git tutorial at [Git Tutorial](tutorials/git_tutorial.md). This tutorial will guide you through the fundamental concepts and commands you'll need to commit your changes and collaborate with your team.

## 3. Utils

This section contains helpful resources and tools to support your work.

### 3.1. Getting Started with Gemini API

If you're looking for **detailed steps**, including how to obtain an API key and example usage, please refer to the full tutorial at [Gemini 2.0 Tutorial](tutorials/gemini_tutorial.md)

### 3.2. Document Conversion Methods

Converting PDF documents to text can be essential for leveraging existing content in your project. There are methods and tools available for this conversion, which you can explore in detail in the [PDF to Text Guide](tutorials/pdf__to__txt.ipynb).


## 4. Submission Guidelines

In this section, we will outline the expectations for project submission. Understanding these guidelines is crucial to ensure your work is evaluated correctly. There are specific methods and criteria for submission, which you should follow closely to enhance your chances of success. Make sure to read through the following points carefully.
For more detailed information on the submission process and what is expected, please refer to the [Submission Process Guide](submission/README.md).

## 5. Web App (Redactor)

Interactive front end (HTML/CSS/JS) + small Python server. Upload a PDF, DOCX or TXT file and get the same format back with personal data censored (each sensitive word becomes `*`).

```bash
pip install -r submission/app/requirements.txt
copy submission\app\.env.example submission\app\.env   # then put your Gemini API key in submission\app\.env (git-ignored, never commit it)
python submission/app/server.py
# open http://127.0.0.1:8000
```

- `submission/app/llm.py` - Gemini detector: a prompt-engineered (system prompt + few-shot example) call that returns the exact sensitive strings; temperature 0, JSON schema output
- `submission/app/anonymizer.py` - masks the strings Gemini returns (one `*` per word) per format; falls back to built-in regex rules if Gemini is unavailable
- `submission/app/server.py` - static files + `POST /api/anonymize` (max 10 MB, nothing is stored; detection calls the Gemini API)
- `submission/app/static/` - drag & drop UI with original vs censored preview and download

Libraries: PyMuPDF (PDFs are redacted in place, so tables and layout are preserved; AGPL-licensed), python-docx.


### Regenerating the hackathon submission

```bash
python submission/generate_submission.py   # needs GEMINI_API_KEY in submission/app/.env
```

Writes `submission/submission.txt` (the text to be evaluated) and `submission/anonymized_document.pdf` using the same Gemini pipeline as the web app. The exact prompt is in `submission/prompt.txt`.

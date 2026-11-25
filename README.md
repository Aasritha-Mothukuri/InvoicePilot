# InvoicePilot

**Account-Based Agentic AI Invoice Processing and Payment Tracking Application**

InvoicePilot is a Streamlit-based application that helps users upload, process, validate, and track invoices using AI.

## What is included

- Streamlit application with Supabase email/password authentication.
- Supabase PostgreSQL database protected by Row Level Security (RLS).
- PDF text extraction using PyMuPDF.
- Gemini as the primary LLM and optional Groq provider.
- Single-agent plan, extract, and validate workflow.
- User-scoped retrieval (lightweight lexical RAG) for invoice question answering.
- Payment status updates and reminder draft generation.
- Sample text-based PDF invoices, tests, project report, and presentation.

## Project structure

- `app.py` – Main Streamlit application.
- `invoicepilot/` – Authentication, database, agent, and PDF processing modules.
- `requirements.txt` – Python dependencies.
- `tests/` – Project tests.
- `.streamlit/secrets.toml` – Local application secrets (not included in GitHub).

## Quick start

For Windows installation and setup instructions, see [SETUP_WINDOWS.md](SETUP_WINDOWS.md).

## Important notes

- Never commit `.streamlit/secrets.toml`, API keys, or other credentials.
- The application does not send emails or process actual payments.
- Invoice text is sent to the configured LLM provider for AI extraction and question answering.
- The current version supports text-based PDFs. Scanned PDFs requiring OCR are not supported.
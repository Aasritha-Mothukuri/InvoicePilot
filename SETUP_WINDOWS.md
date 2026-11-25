# Windows setup — beginner instructions

## 1. Install Python
Install Python 3.11.x from https://www.python.org/downloads/ and tick **Add Python to PATH**.
Open Windows Terminal or Command Prompt. Run:
```bat
py -3.11 --version
```

## 2. Create the Supabase project
1. Visit https://supabase.com/ and create a free project.
2. In Project Settings → API, copy the Project URL and the `anon` / publishable key. Do NOT use the service_role key.
3. Open SQL Editor, paste all contents of `supabase/schema.sql`, and click Run.
4. In Authentication → Providers, enable Email. For a quick classroom demo you may disable email confirmation; for real use keep confirmation enabled.
5. In Authentication → URL Configuration, set the local site URL to `http://localhost:8501`.

## 3. Configure secrets
Copy `.streamlit\secrets.example.toml` to `.streamlit\secrets.toml`.
Open the new `secrets.toml` in Notepad and replace placeholders with your keys. Keep the file private. Choose `LLM_PROVIDER = "gemini"` and add your Gemini key. Groq is optional: set provider to `groq` and add the Groq key if needed.

Get Gemini key: https://aistudio.google.com/app/apikey
Get Groq key: https://console.groq.com/keys

## 4. Install and run
Open Command Prompt in the extracted InvoicePilot folder. Run these commands one at a time:
```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```
The app opens at http://localhost:8501. Create an account, log in, and try the sample PDFs in `sample_invoices`.

## 5. Test
In the activated terminal:
```bat
pytest -q
```
Manual test: register two accounts; upload a sample invoice in account A; confirm it appears in A; log into account B and confirm it is absent; change status to Paid; ask the assistant about pending/overdue invoices; generate a reminder draft.

## 6. Deployment
For a simple demo, Streamlit Community Cloud can deploy this GitHub repository. Add the five secret values in App → Settings → Secrets. Do not upload your local secrets file. Keep Supabase RLS enabled. Deployment providers and free-tier limits can change; verify current terms before submission.

## Troubleshooting
- `py` not found: reinstall Python and select Add Python to PATH.
- Supabase relation missing: rerun `supabase/schema.sql` in SQL Editor.
- Invalid API key: re-copy the key into secrets.toml, without extra quotes inside the value.
- Gemini model/provider error: switch to Groq only if a valid Groq key is configured.
- Scanned PDF has no text: this version supports text-based PDFs, not OCR.
- Login confirmation: check email or disable confirmation only for a controlled academic demo.

## Privacy and safety
The app uses the Supabase anon key plus user JWT and RLS. Never put a service-role key in Streamlit secrets. PDF extracted text and invoice questions can be sent to Gemini or Groq. Use synthetic data in demonstrations. No payment execution or email delivery is implemented.

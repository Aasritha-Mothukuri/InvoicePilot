
import json
import math
import re
from datetime import date, datetime
from .config import settings


# ============================================================
# SYSTEM PROMPTS
# ============================================================

EXTRACTION_SYSTEM = """
You are InvoicePilot's invoice processing assistant.

Extract invoice information from the supplied text.
Return ONLY one valid JSON object.

Never invent missing information.
Use null for unknown fields.

Required JSON fields:
invoice_number
customer_name
invoice_date
due_date
subtotal
tax_amount
total_amount
currency

Rules:
- Dates must use YYYY-MM-DD.
- Amounts must be numeric values, not strings.
- Currency must be a three-letter code such as INR or USD.
- Use the customer/bill-to name as customer_name where clear.
- Do not calculate or guess missing invoice values.
"""

GENERAL_SYSTEM = """
You are InvoicePilot, an AI assistant for invoice management.

Answer clearly and accurately.
Use only the invoice records and conversation context supplied.
Never invent invoice details.
If the available information is insufficient, say so.
"""


# ============================================================
# LLM PROVIDER MANAGEMENT
# ============================================================

def _llm(prompt, system_prompt=GENERAL_SYSTEM):
    """
    Calls the configured primary LLM provider.
    Automatically attempts the secondary provider if needed.
    """

    providers = {
        "gemini": bool(settings.gemini_key),
        "groq": bool(settings.groq_key)
    }

    primary = settings.provider

    if primary not in providers:
        primary = "gemini"

    order = [
        primary,
        "groq" if primary == "gemini" else "gemini"
    ]

    errors = []

    for provider in order:

        if not providers[provider]:
            continue

        try:

            if provider == "gemini":

                from google import genai

                client = genai.Client(
                    api_key=settings.gemini_key
                )

                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=(
                        system_prompt
                        + "\n\n"
                        + prompt
                    )
                )

                result = response.text

            else:

                from groq import Groq

                client = Groq(
                    api_key=settings.groq_key
                )

                response = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0
                )

                result = response.choices[0].message.content

            if not result:
                raise RuntimeError(
                    f"{provider} returned an empty response."
                )

            return result.strip()

        except Exception as error:

            errors.append(
                f"{provider.upper()}: {error}"
            )

    if not errors:
        raise RuntimeError(
            "No AI provider is configured. "
            "Check GEMINI_API_KEY and GROQ_API_KEY."
        )

    raise RuntimeError(
        "Both AI providers failed or are unavailable:\n"
        + "\n".join(errors)
    )


# ============================================================
# JSON RESPONSE PARSER
# ============================================================

def _json_from_text(text):
    """
    Extracts a JSON object from an LLM response.
    """

    text = text.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.I
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    match = re.search(
        r"\{.*\}",
        text,
        re.S
    )

    if not match:
        raise ValueError(
            "AI did not return a valid JSON object."
        )

    result = json.loads(match.group())

    if not isinstance(result, dict):
        raise ValueError(
            "AI response must be a JSON object."
        )

    return result


# ============================================================
# INVOICE VALIDATION
# ============================================================

def validate(invoice):
    """
    Validates required invoice fields, dates and amounts.
    Returns a list of validation errors.
    """

    errors = []

    required_fields = [
        "invoice_number",
        "customer_name",
        "total_amount"
    ]

    for field in required_fields:

        value = invoice.get(field)

        if value is None or str(value).strip() == "":
            errors.append(
                f"Missing required field: {field}"
            )

    # Validate numerical amounts.

    amount_fields = [
        "subtotal",
        "tax_amount",
        "total_amount"
    ]

    for field in amount_fields:

        value = invoice.get(field)

        if value is None:
            continue

        try:

            if isinstance(value, bool):
                raise ValueError()

            number = float(value)

            if not math.isfinite(number):
                raise ValueError()

            if number < 0:
                errors.append(
                    f"{field} cannot be negative."
                )

            invoice[field] = number

        except (ValueError, TypeError, OverflowError):

            errors.append(
                f"{field} must be a valid number."
            )

    # Validate dates.

    parsed_dates = {}

    for field in ("invoice_date", "due_date"):

        value = invoice.get(field)

        if value in (None, ""):
            continue

        try:

            parsed_dates[field] = date.fromisoformat(
                str(value)
            )

        except (ValueError, TypeError):

            errors.append(
                f"{field} must use YYYY-MM-DD format."
            )

    # Due date cannot precede invoice date.

    if (
        "invoice_date" in parsed_dates
        and "due_date" in parsed_dates
    ):

        if (
            parsed_dates["due_date"]
            < parsed_dates["invoice_date"]
        ):

            errors.append(
                "Due date cannot be before invoice date."
            )

    # Check subtotal + tax = total.

    values = [
        invoice.get("subtotal"),
        invoice.get("tax_amount"),
        invoice.get("total_amount")
    ]

    if all(value is not None for value in values):

        if all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            for value in values
        ):

            calculated_total = (
                invoice["subtotal"]
                + invoice["tax_amount"]
            )

            if abs(
                calculated_total
                - invoice["total_amount"]
            ) > 0.02:

                errors.append(
                    "Subtotal plus tax does not equal total."
                )

    # Set safe defaults.

    if not invoice.get("currency"):
        invoice["currency"] = "INR"

    if not invoice.get("status"):
        invoice["status"] = "Pending"

    return errors


# ============================================================
# INVOICE PROCESSING AGENT
# ============================================================

def process_invoice(text, session):
    """
    Single-agent invoice processing workflow.

    1. Understand the invoice processing goal.
    2. Create an execution plan.
    3. Use extracted PDF text.
    4. Call the LLM for structured extraction.
    5. Validate extracted fields.
    6. Return a structured result for database saving.
    """

    if not text or not text.strip():

        return {
            "valid": False,
            "errors": ["The PDF contains no readable text."],
            "plan": [],
            "trace": [],
            "invoice": {}
        }

    plan = [
        "Understand the invoice processing request.",
        "Use the PDF extraction tool output.",
        "Extract structured invoice fields using the LLM.",
        "Validate required fields, dates and amounts.",
        "Prepare the validated invoice for database storage."
    ]

    trace = []

    trace.append({
        "step": 1,
        "task": "Goal understanding",
        "result": "Invoice extraction requested."
    })

    trace.append({
        "step": 2,
        "task": "PDF text input",
        "result": "Received extracted PDF text."
    })

    try:

        raw = _llm(
            "Extract invoice fields from the following PDF text:\n\n"
            + text[:22000],
            EXTRACTION_SYSTEM
        )

        trace.append({
            "step": 3,
            "task": "LLM extraction",
            "result": "Structured extraction response received."
        })

        invoice = _json_from_text(raw)

        errors = validate(invoice)

        if errors:

            trace.append({
                "step": 4,
                "task": "Invoice validation",
                "result": "Validation failed."
            })

            trace.append({
                "step": 5,
                "task": "Database preparation",
                "result": "Invoice not approved for saving."
            })

        else:

            trace.append({
                "step": 4,
                "task": "Invoice validation",
                "result": "All validation checks passed."
            })

            trace.append({
                "step": 5,
                "task": "Database preparation",
                "result": "Invoice is ready for account-scoped saving."
            })

        return {
            "valid": not errors,
            "errors": errors,
            "plan": plan,
            "trace": trace,
            "invoice": invoice
        }

    except Exception as error:

        trace.append({
            "step": 3,
            "task": "Invoice extraction",
            "result": f"Processing failed: {error}"
        })

        return {
            "valid": False,
            "errors": [str(error)],
            "plan": plan,
            "trace": trace,
            "invoice": {}
        }


# ============================================================
# RAG RETRIEVAL
# ============================================================

def _retrieve_invoices(question, invoices, limit=12):
    """
    Keyword-based retrieval from the authenticated user's
    invoice records supplied by the application.
    """

    terms = [
        term.lower()
        for term in re.findall(
            r"[a-zA-Z0-9]+",
            question
        )
        if len(term) > 2
    ]

    scored = []

    for invoice in invoices:

        searchable_text = " ".join(
            str(invoice.get(field, ""))
            for field in (
                "invoice_number",
                "customer_name",
                "invoice_date",
                "due_date",
                "status",
                "extracted_text"
            )
        ).lower()

        score = sum(
            1 for term in terms
            if term in searchable_text
        )

        if score > 0:
            scored.append((score, invoice))

    scored.sort(
        key=lambda item: item[0],
        reverse=True
    )

    if scored:
        return [
            invoice
            for score, invoice in scored[:limit]
        ]

    # If no specific keyword matches, use recent records.
    return invoices[:limit]


# ============================================================
# AI INVOICE QUESTION ANSWERING
# ============================================================

def answer_question(question, invoices, history=None):
    """
    RAG workflow:

    1. Understand the user's question.
    2. Retrieve relevant invoice records.
    3. Add conversation context.
    4. Ask the LLM to generate a grounded response.
    5. Use deterministic fallback answers if providers fail.
    """

    if not question or not question.strip():
        return "Please enter an invoice-related question."

    if not invoices:
        return (
            "There are no invoices saved in your account yet. "
            "Upload an invoice before asking questions."
        )

    retrieved = _retrieve_invoices(
        question,
        invoices
    )

    context = json.dumps(
        [
            {
                field: invoice.get(field)
                for field in (
                    "invoice_number",
                    "customer_name",
                    "invoice_date",
                    "due_date",
                    "subtotal",
                    "tax_amount",
                    "total_amount",
                    "currency",
                    "status"
                )
            }
            for invoice in retrieved
        ],
        default=str
    )

    # Include recent conversation history.

    history_text = ""

    if history:

        recent_messages = history[-6:]

        history_text = "\n".join(
            f"{message.get('role', 'user')}: "
            f"{str(message.get('content', ''))[:1000]}"
            for message in recent_messages
            if isinstance(message, dict)
        )

    prompt = f"""
Answer the user's invoice question using only the
retrieved invoice records below.

If the information is unavailable, say so clearly.

Recent conversation:
{history_text}

User question:
{question}

Retrieved invoice records:
{context}
"""

    try:

        return _llm(
            prompt,
            GENERAL_SYSTEM
        )

    except Exception:

        # Deterministic fallback for common questions.

        today = date.today().isoformat()
        q = question.lower()

        if "overdue" in q:

            rows = [
                invoice for invoice in invoices
                if invoice.get("status") != "Paid"
                and invoice.get("due_date")
                and str(invoice["due_date"]) < today
            ]

            if not rows:
                return "There are no overdue invoices."

            return (
                "Overdue invoices:\n"
                + json.dumps(rows, default=str, indent=2)
            )

        if "pending" in q:

            rows = [
                invoice for invoice in invoices
                if invoice.get("status") != "Paid"
            ]

            total = sum(
                float(invoice.get("total_amount") or 0)
                for invoice in rows
            )

            return (
                f"There are {len(rows)} unpaid invoices. "
                f"Total outstanding amount: ₹{total:,.2f}."
            )

        if "paid" in q:

            rows = [
                invoice for invoice in invoices
                if invoice.get("status") == "Paid"
            ]

            return (
                f"Found {len(rows)} paid invoices."
            )

        return (
            "The AI providers are unavailable. "
            "Please try again later."
        )


# ============================================================
# PAYMENT REMINDER GENERATOR
# ============================================================

def _format_amount(amount, currency):
    """
    Formats invoice amounts using the correct currency symbol.
    """

    symbols = {
        "INR": "₹",
        "USD": "$",
        "EUR": "€",
        "GBP": "£"
    }

    symbol = symbols.get(
        str(currency).upper(),
        str(currency).upper() + " "
    )

    try:
        return f"{symbol}{float(amount):,.2f}"
    except (ValueError, TypeError):
        return f"{symbol}{amount}"


def _format_date(value):
    if not value:
        return "the agreed date"

    try:
        return date.fromisoformat(
            str(value)
        ).strftime("%d %B %Y")

    except (ValueError, TypeError):
        return str(value)


def reminder_draft(invoice):
    number = invoice.get("invoice_number", "N/A")
    customer = invoice.get("customer_name", "Customer")
    amount = _format_amount(
        invoice.get("total_amount", 0),
        invoice.get("currency", "INR")
    )

    raw_due = invoice.get("due_date")
    due_date = _format_date(raw_due)
    status = str(invoice.get("status", "Pending")).strip().lower()

    if status == "paid":
        return (
            f"Invoice {number} is marked as Paid. "
            "A payment reminder is not necessary."
        )

    overdue = False
    try:
        parsed_due = date.fromisoformat(str(raw_due)[:10])
        overdue = parsed_due < date.today()
    except (TypeError, ValueError):
        pass

    if overdue:
        subject = f"Overdue Payment Reminder: Invoice {number}"
        payment_sentence = (
            f"payment of {amount} was due on {due_date} "
            "and is now overdue."
        )
    elif raw_due:
        subject = f"Friendly Reminder: Invoice {number} – Payment Due {due_date}"
        payment_sentence = f"payment of {amount} is due on {due_date}."
    else:
        subject = f"Friendly Payment Reminder: Invoice {number}"
        payment_sentence = f"payment of {amount} remains outstanding."

    return f"""Subject: {subject}

Dear {customer} Team,

This is a friendly reminder regarding invoice {number}.
The {payment_sentence}

Please let us know if the payment has already been made or if you need another copy of the invoice.

Thank you,
Accounts Team

[Draft only — no email has been sent.]
"""

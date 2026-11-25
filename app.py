
import streamlit as st
import time
from datetime import date

from invoicepilot.config import settings
from invoicepilot.auth import (
    sign_in,
    sign_up,
    sign_out,
    current_user
)
from invoicepilot.db import (
    list_invoices,
    save_invoice,
    update_status,
    delete_invoice
)
from invoicepilot.agent import (
    process_invoice,
    answer_question,
    reminder_draft
)
from invoicepilot.pdf_tools import extract_pdf_text


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="InvoicePilot",
    page_icon="🧾",
    layout="wide"
)

st.title("🧾 InvoicePilot")

st.caption(
    "Account-based AI invoice processing and payment tracking"
)


# ============================================================
# CONFIGURATION CHECK
# ============================================================

if not settings.supabase_url or not settings.supabase_key:

    st.error(
        "Supabase is not configured. "
        "Follow SETUP_WINDOWS.md and add credentials "
        "to .streamlit/secrets.toml."
    )

    st.stop()


# ============================================================
# SESSION INITIALIZATION
# ============================================================

if "session" not in st.session_state:
    st.session_state.session = None

if "chat" not in st.session_state:
    st.session_state.chat = []

if "draft" not in st.session_state:
    st.session_state.draft = None


# ============================================================
# LOGIN AND REGISTRATION
# ============================================================

if not st.session_state.session:

    tab1, tab2 = st.tabs(
        ["Log in", "Create account"]
    )

    with tab1:

        with st.form("login"):

            email = st.text_input("Email")

            password = st.text_input(
                "Password",
                type="password"
            )

            submitted = st.form_submit_button("Log in")

            if submitted:

                try:

                    st.session_state.session = sign_in(
                        email,
                        password
                    )

                    st.session_state.chat = []
                    st.rerun()

                except Exception as error:

                    st.error(
                        f"Login failed: {error}"
                    )

    with tab2:

        with st.form("register"):

            email = st.text_input("Email address")

            password = st.text_input(
                "Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Create account"
            )

            if submitted:

                try:

                    sign_up(email, password)

                    st.success(
                        "Account created. If email confirmation "
                        "is enabled, confirm your email before logging in."
                    )

                except Exception as error:

                    st.error(
                        f"Registration failed: {error}"
                    )

    st.stop()


# ============================================================
# AUTHENTICATED USER
# ============================================================

user = current_user(
    st.session_state.session
)

if not user:

    st.session_state.session = None
    st.session_state.chat = []
    st.rerun()


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

with st.sidebar:

    st.title("InvoicePilot")

    st.write(
        "Signed in as",
        user["email"]
    )

    if st.button("Log out"):

        try:
            sign_out(st.session_state.session)

        except Exception:
            pass

        st.session_state.session = None
        st.session_state.chat = []
        st.session_state.draft = None

        st.rerun()

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Upload invoice",
            "Invoices",
            "AI assistant",
            "About"
        ]
    )


# ============================================================
# LOAD ACCOUNT-SCOPED INVOICES
# ============================================================

try:

    invoices = list_invoices(
        st.session_state.session
    )

except Exception as error:

    st.error(
        f"Could not load your invoices: {error}. "
        "Check the Supabase SQL setup and RLS policies."
    )

    st.stop()


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    st.subheader("Dashboard")

    today = date.today().isoformat()

    paid = [
        invoice for invoice in invoices
        if invoice.get("status") == "Paid"
    ]

    pending = [
        invoice for invoice in invoices
        if invoice.get("status") != "Paid"
    ]

    overdue = [
        invoice for invoice in pending
        if invoice.get("due_date")
        and str(invoice["due_date"])[:10] < today
    ]

    def amount(rows):

        return sum(
            float(invoice.get("total_amount") or 0)
            for invoice in rows
        )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total invoices",
        len(invoices)
    )

    col2.metric(
        "Paid",
        len(paid)
    )

    col3.metric(
        "Pending",
        len(pending)
    )

    col4.metric(
        "Overdue",
        len(overdue)
    )

    col5.metric(
        "Pending amount",
        f"₹{amount(pending):,.2f}"
    )

    st.divider()

    st.subheader("Recent invoices")

    if invoices:

        st.dataframe(
            invoices[:10],
            width="stretch",
            hide_index=True
        )

    else:

        st.info(
            "No invoices found. Upload your first invoice to get started."
        )


# ============================================================
# UPLOAD AND PROCESS INVOICE
# ============================================================

elif page == "Upload invoice":

    st.subheader("Upload a PDF invoice")

    st.write(
        "Upload a text-based PDF. InvoicePilot will extract, "
        "analyse and validate its information."
    )

    file = st.file_uploader(
        "Choose invoice PDF",
        type=["pdf"]
    )

    if file and st.button(
        "Process invoice with AI",
        type="primary"
    ):

        with st.spinner(
            "Extracting, planning, validating and saving..."
        ):

            try:

                # TOOL 1: PDF text extraction

                raw = extract_pdf_text(
                    file.getvalue()
                )

                # MEASURE AGENT PROCESSING TIME

                start_time = time.perf_counter()

                # AI AGENT: Planning, extraction and validation

                result = process_invoice(
                    raw,
                    st.session_state.session
                )

                processing_time = (
                    time.perf_counter() - start_time
                )

                # DISPLAY AGENT EXECUTION PLAN

                with st.expander(
                    "Agent Execution Plan and Trace",
                    expanded=True
                ):

                    st.markdown(
                        "### Execution Plan"
                    )

                    for index, task in enumerate(
                        result.get("plan", []),
                        start=1
                    ):

                        st.write(
                            f"{index}. {task}"
                        )

                    st.markdown(
                        "### Agent Execution Trace"
                    )

                    for item in result.get("trace", []):

                        st.write(
                            f"**Step {item['step']}: "
                            f"{item['task']}**"
                        )

                        st.caption(
                            item["result"]
                        )

                # DISPLAY PROCESSING TIME

                st.metric(
                    "Agent processing time",
                    f"{processing_time:.2f} seconds"
                )

                # SAVE ONLY VALIDATED INVOICES

                if result.get("valid"):

                    save_invoice(
                        st.session_state.session,
                        result["invoice"],
                        raw
                    )

                    st.success(
                        "Invoice validated and saved to your account."
                    )

                    st.subheader(
                        "Extracted Invoice Details"
                    )

                    st.json(
                        result["invoice"]
                    )

                else:

                    st.warning(
                        "The document needs correction "
                        "and was not saved."
                    )

                    st.subheader(
                        "Validation Errors"
                    )

                    st.json(
                        result.get("errors", [])
                    )

            except Exception as error:

                st.error(
                    f"Processing failed safely: {error}"
                )


# ============================================================
# INVOICE MANAGEMENT
# ============================================================

elif page == "Invoices":

    st.subheader("Your invoices")

    query = st.text_input(
        "Search customer or invoice number"
    )

    status = st.selectbox(
        "Filter status",
        ["All", "Pending", "Paid"]
    )

    rows = [

        invoice for invoice in invoices

        if (
            status == "All"
            or invoice.get("status") == status
        )

        and (
            query.lower() in str(invoice).lower()
        )

    ]

    if not rows:

        st.info(
            "No matching invoices found."
        )

    for invoice in rows:

        with st.expander(
            f'{invoice.get("invoice_number", "No number")} '
            f'· {invoice.get("customer_name", "Unknown")} '
            f'· {invoice.get("status", "Pending")}'
        ):

            st.write(
                {
                    key: value
                    for key, value in invoice.items()
                    if key not in (
                        "id",
                        "user_id",
                        "extracted_text"
                    )
                }
            )

            col1, col2 = st.columns(2)

            with col1:

                new_status = st.selectbox(
                    "Payment status",
                    ["Pending", "Paid"],
                    index=(
                        0 if invoice.get("status") != "Paid"
                        else 1
                    ),
                    key=f"status_{invoice['id']}"
                )

                if st.button(
                    "Update status",
                    key=f"update_{invoice['id']}"
                ):

                    update_status(
                        st.session_state.session,
                        invoice["id"],
                        new_status
                    )

                    st.success(
                        "Payment status updated."
                    )

                    st.rerun()

            with col2:

                if st.button(
                    "Generate reminder draft",
                    key=f"reminder_{invoice['id']}"
                ):

                    st.session_state.draft = reminder_draft(
                        invoice
                    )

    # DISPLAY PAYMENT REMINDER

    if st.session_state.draft:

        st.divider()

        st.subheader(
            "Payment reminder draft"
        )

        st.text_area(
            "Copy this draft",
            st.session_state.draft,
            height=220
        )

        st.caption(
            "This is only a draft. No email or payment is sent."
        )


# ============================================================
# AI ASSISTANT WITH CONVERSATION CONTEXT
# ============================================================

elif page == "AI assistant":

    st.subheader(
        "Ask questions about your saved invoices"
    )

    st.caption(
        "The assistant retrieves your invoice records "
        "and uses conversation history to answer questions."
    )

    for message in st.session_state.chat:

        with st.chat_message(
            message["role"]
        ):

            st.write(
                message["content"]
            )

    question = st.chat_input(
        "e.g. Which invoices are overdue?"
    )

    if question:

        st.session_state.chat.append(
            {
                "role": "user",
                "content": question
            }
        )

        with st.chat_message("assistant"):

            with st.spinner(
                "Retrieving your records and preparing an answer..."
            ):

                answer = answer_question(
                    question,
                    invoices,
                    st.session_state.chat[:-1]
                )

                st.write(answer)

        st.session_state.chat.append(
            {
                "role": "assistant",
                "content": answer
            }
        )


# ============================================================
# ABOUT PROJECT
# ============================================================

elif page == "About":

    st.subheader("About InvoicePilot")

    st.markdown(
        """
        **InvoicePilot** is an account-based AI invoice
        processing and payment tracking application.

        ### Main Features

        - User registration and login
        - Account-isolated invoice records
        - PDF invoice text extraction
        - LLM-powered invoice information extraction
        - Invoice validation and error handling
        - Dashboard and payment status tracking
        - Retrieval-based invoice question answering
        - Conversation context
        - Payment reminder draft generation

        ### Agentic Workflow

        User Goal → Planning → PDF Processing Tool →
        LLM Extraction → Validation → Database Storage →
        Knowledge Retrieval → Final Response

        ### Technologies Used

        - Python 3.11
        - Streamlit
        - Google Gemini
        - Groq fallback provider
        - Supabase Authentication and Database
        - PyMuPDF

        ### Architecture

        InvoicePilot uses one functional AI agent to coordinate
        invoice extraction, validation and question answering.

        The application uses keyword-based retrieval over the
        authenticated user's invoice records to provide context
        to the LLM.

        ### Safety

        - Invoice data is isolated by authenticated user.
        - Invalid invoice data is not saved.
        - The application does not send emails.
        - The application does not process payments.
        """
    )

    st.divider()

    st.caption(
        "InvoicePilot — Agentic AI Course Project"
    )

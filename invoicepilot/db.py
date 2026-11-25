from .auth import client
TABLE="invoices"
def _db(session):
    c=client()
    token=session.session.access_token
    c.postgrest.auth(token)
    return c
def list_invoices(session):
    return _db(session).table(TABLE).select("*").order("created_at",desc=True).execute().data
def save_invoice(session,invoice,raw_text):
    uid=session.user.id
    payload={**invoice,"user_id":uid,"extracted_text":raw_text[:20000]}
    return _db(session).table(TABLE).insert(payload).execute().data
def update_status(session,invoice_id,status):
    return _db(session).table(TABLE).update({"status":status}).eq("id",invoice_id).execute()
def delete_invoice(session,invoice_id):
    return _db(session).table(TABLE).delete().eq("id",invoice_id).execute()

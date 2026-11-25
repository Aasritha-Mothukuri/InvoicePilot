from supabase import create_client
from .config import settings
def client():
    return create_client(settings.supabase_url,settings.supabase_key)
def sign_in(email,password):
    return client().auth.sign_in_with_password({"email":email,"password":password})
def sign_up(email,password):
    return client().auth.sign_up({"email":email,"password":password})
def sign_out(session):
    return client().auth.sign_out()
def current_user(session):
    u=getattr(session,"user",None)
    if not u: return None
    return {"id":u.id,"email":u.email}

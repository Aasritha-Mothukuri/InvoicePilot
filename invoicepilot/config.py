import streamlit as st
class Settings:
    def get(self,key,default=""):
        try: return st.secrets.get(key,default)
        except Exception: return default
    @property
    def supabase_url(self): return self.get("SUPABASE_URL")
    @property
    def supabase_key(self): return self.get("SUPABASE_ANON_KEY")
    @property
    def gemini_key(self): return self.get("GEMINI_API_KEY")
    @property
    def groq_key(self): return self.get("GROQ_API_KEY")
    @property
    def provider(self): return self.get("LLM_PROVIDER","gemini").lower()
settings=Settings()

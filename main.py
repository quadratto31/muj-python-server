import os
from fastapi import FastAPI
from supabase import create_client, Client

app = FastAPI()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/")
def hlavni_stranka():
    return {
        "stav": "Server běží!",
        "zprava": "Ahoj z mého vlastního Python serveru!",
        "supabase_pripojeno": supabase is not None
    }

@app.get("/pozdrav/{jmeno}")
def pozdrav_uzivatele(jmeno: str):
    return {"odpoved": f"Čau {jmeno}, tohle odpověděl tvůj server."}

import os
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from supabase import create_client, Client
from huggingface_hub import HfApi

app = FastAPI(title="NXT Link", version="1.0")

# Připojení ke Supabase (pro uživatele a metadata souborů)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
# Hugging Face Token (pro velkého úložiště zdarma - 10GB+)
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_REPO_ID = os.environ.get("HF_REPO_ID") # např. "tvoje-jmeno/nxt-link-storage"

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

hf_api = HfApi(token=HF_TOKEN) if HF_TOKEN else None

# --- HTML ÚVODNÍ PORTÁL S ADMINEM ---
@app.get("/", response_class=HTMLResponse)
def nxt_link_domu():
    return """
    <!DOCTYPE html>
    <html lang="cs">
    <head>
        <meta charset="UTF-8">
        <title>NXT Link - Portál</>
        <style>
            body { font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; padding: 40px; }
            .card { background: #1e293b; padding: 30px; border-radius: 12px; max-width: 500px; margin: auto; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
            h1 { color: #38bdf8; text-align: center; }
            input, button { width: 100%; padding: 12px; margin: 10px 0; border-radius: 6px; border: none; box-sizing: border-box; }
            input { background: #334155; color: white; }
            button { background: #0284c7; color: white; font-weight: bold; cursor: pointer; }
            button:hover { background: #0369a1; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>NXT Link 🚀</h1>
            <p style="text-align: center; color: #94a3b8;">Vítej v souborovém portálu</p>
            <form action="/login" method="POST">
                <input type="text" name="username" placeholder="Uživatelské jméno" required>
                <input type="password" name="password" placeholder="Heslo" required>
                <button type="submit">Přihlásit se</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Chybí Supabase připojení")
    
    # Ověření uživatele v databázi
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    users = res.data
    
    if not users or users[0]["password"] != password:
        return HTMLResponse("<h3>Nesprávné jméno nebo heslo!</h3><a href='/'>Zpět</a>", status_code=400)
    
    user = users[0]
    if user["role"] == "admin":
        return HTMLResponse(f"<h1>Vítej Admini, {username}!</h1><p>Tady bude správa uživatelů a složek.</p><a href='/'>Odhlásit</a>")
    else:
        return HTMLResponse(f"<h1>Vítej uživateli, {username}!</h1><p>Tohle je tvá soukromá složka.</p><a href='/'>Odhlásit</a>")

@app.get("/api/stav")
def stav_serveru():
    return {
        "projekt": "NXT Link",
        "stav": "Běží stabilně",
        "supabase": supabase is not None,
        "velke_uloziste_aktivni": hf_api is not None
    }

import os
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from supabase import create_client, Client

app = FastAPI(title="NXT Link", version="1.0")

# Připojení ke Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- PORTÁL NXT LINK ---
@app.get("/", response_class=HTMLResponse)
def nxt_link_domu():
    return """
    <!DOCTYPE html>
    <html lang="cs">
    <head>
        <meta charset="UTF-8">
        <title>NXT Link - Portál</title>
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
            <p style="text-align: center; color: #94a3b8;">Přihlášení do souborového portálu</p>
            <form action="/login" method="POST">
                <input type="text" name="username" placeholder="Uživatelské jméno" required>
                <input type="password" name="password" placeholder="Heslo" required>
                <button type="submit">Přihlásit se</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.post("/login", response_class=HTMLResponse)
def login(username: str = Form(...), password: str = Form(...)):
    if not supabase:
        return "<h3>Chyba: Supabase není připojena!</h3><a href='/'>Zpět</a>"
    
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    users = res.data
    
    if not users or users[0]["password"] != password:
        return "<h3>Nesprávné jméno nebo heslo!</h3><a href='/'>Zpět</a>"
    
    user = users[0]
    if user["role"] == "admin":
        return f"<h1>Vítej šéfe (Admin), {username}!</h1><p>Tady bude administrace uživatelů.</p><a href='/'>Odhlásit</a>"
    else:
        return f"<h1>Vítej uživateli, {username}!</h1><p>Tohle je tvůj osobní prostor.</p><a href='/'>Odhlásit</a>"

@app.get("/api/stav")
def stav_serveru():
    return {
        "projekt": "NXT Link",
        "stav": "Běží stabilně",
        "supabase_pripojeno": supabase is not None
    }

import os
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from supabase import create_client, Client

app = FastAPI(title="NXT Link", version="2.0")

# Připojení ke Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MODERNÍ LIQUID GLASS DESIGN (CSS) ---
LIQUID_GLASS_STYLE = """
<style>
    * { box-sizing: border-box; }
    body {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        background: radial-gradient(circle at top left, #1e1b4b, #0f172a, #020617);
        color: #f8fafc;
        margin: 0;
        padding: 0;
        min-height: 100vh;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .glass-card {
        background: rgba(30, 41, 59, 0.65);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 24px;
        padding: 40px;
        width: 100%;
        max-width: 420px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }
    .glass-dashboard {
        background: rgba(30, 41, 59, 0.65);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 24px;
        padding: 40px;
        width: 90%;
        max-width: 800px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }
    h1, h2 { 
        color: #38bdf8; 
        text-align: center; 
        margin-top: 0; 
        text-shadow: 0 0 20px rgba(56, 189, 248, 0.4);
        font-weight: 700;
    }
    p { color: #94a3b8; text-align: center; font-size: 14px; }
    input {
        width: 100%;
        padding: 14px 18px;
        margin: 12px 0;
        background: rgba(15, 23, 42, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        color: white;
        font-size: 15px;
        outline: none;
        transition: all 0.3s ease;
    }
    input:focus {
        border-color: #38bdf8;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
        background: rgba(15, 23, 42, 0.8);
    }
    button, .btn {
        width: 100%;
        padding: 14px;
        margin-top: 15px;
        background: linear-gradient(135deg, #0284c7, #0369a1);
        border: none;
        border-radius: 12px;
        color: white;
        font-weight: bold;
        font-size: 16px;
        cursor: pointer;
        box-shadow: 0 4px 20px rgba(2, 132, 199, 0.4);
        transition: all 0.3s ease;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        box-sizing: border-box;
    }
    button:hover, .btn:hover {
        background: linear-gradient(135deg, #0369a1, #075985);
        box-shadow: 0 6px 25px rgba(2, 132, 199, 0.6);
        transform: translateY(-2px);
    }
    .badge {
        display: inline-block;
        padding: 4px 12px;
        background: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border-radius: 20px;
        font-size: 12px;
        border: 1px solid rgba(56, 189, 248, 0.3);
        margin-bottom: 15px;
    }
    hr { border: 0; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 20px 0; }
</style>
"""

# --- 1. PŘIHLAŠOVACÍ STRÁNKA ---
@app.get("/", response_class=HTMLResponse)
def nxt_link_domu():
    return f"""
    <!DOCTYPE html>
    <html lang="cs">
    <head>
        <meta charset="UTF-8">
        <title>NXT Link - Portál</title>
        {LIQUID_GLASS_STYLE}
    </head>
    <body>
        <div class="glass-card">
            <h1>NXT Link 🌌</h1>
            <p>Zabezpečený serverový portál</p>
            <form action="/login" method="POST">
                <input type="text" name="username" placeholder="Uživatelské jméno" required>
                <input type="password" name="password" placeholder="Heslo" required>
                <button type="submit">Přihlásit se do systému</button>
            </form>
        </div>
    </body>
    </html>
    """

# --- 2. ZPRACOVÁNÍ PŘIHLÁŠENÍ ---
@app.post("/login", response_class=HTMLResponse)
def login(username: str = Form(...), password: str = Form(...)):
    if not supabase:
        return f"""
        <!DOCTYPE html><html lang="cs"><head>{LIQUID_GLASS_STYLE}</head><body>
            <div class="glass-card">
                <h2>Chyba serveru</h2>
                <p>Supabase není správně propojená!</p>
                <a href="/" class="btn">Zpět</a>
            </div>
        </body></html>
        """
    
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    users = res.data
    
    if not users or users[0]["password"] != password:
        return f"""
        <!DOCTYPE html><html lang="cs"><head>{LIQUID_GLASS_STYLE}</head><body>
            <div class="glass-card">
                <h2>Přístup odepřen</h2>
                <p>Nesprávné uživatelské jméno nebo heslo.</p>
                <a href="/" class="btn">Zpět na přihlášení</a>
            </div>
        </body></html>
        """
    
    user = users[0]
    if user["role"] == "admin":
        return f"""
        <!DOCTYPE html><html lang="cs"><head>{LIQUID_GLASS_STYLE}</head><body>
            <div class="glass-dashboard">
                <div class="badge">Administrátor</div>
                <h1>Vítej šéfe, {username} 🚀</h1>
                <p>Tady máš plnou kontrolu nad NXT Link serverem a správou uživatelů.</p>
                <hr>
                <p style="color: #38bdf8; text-align: left;">• Systémové úložiště: Připojeno</p>
                <p style="color: #38bdf8; text-align: left;">• Databáze Supabase: Aktivní</p>
                <br>
                <a href="/" class="btn" style="background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5;">Odhlásit se</a>
            </div>
        </body></html>
        """
    else:
        return f"""
        <!DOCTYPE html><html lang="cs"><head>{LIQUID_GLASS_STYLE}</head><body>
            <div class="glass-dashboard">
                <div class="badge">Uživatel</div>
                <h1>Vítej, {username} 📂</h1>
                <p>Tohle je tvůj osobní prostor v NXT Link cloudu.</p>
                <hr>
                <p style="text-align: left;">Zde brzy přibude správa tvých souborů a složek.</p>
                <br>
                <a href="/" class="btn" style="background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5;">Odhlásit se</a>
            </div>
        </body></html>
        """

@app.get("/api/stav")
def stav_serveru():
    return {
        "projekt": "NXT Link",
        "design": "Liquid Glass",
        "stav": "Běží stabilně",
        "supabase_pripojeno": supabase is not None
    }

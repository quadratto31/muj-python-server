import os
from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from supabase import create_client, Client
from huggingface_hub import HfApi

app = FastAPI(title="NXT Link", version="4.0")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_REPO_ID = os.environ.get("HF_REPO_ID")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

hf_api = HfApi(token=HF_TOKEN) if HF_TOKEN else None

LIQUID_GLASS_STYLE = """
<style>
    * { box-sizing: border-box; }
    body {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        background: radial-gradient(circle at top left, #1e1b4b, #0f172a, #020617);
        color: #f8fafc;
        margin: 0;
        padding: 20px;
        min-height: 100vh;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .glass-card, .glass-dashboard {
        background: rgba(30, 41, 59, 0.65);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 24px;
        padding: 30px;
        width: 100%;
        max-width: 650px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }
    h1, h2 { 
        color: #38bdf8; 
        text-align: center; 
        text-shadow: 0 0 20px rgba(56, 189, 248, 0.4);
    }
    p { color: #94a3b8; text-align: center; font-size: 14px; }
    input, select {
        width: 100%;
        padding: 12px 16px;
        margin: 8px 0;
        background: rgba(15, 23, 42, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: white;
        font-size: 14px;
        outline: none;
    }
    input:focus, select:focus {
        border-color: #38bdf8;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
    }
    button, .btn {
        width: 100%;
        padding: 12px;
        margin-top: 12px;
        background: linear-gradient(135deg, #0284c7, #0369a1);
        border: none;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        font-size: 15px;
        cursor: pointer;
        box-shadow: 0 4px 20px rgba(2, 132, 199, 0.4);
        text-align: center;
        text-decoration: none;
        display: inline-block;
        box-sizing: border-box;
    }
    button:hover, .btn:hover {
        background: linear-gradient(135deg, #0369a1, #075985);
        transform: translateY(-1px);
    }
    .badge {
        display: inline-block;
        padding: 4px 12px;
        background: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border-radius: 20px;
        font-size: 12px;
        border: 1px solid rgba(56, 189, 248, 0.3);
        margin-bottom: 10px;
    }
    table { width: 100%; margin-top: 15px; border-collapse: collapse; }
    th, td { padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 14px; }
    th { color: #38bdf8; }
    a.file-link { color: #38bdf8; text-decoration: none; }
    a.file-link:hover { text-decoration: underline; }
    hr { border: 0; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 20px 0; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
def nxt_link_domu():
    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>NXT Link</title>{LIQUID_GLASS_STYLE}</head>
    <body>
        <div class="glass-card" style="max-width: 420px;">
            <h1>NXT Link 🌌</h1>
            <p>Zabezpečený serverový portál (10GB+ Hugging Face Storage)</p>
            <form action="/login" method="POST">
                <input type="text" name="username" placeholder="Uživatelské jméno" required>
                <input type="password" name="password" placeholder="Heslo" required>
                <button type="submit">Přihlásit se</button>
            </form>
        </div>
    </body></html>
    """

@app.post("/login", response_class=HTMLResponse)
def login(username: str = Form(...), password: str = Form(...)):
    if not supabase:
        return "<h3 style='color:white;text-align:center;'>Chyba: Supabase nebyla připojena!</h3><br><a href='/' class='btn'>Zpět</a>"
    
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    users = res.data
    
    if not users or users[0]["password"] != password:
        return f"""
        <!DOCTYPE html><html lang="cs"><head>{LIQUID_GLASS_STYLE}</head><body>
            <div class="glass-card" style="max-width: 400px;">
                <h2>Přístup odepřen</h2>
                <p>Špatné jméno nebo heslo.</p>
                <a href="/" class="btn">Zpět</a>
            </div>
        </body></html>
        """
    
    user = users[0]
    
    files_res = supabase.table("nxt_files").select("*").eq("owner", username).execute()
    user_files = files_res.data
    
    files_html = ""
    for f in user_files:
        files_html += f"<tr><td>{f['filename']}</td><td><a href='{f['file_url']}' target='_blank' class='file-link'>Stáhnout</a></td></tr>"
    
    if not files_html:
        files_html = "<tr><td colspan='2' style='text-align:center; color:#64748b;'>Zatím žádné soubory.</td></tr>"

    admin_section = ""
    if user["role"] == "admin":
        all_users_res = supabase.table("nxt_users").select("username, role").execute()
        users_rows = "".join([f"<tr><td>{u['username']}</td><td>{u['role']}</td></tr>" for u in all_users_res.data])
        
        admin_section = f"""
        <hr>
        <h2>🛡️ Administrace uživatelů</h2>
        <table>
            <tr><th>Uživatel</th><th>Role</th></tr>
            {users_rows}
        </table>
        <br>
        <form action="/admin/add-user" method="POST">
            <input type="hidden" name="admin_user" value="{username}">
            <input type="hidden" name="admin_pass" value="{password}">
            <input type="text" name="new_user" placeholder="Nové uživatelské jméno" required>
            <input type="password" name="new_pass" placeholder="Heslo nového uživatele" required>
            <select name="new_role">
                <option value="uzivatel">Běžný uživatel</option>
                <option value="admin">Administrátor</option>
            </select>
            <button type="submit" style="background: linear-gradient(135deg, #10b981, #059669);">Přidat nového uživatele</button>
        </form>
        """

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>NXT Link - Portál</title>{LIQUID_GLASS_STYLE}</head>
    <body>
        <div class="glass-dashboard">
            <div class="badge">Přihlášen jako: {username} ({user['role']}) | Úložiště: Hugging Face</div>
            <h1>NXT Link Dashboard 🚀</h1>
            
            <hr>
            <h2>📂 Tvoje soubory</h2>
            <table>
                <tr><th>Název souboru</th><th>Akce</th></tr>
                {files_html}
            </table>
            
            <br>
            <form action="/upload" method="POST" enctype="multipart/form-data">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="password" value="{password}">
                <input type="file" name="file" required style="padding: 10px;">
                <button type="submit">Nahrát nový soubor (do Hugging Face)</button>
            </form>

            {admin_section}
            
            <br><hr>
            <a href="/" class="btn" style="background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5;">Odhlásit se</a>
        </div>
    </body></html>
    """

@app.post("/upload", response_class=HTMLResponse)
async def upload_file(username: str = Form(...), password: str = Form(...), file: UploadFile = File(...)):
    if not supabase:
        return "Chyba databáze"
    
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    if not res.data or res.data[0]["password"] != password:
        return "Neautorizováno"
    
    file_bytes = await file.read()
    file_path_in_repo = f"{username}/{file.filename}"
    
    try:
        if hf_api and HF_REPO_ID:
            # Nahrání souboru na Hugging Face Dataset úložiště (10GB+ zdarma)
            hf_api.upload_file(
                path_or_fileobj=file_bytes,
                path_in_repo=file_path_in_repo,
                repo_id=HF_REPO_ID,
                repo_type="dataset"
            )
            # Veřejný odkaz pro stažení ze serveru Hugging Face
            public_url = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/{file_path_in_repo}"
            storage_provider = "huggingface"
        else:
            raise HTTPException(status_code=500, detail="Hugging Face API není nastaveno v proměnných prostředí!")
        
        # Zápis metadat souboru do Supabase
        supabase.table("nxt_files").insert({
            "owner": username,
            "filename": file.filename,
            "storage_provider": storage_provider,
            "file_url": public_url
        }).execute()
        
    except Exception as e:
        return f"""
        <!DOCTYPE html><html lang="cs"><head>{LIQUID_GLASS_STYLE}</head><body>
            <div class="glass-card" style="text-align:center;">
                <h2>Chyba při nahrávání! ❌</h2>
                <p>{str(e)}</p>
                <form action="/login" method="POST">
                    <input type="hidden" name="username" value="{username}">
                    <input type="hidden" name="password" value="{password}">
                    <button type="submit" class="btn">Zpět</button>
                </form>
            </div>
        </body></html>
        """
    
    return f"""
    <!DOCTYPE html><html lang="cs"><head>{LIQUID_GLASS_STYLE}</head><body>
        <div class="glass-card" style="text-align:center;">
            <h2>Soubor nahrán na Hugging Face! 🎉</h2>
            <p>{file.filename}</p>
            <form action="/login" method="POST">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="password" value="{password}">
                <button type="submit" class="btn">Zpět do přehledu</button>
            </form>
        </div>
    </body></html>
    """

@app.post("/admin/add-user", response_class=HTMLResponse)
def add_user(admin_user: str = Form(...), admin_pass: str = Form(...), new_user: str = Form(...), new_pass: str = Form(...), new_role: str = Form(...)):
    if not supabase:
        return "Chyba"
    
    res = supabase.table("nxt_users").select("*").eq("username", admin_user).execute()
    if not res.data or res.data[0]["password"] != admin_pass or res.data[0]["role"] != "admin":
        return "Neoprávněná akce!"
    
    try:
        supabase.table("nxt_users").insert({
            "username": new_user,
            "password": new_pass,
            "role": new_role
        }).execute()
    except Exception as e:
        return f"Chyba: {str(e)}"

    return f"""
    <!DOCTYPE html><html lang="cs"><head>{LIQUID_GLASS_STYLE}</head><body>
        <div class="glass-card" style="text-align:center;">
            <h2>Uživatel {new_user} vytvořen! 🚀</h2>
            <form action="/login" method="POST">
                <input type="hidden" name="username" value="{admin_user}">
                <input type="hidden" name="password" value="{admin_pass}">
                <button type="submit" class="btn">Zpět do admin panelu</button>
            </form>
        </div>
    </body></html>
    """

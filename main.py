import os
from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from supabase import create_client, Client
from huggingface_hub import HfApi

app = FastAPI(title="VaultGrid OS", version="6.1")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_REPO_ID = os.environ.get("HF_REPO_ID")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

hf_api = HfApi(token=HF_TOKEN) if HF_TOKEN else None

VAULT_GRID_STYLE = """
<style>
    * { box-sizing: border-box; }
    body {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        background: radial-gradient(circle at top left, #090d16, #0f172a, #020617);
        color: #f8fafc;
        margin: 0;
        padding: 20px;
        min-height: 100vh;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .glass-dashboard {
        background: rgba(30, 41, 59, 0.75);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 24px;
        padding: 30px;
        width: 100%;
        max-width: 850px;
        box-shadow: 0 25px 60px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }
    h1, h2 { 
        color: #38bdf8; 
        text-align: center; 
        text-shadow: 0 0 20px rgba(56, 189, 248, 0.4);
    }
    p { color: #94a3b8; font-size: 14px; }
    input, select {
        width: 100%;
        padding: 12px 16px;
        margin: 8px 0;
        background: rgba(15, 23, 42, 0.6);
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
        margin-top: 10px;
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
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 14px; }
    th { color: #38bdf8; }
    a.file-link { color: #38bdf8; text-decoration: none; font-weight: bold; margin-right: 15px; }
    a.file-link:hover { text-decoration: underline; }
    a.delete-link { color: #f87171; text-decoration: none; }
    a.delete-link:hover { text-decoration: underline; }
    .toolbar { display: flex; gap: 10px; margin-top: 15px; background: rgba(15, 23, 42, 0.4); padding: 15px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.05); }
    hr { border: 0; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 20px 0; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
def vault_grid_domu():
    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid OS</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 450px;">
            <h1>VaultGrid ⚡</h1>
            <p style="text-align:center;">Profesionální cloudový serverový portál</p>
            <form action="/dashboard" method="POST">
                <input type="text" name="username" placeholder="Uživatelské jméno" required>
                <input type="password" name="password" placeholder="Heslo" required>
                <button type="submit">Přihlásit se do systému</button>
            </form>
        </div>
    </body></html>
    """

@app.post("/dashboard", response_class=HTMLResponse)
def dashboard(username: str = Form(...), password: str = Form(...), current_folder: str = Form("/")):
    if not supabase:
        return "<h3 style='color:white;text-align:center;'>Chyba databáze!</h3><br><a href='/' class='btn'>Zpět</a>"
    
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    users = res.data
    
    if not users or users[0]["password"] != password:
        return f"""
        <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
            <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
                <h2>Přístup odepřen</h2>
                <p>Špatné jméno nebo heslo.</p>
                <a href="/" class="btn">Zpět</a>
            </div>
        </body></html>
        """
    
    user = users[0]
    
    files_res = supabase.table("nxt_files").select("*").eq("owner", username).eq("folder", current_folder).execute()
    user_files = files_res.data
    
    files_html = ""
    for f in user_files:
        files_html += f"""
        <tr>
            <td>📄 {f['filename']}</td>
            <td>
                <a href="{f['file_url']}" download class="file-link">Stáhnout</a>
                <a href="/delete-file?id={f['id']}&username={username}&password={password}&folder={current_folder}" class="delete-link">Smazat</a>
            </td>
        </tr>
        """
    
    if not files_html:
        files_html = "<tr><td colspan='2' style='text-align:center; color:#64748b;'>Tato složka je prázdná.</td></tr>"

    admin_section = ""
    if user["role"] == "admin":
        all_users_res = supabase.table("nxt_users").select("username, role").execute()
        users_rows = "".join([f"<tr><td>{u['username']}</td><td>{u['role']}</td></tr>" for u in all_users_res.data])
        
        admin_section = f"""
        <hr>
        <h2>🛡️ VaultGrid Admin Panel</h2>
        <table>
            <tr><th>Uživatel</th><th>Role</th></tr>
            {users_rows}
        </table>
        <br>
        <form action="/admin/add-user" method="POST">
            <input type="hidden" name="admin_user" value="{username}">
            <input type="hidden" name="admin_pass" value="{password}">
            <input type="text" name="new_user" placeholder="Nové uživatelské jméno" required>
            <input type="password" name="new_pass" placeholder="Heslo uživatele" required>
            <select name="new_role">
                <option value="uzivatel">Běžný uživatel</option>
                <option value="admin">Administrátor</option>
            </select>
            <button type="submit" style="background: linear-gradient(135deg, #10b981, #059669);">Vytvořit uživatele</button>
        </form>
        """

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid - {current_folder}</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard">
            <div class="badge">Uživatel: {username} ({user['role']}) | Složka: {current_folder}</div>
            <h1>VaultGrid Storage OS ⚡</h1>
            
            <p>Aktuální cesta: <b>{current_folder}</b></p>
            
            <div class="toolbar">
                <form action="/dashboard" method="POST" style="flex: 1; margin:0;">
                    <input type="hidden" name="username" value="{username}">
                    <input type="hidden" name="password" value="{password}">
                    <input type="hidden" name="current_folder" value="/">
                    <button type="submit" style="margin:0; background: #334155;">📁 Kořenová složka (/)</button>
                </form>
                <form action="/dashboard" method="POST" style="flex: 1; margin:0;">
                    <input type="hidden" name="username" value="{username}">
                    <input type="hidden" name="password" value="{password}">
                    <input type="hidden" name="current_folder" value="/dokumenty">
                    <button type="submit" style="margin:0; background: #334155;">📁 /dokumenty</button>
                </form>
                <form action="/dashboard" method="POST" style="flex: 1; margin:0;">
                    <input type="hidden" name="username" value="{username}">
                    <input type="hidden" name="password" value="{password}">
                    <input type="hidden" name="current_folder" value="/media">
                    <button type="submit" style="margin:0; background: #334155;">📁 /media</button>
                </form>
            </div>

            <hr>
            <h2>📂 Soubory v této složce</h2>
            <table>
                <tr><th>Název souboru</th><th>Akce</th></tr>
                {files_html}
            </table>
            
            <br>
            <form action="/upload" method="POST" enctype="multipart/form-data" style="background: rgba(15, 23, 42, 0.4); padding: 15px; border-radius: 14px;">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="password" value="{password}">
                <input type="hidden" name="folder" value="{current_folder}">
                <p style="margin-top:0; color:#38bdf8;">Nahrát do: {current_folder}</p>
                <input type="file" name="file" required style="padding: 10px;">
                <button type="submit">Nahrát soubor sem</button>
            </form>

            {admin_section}
            
            <br><hr>
            <a href="/" class="btn" style="background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5;">Odhlásit se</a>
        </div>
    </body></html>
    """

@app.post("/upload", response_class=HTMLResponse)
async def upload_file(username: str = Form(...), password: str = Form(...), folder: str = Form("/"), file: UploadFile = File(...)):
    if not supabase:
        return "Chyba databáze"
    
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    if not res.data or res.data[0]["password"] != password:
        return "Neautorizováno"
    
    file_bytes = await file.read()
    file_path_in_repo = f"{username}{folder}/{file.filename}".replace("//", "/")
    
    try:
        if hf_api and HF_REPO_ID:
            hf_api.upload_file(
                path_or_fileobj=file_bytes,
                path_in_repo=file_path_in_repo,
                repo_id=HF_REPO_ID,
                repo_type="dataset"
            )
            public_url = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/{file_path_in_repo}"
        else:
            raise HTTPException(status_code=500, detail="Hugging Face není nastaven!")
        
        supabase.table("nxt_files").insert({
            "owner": username,
            "filename": file.filename,
            "storage_provider": "huggingface",
            "file_url": public_url,
            "folder": folder
        }).execute()
        
    except Exception as e:
        return f"<h3>Chyba při nahrávání: {str(e)}</h3><br><a href='/' class='btn'>Zpět</a>"
    
    return f"""
    <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
        <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
            <h2>Soubor nahrán do {folder}! 🎉</h2>
            <p>{file.filename}</p>
            <form action="/dashboard" method="POST">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="password" value="{password}">
                <input type="hidden" name="current_folder" value="{folder}">
                <button type="submit" class="btn">Zpět do složky</button>
            </form>
        </div>
    </body></html>
    """

@app.get("/delete-file", response_class=HTMLResponse)
def delete_file(id: int, username: str, password: str, folder: str):
    if not supabase:
        return "Chyba"
    
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    if not res.data or res.data[0]["password"] != password:
        return "Neoprávněná akce!"
    
    supabase.table("nxt_files").delete().eq("id", id).eq("owner", username).execute()
    
    return f"""
    <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
        <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
            <h2>Soubor smazán! 🗑️</h2>
            <form action="/dashboard" method="POST">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="password" value="{password}">
                <input type="hidden" name="current_folder" value="{folder}">
                <button type="submit" class="btn">Zpět do složky</button>
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
    <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
        <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
            <h2>Uživatel {new_user} vytvořen! 🚀</h2>
            <form action="/dashboard" method="POST">
                <input type="hidden" name="username" value="{admin_user}">
                <input type="hidden" name="password" value="{admin_pass}">
                <input type="hidden" name="current_folder" value="/">
                <button type="submit" class="btn">Zpět do Admin panelu</button>
            </form>
        </div>
    </body></html>
    """

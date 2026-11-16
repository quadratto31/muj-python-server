import os
from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from supabase import create_client, Client
from huggingface_hub import HfApi

app = FastAPI(title="VaultGrid OS", version="9.0")

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
        background: radial-gradient(circle at top left, #070b14, #0f172a, #020617);
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
        max-width: 950px;
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
    .box-section { background: rgba(15, 23, 42, 0.5); padding: 15px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.05); margin-top: 15px; }
    .progress-bar-bg { background: rgba(255,255,255,0.1); border-radius: 10px; height: 12px; width: 100%; overflow: hidden; margin-top: 5px; }
    .progress-bar-fill { background: linear-gradient(90deg, #38bdf8, #0284c7); height: 100%; width: 12%; }
    .breadcrumb { background: rgba(15,23,42,0.8); padding: 10px 15px; border-radius: 8px; margin-bottom: 15px; font-family: monospace; color: #38bdf8; }
    hr { border: 0; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 20px 0; }
</style>
"""

def get_file_icon(filename: str):
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in ["png", "jpg", "jpeg", "gif", "webp"]: return "🖼️"
    elif ext in ["mp4", "mov", "avi"]: return "🎬"
    elif ext in ["mp3", "wav", "flac"]: return "🎵"
    elif ext in ["pdf", "txt", "md", "doc", "docx"]: return "📄"
    elif ext in ["zip", "rar", "7z"]: return "📦"
    elif ext in ["py", "js", "html", "css", "json"]: return "💻"
    else: return "📁"

@app.get("/", response_class=HTMLResponse)
def vault_grid_domu():
    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid OS</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 450px;">
            <h1>VaultGrid OS ⚡</h1>
            <p style="text-align:center;">Přihlášení do zabezpečeného cloudu</p>
            <form action="/dashboard" method="POST">
                <input type="text" name="username" placeholder="Uživatelské jméno" required>
                <input type="password" name="password" placeholder="Heslo" required>
                <button type="submit">Vstoupit do systému</button>
            </form>
        </div>
    </body></html>
    """

@app.post("/dashboard", response_class=HTMLResponse)
def dashboard(username: str = Form(...), password: str = Form(...), current_folder: str = Form("/"), target_owner: str = Form(None), view_trash: str = Form("false")):
    if not supabase:
        return "<h3 style='color:white;text-align:center;'>Chyba databáze!</h3><br><a href='/' class='btn'>Zpět</a>"
    
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    users = res.data
    if not users or users[0]["password"] != password:
        return f"""
        <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
            <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
                <h2>Přístup odepřen</h2>
                <p>Nesprávné jméno nebo heslo.</p>
                <a href="/" class="btn">Zpět</a>
            </div>
        </body></html>
        """
    
    user = users[0]
    is_admin = (user["role"] == "admin")
    view_owner = target_owner if (is_admin and target_owner) else username

    # Kontrola ACL oprávnění pro běžného uživatele
    if not is_admin and current_folder != "/":
        perm_check = supabase.table("nxt_permissions").select("*").eq("username", username).eq("folder_path", current_folder).execute()
        if not perm_check.data:
            return f"""
            <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
                <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
                    <h2>Odepřen přístup 🚫</h2>
                    <p>Nemáš oprávnění vstupovat do složky <b>{current_folder}</b>.</p>
                    <form action="/dashboard" method="POST">
                        <input type="hidden" name="username" value="{username}">
                        <input type="hidden" name="password" value="{password}">
                        <button type="submit" class="btn">Zpět do kořene</button>
                    </form>
                </div>
            </body></html>
            """

    # Telemetrie
    all_user_files = supabase.table("nxt_files").select("size").eq("owner", view_owner).eq("is_deleted", False).execute().data
    total_bytes = sum([f.get("size", 0) for f in all_user_files])
    total_mb = round(total_bytes / (1024 * 1024), 2)

    is_in_trash = (view_trash == "true")
    if is_in_trash:
        files_res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", True).execute()
    else:
        files_res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("folder", current_folder).eq("is_deleted", False).execute()
    
    items = files_res.data
    folders_set = set()
    files_list = []

    for item in items:
        if is_in_trash:
            files_list.append(item)
        else:
            item_folder = item.get("folder", "/")
            if item_folder.startswith(current_folder) and item_folder != current_folder:
                rel_path = item_folder[len(current_folder):].strip("/")
                if rel_path:
                    sub_folder_name = rel_path.split("/")[0]
                    full_sub_path = f"{current_folder.rstrip('/')}/{sub_folder_name}"
                    folders_set.add(full_sub_path)
            
            if item_folder == current_folder and not item['filename'].startswith(".slozkové_meta_"):
                files_list.append(item)

    folders_html = ""
    for f_path in sorted(folders_set):
        folder_name = f_path.split("/")[-1]
        folders_html += f"""
        <form action="/dashboard" method="POST" style="display:inline-block; margin-right: 10px;">
            <input type="hidden" name="username" value="{username}">
            <input type="hidden" name="password" value="{password}">
            <input type="hidden" name="current_folder" value="{f_path}">
            <input type="hidden" name="target_owner" value="{view_owner}">
            <button type="submit" style="background: rgba(56, 189, 248, 0.2); border: 1px solid #38bdf8; color: #38bdf8; padding: 8px 15px; border-radius: 8px; cursor:pointer;">
                📁 {folder_name}
            </button>
        </form>
        """

    files_html = ""
    for f in files_list:
        icon = get_file_icon(f['filename'])
        if is_in_trash:
            action_buttons = f"""
                <a href="/restore-file?id={f['id']}&username={username}&password={password}&target_owner={view_owner}" class="file-link" style="color: #10b981;">Obnovit</a>
                <a href="/delete-permanently?id={f['id']}&username={username}&password={password}&target_owner={view_owner}" class="delete-link">Smazat navždy</a>
            """
        else:
            action_buttons = f"""
                <a href="{f['file_url']}" download class="file-link">Stáhnout</a>
                <a href="/delete-file?id={f['id']}&username={username}&password={password}&folder={current_folder}&target_owner={view_owner}" class="delete-link">Do koše</a>
            """
        files_html += f"<tr><td>{icon} {f['filename']}</td><td>{action_buttons}</td></tr>"
    
    if not folders_html and not files_html:
        files_html = "<tr><td colspan='2' style='text-align:center; color:#64748b;'>Tento adresář je prázdný.</td></tr>"

    breadcrumb_html = f"<a href='#' onclick='navigate(\"/\")' style='color:#38bdf8; text-decoration:none;'>🏠 Domů</a>"
    path_parts = current_folder.strip("/").split("/") if current_folder != "/" else []
    built_path = ""
    for part in path_parts:
        if part:
            built_path += f"/{part}"
            breadcrumb_html += f" / <a href='#' onclick='navigate(\"{built_path}\")' style='color:#38bdf8; text-decoration:none;'>{part}</a>"

    admin_section = ""
    target_owner_selector = ""
    if is_admin:
        all_users_res = supabase.table("nxt_users").select("username, role").execute()
        all_users = all_users_res.data
        users_rows = "".join([f"<tr><td>{u['username']}</td><td>{u['role']}</td></tr>" for u in all_users])
        options_html = "".join([f"<option value='{u['username']}' {'selected' if u['username'] == view_owner else ''}>{u['username']}</option>" for u in all_users])
        
        target_owner_selector = f"""
        <div class="box-section" style="border-color: rgba(56, 189, 248, 0.3);">
            <p style="color:#38bdf8; margin-top:0;"><b>🛡️ Admin režim: Správa úložiště uživatele</b></p>
            <form action="/dashboard" method="POST">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="password" value="{password}">
                <input type="hidden" name="current_folder" value="{current_folder}">
                <select name="target_owner" onchange="this.form.submit()">{options_html}</select>
            </form>
        </div>
        """

        # Načtení seznamu existujících složek pro udělování přístupů
        all_folders_res = supabase.table("nxt_files").select("folder").eq("owner", view_owner).execute()
        folders_list_acl = sorted(list(set([item['folder'] for item in all_folders_res.data if item['folder'] != '/'])))
        folder_options = "".join([f"<option value='{f}'>{f}</option>" for f in folders_list_acl])
        user_options = "".join([f"<option value='{u['username']}'>{u['username']}</option>" for u in all_users])

        admin_section = f"""
        <hr>
        <h2>🛡️ Správa oprávnění a přístupů (ACL)</h2>
        <form action="/admin/grant-access" method="POST" class="box-section">
            <input type="hidden" name="admin_user" value="{username}">
            <input type="hidden" name="admin_pass" value="{password}">
            <p style="color:#38bdf8; margin-top:0;"><b>Udělit uživateli přístup ke složce</b></p>
            <label>Uživatel:</label>
            <select name="target_user">{user_options}</select>
            <label style="margin-top:10px; display:block;">Složka:</label>
            <select name="folder_path"><option value="/">/</option>{folder_options}</select>
            <button type="submit" style="background: linear-gradient(135deg, #10b981, #059669); margin-top: 15px;">Udělit přístup</button>
        </form>

        <h2>🛡️ VaultGrid Správa uživatelů</h2>
        <table><tr><th>Uživatel</th><th>Role</th></tr>{users_rows}</table>
        <br>
        <form action="/admin/add-user" method="POST" class="box-section">
            <input type="hidden" name="admin_user" value="{username}">
            <input type="hidden" name="admin_pass" value="{password}">
            <p style="color:#38bdf8; margin-top:0;"><b>Vytvořit nového uživatele</b></p>
            <input type="text" name="new_user" placeholder="Uživatelské jméno" required>
            <input type="password" name="new_pass" placeholder="Heslo" required>
            <select name="new_role"><option value="uzivatel">Běžný uživatel</option><option value="admin">Administrátor</option></select>
            <button type="submit" style="background: linear-gradient(135deg, #10b981, #059669);">Vytvořit uživatele</button>
        </form>
        """

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid OS - Dashboard</title>{VAULT_GRID_STYLE}
    <script>
        function navigate(path) {{
            const form = document.createElement('form');
            form.method = 'POST'; form.action = '/dashboard';
            const u = document.createElement('input'); u.type = 'hidden'; u.name = 'username'; u.value = '{username}';
            const p = document.createElement('input'); p.type = 'hidden'; p.name = 'password'; p.value = '{password}';
            const f = document.createElement('input'); f.type = 'hidden'; f.name = 'current_folder'; f.value = path;
            const o = document.createElement('input'); o.type = 'hidden'; o.name = 'target_owner'; o.value = '{view_owner}';
            form.appendChild(u); form.appendChild(p); form.appendChild(f); form.appendChild(o);
            document.body.appendChild(form); form.submit();
        }}
    </script>
    </head>
    <body>
        <div class="glass-dashboard">
            <div class="badge">Uživatel: {username} ({user['role']}) | Spravuje: {view_owner}</div>
            <h1>VaultGrid Storage OS ⚡</h1>
            
            <div class="box-section" style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <p style="margin:0; color:#38bdf8;"><b>Stav serveru & Služeb</b></p>
                    <span style="color: #10b981; font-size: 13px;">● Supabase Online</span> &nbsp;&nbsp; 
                    <span style="color: #10b981; font-size: 13px;">● Hugging Face API Online</span>
                </div>
                <div style="width: 250px;">
                    <p style="margin:0; font-size: 13px;">Využito místa: <b>{total_mb} MB</b></p>
                    <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {min(total_mb / 100, 100)}%;"></div></div>
                </div>
            </div>

            {target_owner_selector}

            <div class="box-section">
                <div class="breadcrumb">Cesta: {breadcrumb_html}</div>
                <div style="display:flex; gap: 10px; margin-bottom: 15px;">
                    <form action="/dashboard" method="POST" style="margin:0;">
                        <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                        <input type="hidden" name="current_folder" value="/"><input type="hidden" name="target_owner" value="{view_owner}">
                        <button type="submit" style="margin:0; background: #334155; padding: 10px 15px;">🏠 Domů</button>
                    </form>
                    <form action="/dashboard" method="POST" style="margin:0;">
                        <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                        <input type="hidden" name="current_folder" value="{current_folder}"><input type="hidden" name="target_owner" value="{view_owner}">
                        <input type="hidden" name="view_trash" value="{"false" if is_in_trash else "true"}">
                        <button type="submit" style="margin:0; background: {"#0284c7" if is_in_trash else "#334155"}; padding: 10px 15px;">🗑️ Koš</button>
                    </form>
                </div>
                {"<!-- Skrýt tvoření v koši -->" if is_in_trash else f'''
                <form action="/create-folder" method="POST" style="display:flex; gap:10px;">
                    <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                    <input type="hidden" name="current_folder" value="{current_folder}"><input type="hidden" name="target_owner" value="{view_owner}">
                    <input type="text" name="new_folder_name" placeholder="Název nové podsložky..." required style="margin:0;">
                    <button type="submit" style="margin:0; width: 180px; background: #0284c7;">+ Vytvořit složku</button>
                </form>
                '''}
            </div>

            <hr>
            <h2>{"🗑️ Obsah Koše" if is_in_trash else f"📂 Složky a soubory v {current_folder}"}</h2>
            {"<div style='margin-bottom:15px;'>" + folders_html + "</div>" if not is_in_trash and folders_html else ""}
            <table><tr><th>Položka</th><th>Akce</th></tr>{files_html}</table>
            
            {"<!-- Skrýt nahrávání v koši -->" if is_in_trash else f'''
            <br>
            <form action="/upload" method="POST" enctype="multipart/form-data" class="box-section">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="folder" value="{current_folder}"><input type="hidden" name="target_owner" value="{view_owner}">
                <p style="margin-top:0; color:#38bdf8;"><b>📤 Nahrát nový soubor do: {current_folder}</b></p>
                <input type="file" name="file" required style="padding: 10px;">
                <button type="submit">Nahrát do VaultGridu</button>
            </form>
            '''}

            {admin_section}
            <br><hr>
            <a href="/" class="btn" style="background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5;">Odhlásit se</a>
        </div>
    </body></html>
    """

@app.post("/admin/grant-access", response_class=HTMLResponse)
def grant_access(admin_user: str = Form(...), admin_pass: str = Form(...), target_user: str = Form(...), folder_path: str = Form(...)):
    if not supabase: return "Chyba"
    res = supabase.table("nxt_users").select("*").eq("username", admin_user).execute()
    if not res.data or res.data[0]["password"] != admin_pass or res.data[0]["role"] != "admin":
        return "Neoprávněná akce!"
    
    try:
        supabase.table("nxt_permissions").insert({
            "username": target_user,
            "folder_path": folder_path
        }).execute()
    except Exception:
        pass # Už možná existuje

    return f"""
    <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
        <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
            <h2>Přístup pro {target_user} k {folder_path} udělen! 🔑</h2>
            <form action="/dashboard" method="POST">
                <input type="hidden" name="username" value="{admin_user}">
                <input type="hidden" name="password" value="{admin_pass}">
                <button type="submit" class="btn">Zpět do admin panelu</button>
            </form>
        </div>
    </body></html>
    """

@app.post("/create-folder", response_class=HTMLResponse)
def create_folder(username: str = Form(...), password: str = Form(...), current_folder: str = Form(...), new_folder_name: str = Form(...), target_owner: str = Form(None)):
    if not supabase: return "Chyba"
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    if not res.data or res.data[0]["password"] != password: return "Neautorizováno"
    
    clean_name = new_folder_name.strip().replace("/", "")
    if not clean_name: return "Neplatný název"
    
    new_path = f"{current_folder.rstrip('/')}/{clean_name}"
    view_owner = target_owner if target_owner else username
    
    try:
        supabase.table("nxt_files").insert({
            "owner": view_owner, "filename": f".slozkové_meta_{clean_name}",
            "storage_provider": "system", "file_url": "#", "folder": new_path, "size": 0, "is_deleted": False
        }).execute()
        # Automaticky udělit přístup tvůrci složky
        supabase.table("nxt_permissions").insert({"username": view_owner, "folder_path": new_path}).execute()
    except Exception:
        pass

    return f"""
    <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
        <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
            <h2>Složka vytvořena! 📁</h2>
            <form action="/dashboard" method="POST">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="current_folder" value="{new_path}"><input type="hidden" name="target_owner" value="{view_owner}">
                <button type="submit" class="btn">Pokračovat</button>
            </form>
        </div>
    </body></html>
    """

@app.post("/upload", response_class=HTMLResponse)
async def upload_file(username: str = Form(...), password: str = Form(...), folder: str = Form("/"), target_owner: str = Form(None), file: UploadFile = File(...)):
    if not supabase: return "Chyba databáze"
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    if not res.data or res.data[0]["password"] != password: return "Neautorizováno"
    
    view_owner = target_owner if target_owner else username
    file_bytes = await file.read()
    file_size = len(file_bytes)
    file_path_in_repo = f"{view_owner}{folder}/{file.filename}".replace("//", "/")
    
    try:
        if hf_api and HF_REPO_ID:
            hf_api.upload_file(path_or_fileobj=file_bytes, path_in_repo=file_path_in_repo, repo_id=HF_REPO_ID, repo_type="dataset")
            public_url = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/{file_path_in_repo}"
        else:
            raise HTTPException(status_code=500, detail="Hugging Face není nastaven!")
        
        supabase.table("nxt_files").insert({
            "owner": view_owner, "filename": file.filename, "storage_provider": "huggingface",
            "file_url": public_url, "folder": folder, "size": file_size, "is_deleted": False
        }).execute()
    except Exception as e:
        return f"<h3>Chyba při nahrávání: {str(e)}</h3><br><a href='/' class='btn'>Zpět</a>"
    
    return f"""
    <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
        <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
            <h2>Soubor úspěšně nahrán! 🎉</h2>
            <form action="/dashboard" method="POST">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="current_folder" value="{folder}"><input type="hidden" name="target_owner" value="{view_owner}">
                <button type="submit" class="btn">Zpět do složky</button>
            </form>
        </div>
    </body></html>
    """

@app.get("/delete-file", response_class=HTMLResponse)
def delete_file(id: int, username: str, password: str, folder: str, target_owner: str = None):
    if not supabase: return "Chyba"
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    if not res.data or res.data[0]["password"] != password: return "Neoprávněná akce!"
    view_owner = target_owner if target_owner else username
    supabase.table("nxt_files").update({"is_deleted": True}).eq("id", id).execute()
    return f"""
    <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
        <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
            <h2>Položka přesunuta do koše 🗑️</h2>
            <form action="/dashboard" method="POST">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="current_folder" value="{folder}"><input type="hidden" name="target_owner" value="{view_owner}">
                <button type="submit" class="btn">Zpět</button>
            </form>
        </div>
    </body></html>
    """

@app.get("/restore-file", response_class=HTMLResponse)
def restore_file(id: int, username: str, password: str, target_owner: str = None):
    if not supabase: return "Chyba"
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    if not res.data or res.data[0]["password"] != password: return "Neoprávněná akce!"
    view_owner = target_owner if target_owner else username
    supabase.table("nxt_files").update({"is_deleted": False}).eq("id", id).execute()
    return f"""
    <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
        <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
            <h2>Položka obnovena! ✅</h2>
            <form action="/dashboard" method="POST">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="current_folder" value="/"><input type="hidden" name="target_owner" value="{view_owner}"><input type="hidden" name="view_trash" value="true">
                <button type="submit" class="btn">Zpět do koše</button>
            </form>
        </div>
    </body></html>
    """

@app.get("/delete-permanently", response_class=HTMLResponse)
def delete_permanently(id: int, username: str, password: str, target_owner: str = None):
    if not supabase: return "Chyba"
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    if not res.data or res.data[0]["password"] != password: return "Neoprávněná akce!"
    view_owner = target_owner if target_owner else username
    supabase.table("nxt_files").delete().eq("id", id).execute()
    return f"""
    <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
        <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
            <h2>Definitivně smazáno! ❌</h2>
            <form action="/dashboard" method="POST">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="current_folder" value="/"><input type="hidden" name="target_owner" value="{view_owner}"><input type="hidden" name="view_trash" value="true">
                <button type="submit" class="btn">Zpět do koše</button>
            </form>
        </div>
    </body></html>
    """

@app.post("/admin/add-user", response_class=HTMLResponse)
def add_user(admin_user: str = Form(...), admin_pass: str = Form(...), new_user: str = Form(...), new_pass: str = Form(...), new_role: str = Form(...)):
    if not supabase: return "Chyba"
    res = supabase.table("nxt_users").select("*").eq("username", admin_user).execute()
    if not res.data or res.data[0]["password"] != admin_pass or res.data[0]["role"] != "admin":
        return "Neoprávněná akce!"
    try:
        supabase.table("nxt_users").insert({"username": new_user, "password": new_pass, "role": new_role}).execute()
    except Exception as e:
        return f"Chyba: {str(e)}"
    return f"""
    <!DOCTYPE html><html lang="cs"><head>{VAULT_GRID_STYLE}</head><body>
        <div class="glass-dashboard" style="max-width: 400px; text-align:center;">
            <h2>Uživatel {new_user} vytvořen! 🚀</h2>
            <form action="/dashboard" method="POST">
                <input type="hidden" name="username" value="{admin_user}"><input type="hidden" name="password" value="{admin_pass}">
                <button type="submit" class="btn">Zpět do Admin panelu</button>
            </form>
        </div>
    </body></html>
    """

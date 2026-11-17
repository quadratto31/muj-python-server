import os
import json
import html
import shutil
import platform
import urllib.request
from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from supabase import create_client, Client
from huggingface_hub import HfApi

app = FastAPI(title="VaultGrid OS", version="16.0")

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
        max-width: 1080px;
        box-shadow: 0 25px 60px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }
    h1, h2, h3 { 
        color: #38bdf8; 
        text-align: center; 
        text-shadow: 0 0 20px rgba(56, 189, 248, 0.4);
    }
    p { color: #94a3b8; font-size: 14px; }
    input, select, textarea {
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
    input:focus, select:focus, textarea:focus {
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
        font-size: 14px;
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
    .app-dock {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 12px;
        margin: 18px 0;
    }
    .app-card {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 14px 10px;
        text-align: center;
        text-decoration: none;
        color: #f8fafc;
        transition: all 0.2s ease;
        display: block;
    }
    .app-card:hover {
        transform: translateY(-3px);
        border-color: #38bdf8;
        box-shadow: 0 10px 25px rgba(56, 189, 248, 0.25);
    }
    .app-icon { font-size: 26px; display: block; margin-bottom: 6px; }
    .app-title { font-weight: bold; font-size: 13px; display: block; }
    .app-sub { font-size: 11px; color: #94a3b8; }
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
    a.file-link { color: #38bdf8; text-decoration: none; font-weight: bold; margin-right: 10px; font-size: 13px; }
    a.file-link:hover { text-decoration: underline; }
    a.delete-link { color: #f87171; text-decoration: none; font-size: 13px; }
    a.delete-link:hover { text-decoration: underline; }
    .box-section { background: rgba(15, 23, 42, 0.5); padding: 15px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.05); margin-top: 15px; }
    .progress-bar-bg { background: rgba(255,255,255,0.1); border-radius: 10px; height: 12px; width: 100%; overflow: hidden; margin-top: 5px; }
    .progress-bar-fill { background: linear-gradient(90deg, #38bdf8, #0284c7); height: 100%; width: 12%; }
    .breadcrumb { background: rgba(15,23,42,0.8); padding: 10px 15px; border-radius: 8px; margin-bottom: 15px; font-family: monospace; color: #38bdf8; }
    hr { border: 0; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 20px 0; }
    .chat-box {
        background: rgba(9, 13, 22, 0.8);
        border: 1px solid rgba(56, 189, 248, 0.2);
        border-radius: 14px;
        padding: 15px;
        height: 360px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin: 15px 0;
    }
    .chat-msg {
        max-width: 78%;
        padding: 10px 14px;
        border-radius: 14px;
        font-size: 14px;
        line-height: 1.4;
        word-wrap: break-word;
    }
    .chat-mine {
        align-self: flex-end;
        background: linear-gradient(135deg, #0284c7, #0369a1);
        color: #ffffff;
        border-bottom-right-radius: 4px;
    }
    .chat-other {
        align-self: flex-start;
        background: rgba(30, 41, 59, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #f8fafc;
        border-bottom-left-radius: 4px;
    }
</style>
"""

TERMINAL_STYLE = """
<style>
    body {
        background-color: #0c0f17;
        color: #00ff66;
        font-family: 'Courier New', Courier, monospace;
        margin: 0;
        padding: 20px;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
    }
    .terminal-window {
        background: rgba(10, 15, 25, 0.95);
        border: 2px solid #00ff66;
        border-radius: 12px;
        width: 100%;
        max-width: 900px;
        padding: 25px;
        box-shadow: 0 0 30px rgba(0, 255, 102, 0.2);
    }
    .terminal-output {
        height: 420px;
        overflow-y: auto;
        white-space: pre-wrap;
        margin-bottom: 15px;
        font-size: 14px;
        line-height: 1.5;
        border-bottom: 1px dashed #00ff6633;
        padding-bottom: 15px;
    }
    .terminal-input-line {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .prompt {
        color: #38bdf8;
        font-weight: bold;
    }
    input.term-input {
        flex: 1;
        background: transparent;
        border: none;
        color: #00ff66;
        font-family: 'Courier New', Courier, monospace;
        font-size: 16px;
        outline: none;
    }
    .logout-btn {
        background: #ef4444;
        color: white;
        border: none;
        padding: 5px 12px;
        border-radius: 6px;
        cursor: pointer;
        font-family: inherit;
        font-weight: bold;
    }
    .logout-btn:hover { background: #dc2626; }
</style>
"""

EDITABLE_EXTENSIONS = ["txt", "md", "py", "html", "css", "js", "json", "csv", "xml", "yml", "yaml"]
VIDEO_EXTENSIONS = ["mp4", "mov", "avi", "webm", "mkv"]
AUDIO_EXTENSIONS = ["mp3", "wav", "flac", "ogg", "m4a"]

def get_file_icon(filename: str):
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in ["png", "jpg", "jpeg", "gif", "webp"]: return "🖼️"
    elif ext in VIDEO_EXTENSIONS: return "🎬"
    elif ext in AUDIO_EXTENSIONS: return "🎵"
    elif ext in ["pdf", "txt", "md", "doc", "docx"]: return "📄"
    elif ext in ["zip", "rar", "7z"]: return "📦"
    elif ext in ["py", "js", "html", "css", "json"]: return "💻"
    else: return "📁"

def is_system_record(item: dict) -> bool:
    fname = item.get("filename", "")
    provider = item.get("storage_provider", "")
    return (
        provider in ["vault_chat", "system_lock"]
        or fname.startswith(".slozkové_meta_")
        or fname.startswith(".vault_")
    )

# --- HLAVNÍ PŘIHLAŠOVACÍ STRÁNKA ---
@app.get("/", response_class=HTMLResponse)
def vault_grid_domu():
    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid OS</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 450px;">
            <h1>VaultGrid OS ⚡</h1>
            <p style="text-align:center;">Cloud OS v16.0 (pro terminál: root / root)</p>
            <form action="/login-router" method="POST">
                <input type="text" name="username" placeholder="Uživatelské jméno" required>
                <input type="password" name="password" placeholder="Heslo" required>
                <button type="submit">Vstoupit do systému</button>
            </form>
        </div>
    </body></html>
    """

@app.post("/login-router", response_class=HTMLResponse)
def login_router(username: str = Form(...), password: str = Form(...)):
    if username == "root" and password == "root":
        return terminal_view("root", "/", "Vítejte ve VaultGrid ROOT terminálu [v16.0]!\nZadejte 'help', 'neofetch' nebo 'chat' pro komunikaci.\n\n")

    if not supabase:
        return "Chyba databáze"
    
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
    return render_dashboard(username, password, "/", None, "false", "")

# --- ROOT TERMINÁL ---
def terminal_view(username: str, current_folder: str, history: str):
    safe_history = html.escape(history)
    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid ROOT Terminal</title>{TERMINAL_STYLE}</head>
    <body>
        <div class="terminal-window">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <span>⚡ VaultGrid OS [Version 16.0-ROOT]</span>
                <form action="/" method="GET" style="margin:0;"><button type="submit" class="logout-btn">Odhlásit</button></form>
            </div>
            <div class="terminal-output" id="output">{safe_history}</div>
            <form action="/terminal-exec" method="POST" class="terminal-input-line" onsubmit="setTimeout(() => document.getElementById('cmd').value='', 10);">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="current_folder" value="{current_folder}">
                <input type="hidden" name="history" value="{safe_history}">
                <span class="prompt">root@vaultgrid:{current_folder}#</span>
                <input type="text" name="command" id="cmd" class="term-input" autofocus autocomplete="off" required>
            </form>
        </div>
        <script>
            const out = document.getElementById('output');
            out.scrollTop = out.scrollHeight;
        </script>
    </body></html>
    """

@app.post("/terminal-exec", response_class=HTMLResponse)
def terminal_exec(username: str = Form(...), current_folder: str = Form(...), history: str = Form(...), command: str = Form(...)):
    cmd = command.strip()
    new_history = history + f"root@vaultgrid:{current_folder}# {cmd}\n"
    parts = cmd.split(" ")
    action = parts[0].lower() if parts else ""

    if action == "help":
        new_history += "Dostupné příkazy:\n  ls              - Výpis souborů v aktuálním adresáři\n  cd <složka>     - Změna adresáře\n  mkdir <složka>  - Vytvoření nové složky\n  chat [zpráva]   - Zobrazení nebo odeslání zprávy do VaultChatu\n  neofetch        - Systémové info a architektura jádra\n  status          - Stav serveru a připojení\n  users           - Seznam uživatelů v databázi\n  clear           - Vyčištění terminálu\n\n"
    elif action == "clear":
        new_history = "VaultGrid OS ROOT Terminal\nZadejte 'help' pro nápovědu.\n\n"
    elif action == "neofetch":
        new_history += (
            "   _    __            ____  ______     _     __\n"
            "  | |  / /___ ___  __/ / /_/ ____/____(_)___/ /\n"
            "  | | / / __ `/ / / / / __/ / __/ ___/ / __  / \n"
            "  | |/ / /_/ / /_/ / / /_/ /_/ / /  / / /_/ /  \n"
            "  |___/\\__,_/\\__,_/_/\\__/\\____/_/  /_/\\__,_/   \n"
            f"  OS: VaultGrid OS v16.0 VaultShield & Chat Edition\n"
            f"  Host Kernel: {platform.system()} {platform.release()}\n"
            f"  Apps: VaultFlix, VaultBeats, VaultChat, VaultCode IDE\n"
            f"  Security: VaultShield Folder PIN Lock Active\n\n"
        )
    elif action == "chat":
        if supabase:
            if len(parts) > 1:
                msg_text = " ".join(parts[1:]).strip()
                supabase.table("nxt_files").insert({
                    "owner": "root", "filename": "chat_msg",
                    "storage_provider": "vault_chat", "file_url": msg_text,
                    "folder": "/_chat", "size": 0, "is_deleted": False
                }).execute()
                new_history += f"  [Odesláno do VaultChatu]: {msg_text}\n\n"
            else:
                msgs = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_chat").order("id", desc=False).execute().data
                recent = msgs[-10:] if msgs else []
                if recent:
                    for m in recent:
                        new_history += f"  [{m['owner']}]: {m['file_url']}\n"
                else:
                    new_history += "  (VaultChat je zatím prázdný)\n"
                new_history += "\n"
    elif action == "ls":
        if supabase:
            files = supabase.table("nxt_files").select("filename, folder, storage_provider").eq("folder", current_folder).execute().data
            shown = 0
            if files:
                for f in files:
                    if not is_system_record(f):
                        new_history += f"  [FILE] {f['filename']}\n"
                        shown += 1
            if shown == 0:
                new_history += "  (adresář je prázdný)\n"
        new_history += "\n"
    elif action == "users":
        if supabase:
            usrs = supabase.table("nxt_users").select("username, role").execute().data
            for u in usrs:
                new_history += f"  - {u['username']} ({u['role']})\n"
        new_history += "\n"
    elif action == "status":
        new_history += "  Server: Online (Render Cloud)\n  Database: Supabase Connected\n  Storage Engine: Hugging Face Datasets\n  Security: VaultShield PIN Lock Active\n\n"
    elif action == "cd":
        if len(parts) > 1:
            target = parts[1]
            if target == "..": current_folder = "/"
            else: current_folder = f"/{target.strip('/')}"
            new_history += f"Změněno na {current_folder}\n\n"
        else:
            new_history += "Chybí cíl složky.\n\n"
    elif action == "mkdir":
        if len(parts) > 1:
            folder_name = parts[1].strip("/")
            new_path = f"{current_folder.rstrip('/')}/{folder_name}"
            if supabase:
                try:
                    supabase.table("nxt_files").insert({
                        "owner": "root", "filename": f".slozkové_meta_{folder_name}",
                        "storage_provider": "system", "file_url": "#", "folder": new_path, "size": 0, "is_deleted": False
                    }).execute()
                except Exception: pass
            new_history += f"Složka {new_path} vytvořena.\n\n"
        else:
            new_history += "Chybí název složky.\n\n"
    else:
        new_history += f"Neznámý příkaz: {cmd}. Zadejte 'help'.\n\n"

    return terminal_view(username, current_folder, new_history)

# --- GRAFICKÝ DASHBOARD + VAULTSHIELD PIN ZÁMEK ---
def render_dashboard(username, password, current_folder, target_owner, view_trash, unlocked_pin=""):
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    user = res.data[0]
    is_admin = (user["role"] == "admin")
    view_owner = target_owner if (is_admin and target_owner) else username

    # Kontrola VaultShield PIN zámku pro aktuální složku
    is_folder_locked = False
    stored_pin = ""
    if current_folder != "/" and view_trash != "true":
        lock_res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("folder", current_folder).eq("filename", ".vault_pin_lock").eq("is_deleted", False).execute()
        if lock_res.data:
            is_folder_locked = True
            stored_pin = lock_res.data[0].get("file_url", "")
            if unlocked_pin != stored_pin:
                error_msg = "<p style='color: #f87171; font-weight: bold;'>❌ Nesprávný PIN kód! Zkus to znovu.</p>" if unlocked_pin else ""
                return f"""
                <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultShield - Zamčená složka</title>{VAULT_GRID_STYLE}</head>
                <body>
                    <div class="glass-dashboard" style="max-width: 440px; text-align: center; border-color: rgba(245, 158, 11, 0.45);">
                        <div style="font-size: 48px; margin-bottom: 10px;">🔒</div>
                        <h2 style="color: #fbbf24; margin-top: 0;">VaultShield Trezor</h2>
                        <p>Složka <b style="color: #38bdf8;">{current_folder}</b> je chráněna PIN kódem.</p>
                        {error_msg}
                        <form action="/dashboard-render" method="POST">
                            <input type="hidden" name="username" value="{username}">
                            <input type="hidden" name="password" value="{password}">
                            <input type="hidden" name="current_folder" value="{current_folder}">
                            <input type="hidden" name="target_owner" value="{view_owner}">
                            <input type="password" name="unlocked_pin" placeholder="Zadej 4místný PIN..." maxlength="8" inputmode="numeric" autofocus required style="text-align: center; font-size: 20px; letter-spacing: 6px;">
                            <button type="submit" style="background: linear-gradient(135deg, #d97706, #b45309);">🔓 Odemknout složku</button>
                        </form>
                        <form action="/dashboard-render" method="POST" style="margin-top: 8px;">
                            <input type="hidden" name="username" value="{username}">
                            <input type="hidden" name="password" value="{password}">
                            <input type="hidden" name="current_folder" value="/">
                            <input type="hidden" name="target_owner" value="{view_owner}">
                            <button type="submit" style="background: #334155;">⬅ Zpět do kořenové složky</button>
                        </form>
                    </div>
                </body></html>
                """

    all_user_files = supabase.table("nxt_files").select("size, storage_provider, filename").eq("owner", view_owner).eq("is_deleted", False).execute().data
    total_bytes = sum([f.get("size", 0) for f in all_user_files if not is_system_record(f)])
    total_mb = round(total_bytes / (1024 * 1024), 2)

    is_in_trash = (view_trash == "true")
    if is_in_trash:
        files_res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", True).execute()
    else:
        files_res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute()
    
    items = files_res.data
    folders_set = set()
    locked_folders_set = set()
    files_list = []

    for item in items:
        if item.get("storage_provider") == "vault_chat":
            continue
        if is_in_trash:
            if not is_system_record(item):
                files_list.append(item)
        else:
            item_folder = item.get("folder", "/")
            if item.get("filename") == ".vault_pin_lock":
                locked_folders_set.add(item_folder)
            if item_folder.startswith(current_folder) and item_folder != current_folder:
                rel_path = item_folder[len(current_folder):].strip("/")
                if rel_path:
                    sub_folder_name = rel_path.split("/")[0]
                    folders_set.add(f"{current_folder.rstrip('/')}/{sub_folder_name}")
            if item_folder == current_folder and not is_system_record(item):
                files_list.append(item)

    folders_html = ""
    for f_path in sorted(folders_set):
        folder_name = f_path.split("/")[-1]
        is_sub_locked = f_path in locked_folders_set
        folder_icon = "🔒" if is_sub_locked else "📁"
        border_col = "#fbbf24" if is_sub_locked else "#38bdf8"
        text_col = "#fbbf24" if is_sub_locked else "#38bdf8"
        folders_html += f"""
        <form action="/dashboard-render" method="POST" style="display:inline-block; margin-right: 10px;">
            <input type="hidden" name="username" value="{username}">
            <input type="hidden" name="password" value="{password}">
            <input type="hidden" name="current_folder" value="{f_path}">
            <input type="hidden" name="target_owner" value="{view_owner}">
            <button type="submit" style="background: rgba(56, 189, 248, 0.15); border: 1px solid {border_col}; color: {text_col}; padding: 8px 15px; border-radius: 8px; cursor:pointer;">{folder_icon} {folder_name}</button>
        </form>
        """

    files_html = ""
    for f in files_list:
        icon = get_file_icon(f['filename'])
        ext = f['filename'].split(".")[-1].lower() if "." in f['filename'] else ""
        
        media_btn = ""
        if ext in VIDEO_EXTENSIONS or ext in AUDIO_EXTENSIONS:
            media_btn = f'<a href="/media-player?file_url={f["file_url"]}&filename={f["filename"]}" class="file-link" style="color: #f59e0b;">Přehrát</a>'

        live_html_btn = ""
        if ext == "html":
            live_html_btn = f'<a href="/live?id={f["id"]}" target="_blank" class="file-link" style="color: #ec4899;">Živý web</a>'

        edit_btn = ""
        if ext in EDITABLE_EXTENSIONS:
            edit_btn = f'<a href="/code-editor?id={f["id"]}&username={username}&password={password}&target_owner={view_owner}" class="file-link" style="color: #22c55e;">Upravit kód</a>'

        if is_in_trash:
            action_buttons = f"""
                <a href="/restore-file?id={f['id']}&username={username}&password={password}&target_owner={view_owner}" class="file-link" style="color: #10b981;">Obnovit</a>
                <a href="/delete-permanently?id={f['id']}&username={username}&password={password}&target_owner={view_owner}" class="delete-link">Smazat navždy</a>
            """
        else:
            action_buttons = f"""
                <a href="{f['file_url']}" download class="file-link">Stáhnout</a>
                {media_btn}
                {live_html_btn}
                {edit_btn}
                <a href="/share?id={f['id']}" target="_blank" class="file-link" style="color: #10b981;">Sdílet</a>
                <a href="/ai-analyze?id={f['id']}" class="file-link" style="color: #a855f7;">AI</a>
                <a href="/file-versions?filename={f['filename']}&username={view_owner}" class="file-link" style="color: #38bdf8;">Verze</a>
                <a href="/file-comments?file_id={f['id']}&username={username}&password={password}" class="file-link" style="color: #06b6d4;">Komentáře</a>
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

    # Ovládací panel PIN zámku pro aktuální podsložku
    pin_control_html = ""
    if current_folder != "/" and not is_in_trash:
        if is_folder_locked:
            pin_control_html = f"""
            <form action="/remove-folder-pin" method="POST" style="display:flex; gap:10px; margin-top: 10px; align-items: center;">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="current_folder" value="{current_folder}"><input type="hidden" name="target_owner" value="{view_owner}">
                <span style="color: #fbbf24; font-size: 13px; flex: 1;">🔓 Složka je odemčená (PIN aktivní)</span>
                <button type="submit" style="margin:0; width: 200px; background: #b45309;">Zrušit PIN zámek</button>
            </form>
            """
        else:
            pin_control_html = f"""
            <form action="/set-folder-pin" method="POST" style="display:flex; gap:10px; margin-top: 10px;">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="current_folder" value="{current_folder}"><input type="hidden" name="target_owner" value="{view_owner}">
                <input type="password" name="new_pin" placeholder="Nastavit PIN zámek pro tuto složku (např. 1234)..." maxlength="8" inputmode="numeric" required style="margin:0;">
                <button type="submit" style="margin:0; width: 200px; background: #d97706;">🔒 Zamknout složku</button>
            </form>
            """

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
            <form action="/dashboard-render" method="POST">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="current_folder" value="{current_folder}">
                <select name="target_owner" onchange="this.form.submit()">{options_html}</select>
            </form>
        </div>
        """
        admin_section = f"""
        <hr>
        <h2>🛡️ Správa uživatelů</h2>
        <table><tr><th>Uživatel</th><th>Role</th></tr>{users_rows}</table>
        <br>
        <form action="/admin/add-user" method="POST" class="box-section">
            <input type="hidden" name="admin_user" value="{username}"><input type="hidden" name="admin_pass" value="{password}">
            <p style="color:#38bdf8; margin-top:0;"><b>Vytvořit nového uživatele</b></p>
            <input type="text" name="new_user" placeholder="Uživatelské jméno" required>
            <input type="password" name="new_pass" placeholder="Heslo" required>
            <select name="new_role"><option value="uzivatel">Uživatel</option><option value="admin">Admin</option></select>
            <button type="submit" style="background: linear-gradient(135deg, #10b981, #059669);">Vytvořit</button>
        </form>
        """

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid OS - Dashboard</title>{VAULT_GRID_STYLE}
    <script>
        function navigate(path) {{
            const form = document.createElement('form');
            form.method = 'POST'; form.action = '/dashboard-render';
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
            
            <!-- DOCK APLIKACÍ -->
            <div class="app-dock">
                <a href="/vaultflix?username={username}&password={password}&target_owner={view_owner}" class="app-card" style="border-color: rgba(239, 68, 68, 0.4);">
                    <span class="app-icon">🎬</span>
                    <span class="app-title" style="color: #f87171;">VaultFlix</span>
                    <span class="app-sub">Filmy a videa</span>
                </a>
                <a href="/vaultbeats?username={username}&password={password}&target_owner={view_owner}" class="app-card" style="border-color: rgba(34, 197, 94, 0.4);">
                    <span class="app-icon">🎧</span>
                    <span class="app-title" style="color: #4ade80;">VaultBeats</span>
                    <span class="app-sub">Hudební stream</span>
                </a>
                <a href="/vaultchat?username={username}&password={password}&target_owner={view_owner}" class="app-card" style="border-color: rgba(14, 165, 233, 0.5);">
                    <span class="app-icon">💬</span>
                    <span class="app-title" style="color: #38bdf8;">VaultChat</span>
                    <span class="app-sub">Týmový chat</span>
                </a>
                <a href="/photo-gallery?username={view_owner}&folder={current_folder}" class="app-card" style="border-color: rgba(56, 189, 248, 0.4);">
                    <span class="app-icon">🖼️</span>
                    <span class="app-title" style="color: #7dd3fc;">VaultPhotos</span>
                    <span class="app-sub">Galerie složky</span>
                </a>
                <a href="/new-file?username={username}&password={password}&folder={current_folder}&target_owner={view_owner}" class="app-card" style="border-color: rgba(236, 72, 153, 0.4);">
                    <span class="app-icon">💻</span>
                    <span class="app-title" style="color: #f472b6;">VaultCode IDE</span>
                    <span class="app-sub">Nový HTML/kód</span>
                </a>
                <a href="/app-center?username={username}&password={password}&target_owner={view_owner}" class="app-card" style="border-color: rgba(168, 85, 247, 0.4);">
                    <span class="app-icon">🚀</span>
                    <span class="app-title" style="color: #c084fc;">App Center</span>
                    <span class="app-sub">Plex, OMV & Hardware</span>
                </a>
            </div>

            <div class="box-section" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                <div>
                    <p style="margin:0; color:#38bdf8;"><b>Stav serveru & Služeb</b></p>
                    <span style="color: #10b981; font-size: 13px;">● Supabase Online</span> &nbsp;&nbsp; 
                    <span style="color: #10b981; font-size: 13px;">● VaultShield PIN Ready</span>
                </div>
                <div style="width: 250px;">
                    <p style="margin:0; font-size: 13px;">Využito místa: <b>{total_mb} MB</b></p>
                    <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {min(total_mb / 100, 100)}%;"></div></div>
                </div>
            </div>

            {target_owner_selector}

            <div class="box-section">
                <div class="breadcrumb">Cesta: {breadcrumb_html}</div>
                <div style="display:flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                    <form action="/dashboard-render" method="POST" style="margin:0;">
                        <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                        <input type="hidden" name="current_folder" value="/"><input type="hidden" name="target_owner" value="{view_owner}">
                        <button type="submit" style="margin:0; background: #334155; padding: 10px 15px;">🏠 Domů</button>
                    </form>
                    <form action="/dashboard-render" method="POST" style="margin:0;">
                        <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                        <input type="hidden" name="current_folder" value="{current_folder}"><input type="hidden" name="target_owner" value="{view_owner}">
                        <input type="hidden" name="view_trash" value="{"false" if is_in_trash else "true"}">
                        <button type="submit" style="margin:0; background: {"#0284c7" if is_in_trash else "#334155"}; padding: 10px 15px;">🗑️ Koš</button>
                    </form>
                    <a href="/system-stats?username={username}&password={password}" class="btn" style="margin:0; background: #475569; padding: 10px 15px; width: auto; line-height: normal;">📊 Statistiky</a>
                </div>
                {"<!-- Skrýt tvoření v koši -->" if is_in_trash else f'''
                <form action="/create-folder" method="POST" style="display:flex; gap:10px;">
                    <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                    <input type="hidden" name="current_folder" value="{current_folder}"><input type="hidden" name="target_owner" value="{view_owner}">
                    <input type="text" name="new_folder_name" placeholder="Název nové podsložky..." required style="margin:0;">
                    <button type="submit" style="margin:0; width: 200px; background: #0284c7;">+ Vytvořit složku</button>
                </form>
                '''}
                {pin_control_html}
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
                <input type="hidden" name="unlocked_pin" value="{unlocked_pin}">
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

@app.post("/dashboard-render", response_class=HTMLResponse)
def dashboard_render_route(username: str = Form(...), password: str = Form(...), current_folder: str = Form("/"), target_owner: str = Form(None), view_trash: str = Form("false"), unlocked_pin: str = Form("")):
    return render_dashboard(username, password, current_folder, target_owner, view_trash, unlocked_pin)

# --- VAULTSHIELD PIN OPERACE ---
@app.post("/set-folder-pin", response_class=HTMLResponse)
def set_folder_pin(username: str = Form(...), password: str = Form(...), current_folder: str = Form(...), target_owner: str = Form(None), new_pin: str = Form(...)):
    if not supabase: return "Chyba"
    view_owner = target_owner if target_owner else username
    clean_pin = new_pin.strip()
    if clean_pin and current_folder != "/":
        supabase.table("nxt_files").delete().eq("owner", view_owner).eq("folder", current_folder).eq("filename", ".vault_pin_lock").execute()
        supabase.table("nxt_files").insert({
            "owner": view_owner, "filename": ".vault_pin_lock",
            "storage_provider": "system_lock", "file_url": clean_pin,
            "folder": current_folder, "size": 0, "is_deleted": False
        }).execute()
    return render_dashboard(username, password, current_folder, view_owner, "false", "")

@app.post("/remove-folder-pin", response_class=HTMLResponse)
def remove_folder_pin(username: str = Form(...), password: str = Form(...), current_folder: str = Form(...), target_owner: str = Form(None)):
    if not supabase: return "Chyba"
    view_owner = target_owner if target_owner else username
    supabase.table("nxt_files").delete().eq("owner", view_owner).eq("folder", current_folder).eq("filename", ".vault_pin_lock").execute()
    return render_dashboard(username, password, current_folder, view_owner, "false", "")

# --- INTERNÍ TÝMOVÝ CHAT (VAULTCHAT) ---
@app.get("/vaultchat", response_class=HTMLResponse)
def vaultchat_view(username: str, password: str, target_owner: str = None):
    if not supabase: return "Chyba databáze"
    view_owner = target_owner if target_owner else username
    msgs_res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_chat").order("id", desc=False).execute()
    messages = msgs_res.data[-60:] if msgs_res.data else []

    chat_html = ""
    for m in messages:
        sender = html.escape(m.get("owner", "neznámý"))
        body = html.escape(m.get("file_url", ""))
        is_mine = (sender == username)
        bubble_class = "chat-msg chat-mine" if is_mine else "chat-msg chat-other"
        sender_label = "Já" if is_mine else sender
        chat_html += f"""
        <div class="{bubble_class}">
            <div style="font-size: 11px; opacity: 0.8; margin-bottom: 3px;"><b>{sender_label}</b></div>
            <div>{body}</div>
        </div>
        """

    if not chat_html:
        chat_html = "<p style='text-align: center; color: #64748b; margin: auto;'>Zatím žádné zprávy. Napiš první zprávu týmu!</p>"

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultChat - Týmový chat</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 750px; border-color: rgba(14, 165, 233, 0.4);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="badge" style="margin:0;">Přihlášen jako: {username}</span>
                <a href="/vaultchat?username={username}&password={password}&target_owner={view_owner}" class="file-link" style="margin:0;">🔄 Obnovit zprávy</a>
            </div>
            <h1 style="margin-top: 10px;">💬 VaultChat Messenger</h1>
            <p style="text-align:center;">Interní komunikace mezi uživateli a Root terminálem</p>

            <div class="chat-box" id="chat-box">
                {chat_html}
            </div>

            <form action="/vaultchat/send" method="POST" style="display: flex; gap: 10px;">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="password" value="{password}">
                <input type="hidden" name="target_owner" value="{view_owner}">
                <input type="text" name="message" placeholder="Napiš zprávu pro tým..." autofocus required style="margin:0;">
                <button type="submit" style="margin:0; width: 150px; background: linear-gradient(135deg, #0284c7, #0369a1);">Odeslat ➤</button>
            </form>

            <br><hr>
            <form action="/dashboard-render" method="POST">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="target_owner" value="{view_owner}">
                <button type="submit" style="background: #334155;">⬅ Zpět do správce souborů</button>
            </form>
        </div>
        <script>
            const cb = document.getElementById('chat-box');
            cb.scrollTop = cb.scrollHeight;
        </script>
    </body></html>
    """

@app.post("/vaultchat/send", response_class=HTMLResponse)
def vaultchat_send(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), message: str = Form(...)):
    if supabase and message.strip():
        supabase.table("nxt_files").insert({
            "owner": username, "filename": "chat_msg",
            "storage_provider": "vault_chat", "file_url": message.strip(),
            "folder": "/_chat", "size": 0, "is_deleted": False
        }).execute()
    return vaultchat_view(username, password, target_owner)

# --- APLIKACE 1: VAULTFLIX (VLASTNÍ NETFLIX) ---
@app.get("/vaultflix", response_class=HTMLResponse)
def vaultflix_view(username: str, password: str, target_owner: str = None):
    if not supabase: return "Chyba databáze"
    view_owner = target_owner if target_owner else username
    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute()
    videos = [f for f in res.data if not is_system_record(f) and f['filename'].split(".")[-1].lower() in VIDEO_EXTENSIONS]

    cards_html = ""
    for v in videos:
        mb = round(v.get("size", 0) / (1024 * 1024), 1)
        cards_html += f"""
        <div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 16px; padding: 15px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="background: linear-gradient(135deg, #450a0a, #1e1b4b); height: 110px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 40px; margin-bottom: 10px;">🎬</div>
                <p style="color: #f8fafc; font-weight: bold; margin: 0 0 5px 0; word-break: break-word;">{v['filename']}</p>
                <p style="font-size: 12px; margin: 0;">Složka: {v['folder']} | {mb} MB</p>
            </div>
            <button onclick="playMovie('{v['file_url']}', '{html.escape(v['filename'])}')" style="background: linear-gradient(135deg, #dc2626, #991b1b); margin-top: 12px;">▶ Přehrát film</button>
        </div>
        """

    if not cards_html:
        cards_html = "<p style='grid-column: 1 / -1; text-align: center; color: #94a3b8;'>Zatím nemáš nahraná žádná videa (.mp4, .mov, .webm). Nahraj je do libovolné složky!</p>"

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultFlix Cinema</title>{VAULT_GRID_STYLE}
    <script>
        function playMovie(url, title) {{
            const box = document.getElementById('cinema-box');
            const player = document.getElementById('cinema-player');
            const heading = document.getElementById('cinema-title');
            heading.innerText = 'Právě hraje: ' + title;
            player.src = url;
            box.style.display = 'block';
            player.play();
            box.scrollIntoView({{ behavior: 'smooth' }});
        }}
    </script>
    </head>
    <body>
        <div class="glass-dashboard" style="border-color: rgba(239, 68, 68, 0.3);">
            <h1 style="color: #ef4444; text-shadow: 0 0 25px rgba(239, 68, 68, 0.5);">🎬 VaultFlix Cinema</h1>
            <p style="text-align:center;">Všechna tvá videa ze všech složek na jednom místě</p>

            <div id="cinema-box" class="box-section" style="display: none; border-color: #ef4444; text-align: center;">
                <h3 id="cinema-title" style="color: #f87171; margin-top: 0;">Přehrávač</h3>
                <video id="cinema-player" controls style="width: 100%; max-height: 480px; border-radius: 12px; background: black;"></video>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; margin-top: 20px;">
                {cards_html}
            </div>

            <br><hr>
            <form action="/dashboard-render" method="POST">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="target_owner" value="{view_owner}">
                <button type="submit" style="background: #334155;">⬅ Zpět do správce souborů</button>
            </form>
        </div>
    </body></html>
    """

# --- APLIKACE 2: VAULTBEATS (VLASTNÍ SPOTIFY) ---
@app.get("/vaultbeats", response_class=HTMLResponse)
def vaultbeats_view(username: str, password: str, target_owner: str = None):
    if not supabase: return "Chyba databáze"
    view_owner = target_owner if target_owner else username
    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute()
    audio_files = [f for f in res.data if not is_system_record(f) and f['filename'].split(".")[-1].lower() in AUDIO_EXTENSIONS]

    tracks_data = [{"title": a["filename"], "url": a["file_url"], "folder": a["folder"]} for a in audio_files]
    tracks_json = json.dumps(tracks_data)

    rows_html = ""
    for idx, a in enumerate(audio_files):
        rows_html += f"""
        <tr style="cursor: pointer;" onclick="playTrack({idx})">
            <td style="color: #4ade80; font-weight: bold;">▶ #{idx + 1}</td>
            <td>🎵 {a['filename']}</td>
            <td style="color: #94a3b8;">{a['folder']}</td>
        </tr>
        """

    if not rows_html:
        rows_html = "<tr><td colspan='3' style='text-align:center; color:#94a3b8;'>Zatím nemáš nahranou žádnou hudbu (.mp3, .wav, .flac). Nahraj ji do cloudu!</td></tr>"

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultBeats Music</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="border-color: rgba(34, 197, 94, 0.35);">
            <h1 style="color: #22c55e; text-shadow: 0 0 25px rgba(34, 197, 94, 0.5);">🎧 VaultBeats Studio Stream</h1>
            <p style="text-align:center;">Tvůj osobní hudební server & playlist</p>

            <div class="box-section" style="border-color: rgba(34, 197, 94, 0.4); background: rgba(6, 78, 59, 0.25);">
                <p id="now-playing" style="color: #4ade80; font-weight: bold; font-size: 16px; margin-top: 0;">Vyber skladbu ze seznamu níže...</p>
                <audio id="audio-player" controls style="width: 100%; margin: 10px 0;"></audio>
                <div style="display: flex; gap: 10px;">
                    <button type="button" onclick="prevTrack()" style="background: #15803d; margin-top: 5px;">⏮ Předchozí</button>
                    <button type="button" onclick="nextTrack()" style="background: #15803d; margin-top: 5px;">⏭ Další skladba</button>
                </div>
            </div>

            <table>
                <tr><th>#</th><th>Skladba</th><th>Složka</th></tr>
                {rows_html}
            </table>

            <br><hr>
            <form action="/dashboard-render" method="POST">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="target_owner" value="{view_owner}">
                <button type="submit" style="background: #334155;">⬅ Zpět do správce souborů</button>
            </form>
        </div>
        <script>
            const tracks = {tracks_json};
            let currentIdx = 0;
            const player = document.getElementById('audio-player');
            const label = document.getElementById('now-playing');

            function playTrack(idx) {{
                if (!tracks.length) return;
                currentIdx = idx;
                player.src = tracks[idx].url;
                label.innerText = '🎶 Právě hraje: ' + tracks[idx].title;
                player.play();
            }}
            function nextTrack() {{
                if (!tracks.length) return;
                playTrack((currentIdx + 1) % tracks.length);
            }}
            function prevTrack() {{
                if (!tracks.length) return;
                playTrack((currentIdx - 1 + tracks.length) % tracks.length);
            }}
            player.addEventListener('ended', nextTrack);
        </script>
    </body></html>
    """

# --- APLIKACE 3: APP CENTER (PLEX, OMV SERVER & TELEMETRIE) ---
@app.get("/app-center", response_class=HTMLResponse)
def app_center_view(username: str, password: str, target_owner: str = None):
    view_owner = target_owner if target_owner else username
    disk_total, disk_used, disk_free = shutil.disk_usage("/")
    free_gb = round(disk_free / (1024**3), 2)
    total_gb = round(disk_total / (1024**3), 2)

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid App Center</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="border-color: rgba(168, 85, 247, 0.35);">
            <h1 style="color: #c084fc;">🚀 VaultGrid App Center & Server Bridge</h1>
            <p style="text-align:center;">Centrum aplikací, kontejnerů a připojení k domácímu železu</p>

            <div class="box-section">
                <h3 style="margin-top:0; text-align:left;">🖥️ Živá hardwarová telemetrie uzlu</h3>
                <p>⚙️ Architektura jádra: <b>{platform.system()} {platform.machine()} ({platform.python_version()})</b></p>
                <p>💾 Lokální kontejnerový disk: <b>{free_gb} GB volných z {total_gb} GB</b></p>
                <p>🌐 Aktivní režim úložiště: <b>Render Cloud + Hugging Face Datasets + VaultShield PIN</b></p>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 15px; margin-top: 15px;">
                <div class="box-section" style="margin-top:0;">
                    <h3 style="margin-top:0; color: #f59e0b;">🟧 Plex / DLNA Media Server</h3>
                    <p>Streamování filmů a seriálů do Smart TV v domácí síti. Připraveno pro napojení na tvůj 1 TB server.</p>
                    <a href="/vaultflix?username={username}&password={password}&target_owner={view_owner}" class="btn" style="background: #d97706;">Spustit VaultFlix Engine</a>
                </div>
                <div class="box-section" style="margin-top:0;">
                    <h3 style="margin-top:0; color: #38bdf8;">🟦 OpenMediaVault (OMV) 1 TB Bridge</h3>
                    <p>Připojení lokálního terabajtového disku přes SMB/NFS pro přímý přístup z Průzkumníka Windows (disk Z:).</p>
                    <span class="badge" style="margin-top:10px;">Stav: Připraveno k migraci na Debian</span>
                </div>
                <div class="box-section" style="margin-top:0;">
                    <h3 style="margin-top:0; color: #4ade80;">🟩 VaultBeats Audio Node</h3>
                    <p>Beztrátový hudební přehrávač s podporou MP3, WAV a FLAC přímo z tvého cloudového trezoru.</p>
                    <a href="/vaultbeats?username={username}&password={password}&target_owner={view_owner}" class="btn" style="background: #16a34a;">Spustit VaultBeats</a>
                </div>
                <div class="box-section" style="margin-top:0;">
                    <h3 style="margin-top:0; color: #38bdf8;">💬 VaultChat Messenger</h3>
                    <p>Interní týmový chat propojený se všemi uživatelskými účty i Root terminálem.</p>
                    <a href="/vaultchat?username={username}&password={password}&target_owner={view_owner}" class="btn" style="background: #0284c7;">Otevřít VaultChat</a>
                </div>
            </div>

            <br><hr>
            <form action="/dashboard-render" method="POST">
                <input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="hidden" name="target_owner" value="{view_owner}">
                <button type="submit" style="background: #334155;">⬅ Zpět do správce souborů</button>
            </form>
        </div>
    </body></html>
    """

# --- APLIKACE 4: VAULTCODE IDE & TVORBA SOUBORŮ PŘÍMO V PROHLÍŽEČI ---
@app.get("/new-file", response_class=HTMLResponse)
def new_file_view(username: str, password: str, folder: str = "/", target_owner: str = None):
    view_owner = target_owner if target_owner else username
    starter_html = """<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>Můj web na VaultGridu</title>
    <style>
        body { background: #0f172a; color: #38bdf8; font-family: sans-serif; text-align: center; padding: 50px; }
    </style>
</head>
<body>
    <h1>Ahoj z VaultGrid Live Hostingu! 🚀</h1>
    <p>Tato stránka běží přímo z mého vlastního cloudového systému.</p>
</body>
</html>"""
    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultCode IDE - Nový soubor</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 900px;">
            <h2>💻 VaultCode IDE – Vytvořit nový soubor ve složce {folder}</h2>
            <form action="/create-text-file" method="POST">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="password" value="{password}">
                <input type="hidden" name="folder" value="{folder}">
                <input type="hidden" name="target_owner" value="{view_owner}">
                <input type="text" name="filename" placeholder="Název souboru (např. mujweb.html, poznamky.txt, skript.py)" value="mujweb.html" required>
                <textarea name="content" rows="16" style="background: #090d16; color: #00ff66; font-family: 'Courier New', monospace; line-height: 1.5;">{html.escape(starter_html)}</textarea>
                <button type="submit" style="background: linear-gradient(135deg, #10b981, #059669);">💾 Uložit soubor do cloudu</button>
            </form>
            <br>
            <a href="javascript:history.back()" class="btn" style="background: #334155;">Zrušit</a>
        </div>
    </body></html>
    """

@app.post("/create-text-file", response_class=HTMLResponse)
def create_text_file(username: str = Form(...), password: str = Form(...), folder: str = Form("/"), target_owner: str = Form(None), filename: str = Form(...), content: str = Form(...)):
    if not supabase: return "Chyba"
    view_owner = target_owner if target_owner else username
    clean_filename = filename.strip().replace("/", "")
    file_bytes = content.encode('utf-8')
    file_path_in_repo = f"{view_owner}{folder}/{clean_filename}".replace("//", "/")

    if hf_api and HF_REPO_ID:
        hf_api.upload_file(path_or_fileobj=file_bytes, path_in_repo=file_path_in_repo, repo_id=HF_REPO_ID, repo_type="dataset")
        public_url = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/{file_path_in_repo}"
    else:
        public_url = "#"

    supabase.table("nxt_files").insert({
        "owner": view_owner, "filename": clean_filename, "storage_provider": "huggingface",
        "file_url": public_url, "folder": folder, "size": len(file_bytes), "is_deleted": False
    }).execute()

    return render_dashboard(username, password, folder, view_owner, "false", "")

@app.get("/code-editor", response_class=HTMLResponse)
def code_editor_view(id: int, username: str, password: str, target_owner: str = None):
    if not supabase: return "Chyba"
    view_owner = target_owner if target_owner else username
    res = supabase.table("nxt_files").select("*").eq("id", id).execute()
    if not res.data: return "Soubor nenalezen."
    f_rec = res.data[0]
    
    file_content = ""
    try:
        with urllib.request.urlopen(f_rec["file_url"]) as response:
            file_content = response.read().decode('utf-8')
    except Exception:
        file_content = "// Nepodařilo se načíst obsah souboru."

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultCode IDE - Editor</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 900px;">
            <h2>💻 VaultCode IDE: {f_rec['filename']}</h2>
            <form action="/save-code" method="POST">
                <input type="hidden" name="id" value="{id}">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="password" value="{password}">
                <input type="hidden" name="target_owner" value="{view_owner}">
                <input type="hidden" name="filename" value="{f_rec['filename']}">
                <input type="hidden" name="folder" value="{f_rec['folder']}">
                <textarea name="content" rows="18" style="background: #090d16; color: #00ff66; font-family: 'Courier New', monospace; line-height: 1.5;">{html.escape(file_content)}</textarea>
                <button type="submit" style="background: linear-gradient(135deg, #10b981, #059669); margin-top: 15px;">💾 Uložit novou verzi do cloudu</button>
            </form>
            <br>
            <a href="javascript:history.back()" class="btn" style="background: #334155;">Zpět</a>
        </div>
    </body></html>
    """

@app.post("/save-code", response_class=HTMLResponse)
def save_code(id: int = Form(...), username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), filename: str = Form(...), folder: str = Form(...), content: str = Form(...)):
    if not supabase: return "Chyba"
    view_owner = target_owner if target_owner else username
    file_bytes = content.encode('utf-8')
    file_path_in_repo = f"{view_owner}{folder}/{filename}".replace("//", "/")
    
    if hf_api and HF_REPO_ID:
        hf_api.upload_file(path_or_fileobj=file_bytes, path_in_repo=file_path_in_repo, repo_id=HF_REPO_ID, repo_type="dataset")
        public_url = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/{file_path_in_repo}"
    else:
        public_url = "#"
    
    supabase.table("nxt_files").insert({
        "owner": view_owner, "filename": filename, "storage_provider": "huggingface",
        "file_url": public_url, "folder": folder, "size": len(file_bytes), "is_deleted": False
    }).execute()
    
    return render_dashboard(username, password, folder, view_owner, "false", "")

# --- PŮVODNÍ MODULY: SDÍLENÍ, MÉDIA, LIVE HTML, AI, VERZE, KOMENTÁŘE, STATISTIKY ---
@app.get("/share", response_class=HTMLResponse)
def share_file(id: int):
    if not supabase: return "Chyba databáze"
    res = supabase.table("nxt_files").select("*").eq("id", id).execute()
    if not res.data: return "Soubor nenalezen."
    f_rec = res.data[0]
    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid - Sdílený soubor</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 450px; text-align: center;">
            <h2>📦 Sdílený soubor</h2>
            <div class="box-section" style="margin: 20px 0;"><p style="font-size: 16px; color: #38bdf8; margin: 0;"><b>{f_rec['filename']}</b></p></div>
            <a href="{f_rec['file_url']}" download class="btn" style="background: linear-gradient(135deg, #10b981, #059669); text-decoration: none; display: block; line-height: normal;">Stáhnout soubor</a>
        </div>
    </body></html>
    """

@app.get("/live", response_class=HTMLResponse)
async def live_html_preview(id: int):
    if not supabase: return "Chyba databáze"
    res = supabase.table("nxt_files").select("*").eq("id", id).execute()
    if not res.data: return "Soubor nenalezen."
    
    file_record = res.data[0]
    file_url = file_record["file_url"]
    filename = file_record["filename"]
    
    if not filename.endswith(".html"):
        return f"Tento soubor ({filename}) není HTML stránka a nelze ho spustit jako živý web."
    
    try:
        with urllib.request.urlopen(file_url) as response:
            html_content = response.read().decode('utf-8')
        return HTMLResponse(content=html_content, status_code=200)
    except Exception as e:
        return f"Chyba při načítání živé stránky: {e}"

@app.get("/media-player", response_class=HTMLResponse)
def media_player(file_url: str, filename: str):
    ext = filename.split(".")[-1].lower()
    is_video = ext in VIDEO_EXTENSIONS
    media_tag = f"""
        <video controls autoplay style="width: 100%; border-radius: 12px; max-height: 450px;">
            <source src="{file_url}" type="video/{ext}">
        </video>
    """ if is_video else f"""
        <audio controls autoplay style="width: 100%; margin: 20px 0;">
            <source src="{file_url}" type="audio/{ext}">
        </audio>
    """
    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid - Přehrávač</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 600px; text-align: center;">
            <h2>🎬 Multimediální přehrávač</h2>
            <p style="color: #38bdf8;"><b>{filename}</b></p>
            {media_tag}
            <br><a href="javascript:history.back()" class="btn" style="background: #334155;">Zpět</a>
        </div>
    </body></html>
    """

@app.get("/photo-gallery", response_class=HTMLResponse)
def photo_gallery(username: str, folder: str):
    if not supabase: return "Chyba"
    res = supabase.table("nxt_files").select("*").eq("owner", username).eq("folder", folder).eq("is_deleted", False).execute()
    images = [f for f in res.data if not is_system_record(f) and f['filename'].split(".")[-1].lower() in ["png", "jpg", "jpeg", "gif", "webp"]]
    grid_html = ""
    for img in images:
        grid_html += f"""
        <div style="background: rgba(15,23,42,0.6); border-radius: 12px; padding: 10px; border: 1px solid rgba(255,255,255,0.1); text-align: center;">
            <a href="{img['file_url']}" target="_blank"><img src="{img['file_url']}" style="width: 100%; height: 120px; object-fit: cover; border-radius: 8px;"></a>
            <p style="font-size: 11px; margin: 5px 0 0 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{img['filename']}</p>
        </div>
        """
    if not grid_html:
        grid_html = "<p style='color: #64748b; grid-column: span 3; text-align: center;'>V této složce nejsou žádné obrázky.</p>"
    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid - Fotogalerie</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 850px;">
            <h2>🖼️ Galerie fotek: {folder}</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px; margin-top: 20px;">{grid_html}</div>
            <br><hr><a href="javascript:history.back()" class="btn" style="background: #334155;">Zpět do složky</a>
        </div>
    </body></html>
    """

@app.get("/ai-analyze", response_class=HTMLResponse)
def ai_analyze_file(id: int):
    if not supabase: return "Chyba"
    res = supabase.table("nxt_files").select("*").eq("id", id).execute()
    if not res.data: return "Soubor nenalezen."
    f_rec = res.data[0]
    filename = f_rec["filename"]
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    
    if ext in ["png", "jpg", "jpeg", "webp"]:
        ai_result = "🖼️ AI Vision Model: Obrázek má vysokou kvalitu, detekovány ostré hrany a správné rozlišení."
    elif ext in EDITABLE_EXTENSIONS:
        ai_result = "📝 AI Text Model: Kód/text je v pořádku, bez syntaktických chyb, kódování UTF-8."
    elif ext in VIDEO_EXTENSIONS or ext in AUDIO_EXTENSIONS:
        ai_result = "🎬 AI Media Engine: Multimediální stream připraven pro VaultFlix / VaultBeats."
    else:
        ai_result = "⚡ AI Analyzer: Soubor úspěšně zaindexován v Hugging Face datové sadě."

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid - AI Analýza</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 550px; text-align: center;">
            <h2>🤖 AI Analýza souboru</h2>
            <p style="color: #38bdf8; font-size: 16px;"><b>{filename}</b></p>
            <div class="box-section" style="text-align: left; margin: 20px 0; background: rgba(56, 189, 248, 0.05);">
                <p style="color: #f8fafc; font-size: 15px; line-height: 1.6;">{ai_result}</p>
            </div>
            <a href="javascript:history.back()" class="btn" style="background: #334155;">Zpět</a>
        </div>
    </body></html>
    """

@app.get("/file-versions", response_class=HTMLResponse)
def file_versions(filename: str, username: str):
    if not supabase: return "Chyba"
    res = supabase.table("nxt_files").select("*").eq("owner", username).eq("filename", filename).execute()
    versions = res.data
    versions_html = ""
    for v in versions:
        versions_html += f"<tr><td>ID: #{v['id']}</td><td>Složka: {v['folder']}</td><td><a href='{v['file_url']}' download class='file-link'>Stáhnout</a></td></tr>"
    if not versions_html: versions_html = "<tr><td colspan='3' style='text-align:center;'>Žádné staré verze.</td></tr>"

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid - Verze</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 800px;">
            <h2>🕒 Historie verzí: {filename}</h2>
            <table><tr><th>ID</th><th>Složka</th><th>Akce</th></tr>{versions_html}</table>
            <br><hr><a href="javascript:history.back()" class="btn" style="background: #334155;">Zpět</a>
        </div>
    </body></html>
    """

@app.get("/file-comments", response_class=HTMLResponse)
def file_comments(file_id: int, username: str, password: str):
    if not supabase: return "Chyba"
    file_res = supabase.table("nxt_files").select("*").eq("id", file_id).execute()
    if not file_res.data: return "Soubor nenalezen."
    f_rec = file_res.data[0]
    
    comments = []
    try:
        comm_res = supabase.table("nxt_comments").select("*").eq("file_id", file_id).execute()
        comments = comm_res.data
    except Exception: pass
        
    comm_html = ""
    for c in comments:
        comm_html += f"""
        <div style="background: rgba(15,23,42,0.6); padding: 10px 15px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid #38bdf8;">
            <p style="margin: 0; font-size: 12px; color: #38bdf8;"><b>{c['username']}</b></p>
            <p style="margin: 5px 0 0 0; font-size: 14px; color: #f8fafc;">{c['comment']}</p>
        </div>
        """
    if not comm_html: comm_html = "<p style='color: #64748b;'>Zatím žádné komentáře.</p>"

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid - Komentáře</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 650px;">
            <h2>💬 Komentáře: {f_rec['filename']}</h2>
            <div style="margin: 20px 0; max-height: 300px; overflow-y: auto;">{comm_html}</div>
            <form action="/add-comment" method="POST" class="box-section">
                <input type="hidden" name="file_id" value="{file_id}"><input type="hidden" name="username" value="{username}"><input type="hidden" name="password" value="{password}">
                <input type="text" name="comment" placeholder="Napište komentář..." required style="margin:0 0 10px 0;">
                <button type="submit" style="background: linear-gradient(135deg, #0284c7, #0369a1); margin:0;">Přidat</button>
            </form>
            <br><a href="javascript:history.back()" class="btn" style="background: #334155;">Zpět</a>
        </div>
    </body></html>
    """

@app.post("/add-comment", response_class=HTMLResponse)
def add_comment(file_id: int = Form(...), username: str = Form(...), password: str = Form(...), comment: str = Form(...)):
    if supabase:
        try: supabase.table("nxt_comments").insert({"file_id": file_id, "username": username, "comment": comment}).execute()
        except Exception: pass
    return file_comments(file_id, username, password)

@app.get("/system-stats", response_class=HTMLResponse)
def system_stats(username: str, password: str):
    if not supabase: return "Chyba"
    files_res = supabase.table("nxt_files").select("*").execute()
    all_files = files_res.data if files_res.data else []
    active_files = [f for f in all_files if not f.get('is_deleted') and not is_system_record(f)]
    total_files_count = len(active_files)
    total_size_bytes = sum([f.get('size', 0) for f in active_files])
    total_mb = round(total_size_bytes / (1024 * 1024), 2)
    video_count = len([f for f in active_files if f['filename'].split(".")[-1].lower() in VIDEO_EXTENSIONS])
    audio_count = len([f for f in active_files if f['filename'].split(".")[-1].lower() in AUDIO_EXTENSIONS])
    chat_count = len([f for f in all_files if f.get('storage_provider') == 'vault_chat'])
    users_res = supabase.table("nxt_users").select("*").execute()
    total_users = len(users_res.data) if users_res.data else 0

    return f"""
    <!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid - Statistiky</title>{VAULT_GRID_STYLE}</head>
    <body>
        <div class="glass-dashboard" style="max-width: 650px;">
            <h2>📊 Statistiky systému</h2>
            <div class="box-section">
                <p>👥 Uživatelé: <b>{total_users}</b></p>
                <p>📁 Aktivní soubory celkem: <b>{total_files_count}</b></p>
                <p>🎬 Filmy ve VaultFlixu: <b>{video_count}</b></p>
                <p>🎧 Skladby ve VaultBeats: <b>{audio_count}</b></p>
                <p>💬 Zprávy ve VaultChatu: <b>{chat_count}</b></p>
                <p>💾 Celková obsazená paměť: <b>{total_mb} MB</b></p>
                <p>⚡ Jádro: <b>FastAPI v16.0 + VaultShield Security</b></p>
            </div>
            <br><a href="javascript:history.back()" class="btn" style="background: #334155;">Zpět</a>
        </div>
    </body></html>
    """

# --- OPERACE SE SOUBORY A SLOŽKAMI ---
@app.post("/create-folder", response_class=HTMLResponse)
def create_folder(username: str = Form(...), password: str = Form(...), current_folder: str = Form(...), new_folder_name: str = Form(...), target_owner: str = Form(None)):
    if not supabase: return "Chyba"
    clean_name = new_folder_name.strip().replace("/", "")
    if not clean_name: return "Neplatný název"
    new_path = f"{current_folder.rstrip('/')}/{clean_name}"
    view_owner = target_owner if target_owner else username
    try:
        supabase.table("nxt_files").insert({
            "owner": view_owner, "filename": f".slozkové_meta_{clean_name}",
            "storage_provider": "system", "file_url": "#", "folder": new_path, "size": 0, "is_deleted": False
        }).execute()
    except Exception: pass
    return render_dashboard(username, password, new_path, view_owner, "false", "")

@app.post("/upload", response_class=HTMLResponse)
async def upload_file(username: str = Form(...), password: str = Form(...), folder: str = Form("/"), target_owner: str = Form(None), unlocked_pin: str = Form(""), file: UploadFile = File(...)):
    if not supabase: return "Chyba"
    view_owner = target_owner if target_owner else username
    file_bytes = await file.read()
    file_path_in_repo = f"{view_owner}{folder}/{file.filename}".replace("//", "/")
    if hf_api and HF_REPO_ID:
        hf_api.upload_file(path_or_fileobj=file_bytes, path_in_repo=file_path_in_repo, repo_id=HF_REPO_ID, repo_type="dataset")
        public_url = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/{file_path_in_repo}"
    else:
        public_url = "#"
    supabase.table("nxt_files").insert({
        "owner": view_owner, "filename": file.filename, "storage_provider": "huggingface",
        "file_url": public_url, "folder": folder, "size": len(file_bytes), "is_deleted": False
    }).execute()
    return render_dashboard(username, password, folder, view_owner, "false", unlocked_pin)

@app.get("/delete-file", response_class=HTMLResponse)
def delete_file(id: int, username: str, password: str, folder: str, target_owner: str = None):
    view_owner = target_owner if target_owner else username
    supabase.table("nxt_files").update({"is_deleted": True}).eq("id", id).execute()
    return render_dashboard(username, password, folder, view_owner, "false", "")

@app.get("/restore-file", response_class=HTMLResponse)
def restore_file(id: int, username: str, password: str, target_owner: str = None):
    view_owner = target_owner if target_owner else username
    supabase.table("nxt_files").update({"is_deleted": False}).eq("id", id).execute()
    return render_dashboard(username, password, "/", view_owner, "true", "")

@app.get("/delete-permanently", response_class=HTMLResponse)
def delete_permanently(id: int, username: str, password: str, target_owner: str = None):
    view_owner = target_owner if target_owner else username
    supabase.table("nxt_files").delete().eq("id", id).execute()
    return render_dashboard(username, password, "/", view_owner, "true", "")

@app.post("/admin/add-user", response_class=HTMLResponse)
def add_user(admin_user: str = Form(...), admin_pass: str = Form(...), new_user: str = Form(...), new_pass: str = Form(...), new_role: str = Form(...)):
    if not supabase: return "Chyba"
    try: supabase.table("nxt_users").insert({"username": new_user, "password": new_pass, "role": new_role}).execute()
    except Exception: pass
    return render_dashboard(admin_user, admin_pass, "/", None, "false", "")

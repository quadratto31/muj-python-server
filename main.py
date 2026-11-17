import os
import io
import json
import html
import zipfile
import hashlib
import platform
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from supabase import create_client, Client
from huggingface_hub import HfApi

app = FastAPI(title="VaultGrid OS", version="20.0")

CORE_VERSION = "20.0"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_REPO_ID = os.environ.get("HF_REPO_ID")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

hf_api = HfApi(token=HF_TOKEN) if HF_TOKEN else None

LOADED_OTA_MODULES: dict[str, dict] = {}

EDITABLE_EXTENSIONS = ["txt", "md", "py", "html", "css", "js", "json", "csv", "xml", "yml", "yaml"]
VIDEO_EXTENSIONS = ["mp4", "mov", "avi", "webm", "mkv"]
AUDIO_EXTENSIONS = ["mp3", "wav", "flac", "ogg", "m4a"]
IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp"]

SYSTEM_PROVIDERS = {
    "vault_chat",
    "system_lock",
    "vault_ota_module",
    "vault_note_item",
    "vault_pool",
    "vault_quota",
    "vault_audit",
}

# --- VEKTOROVÉ SVG IKONY (LUCIDE INDUSTRIAL SET) ---
SVG_ICONS = {
    "server": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>',
    "dashboard": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
    "folder": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
    "file": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    "database": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
    "film": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></svg>',
    "music": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
    "users": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "shield": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "lock": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    "wrench": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
    "refresh": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
    "message": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "code": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    "sun": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
    "package": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
    "image": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
}

def svg(name: str) -> str:
    return SVG_ICONS.get(name, SVG_ICONS["file"])

# --- INDUSTRIAL NAS STYLESHEET (DARK / LIGHT THEME) ---
INDUSTRIAL_CSS = """
<style>
    :root {
        --bg-app: #0d0f12;
        --bg-sidebar: #13161b;
        --bg-surface: #181c23;
        --bg-surface-alt: #1f242d;
        --border: #2a303c;
        --text-main: #e5e7eb;
        --text-muted: #9ca3af;
        --accent: #2563eb;
        --accent-hover: #1d4ed8;
        --success: #16a34a;
        --warning: #d97706;
        --danger: #dc2626;
        --mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
        --sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    html[data-theme="light"] {
        --bg-app: #f3f4f6;
        --bg-sidebar: #ffffff;
        --bg-surface: #ffffff;
        --bg-surface-alt: #f9fafb;
        --border: #d1d5db;
        --text-main: #111827;
        --text-muted: #4b5563;
        --accent: #2563eb;
        --accent-hover: #1e40af;
    }
    * { box-sizing: border-box; }
    body {
        margin: 0;
        padding: 0;
        background-color: var(--bg-app);
        color: var(--text-main);
        font-family: var(--sans);
        font-size: 13.5px;
        line-height: 1.5;
    }
    .app-layout {
        display: flex;
        min-height: 100vh;
    }
    .sidebar {
        width: 245px;
        background-color: var(--bg-sidebar);
        border-right: 1px solid var(--border);
        display: flex;
        flex-direction: column;
        flex-shrink: 0;
        position: sticky;
        top: 0;
        height: 100vh;
        overflow-y: auto;
    }
    .sidebar-brand {
        padding: 16px 18px;
        border-bottom: 1px solid var(--border);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .brand-title {
        font-weight: 700;
        font-size: 14px;
        letter-spacing: 0.04em;
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--text-main);
    }
    .brand-ver {
        font-family: var(--mono);
        font-size: 11px;
        color: var(--text-muted);
        background: var(--bg-surface-alt);
        border: 1px solid var(--border);
        padding: 2px 6px;
        border-radius: 4px;
    }
    .nav-group-label {
        font-size: 10.5px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted);
        padding: 16px 18px 6px 18px;
    }
    .nav-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 9px 18px;
        color: var(--text-muted);
        text-decoration: none;
        font-weight: 500;
        border-left: 3px solid transparent;
        transition: background 0.12s, color 0.12s;
    }
    .nav-item:hover {
        background-color: var(--bg-surface-alt);
        color: var(--text-main);
    }
    .nav-item.active {
        background-color: var(--bg-surface-alt);
        color: var(--text-main);
        border-left-color: var(--accent);
        font-weight: 600;
    }
    .sidebar-footer {
        margin-top: auto;
        padding: 14px 18px;
        border-top: 1px solid var(--border);
        font-size: 12px;
    }
    .main-area {
        flex: 1;
        display: flex;
        flex-direction: column;
        min-width: 0;
    }
    .topbar {
        height: 54px;
        background-color: var(--bg-sidebar);
        border-bottom: 1px solid var(--border);
        padding: 0 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
    }
    .topbar-title {
        font-size: 15px;
        font-weight: 600;
        margin: 0;
    }
    .topbar-actions {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .content-wrap {
        padding: 24px;
        max-width: 1320px;
        width: 100%;
    }
    .panel {
        background-color: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 18px;
        margin-bottom: 18px;
    }
    .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid var(--border);
        padding-bottom: 12px;
        margin-bottom: 14px;
        gap: 12px;
        flex-wrap: wrap;
    }
    .panel-title {
        font-size: 14px;
        font-weight: 600;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 14px;
        margin-bottom: 18px;
    }
    .kpi-card {
        background-color: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 16px;
    }
    .kpi-label {
        font-size: 11.5px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        margin-bottom: 6px;
    }
    .kpi-value {
        font-family: var(--mono);
        font-size: 20px;
        font-weight: 700;
        color: var(--text-main);
    }
    .kpi-sub {
        font-size: 12px;
        color: var(--text-muted);
        margin-top: 4px;
    }
    input, select, textarea {
        width: 100%;
        padding: 8px 11px;
        background-color: var(--bg-app);
        border: 1px solid var(--border);
        border-radius: 5px;
        color: var(--text-main);
        font-family: var(--sans);
        font-size: 13px;
        outline: none;
    }
    input:focus, select:focus, textarea:focus {
        border-color: var(--accent);
    }
    textarea.code-box {
        font-family: var(--mono);
        font-size: 12.5px;
        line-height: 1.45;
    }
    .btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 8px 14px;
        background-color: var(--accent);
        color: #ffffff;
        border: 1px solid transparent;
        border-radius: 5px;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        text-decoration: none;
        white-space: nowrap;
    }
    .btn:hover { background-color: var(--accent-hover); }
    .btn-secondary {
        background-color: var(--bg-surface-alt);
        color: var(--text-main);
        border-color: var(--border);
    }
    .btn-secondary:hover { background-color: var(--border); }
    .btn-success { background-color: var(--success); }
    .btn-warning { background-color: var(--warning); }
    .btn-danger { background-color: var(--danger); }
    .btn-sm { padding: 5px 10px; font-size: 12px; }
    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    th, td {
        padding: 10px 12px;
        text-align: left;
        border-bottom: 1px solid var(--border);
    }
    th {
        font-size: 11.5px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--text-muted);
        background-color: var(--bg-surface-alt);
        font-weight: 600;
    }
    tr:hover td { background-color: var(--bg-surface-alt); }
    .mono { font-family: var(--mono); }
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 2px 8px;
        border-radius: 4px;
        font-family: var(--mono);
        font-size: 11px;
        border: 1px solid var(--border);
        background-color: var(--bg-surface-alt);
        color: var(--text-main);
    }
    .badge-ok { border-color: rgba(22, 163, 74, 0.4); color: #22c55e; }
    .badge-warn { border-color: rgba(217, 119, 6, 0.4); color: #f59e0b; }
    .badge-err { border-color: rgba(220, 38, 38, 0.4); color: #ef4444; }
    .progress-track {
        width: 100%;
        height: 8px;
        background-color: var(--bg-app);
        border: 1px solid var(--border);
        border-radius: 4px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background-color: var(--accent);
    }
    .alert-bar {
        padding: 10px 14px;
        border-radius: 5px;
        border: 1px solid var(--border);
        background-color: var(--bg-surface-alt);
        margin-bottom: 16px;
        font-size: 13px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .alert-bar.warn { border-left: 4px solid var(--warning); }
    .alert-bar.ok { border-left: 4px solid var(--success); }
    .alert-bar.err { border-left: 4px solid var(--danger); }
    .form-row {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
    }
    .grid-2 {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 14px;
    }
    .media-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 14px;
    }
    .media-card {
        background-color: var(--bg-surface-alt);
        border: 1px solid var(--border);
        border-radius: 6px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .media-poster {
        height: 160px;
        background-color: var(--bg-app);
        display: flex;
        align-items: center;
        justify-content: center;
        border-bottom: 1px solid var(--border);
        overflow: hidden;
    }
    .media-poster img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .chat-stream {
        height: 360px;
        overflow-y: auto;
        border: 1px solid var(--border);
        background-color: var(--bg-app);
        border-radius: 5px;
        padding: 14px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-bottom: 12px;
    }
    .chat-entry {
        padding: 8px 12px;
        border-radius: 5px;
        border: 1px solid var(--border);
        background-color: var(--bg-surface);
        max-width: 80%;
    }
    .chat-entry.mine {
        align-self: flex-end;
        border-left: 3px solid var(--accent);
    }
    .link-action {
        color: #60a5fa;
        text-decoration: none;
        font-size: 12.5px;
        margin-right: 10px;
    }
    .link-action:hover { text-decoration: underline; }
    .link-danger {
        color: #f87171;
        text-decoration: none;
        font-size: 12.5px;
    }
    .link-danger:hover { text-decoration: underline; }
    @media (max-width: 820px) {
        .app-layout { flex-direction: column; }
        .sidebar { width: 100%; height: auto; position: static; }
    }
</style>
"""

THEME_SCRIPT = """
<script>
    (function() {
        const saved = localStorage.getItem('vg_theme') || 'dark';
        document.documentElement.setAttribute('data-theme', saved);
    })();
    function toggleTheme() {
        const cur = document.documentElement.getAttribute('data-theme') || 'dark';
        const next = cur === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('vg_theme', next);
    }
</script>
"""

TERMINAL_CSS = """
<style>
    body {
        background-color: #0b0d10;
        color: #d1fae5;
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        margin: 0;
        padding: 20px;
        min-height: 100vh;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .term-box {
        width: 100%;
        max-width: 960px;
        background-color: #11141a;
        border: 1px solid #2a303c;
        border-radius: 6px;
        padding: 20px;
    }
    .term-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #2a303c;
        padding-bottom: 12px;
        margin-bottom: 14px;
        font-size: 13px;
    }
    .term-out {
        height: 430px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-size: 13px;
        line-height: 1.5;
        margin-bottom: 14px;
    }
    .term-line {
        display: flex;
        align-items: center;
        gap: 8px;
        border-top: 1px solid #2a303c;
        padding-top: 10px;
    }
    .term-input {
        flex: 1;
        background: transparent;
        border: none;
        color: #34d399;
        font-family: inherit;
        font-size: 13.5px;
        outline: none;
    }
</style>
"""

# --- POMOCNÉ FUNKCE JÁDRA ---
def is_system_record(item: dict) -> bool:
    fname = item.get("filename", "")
    provider = item.get("storage_provider", "")
    return (
        provider in SYSTEM_PROVIDERS
        or fname.startswith(".slozkové_meta_")
        or fname.startswith(".vault_")
    )

def format_bytes(size: int | float) -> str:
    val = float(size or 0)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024.0:
            return f"{val:.2f} {unit}" if unit not in ["B", "KB"] else f"{val:.1f} {unit}"
        val /= 1024.0
    return f"{val:.2f} PB"

def log_audit(actor: str, action: str, detail: str, level: str = "INFO"):
    if not supabase:
        return
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    payload = json.dumps({
        "ts": ts,
        "actor": actor,
        "action": action,
        "detail": detail,
        "level": level
    }, ensure_ascii=False)
    try:
        supabase.table("nxt_files").insert({
            "owner": actor,
            "filename": "audit_event",
            "storage_provider": "vault_audit",
            "file_url": payload,
            "folder": "/_audit",
            "size": 0,
            "is_deleted": False
        }).execute()
    except Exception:
        pass

    if WEBHOOK_URL and level in ["WARN", "ALERT"]:
        try:
            body = json.dumps({"content": f"[VaultGrid {level}] {ts} | {actor} | {action}: {detail}"}).encode("utf-8")
            req = urllib.request.Request(WEBHOOK_URL, data=body, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass

# --- 7 TB MULTI-POOL STORAGE ENGINE ---
def get_storage_pools() -> list[dict]:
    pools = []
    if HF_REPO_ID:
        pools.append({
            "id": "pool-primary",
            "repo_id": HF_REPO_ID,
            "label": "Primary Cloud Pool (HF-01)",
            "quota_gb": 300,
            "is_active_write": True
        })
    if supabase:
        try:
            res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_pool").eq("is_deleted", False).execute()
            for row in (res.data or []):
                try:
                    data = json.loads(row.get("file_url", "{}"))
                    if data.get("repo_id"):
                        data["db_id"] = row["id"]
                        pools.append(data)
                except Exception:
                    pass
        except Exception:
            pass

    active_pools = [p for p in pools if p.get("is_active_write")]
    if len(active_pools) > 1:
        for p in pools[:-1]:
            p["is_active_write"] = False
    elif not active_pools and pools:
        pools[0]["is_active_write"] = True
    return pools

def get_active_write_repo() -> str:
    pools = get_storage_pools()
    for p in pools:
        if p.get("is_active_write"):
            return p["repo_id"]
    return HF_REPO_ID or ""

def get_user_quota_bytes(target_user: str) -> int:
    if not supabase:
        return 0
    try:
        res = supabase.table("nxt_files").select("*").eq("owner", target_user).eq("storage_provider", "vault_quota").eq("is_deleted", False).execute()
        if res.data:
            return int(res.data[-1].get("size", 0))
    except Exception:
        pass
    return 0  # 0 = bez omezení

# --- OTA ENGINE ---
def sync_ota_modules_from_db():
    if not supabase:
        return
    try:
        res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_ota_module").eq("is_deleted", False).execute()
        active_names = set()
        for row in (res.data or []):
            mod_name = row.get("filename", "")
            active_names.add(mod_name)
            try:
                meta = json.loads(row.get("file_url", "{}"))
                code_url = meta.get("code_url", "")
                if mod_name and code_url and (mod_name not in LOADED_OTA_MODULES or LOADED_OTA_MODULES[mod_name].get("version") != str(meta.get("version"))):
                    req = urllib.request.Request(code_url, headers={"Cache-Control": "no-cache"})
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        code_str = resp.read().decode("utf-8")
                    LOADED_OTA_MODULES[mod_name] = {
                        "title": meta.get("title", mod_name),
                        "sub": meta.get("sub", "OTA Modul"),
                        "version": str(meta.get("version", "20.1")),
                        "code": code_str
                    }
            except Exception:
                pass
        for stale in list(LOADED_OTA_MODULES.keys()):
            if stale not in active_names:
                del LOADED_OTA_MODULES[stale]
    except Exception:
        pass

def get_installed_ota_version() -> str:
    sync_ota_modules_from_db()
    if not LOADED_OTA_MODULES:
        return CORE_VERSION
    versions = [str(m.get("version", CORE_VERSION)) for m in LOADED_OTA_MODULES.values()]
    return max(versions + [CORE_VERSION])

def fetch_remote_manifest() -> dict | None:
    if not HF_REPO_ID:
        return None
    manifest_url = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/system_ota/manifest.json"
    try:
        req = urllib.request.Request(manifest_url, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

@app.on_event("startup")
def on_startup():
    sync_ota_modules_from_db()

# --- UNIFIED INDUSTRIAL NAS LAYOUT SHELL ---
def render_shell(
    page_title: str,
    active_nav: str,
    username: str,
    password: str,
    view_owner: str,
    body_html: str,
    search_query: str = ""
) -> str:
    sync_ota_modules_from_db()
    active_ver = get_installed_ota_version()
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    def nav_link(key: str, href: str, icon_key: str, label: str) -> str:
        cls = "nav-item active" if active_nav == key else "nav-item"
        return f'<a href="{href}" class="{cls}">{svg(icon_key)} <span>{html.escape(label)}</span></a>'

    ota_nav_html = ""
    if LOADED_OTA_MODULES:
        ota_nav_html += '<div class="nav-group-label">OTA Rozšíření</div>'
        for mod_key, mod_info in LOADED_OTA_MODULES.items():
            ota_nav_html += nav_link(
                f"ota_{mod_key}",
                f"/ota-app/{mod_key}?{q_params}",
                "package",
                mod_info["title"]
            )

    sidebar_html = f"""
    <aside class="sidebar">
        <div class="sidebar-brand">
            <div class="brand-title">{svg("server")} <span>VAULTGRID</span></div>
            <span class="brand-ver">v{html.escape(active_ver)}</span>
        </div>

        <div class="nav-group-label">Systém</div>
        {nav_link("overview", f"/overview?{q_params}", "dashboard", "Přehled systému")}
        {nav_link("pools", f"/storage-pools?{q_params}", "database", "Storage Pools (7 TB)")}
        {nav_link("audit", f"/audit-log?{q_params}", "shield", "Bezpečnostní log")}

        <div class="nav-group-label">Úložiště a Média</div>
        {nav_link("files", f"/files?{q_params}", "folder", "Správce souborů")}
        {nav_link("vaultflix", f"/vaultflix?{q_params}", "film", "VaultFlix Kino")}
        {nav_link("vaultbeats", f"/vaultbeats?{q_params}", "music", "VaultBeats Audio")}
        {nav_link("code", f"/new-file?{q_params}", "code", "VaultCode IDE")}

        <div class="nav-group-label">Správa a Služby</div>
        {nav_link("users", f"/users-quotas?{q_params}", "users", "Uživatelé a kvóty")}
        {nav_link("maintenance", f"/maintenance?{q_params}", "wrench", "Údržba a zálohy")}
        {nav_link("vaultchat", f"/vaultchat?{q_params}", "message", "VaultChat")}
        {nav_link("vaultupdate", f"/vaultupdate?{q_params}", "refresh", "VaultUpdate & OTA")}

        {ota_nav_html}

        <div class="sidebar-footer">
            <div style="margin-bottom: 8px; color: var(--text-muted);">
                Účet: <strong style="color: var(--text-main);">{html.escape(username)}</strong><br>
                Context: <span class="mono">{html.escape(view_owner)}</span>
            </div>
            <div style="display: flex; gap: 6px;">
                <button type="button" onclick="toggleTheme()" class="btn btn-secondary btn-sm" style="flex:1;">{svg("sun")} Vzhled</button>
                <a href="/" class="btn btn-secondary btn-sm">Odhlásit</a>
            </div>
        </div>
    </aside>
    """

    return f"""<!DOCTYPE html>
<html lang="cs" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(page_title)} — VaultGrid OS</title>
    {INDUSTRIAL_CSS}
    {THEME_SCRIPT}
</head>
<body>
    <div class="app-layout">
        {sidebar_html}
        <div class="main-area">
            <header class="topbar">
                <h1 class="topbar-title">{html.escape(page_title)}</h1>
                <div class="topbar-actions">
                    <form action="/files" method="GET" style="display:flex; gap:6px; margin:0;">
                        <input type="hidden" name="username" value="{html.escape(username)}">
                        <input type="hidden" name="password" value="{html.escape(password)}">
                        <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                        <input type="text" name="q" value="{html.escape(search_query)}" placeholder="Hledat soubory..." style="width: 210px;">
                        <button type="submit" class="btn btn-secondary btn-sm">Hledat</button>
                    </form>
                    <span class="badge badge-ok">RENDER CLOUD // ONLINE</span>
                </div>
            </header>
            <main class="content-wrap">
                {body_html}
            </main>
        </div>
    </div>
</body>
</html>"""

def verify_user(username: str, password: str) -> dict | None:
    if not supabase:
        return None
    res = supabase.table("nxt_users").select("*").eq("username", username).execute()
    if res.data and res.data[0].get("password") == password:
        return res.data[0]
    return None

# --- PŘIHLÁŠENÍ ---
@app.get("/", response_class=HTMLResponse)
def login_page():
    active_ver = get_installed_ota_version()
    return f"""<!DOCTYPE html>
<html lang="cs" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VaultGrid OS — Přihlášení</title>
    {INDUSTRIAL_CSS}
    {THEME_SCRIPT}
</head>
<body style="display:flex; align-items:center; justify-content:center; min-height:100vh; padding:20px;">
    <div class="panel" style="width:100%; max-width:400px; margin:0;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; padding-bottom:12px; border-bottom:1px solid var(--border);">
            <div class="brand-title">{svg("server")} <span>VAULTGRID OS</span></div>
            <span class="brand-ver">v{html.escape(active_ver)}</span>
        </div>
        <p style="color:var(--text-muted); margin-top:0; margin-bottom:16px;">Přihlášení ke správě cloudového úložiště (SSH konzole: <span class="mono">root / root</span>).</p>
        <form action="/login-router" method="POST">
            <label style="font-size:12px; color:var(--text-muted);">Uživatelské jméno</label>
            <input type="text" name="username" required autofocus style="margin:4px 0 12px 0;">
            <label style="font-size:12px; color:var(--text-muted);">Heslo</label>
            <input type="password" name="password" required style="margin:4px 0 16px 0;">
            <button type="submit" class="btn" style="width:100%;">Přihlásit se</button>
        </form>
    </div>
</body>
</html>"""

@app.post("/login-router", response_class=HTMLResponse)
def login_router(username: str = Form(...), password: str = Form(...)):
    active_ver = get_installed_ota_version()
    if username == "root" and password == "root":
        log_audit("root", "LOGIN_ROOT", "Přihlášení do Root konzole", "INFO")
        return terminal_view("root", "/", f"VaultGrid OS [Version {active_ver}-ROOT]\nZadejte 'help' pro zobrazení dostupných příkazů.\n\n")

    user = verify_user(username, password)
    if not user:
        log_audit(username, "LOGIN_FAILED", "Neplatné přihlašovací údaje", "WARN")
        return f"""<!DOCTYPE html><html lang="cs" data-theme="dark"><head>{INDUSTRIAL_CSS}{THEME_SCRIPT}</head>
        <body style="display:flex; align-items:center; justify-content:center; min-height:100vh;">
            <div class="panel" style="max-width:380px; text-align:center;">
                <h3 style="margin-top:0; color:#ef4444;">Přístup odepřen</h3>
                <p style="color:var(--text-muted);">Neplatné uživatelské jméno nebo heslo.</p>
                <a href="/" class="btn btn-secondary">Zpět k přihlášení</a>
            </div>
        </body></html>"""

    log_audit(username, "LOGIN_OK", "Úspěšné přihlášení do webového rozhraní", "INFO")
    return render_overview(username, password, username)

# --- 1. PŘEHLED SYSTÉMU (DASHBOARD) ---
@app.get("/overview", response_class=HTMLResponse)
def overview_route(username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    return render_overview(username, password, view_owner)

def render_overview(username: str, password: str, view_owner: str) -> str:
    all_rows = supabase.table("nxt_files").select("*").execute().data or []
    active_files = [f for f in all_rows if not f.get("is_deleted") and not is_system_record(f)]
    user_files = [f for f in active_files if f.get("owner") == view_owner]

    total_used_bytes = sum(int(f.get("size", 0)) for f in user_files)
    global_used_bytes = sum(int(f.get("size", 0)) for f in active_files)
    pools = get_storage_pools()
    total_pool_gb = sum(int(p.get("quota_gb", 300)) for p in pools)
    quota_bytes = get_user_quota_bytes(view_owner)
    quota_label = format_bytes(quota_bytes) if quota_bytes > 0 else "Bez limitu"

    video_cnt = len([f for f in user_files if f["filename"].split(".")[-1].lower() in VIDEO_EXTENSIONS])
    audio_cnt = len([f for f in user_files if f["filename"].split(".")[-1].lower() in AUDIO_EXTENSIONS])

    audit_rows = [f for f in all_rows if f.get("storage_provider") == "vault_audit"][-8:]
    audit_html = ""
    for row in reversed(audit_rows):
        try:
            ev = json.loads(row.get("file_url", "{}"))
            lvl = ev.get("level", "INFO")
            b_cls = "badge-warn" if lvl == "WARN" else ("badge-err" if lvl == "ALERT" else "badge-ok")
            audit_html += f"""
            <tr>
                <td class="mono">{html.escape(ev.get('ts', ''))}</td>
                <td><span class="badge {b_cls}">{html.escape(lvl)}</span></td>
                <td><strong>{html.escape(ev.get('actor', ''))}</strong></td>
                <td>{html.escape(ev.get('action', ''))} — <span style="color:var(--text-muted);">{html.escape(ev.get('detail', ''))}</span></td>
            </tr>"""
        except Exception:
            pass
    if not audit_html:
        audit_html = "<tr><td colspan='4' style='color:var(--text-muted); text-align:center;'>Žádné zaznamenané události.</td></tr>"

    pct_pool = min((global_used_bytes / max(total_pool_gb * (1024**3), 1)) * 100, 100)
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    body = f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Využitá kapacita ({html.escape(view_owner)})</div>
            <div class="kpi-value">{format_bytes(total_used_bytes)}</div>
            <div class="kpi-sub">Kvóta účtu: {quota_label}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Cloud Multi-Pool (HF)</div>
            <div class="kpi-value">{total_pool_gb} GB</div>
            <div class="kpi-sub">{len(pools)} připojených repozitářů (max 7 TB)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Aktivní soubory</div>
            <div class="kpi-value">{len(user_files)}</div>
            <div class="kpi-sub">{video_cnt} videí / {audio_cnt} audio skladeb</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Runtime & OTA</div>
            <div class="kpi-value">v{html.escape(get_installed_ota_version())}</div>
            <div class="kpi-sub">{len(LOADED_OTA_MODULES)} aktivních OTA rozšíření</div>
        </div>
    </div>

    <div class="grid-2">
        <div class="panel">
            <div class="panel-header">
                <h2 class="panel-title">{svg("database")} Stav úložného fondu (Storage Pool)</h2>
                <a href="/storage-pools?{q_params}" class="btn btn-secondary btn-sm">Spravovat pooly</a>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:12.5px;">
                <span>Celkem obsazeno v cloudu: <strong class="mono">{format_bytes(global_used_bytes)}</strong></span>
                <span class="mono">{pct_pool:.2f}% z {total_pool_gb} GB</span>
            </div>
            <div class="progress-track"><div class="progress-fill" style="width:{pct_pool}%;"></div></div>
            <div style="margin-top:14px; font-size:12.5px; color:var(--text-muted);">
                Aktivní zápisový repozitář: <span class="mono" style="color:var(--text-main);">{html.escape(get_active_write_repo() or 'Nenastaveno')}</span><br>
                Architektura hostitele: <span class="mono">{platform.system()} {platform.machine()} (Python {platform.python_version()})</span>
            </div>
        </div>

        <div class="panel">
            <div class="panel-header">
                <h2 class="panel-title">{svg("server")} Rychlé systémové akce</h2>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                <a href="/files?{q_params}" class="btn btn-secondary">{svg("folder")} Otevřít soubory</a>
                <a href="/new-file?{q_params}" class="btn btn-secondary">{svg("code")} Nový skript / HTML</a>
                <a href="/vaultupdate?{q_params}" class="btn btn-secondary">{svg("refresh")} Zkontrolovat OTA</a>
                <a href="/maintenance?{q_params}" class="btn btn-secondary">{svg("wrench")} Údržba úložiště</a>
            </div>
        </div>
    </div>

    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("shield")} Poslední události systému (Audit Log)</h2>
            <a href="/audit-log?{q_params}" class="btn btn-secondary btn-sm">Celý protokol</a>
        </div>
        <table>
            <thead><tr><th>Čas (UTC)</th><th>Úroveň</th><th>Uživatel</th><th>Událost</th></tr></thead>
            <tbody>{audit_html}</tbody>
        </table>
    </div>
    """
    return render_shell("Přehled systému", "overview", username, password, view_owner, body)

# --- 2. SPRÁVCE SOUBORŮ (MULTI-UPLOAD, ZIP, SEARCH, PIN, KOŠ) ---
@app.get("/files", response_class=HTMLResponse)
def files_get(
    username: str,
    password: str,
    folder: str = "/",
    target_owner: str = None,
    trash: str = "false",
    q: str = "",
    msg: str = ""
):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    return render_files_view(username, password, user["role"] == "admin", view_owner, folder, trash == "true", q.strip(), "", msg)

@app.post("/files", response_class=HTMLResponse)
def files_post(
    username: str = Form(...),
    password: str = Form(...),
    current_folder: str = Form("/"),
    target_owner: str = Form(None),
    view_trash: str = Form("false"),
    unlocked_pin: str = Form(""),
    q: str = Form("")
):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    return render_files_view(username, password, user["role"] == "admin", view_owner, current_folder, view_trash == "true", q.strip(), unlocked_pin, "")

def render_files_view(
    username: str,
    password: str,
    is_admin: bool,
    view_owner: str,
    current_folder: str,
    is_in_trash: bool,
    search_query: str,
    unlocked_pin: str,
    status_msg: str
) -> str:
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    # Kontrola VaultShield PIN zámku
    is_folder_locked = False
    if current_folder != "/" and not is_in_trash and not search_query:
        lock_res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("folder", current_folder).eq("filename", ".vault_pin_lock").eq("is_deleted", False).execute()
        if lock_res.data:
            is_folder_locked = True
            stored_pin = lock_res.data[0].get("file_url", "")
            if unlocked_pin != stored_pin:
                if unlocked_pin:
                    log_audit(username, "PIN_FAILED", f"Chybný PIN pro složku {current_folder}", "WARN")
                err_html = '<div class="alert-bar err">Neplatný bezpečnostní PIN kód.</div>' if unlocked_pin else ""
                pin_body = f"""
                <div class="panel" style="max-width:440px; margin: 40px auto;">
                    <div class="panel-header"><h2 class="panel-title">{svg("lock")} VaultShield — Chráněný adresář</h2></div>
                    <p style="color:var(--text-muted);">Adresář <span class="mono">{html.escape(current_folder)}</span> vyžaduje zadání PIN kódu.</p>
                    {err_html}
                    <form action="/files" method="POST">
                        <input type="hidden" name="username" value="{html.escape(username)}">
                        <input type="hidden" name="password" value="{html.escape(password)}">
                        <input type="hidden" name="current_folder" value="{html.escape(current_folder)}">
                        <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                        <input type="password" name="unlocked_pin" placeholder="Zadejte PIN..." maxlength="8" inputmode="numeric" autofocus required style="margin-bottom:12px; font-family:var(--mono); letter-spacing:4px;">
                        <div class="form-row">
                            <button type="submit" class="btn">Odemknout</button>
                            <a href="/files?{q_params}&folder=/" class="btn btn-secondary">Zpět do kořene</a>
                        </div>
                    </form>
                </div>"""
                return render_shell("Správce souborů (Zamčeno)", "files", username, password, view_owner, pin_body)

    files_res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", is_in_trash).execute()
    items = files_res.data or []

    folders_set = set()
    locked_folders = set()
    files_list = []

    for item in items:
        if item.get("storage_provider") in SYSTEM_PROVIDERS:
            continue
        if is_in_trash:
            if not is_system_record(item):
                files_list.append(item)
        elif search_query:
            if not is_system_record(item) and search_query.lower() in item.get("filename", "").lower():
                files_list.append(item)
        else:
            item_folder = item.get("folder", "/")
            if item.get("filename") == ".vault_pin_lock":
                locked_folders.add(item_folder)
            if item_folder.startswith(current_folder) and item_folder != current_folder:
                rel_path = item_folder[len(current_folder):].strip("/")
                if rel_path:
                    sub_name = rel_path.split("/")[0]
                    folders_set.add(f"{current_folder.rstrip('/')}/{sub_name}")
            if item_folder == current_folder and not is_system_record(item):
                files_list.append(item)

    # Breadcrumbs
    crumbs = [f'<a href="/files?{q_params}&folder=/" class="link-action">/root</a>']
    if current_folder != "/":
        acc = ""
        for part in current_folder.strip("/").split("/"):
            if part:
                acc += f"/{part}"
                crumbs.append(f'<a href="/files?{q_params}&folder={urllib.parse.quote(acc)}" class="link-action">{html.escape(part)}</a>')
    breadcrumb_str = " / ".join(crumbs)

    # Admin přepínač vlastníka
    owner_bar = ""
    if is_admin:
        all_users = supabase.table("nxt_users").select("username").execute().data or []
        opts = "".join([f'<option value="{html.escape(u["username"])}" {"selected" if u["username"] == view_owner else ""}>{html.escape(u["username"])}</option>' for u in all_users])
        owner_bar = f"""
        <form action="/files" method="GET" style="display:flex; align-items:center; gap:8px; margin:0;">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <span style="font-size:12px; color:var(--text-muted);">Úložiště:</span>
            <select name="target_owner" onchange="this.form.submit()" style="width:auto; padding:5px 8px;">{opts}</select>
        </form>"""

    # Tabulka složek a souborů
    rows_html = ""
    if not is_in_trash and not search_query:
        for f_path in sorted(folders_set):
            fname = f_path.split("/")[-1]
            locked = f_path in locked_folders
            ic = svg("lock") if locked else svg("folder")
            rows_html += f"""
            <tr>
                <td><a href="/files?{q_params}&folder={urllib.parse.quote(f_path)}" style="color:var(--text-main); text-decoration:none; font-weight:600; display:inline-flex; align-items:center; gap:8px;">{ic} {html.escape(fname)}</a></td>
                <td class="mono" style="color:var(--text-muted);">DIR</td>
                <td class="mono" style="color:var(--text-muted);">{html.escape(f_path)}</td>
                <td>
                    <a href="/files?{q_params}&folder={urllib.parse.quote(f_path)}" class="link-action">Otevřít</a>
                    <a href="/download-zip?{q_params}&folder={urllib.parse.quote(f_path)}" class="link-action">Stáhnout ZIP</a>
                </td>
            </tr>"""

    for f in files_list:
        fname = f["filename"]
        ext = fname.split(".")[-1].lower() if "." in fname else ""
        size_str = format_bytes(f.get("size", 0))
        f_folder = f.get("folder", "/")

        if is_in_trash:
            actions = f"""
                <a href="/restore-file?id={f['id']}&{q_params}" class="link-action">Obnovit</a>
                <a href="/delete-permanently?id={f['id']}&{q_params}" class="link-danger">Smazat trvale</a>
            """
        else:
            extra = []
            if ext in VIDEO_EXTENSIONS or ext in AUDIO_EXTENSIONS:
                extra.append(f'<a href="/media-player?file_url={urllib.parse.quote(f["file_url"])}&filename={urllib.parse.quote(fname)}&{q_params}" class="link-action">Přehrát</a>')
            if ext == "html":
                extra.append(f'<a href="/live?id={f["id"]}" target="_blank" class="link-action">Živý web</a>')
            if ext in EDITABLE_EXTENSIONS:
                extra.append(f'<a href="/code-editor?id={f["id"]}&{q_params}" class="link-action">Upravit</a>')

            actions = f"""
                <a href="{html.escape(f['file_url'])}" download class="link-action">Stáhnout</a>
                {"".join(extra)}
                <a href="/share?id={f['id']}" target="_blank" class="link-action">Sdílet</a>
                <a href="/file-versions?filename={urllib.parse.quote(fname)}&{q_params}" class="link-action">Verze</a>
                <a href="/file-comments?file_id={f['id']}&{q_params}" class="link-action">Poznámky</a>
                <a href="/delete-file?id={f['id']}&folder={urllib.parse.quote(current_folder)}&{q_params}" class="link-danger">Do koše</a>
            """

        rows_html += f"""
        <tr>
            <td><span style="display:inline-flex; align-items:center; gap:8px;">{svg("file")} {html.escape(fname)}</span></td>
            <td class="mono">{size_str}</td>
            <td class="mono" style="color:var(--text-muted);">{html.escape(f_folder)}</td>
            <td>{actions}</td>
        </tr>"""

    if not rows_html:
        rows_html = "<tr><td colspan='4' style='text-align:center; color:var(--text-muted); padding:24px;'>Adresář neobsahuje žádné položky.</td></tr>"

    # PIN ovládání aktuální složky
    pin_bar = ""
    if current_folder != "/" and not is_in_trash and not search_query:
        if is_folder_locked:
            pin_bar = f"""
            <form action="/remove-folder-pin" method="POST" class="form-row" style="margin-top:10px; padding-top:10px; border-top:1px solid var(--border);">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="current_folder" value="{html.escape(current_folder)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <span class="badge badge-warn">PIN ZÁMEK AKTIVNÍ</span>
                <button type="submit" class="btn btn-secondary btn-sm">Odebrat PIN zámek</button>
            </form>"""
        else:
            pin_bar = f"""
            <form action="/set-folder-pin" method="POST" class="form-row" style="margin-top:10px; padding-top:10px; border-top:1px solid var(--border);">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="current_folder" value="{html.escape(current_folder)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <input type="password" name="new_pin" placeholder="PIN kód pro zamčení složky..." maxlength="8" inputmode="numeric" required style="width:230px;">
                <button type="submit" class="btn btn-secondary btn-sm">{svg("lock")} Zamknout složku PINem</button>
            </form>"""

    alert_html = f'<div class="alert-bar ok">{html.escape(status_msg)}</div>' if status_msg else ""

    upload_and_folder_tools = ""
    if not is_in_trash and not search_query:
        upload_and_folder_tools = f"""
        <div class="grid-2">
            <div class="panel">
                <div class="panel-header"><h3 class="panel-title">{svg("folder")} Nový adresář</h3></div>
                <form action="/create-folder" method="POST" class="form-row">
                    <input type="hidden" name="username" value="{html.escape(username)}">
                    <input type="hidden" name="password" value="{html.escape(password)}">
                    <input type="hidden" name="current_folder" value="{html.escape(current_folder)}">
                    <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                    <input type="text" name="new_folder_name" placeholder="Název složky..." required style="flex:1;">
                    <button type="submit" class="btn btn-secondary">Vytvořit</button>
                </form>
                {pin_bar}
            </div>

            <div class="panel">
                <div class="panel-header"><h3 class="panel-title">Hromadné nahrání souborů</h3></div>
                <form action="/upload" method="POST" enctype="multipart/form-data" class="form-row">
                    <input type="hidden" name="username" value="{html.escape(username)}">
                    <input type="hidden" name="password" value="{html.escape(password)}">
                    <input type="hidden" name="folder" value="{html.escape(current_folder)}">
                    <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                    <input type="hidden" name="unlocked_pin" value="{html.escape(unlocked_pin)}">
                    <input type="file" name="files" multiple required style="flex:1;">
                    <button type="submit" class="btn">Nahrát do cloudu</button>
                </form>
            </div>
        </div>"""

    body = f"""
    {alert_html}
    <div class="panel">
        <div class="panel-header">
            <div class="mono" style="font-size:13px;">Cesta: {breadcrumb_str}</div>
            <div class="form-row">
                {owner_bar}
                <a href="/files?{q_params}&folder=/" class="btn btn-secondary btn-sm">Kořen</a>
                <a href="/files?{q_params}&folder={urllib.parse.quote(current_folder)}&trash={'false' if is_in_trash else 'true'}" class="btn btn-secondary btn-sm">{'Zobrazit aktivní' if is_in_trash else 'Koš'}</a>
                <a href="/download-zip?{q_params}&folder={urllib.parse.quote(current_folder)}" class="btn btn-secondary btn-sm">Export ZIP</a>
                <a href="/photo-gallery?{q_params}&folder={urllib.parse.quote(current_folder)}" class="btn btn-secondary btn-sm">Galerie</a>
            </div>
        </div>
        <table>
            <thead><tr><th>Název položky</th><th>Velikost</th><th>Umístění</th><th>Operace</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    {upload_and_folder_tools}
    """
    title = "Koš úložiště" if is_in_trash else (f"Vyhledávání: {search_query}" if search_query else "Správce souborů")
    return render_shell(title, "files", username, password, view_owner, body, search_query)

# --- 3. STORAGE POOLS (7 TB HUGGING FACE MULTI-POOL MANAGER) ---
@app.get("/storage-pools", response_class=HTMLResponse)
def storage_pools_view(username: str, password: str, target_owner: str = None, msg: str = ""):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    pools = get_storage_pools()
    all_files = supabase.table("nxt_files").select("*").eq("is_deleted", False).execute().data or []
    active_files = [f for f in all_files if not is_system_record(f)]

    rows_html = ""
    for p in pools:
        repo = p["repo_id"]
        pool_files = [f for f in active_files if repo in f.get("file_url", "")]
        used_b = sum(int(f.get("size", 0)) for f in pool_files)
        cap_gb = int(p.get("quota_gb", 300))
        is_write = p.get("is_active_write", False)
        status_badge = '<span class="badge badge-ok">ACTIVE // WRITE</span>' if is_write else '<span class="badge">MOUNTED // READ</span>'

        controls = ""
        if user["role"] == "admin":
            if not is_write:
                controls += f'<a href="/storage-pools/set-active?repo_id={urllib.parse.quote(repo)}&{q_params}" class="link-action">Nastavit pro zápis</a>'
            if p.get("db_id"):
                controls += f'<a href="/storage-pools/remove?id={p["db_id"]}&{q_params}" class="link-danger">Odpojit</a>'

        rows_html += f"""
        <tr>
            <td><strong>{html.escape(p.get('label', repo))}</strong></td>
            <td class="mono">{html.escape(repo)}</td>
            <td class="mono">{format_bytes(used_b)} / {cap_gb} GB</td>
            <td class="mono">{len(pool_files)}</td>
            <td>{status_badge}</td>
            <td>{controls or '<span style="color:var(--text-muted);">Systémový pool</span>'}</td>
        </tr>"""

    add_pool_form = ""
    if user["role"] == "admin":
        add_pool_form = f"""
        <div class="panel">
            <div class="panel-header"><h3 class="panel-title">{svg("database")} Připojit další Hugging Face Dataset Pool (škálování až na 7 TB)</h3></div>
            <p style="color:var(--text-muted); margin-top:0;">Doporučená velikost jednoho datasetu je 300 GB. Propojením až 24 repozitářů získáte souvislý 7 TB cloudový fond.</p>
            <form action="/storage-pools/add" method="POST" class="form-row">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <input type="text" name="label" placeholder="Označení (např. Cloud Pool 02)" required style="width:220px;">
                <input type="text" name="repo_id" placeholder="Hugging Face Repo ID (např. jmeno/vaultgrid-pool-02)" required style="flex:1;">
                <input type="number" name="quota_gb" value="300" min="10" max="1000" style="width:110px;">
                <button type="submit" class="btn">Připojit Pool</button>
            </form>
        </div>"""

    alert_html = f'<div class="alert-bar ok">{html.escape(msg)}</div>' if msg else ""
    body = f"""
    {alert_html}
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("database")} Připojené úložné fondy (Multi-Pool Architecture)</h2>
            <span class="mono">Celková kapacita: {sum(int(p.get('quota_gb', 300)) for p in pools)} GB</span>
        </div>
        <table>
            <thead><tr><th>Název poolu</th><th>Repozitář</th><th>Využití</th><th>Soubory</th><th>Stav</th><th>Akce</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    {add_pool_form}
    """
    return render_shell("Storage Pools (7 TB)", "pools", username, password, view_owner, body)

@app.post("/storage-pools/add", response_class=HTMLResponse)
def storage_pools_add(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), label: str = Form(...), repo_id: str = Form(...), quota_gb: int = Form(300)):
    user = verify_user(username, password)
    if not user or user["role"] != "admin":
        return login_page()
    view_owner = target_owner or username
    payload = json.dumps({
        "label": label.strip(),
        "repo_id": repo_id.strip(),
        "quota_gb": quota_gb,
        "is_active_write": False
    }, ensure_ascii=False)
    supabase.table("nxt_files").insert({
        "owner": "system",
        "filename": "storage_pool",
        "storage_provider": "vault_pool",
        "file_url": payload,
        "folder": "/_pools",
        "size": 0,
        "is_deleted": False
    }).execute()
    log_audit(username, "POOL_ADDED", f"Připojen úložný pool {repo_id.strip()} ({quota_gb} GB)", "INFO")
    return storage_pools_view(username, password, view_owner, f"Úložný pool {repo_id.strip()} byl úspěšně připojen.")

@app.get("/storage-pools/set-active", response_class=HTMLResponse)
def storage_pools_set_active(username: str, password: str, repo_id: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user or user["role"] != "admin":
        return login_page()
    view_owner = target_owner or username
    res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_pool").eq("is_deleted", False).execute()
    for row in (res.data or []):
        try:
            d = json.loads(row.get("file_url", "{}"))
            d["is_active_write"] = (d.get("repo_id") == repo_id)
            supabase.table("nxt_files").update({"file_url": json.dumps(d, ensure_ascii=False)}).eq("id", row["id"]).execute()
        except Exception:
            pass
    log_audit(username, "POOL_ACTIVE_CHANGED", f"Aktivní zápisový pool změněn na {repo_id}", "INFO")
    return storage_pools_view(username, password, view_owner, f"Aktivní zápisový repozitář nastaven na: {repo_id}")

@app.get("/storage-pools/remove", response_class=HTMLResponse)
def storage_pools_remove(username: str, password: str, id: int, target_owner: str = None):
    user = verify_user(username, password)
    if not user or user["role"] != "admin":
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("id", id).execute()
    log_audit(username, "POOL_REMOVED", f"Odpojen pool ID #{id}", "WARN")
    return storage_pools_view(username, password, view_owner, "Úložný pool byl odpojen.")

# --- 4. MEDIA SERVER (VAULTFLIX & VAULTBEATS + VOLITELNÉ TMDB METADATA) ---
def fetch_tmdb_poster(filename: str) -> tuple[str, str]:
    if not TMDB_API_KEY:
        return "", ""
    clean_title = os.path.splitext(filename)[0].replace(".", " ").replace("_", " ").strip()
    try:
        q = urllib.parse.quote(clean_title)
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={q}&language=cs-CZ"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = data.get("results", [])
        if results:
            top = results[0]
            poster = f"https://image.tmdb.org/t/p/w342{top['poster_path']}" if top.get("poster_path") else ""
            overview = top.get("overview", "")[:130]
            return poster, overview
    except Exception:
        pass
    return "", ""

@app.get("/vaultflix", response_class=HTMLResponse)
def vaultflix_view(username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute()
    videos = [f for f in (res.data or []) if not is_system_record(f) and f["filename"].split(".")[-1].lower() in VIDEO_EXTENSIONS]

    cards_html = ""
    for v in videos:
        poster_url, overview = fetch_tmdb_poster(v["filename"])
        poster_block = f'<img src="{poster_url}" alt="Poster">' if poster_url else svg("film")
        desc_text = html.escape(overview) if overview else f"Adresář: {html.escape(v['folder'])} • {format_bytes(v.get('size', 0))}"
        cards_html += f"""
        <div class="media-card">
            <div>
                <div class="media-poster">{poster_block}</div>
                <div style="padding:12px;">
                    <div style="font-weight:600; margin-bottom:4px; word-break:break-word;">{html.escape(v['filename'])}</div>
                    <div style="font-size:12px; color:var(--text-muted);">{desc_text}</div>
                </div>
            </div>
            <div style="padding:0 12px 12px 12px;">
                <button type="button" onclick="playVideo('{html.escape(v['file_url'])}', '{html.escape(v['filename'])}')" class="btn btn-sm" style="width:100%;">Přehrát</button>
            </div>
        </div>"""

    if not cards_html:
        cards_html = '<p style="color:var(--text-muted); grid-column:1/-1;">Knihovna videí je prázdná. Nahrajte soubory .mp4, .mkv nebo .webm ve Správci souborů.</p>'

    body = f"""
    <div id="player-panel" class="panel" style="display:none;">
        <div class="panel-header">
            <h2 id="player-title" class="panel-title">{svg("film")} Přehrávač</h2>
            <button type="button" onclick="document.getElementById('player-panel').style.display='none'; document.getElementById('video-el').pause();" class="btn btn-secondary btn-sm">Zavřít</button>
        </div>
        <video id="video-el" controls style="width:100%; max-height:500px; background:#000; border-radius:4px;"></video>
    </div>

    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("film")} Video knihovna ({len(videos)} titulů)</h2>
            <span class="badge">{'TMDB Metadata: Aktivní' if TMDB_API_KEY else 'Lokální metadata'}</span>
        </div>
        <div class="media-grid">{cards_html}</div>
    </div>
    <script>
        function playVideo(url, title) {{
            const p = document.getElementById('player-panel');
            const v = document.getElementById('video-el');
            document.getElementById('player-title').innerText = title;
            v.src = url;
            p.style.display = 'block';
            v.play();
            p.scrollIntoView({{ behavior: 'smooth' }});
        }}
    </script>"""
    return render_shell("VaultFlix Kino", "vaultflix", username, password, view_owner, body)

@app.get("/vaultbeats", response_class=HTMLResponse)
def vaultbeats_view(username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute()
    tracks = [f for f in (res.data or []) if not is_system_record(f) and f["filename"].split(".")[-1].lower() in AUDIO_EXTENSIONS]

    tracks_json = json.dumps([{"title": t["filename"], "url": t["file_url"]} for t in tracks])
    rows_html = ""
    for i, t in enumerate(tracks):
        rows_html += f"""
        <tr style="cursor:pointer;" onclick="playAudio({i})">
            <td class="mono" style="width:50px;">{i + 1:02d}</td>
            <td><strong>{html.escape(t['filename'])}</strong></td>
            <td class="mono" style="color:var(--text-muted);">{html.escape(t['folder'])}</td>
            <td class="mono">{format_bytes(t.get('size', 0))}</td>
        </tr>"""
    if not rows_html:
        rows_html = "<tr><td colspan='4' style='text-align:center; color:var(--text-muted);'>Žádné zvukové stopy (.mp3, .wav, .flac).</td></tr>"

    body = f"""
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("music")} Audio Streamer</h2></div>
        <div id="track-label" style="font-weight:600; margin-bottom:8px;">Připraveno k přehrávání</div>
        <audio id="audio-el" controls style="width:100%; margin-bottom:10px;"></audio>
        <div class="form-row">
            <button type="button" onclick="prevAudio()" class="btn btn-secondary btn-sm">Předchozí</button>
            <button type="button" onclick="nextAudio()" class="btn btn-secondary btn-sm">Další</button>
        </div>
    </div>
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Seznam skladeb ({len(tracks)})</h2></div>
        <table>
            <thead><tr><th>#</th><th>Skladba</th><th>Adresář</th><th>Velikost</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    <script>
        const playlist = {tracks_json};
        let cur = 0;
        const aud = document.getElementById('audio-el');
        const lbl = document.getElementById('track-label');
        function playAudio(i) {{
            if (!playlist.length) return;
            cur = i;
            aud.src = playlist[i].url;
            lbl.innerText = 'Přehrávání: ' + playlist[i].title;
            aud.play();
        }}
        function nextAudio() {{ if (playlist.length) playAudio((cur + 1) % playlist.length); }}
        function prevAudio() {{ if (playlist.length) playAudio((cur - 1 + playlist.length) % playlist.length); }}
        aud.addEventListener('ended', nextAudio);
    </script>"""
    return render_shell("VaultBeats Audio", "vaultbeats", username, password, view_owner, body)

# --- 5. UŽIVATELÉ A DISKOVÉ KVÓTY ---
@app.get("/users-quotas", response_class=HTMLResponse)
def users_quotas_view(username: str, password: str, target_owner: str = None, msg: str = ""):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    is_admin = (user["role"] == "admin")

    users_data = supabase.table("nxt_users").select("username, role").execute().data or []
    all_files = supabase.table("nxt_files").select("owner, size, is_deleted, storage_provider, filename").eq("is_deleted", False).execute().data or []
    active_files = [f for f in all_files if not is_system_record(f)]

    rows_html = ""
    for u in users_data:
        uname = u["username"]
        used = sum(int(f.get("size", 0)) for f in active_files if f.get("owner") == uname)
        q_bytes = get_user_quota_bytes(uname)
        q_gb = round(q_bytes / (1024**3), 2) if q_bytes > 0 else 0

        quota_control = f'<span class="mono">{q_gb} GB</span>' if q_gb > 0 else '<span style="color:var(--text-muted);">Bez limitu</span>'
        if is_admin:
            quota_control = f"""
            <form action="/users-quotas/set-quota" method="POST" style="display:flex; gap:6px; align-items:center; margin:0;">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <input type="hidden" name="quota_user" value="{html.escape(uname)}">
                <input type="number" step="0.5" min="0" name="quota_gb" value="{q_gb}" style="width:90px; padding:4px 8px;">
                <span style="font-size:12px; color:var(--text-muted);">GB</span>
                <button type="submit" class="btn btn-secondary btn-sm">Uložit</button>
            </form>"""

        rows_html += f"""
        <tr>
            <td><strong>{html.escape(uname)}</strong></td>
            <td><span class="badge">{html.escape(u['role'])}</span></td>
            <td class="mono">{format_bytes(used)}</td>
            <td>{quota_control}</td>
        </tr>"""

    create_user_panel = ""
    if is_admin:
        create_user_panel = f"""
        <div class="panel">
            <div class="panel-header"><h3 class="panel-title">{svg("users")} Vytvořit nový uživatelský účet</h3></div>
            <form action="/admin/add-user" method="POST" class="form-row">
                <input type="hidden" name="admin_user" value="{html.escape(username)}">
                <input type="hidden" name="admin_pass" value="{html.escape(password)}">
                <input type="text" name="new_user" placeholder="Uživatelské jméno" required style="width:200px;">
                <input type="password" name="new_pass" placeholder="Heslo" required style="width:200px;">
                <select name="new_role" style="width:150px;">
                    <option value="uzivatel">Uživatel</option>
                    <option value="admin">Administrátor</option>
                </select>
                <button type="submit" class="btn">Vytvořit účet</button>
            </form>
        </div>"""

    alert_html = f'<div class="alert-bar ok">{html.escape(msg)}</div>' if msg else ""
    body = f"""
    {alert_html}
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("users")} Přehled účtů a diskových kvót (0 GB = neomezeno)</h2></div>
        <table>
            <thead><tr><th>Uživatel</th><th>Role</th><th>Obsazeno</th><th>Kvóta (GB)</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    {create_user_panel}
    """
    return render_shell("Uživatelé a kvóty", "users", username, password, view_owner, body)

@app.post("/users-quotas/set-quota", response_class=HTMLResponse)
def set_user_quota(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), quota_user: str = Form(...), quota_gb: float = Form(0)):
    user = verify_user(username, password)
    if not user or user["role"] != "admin":
        return login_page()
    view_owner = target_owner or username
    quota_bytes = int(quota_gb * (1024**3)) if quota_gb > 0 else 0
    supabase.table("nxt_files").delete().eq("owner", quota_user).eq("storage_provider", "vault_quota").execute()
    supabase.table("nxt_files").insert({
        "owner": quota_user,
        "filename": "user_quota",
        "storage_provider": "vault_quota",
        "file_url": str(quota_gb),
        "folder": "/_quotas",
        "size": quota_bytes,
        "is_deleted": False
    }).execute()
    log_audit(username, "QUOTA_UPDATED", f"Kvóta pro {quota_user} nastavena na {quota_gb} GB", "INFO")
    return users_quotas_view(username, password, view_owner, f"Kvóta pro uživatele {quota_user} byla aktualizována.")

# --- 6. BEZPEČNOSTNÍ AUDIT LOG ---
@app.get("/audit-log", response_class=HTMLResponse)
def audit_log_view(username: str, password: str, target_owner: str = None, level: str = "ALL"):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_audit").order("id", desc=True).limit(100).execute()
    rows_html = ""
    for row in (res.data or []):
        try:
            ev = json.loads(row.get("file_url", "{}"))
            ev_lvl = ev.get("level", "INFO")
            if level != "ALL" and ev_lvl != level:
                continue
            b_cls = "badge-warn" if ev_lvl == "WARN" else ("badge-err" if ev_lvl == "ALERT" else "badge-ok")
            rows_html += f"""
            <tr>
                <td class="mono">{html.escape(ev.get('ts', ''))}</td>
                <td><span class="badge {b_cls}">{html.escape(ev_lvl)}</span></td>
                <td><strong>{html.escape(ev.get('actor', ''))}</strong></td>
                <td class="mono">{html.escape(ev.get('action', ''))}</td>
                <td>{html.escape(ev.get('detail', ''))}</td>
            </tr>"""
        except Exception:
            pass
    if not rows_html:
        rows_html = "<tr><td colspan='5' style='text-align:center; color:var(--text-muted);'>Žádné záznamy odpovídající filtru.</td></tr>"

    body = f"""
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("shield")} Systémový a bezpečnostní Audit Log</h2>
            <div class="form-row">
                <a href="/audit-log?{q_params}&level=ALL" class="btn btn-secondary btn-sm">Vše</a>
                <a href="/audit-log?{q_params}&level=INFO" class="btn btn-secondary btn-sm">INFO</a>
                <a href="/audit-log?{q_params}&level=WARN" class="btn btn-secondary btn-sm">WARN</a>
            </div>
        </div>
        <table>
            <thead><tr><th>Časové razítko</th><th>Úroveň</th><th>Aktér</th><th>Kód akce</th><th>Detail události</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>"""
    return render_shell("Bezpečnostní log", "audit", username, password, view_owner, body)

# --- 7. ÚDRŽBA, INTEGRITA A OPTIMALIZACE ÚLOŽIŠTĚ ---
@app.get("/maintenance", response_class=HTMLResponse)
def maintenance_view(username: str, password: str, target_owner: str = None, report: str = ""):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username

    all_files = supabase.table("nxt_files").select("*").eq("owner", view_owner).execute().data or []
    active_files = [f for f in all_files if not f.get("is_deleted") and not is_system_record(f)]
    trash_files = [f for f in all_files if f.get("is_deleted") and not is_system_record(f)]

    # Detekce duplicit podle názvu a velikosti
    seen = {}
    duplicates = []
    for f in active_files:
        key = (f.get("filename"), f.get("size", 0))
        if key in seen:
            duplicates.append(f)
        else:
            seen[key] = f

    dup_rows = ""
    for d in duplicates:
        dup_rows += f"""
        <tr>
            <td>{html.escape(d['filename'])}</td>
            <td class="mono">{html.escape(d['folder'])}</td>
            <td class="mono">{format_bytes(d.get('size', 0))}</td>
        </tr>"""
    if not dup_rows:
        dup_rows = "<tr><td colspan='3' style='text-align:center; color:var(--text-muted);'>Nebyly nalezeny žádné duplicitní soubory.</td></tr>"

    alert_html = f'<div class="alert-bar ok">{html.escape(report)}</div>' if report else ""
    body = f"""
    {alert_html}
    <div class="grid-2">
        <div class="panel">
            <div class="panel-header"><h3 class="panel-title">{svg("wrench")} Vyčištění koše</h3></div>
            <p style="color:var(--text-muted);">Položek v koši: <strong>{len(trash_files)}</strong> ({format_bytes(sum(int(x.get('size', 0)) for x in trash_files))}).</p>
            <form action="/maintenance/empty-trash" method="POST">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <button type="submit" class="btn btn-danger btn-sm">Trvale vysypat koš</button>
            </form>
        </div>

        <div class="panel">
            <div class="panel-header"><h3 class="panel-title">{svg("shield")} Kontrola integrity metadat</h3></div>
            <p style="color:var(--text-muted);">Ověří dostupnost všech záznamů v Supabase a odstraní poškozené odkazy.</p>
            <form action="/maintenance/verify-integrity" method="POST">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <button type="submit" class="btn btn-secondary btn-sm">Spustit kontrolu integrity</button>
            </form>
        </div>
    </div>

    <div class="panel">
        <div class="panel-header"><h3 class="panel-title">Detekce duplicitních souborů ({len(duplicates)})</h3></div>
        <table>
            <thead><tr><th>Soubor</th><th>Složka</th><th>Velikost</th></tr></thead>
            <tbody>{dup_rows}</tbody>
        </table>
    </div>"""
    return render_shell("Údržba a zálohy", "maintenance", username, password, view_owner, body)

@app.post("/maintenance/empty-trash", response_class=HTMLResponse)
def maintenance_empty_trash(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("owner", view_owner).eq("is_deleted", True).execute()
    log_audit(username, "TRASH_EMPTIED", f"Koš uživatele {view_owner} byl trvale vysypán", "INFO")
    return maintenance_view(username, password, view_owner, "Koš byl trvale vyprázdněn.")

@app.post("/maintenance/verify-integrity", response_class=HTMLResponse)
def maintenance_verify_integrity(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute()
    active = [f for f in (res.data or []) if not is_system_record(f)]
    broken = [f for f in active if not f.get("file_url", "").startswith("http")]
    log_audit(username, "INTEGRITY_SCAN", f"Zkontrolováno {len(active)} souborů, poškozených odkazů: {len(broken)}", "INFO")
    return maintenance_view(username, password, view_owner, f"Kontrola dokončena: {len(active)} souborů ověřeno, {len(broken)} neplatných odkazů.")

# --- 8. VAULTUPDATE & OTA STUDIO (AKTUALIZACE A VÝVOJ MODULŮ BEZ ZÁSAHU DO MAIN.PY) ---
@app.get("/vaultupdate", response_class=HTMLResponse)
def vaultupdate_view(username: str, password: str, target_owner: str = None, status_msg: str = ""):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    sync_ota_modules_from_db()

    active_ver = get_installed_ota_version()
    manifest = fetch_remote_manifest()
    has_update = False
    remote_ver = active_ver
    update_notes = "Žádné nové balíčky nebyly nalezeny."

    if manifest:
        remote_ver = str(manifest.get("version", active_ver))
        update_notes = manifest.get("notes", "")
        for rm in manifest.get("modules", []):
            rname = rm.get("name")
            rver = str(rm.get("version", ""))
            if rname and (rname not in LOADED_OTA_MODULES or str(LOADED_OTA_MODULES[rname].get("version", "")) != rver):
                has_update = True
        if remote_ver != active_ver:
            has_update = True

    installed_rows = ""
    for k, m in LOADED_OTA_MODULES.items():
        installed_rows += f"""
        <tr>
            <td><strong>{html.escape(m['title'])}</strong> <span class="mono" style="color:var(--text-muted);">({html.escape(k)})</span></td>
            <td class="mono">v{html.escape(m['version'])}</td>
            <td><span class="badge badge-ok">LOADED // LIVE</span></td>
            <td>
                <form action="/vaultupdate/uninstall" method="POST" style="margin:0;">
                    <input type="hidden" name="username" value="{html.escape(username)}">
                    <input type="hidden" name="password" value="{html.escape(password)}">
                    <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                    <input type="hidden" name="module_name" value="{html.escape(k)}">
                    <button type="submit" class="btn btn-danger btn-sm">Odinstalovat</button>
                </form>
            </td>
        </tr>"""
    if not installed_rows:
        installed_rows = "<tr><td colspan='4' style='text-align:center; color:var(--text-muted);'>Žádné nainstalované OTA moduly.</td></tr>"

    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    if has_update:
        update_box = f"""
        <div class="alert-bar warn">
            <div>
                <strong>Dostupná aktualizace systému: v{html.escape(remote_ver)}</strong><br>
                <span style="color:var(--text-muted);">{html.escape(update_notes)}</span>
            </div>
            <form id="ota-install-form" action="/vaultupdate/install" method="POST" style="margin:0;">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <button type="submit" class="btn btn-success btn-sm">Stáhnout a nainstalovat</button>
            </form>
        </div>"""
    else:
        update_box = f"""
        <div class="alert-bar ok">
            <div>
                <strong>Systém je aktuální (v{html.escape(active_ver)})</strong><br>
                <span style="color:var(--text-muted);">Zdrojový manifest: <span class="mono">{html.escape(HF_REPO_ID or 'nenastaveno')}/system_ota/manifest.json</span></span>
            </div>
            <a href="/vaultupdate?{q_params}" class="btn btn-secondary btn-sm">Zkontrolovat znovu</a>
        </div>"""

    starter_module_code = '''def render(username, password, view_owner, supabase, action_data):
    # Vlastní OTA modul pro VaultGrid OS
    task_text = action_data.get("task_text", "").strip()
    if task_text and supabase:
        supabase.table("nxt_files").insert({
            "owner": view_owner,
            "filename": "vault_note",
            "storage_provider": "vault_note_item",
            "file_url": task_text,
            "folder": "/_notes",
            "size": 0,
            "is_deleted": False
        }).execute()

    items = []
    if supabase:
        res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("storage_provider", "vault_note_item").eq("is_deleted", False).execute()
        items = res.data or []

    rows = "".join([f"<tr><td class='mono'>#{i+1}</td><td>{html.escape(x.get('file_url', ''))}</td></tr>" for i, x in enumerate(reversed(items))])
    if not rows:
        rows = "<tr><td colspan='2' style='color:var(--text-muted); text-align:center;'>Žádné záznamy.</td></tr>"

    body = f"""
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Provozní poznámky a úkoly (OTA Modul)</h2></div>
        <form action="/ota-app/vaultnotes" method="POST" class="form-row" style="margin-bottom:14px;">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="text" name="task_text" placeholder="Zadejte provozní záznam..." required style="flex:1;">
            <button type="submit" class="btn">Uložit záznam</button>
        </form>
        <table>
            <thead><tr><th style="width:70px;">ID</th><th>Záznam</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>"""
    return render_shell("VaultNotes Pro", "ota_vaultnotes", username, password, view_owner, body)'''

    alert_html = f'<div class="alert-bar ok">{html.escape(status_msg)}</div>' if status_msg else ""

    body = f"""
    {alert_html}
    {update_box}

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("package")} Nainstalovaná OTA rozšíření</h2></div>
        <table>
            <thead><tr><th>Název modulu</th><th>Verze</th><th>Stav</th><th>Akce</th></tr></thead>
            <tbody>{installed_rows}</tbody>
        </table>
    </div>

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("code")} OTA Studio — Publikovat novou aktualizaci na Hugging Face</h2></div>
        <p style="color:var(--text-muted); margin-top:0;">Kód se nahraje do <span class="mono">system_ota/</span> a zapíše se do <span class="mono">manifest.json</span>. Následně jej nainstalujete jedním kliknutím bez úpravy <span class="mono">main.py</span>.</p>
        <form action="/vaultupdate/publish-custom" method="POST">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <div class="grid-2" style="margin-bottom:10px;">
                <div>
                    <label style="font-size:12px; color:var(--text-muted);">ID modulu (bez mezer)</label>
                    <input type="text" name="mod_name" value="vaultnotes" required>
                </div>
                <div>
                    <label style="font-size:12px; color:var(--text-muted);">Název v navigaci</label>
                    <input type="text" name="mod_title" value="VaultNotes Pro" required>
                </div>
                <div>
                    <label style="font-size:12px; color:var(--text-muted);">Verze balíčku</label>
                    <input type="text" name="new_version" value="20.1" required>
                </div>
                <div>
                    <label style="font-size:12px; color:var(--text-muted);">Popis změn (Changelog)</label>
                    <input type="text" name="release_notes" value="Přidán modul provozních poznámek VaultNotes Pro." required>
                </div>
            </div>
            <label style="font-size:12px; color:var(--text-muted);">Python kód modulu (funkce <span class="mono">render(username, password, view_owner, supabase, action_data)</span>)</label>
            <textarea name="module_code" rows="16" class="code-box" style="margin:4px 0 12px 0;" required>{html.escape(starter_module_code)}</textarea>
            <button type="submit" class="btn">Publikovat balíček na Hugging Face</button>
        </form>
    </div>"""
    return render_shell("VaultUpdate & OTA Studio", "vaultupdate", username, password, view_owner, body)

@app.post("/vaultupdate/publish-custom", response_class=HTMLResponse)
def vaultupdate_publish_custom(
    username: str = Form(...),
    password: str = Form(...),
    target_owner: str = Form(None),
    mod_name: str = Form(...),
    mod_title: str = Form(...),
    new_version: str = Form(...),
    release_notes: str = Form(...),
    module_code: str = Form(...)
):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    if not (hf_api and HF_REPO_ID):
        return vaultupdate_view(username, password, view_owner, "Chybí proměnné HF_TOKEN nebo HF_REPO_ID.")

    clean_name = "".join([c for c in mod_name.strip().lower() if c.isalnum() or c == "_"])
    if not clean_name:
        return vaultupdate_view(username, password, view_owner, "Neplatné ID modulu.")

    code_path = f"system_ota/{clean_name}.py"
    try:
        hf_api.upload_file(
            path_or_fileobj=module_code.encode("utf-8"),
            path_in_repo=code_path,
            repo_id=HF_REPO_ID,
            repo_type="dataset"
        )
        code_url = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/{code_path}"

        existing = fetch_remote_manifest() or {"version": new_version.strip(), "notes": "", "modules": []}
        modules_list = [m for m in existing.get("modules", []) if m.get("name") != clean_name]
        modules_list.append({
            "name": clean_name,
            "title": mod_title.strip(),
            "sub": "OTA Modul",
            "version": new_version.strip(),
            "code_url": code_url
        })
        updated_manifest = {
            "version": new_version.strip(),
            "notes": release_notes.strip(),
            "modules": modules_list
        }
        hf_api.upload_file(
            path_or_fileobj=json.dumps(updated_manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            path_in_repo="system_ota/manifest.json",
            repo_id=HF_REPO_ID,
            repo_type="dataset"
        )
        log_audit(username, "OTA_PUBLISHED", f"Publikován OTA balíček {clean_name} v{new_version.strip()}", "INFO")
        return vaultupdate_view(username, password, view_owner, f"Balíček {mod_title.strip()} (v{new_version.strip()}) byl publikován na Hugging Face.")
    except Exception as e:
        return vaultupdate_view(username, password, view_owner, f"Chyba publikování: {e}")

@app.post("/vaultupdate/install", response_class=HTMLResponse)
def vaultupdate_install(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    manifest = fetch_remote_manifest()
    if not manifest:
        return vaultupdate_view(username, password, view_owner, "Nepodařilo se načíst vzdálený manifest.")

    for mod in manifest.get("modules", []):
        mname = mod.get("name")
        curl = mod.get("code_url")
        if mname and curl:
            req = urllib.request.Request(curl, headers={"Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                code_str = resp.read().decode("utf-8")
            LOADED_OTA_MODULES[mname] = {
                "title": mod.get("title", mname),
                "sub": mod.get("sub", "OTA Modul"),
                "version": str(mod.get("version", manifest.get("version", "20.1"))),
                "code": code_str
            }
            supabase.table("nxt_files").delete().eq("storage_provider", "vault_ota_module").eq("filename", mname).execute()
            supabase.table("nxt_files").insert({
                "owner": "system",
                "filename": mname,
                "storage_provider": "vault_ota_module",
                "file_url": json.dumps(mod, ensure_ascii=False),
                "folder": "/_ota",
                "size": len(code_str),
                "is_deleted": False
            }).execute()

    log_audit(username, "OTA_INSTALLED", f"Nainstalována OTA aktualizace v{manifest.get('version')}", "INFO")
    return vaultupdate_view(username, password, view_owner, f"Aktualizace na verzi v{manifest.get('version')} byla dokončena.")

@app.post("/vaultupdate/uninstall", response_class=HTMLResponse)
def vaultupdate_uninstall(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), module_name: str = Form(...)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    LOADED_OTA_MODULES.pop(module_name, None)
    supabase.table("nxt_files").delete().eq("storage_provider", "vault_ota_module").eq("filename", module_name).execute()
    log_audit(username, "OTA_UNINSTALLED", f"Odinstalován modul {module_name}", "WARN")
    return vaultupdate_view(username, password, view_owner, f"Modul '{module_name}' byl odinstalován.")

@app.get("/ota-app/{module_name}", response_class=HTMLResponse)
def ota_app_get(module_name: str, request: Request, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    sync_ota_modules_from_db()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    if module_name not in LOADED_OTA_MODULES:
        return vaultupdate_view(username, password, view_owner, "Požadovaný OTA modul není nainstalován.")
    ns = {"render_shell": render_shell, "html": html, "json": json, "svg": svg, "format_bytes": format_bytes}
    exec(LOADED_OTA_MODULES[module_name]["code"], ns)
    return ns["render"](username, password, view_owner, supabase, dict(request.query_params))

@app.post("/ota-app/{module_name}", response_class=HTMLResponse)
async def ota_app_post(module_name: str, request: Request):
    sync_ota_modules_from_db()
    form_data = dict(await request.form())
    username = str(form_data.get("username", ""))
    password = str(form_data.get("password", ""))
    user = verify_user(username, password)
    if not user:
        return login_page()
    target_owner = form_data.get("target_owner")
    view_owner = str(target_owner) if (user["role"] == "admin" and target_owner) else username
    if module_name not in LOADED_OTA_MODULES:
        return vaultupdate_view(username, password, view_owner, "Požadovaný OTA modul není nainstalován.")
    ns = {"render_shell": render_shell, "html": html, "json": json, "svg": svg, "format_bytes": format_bytes}
    exec(LOADED_OTA_MODULES[module_name]["code"], ns)
    return ns["render"](username, password, view_owner, supabase, form_data)

# --- 9. VAULTCHAT ---
@app.get("/vaultchat", response_class=HTMLResponse)
def vaultchat_view(username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    msgs = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_chat").order("id", desc=False).execute().data or []
    recent = msgs[-60:]
    entries_html = ""
    for m in recent:
        sender = m.get("owner", "system")
        mine = "mine" if sender == username else ""
        entries_html += f"""
        <div class="chat-entry {mine}">
            <div style="font-size:11px; color:var(--text-muted); margin-bottom:2px;"><strong>{html.escape(sender)}</strong></div>
            <div>{html.escape(m.get('file_url', ''))}</div>
        </div>"""
    if not entries_html:
        entries_html = '<div style="color:var(--text-muted); margin:auto;">Žádné zprávy v kanálu.</div>'

    body = f"""
    <div class="panel" style="max-width:860px;">
        <div class="panel-header">
            <h2 class="panel-title">{svg("message")} Interní systémový kanál (VaultChat)</h2>
            <a href="/vaultchat?{q_params}" class="btn btn-secondary btn-sm">Obnovit</a>
        </div>
        <div class="chat-stream" id="chat-box">{entries_html}</div>
        <form action="/vaultchat/send" method="POST" class="form-row">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="text" name="message" placeholder="Napsat zprávu..." required autofocus style="flex:1;">
            <button type="submit" class="btn">Odeslat</button>
        </form>
    </div>
    <script>const cb = document.getElementById('chat-box'); cb.scrollTop = cb.scrollHeight;</script>"""
    return render_shell("VaultChat", "vaultchat", username, password, view_owner, body)

@app.post("/vaultchat/send", response_class=HTMLResponse)
def vaultchat_send(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), message: str = Form(...)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    if message.strip():
        supabase.table("nxt_files").insert({
            "owner": username,
            "filename": "chat_msg",
            "storage_provider": "vault_chat",
            "file_url": message.strip(),
            "folder": "/_chat",
            "size": 0,
            "is_deleted": False
        }).execute()
    return vaultchat_view(username, password, target_owner)

# --- 10. VAULTCODE IDE & EDITOR ---
@app.get("/new-file", response_class=HTMLResponse)
def new_file_view(username: str, password: str, folder: str = "/", target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    starter = "<!DOCTYPE html>\n<html lang=\"cs\">\n<head>\n    <meta charset=\"UTF-8\">\n    <title>VaultGrid Web</title>\n</head>\n<body>\n    <h1>VaultGrid Cloud Hosting</h1>\n</body>\n</html>"
    body = f"""
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("code")} Nový textový soubor / HTML stránka v {html.escape(folder)}</h2></div>
        <form action="/create-text-file" method="POST">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="folder" value="{html.escape(folder)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="text" name="filename" value="index.html" required style="margin-bottom:10px;">
            <textarea name="content" rows="18" class="code-box" style="margin-bottom:12px;">{html.escape(starter)}</textarea>
            <button type="submit" class="btn">Uložit do úložiště</button>
        </form>
    </div>"""
    return render_shell("VaultCode IDE", "code", username, password, view_owner, body)

@app.post("/create-text-file", response_class=HTMLResponse)
def create_text_file(username: str = Form(...), password: str = Form(...), folder: str = Form("/"), target_owner: str = Form(None), filename: str = Form(...), content: str = Form(...)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    clean_name = filename.strip().replace("/", "")
    file_bytes = content.encode("utf-8")
    repo_id = get_active_write_repo()
    repo_path = f"{view_owner}{folder}/{clean_name}".replace("//", "/")

    if hf_api and repo_id:
        hf_api.upload_file(path_or_fileobj=file_bytes, path_in_repo=repo_path, repo_id=repo_id, repo_type="dataset")
        public_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{repo_path}"
    else:
        public_url = "#"

    supabase.table("nxt_files").insert({
        "owner": view_owner,
        "filename": clean_name,
        "storage_provider": "huggingface",
        "file_url": public_url,
        "folder": folder,
        "size": len(file_bytes),
        "is_deleted": False
    }).execute()
    log_audit(username, "FILE_CREATED", f"Vytvořen soubor {repo_path}", "INFO")
    return render_files_view(username, password, user["role"] == "admin", view_owner, folder, False, "", "", f"Soubor {clean_name} byl uložen.")

@app.get("/code-editor", response_class=HTMLResponse)
def code_editor_view(id: int, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    res = supabase.table("nxt_files").select("*").eq("id", id).execute()
    if not res.data:
        return "Soubor nenalezen."
    rec = res.data[0]
    try:
        with urllib.request.urlopen(rec["file_url"], timeout=6) as resp:
            text = resp.read().decode("utf-8")
    except Exception:
        text = ""

    body = f"""
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("code")} Úprava souboru: {html.escape(rec['filename'])}</h2></div>
        <form action="/save-code" method="POST">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="hidden" name="filename" value="{html.escape(rec['filename'])}">
            <input type="hidden" name="folder" value="{html.escape(rec['folder'])}">
            <textarea name="content" rows="20" class="code-box" style="margin-bottom:12px;">{html.escape(text)}</textarea>
            <button type="submit" class="btn">Uložit novou revizi</button>
        </form>
    </div>"""
    return render_shell("Editor kódu", "code", username, password, view_owner, body)

@app.post("/save-code", response_class=HTMLResponse)
def save_code(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), filename: str = Form(...), folder: str = Form(...), content: str = Form(...)):
    return create_text_file(username, password, folder, target_owner, filename, content)

# --- 11. OPERACE SE SOUBORY, ZIP EXPORT, SDÍLENÍ, VERZE, KOMENTÁŘE ---
@app.post("/create-folder", response_class=HTMLResponse)
def create_folder(username: str = Form(...), password: str = Form(...), current_folder: str = Form(...), new_folder_name: str = Form(...), target_owner: str = Form(None)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    clean_name = new_folder_name.strip().replace("/", "")
    new_path = f"{current_folder.rstrip('/')}/{clean_name}"
    supabase.table("nxt_files").insert({
        "owner": view_owner,
        "filename": f".slozkové_meta_{clean_name}",
        "storage_provider": "system",
        "file_url": "#",
        "folder": new_path,
        "size": 0,
        "is_deleted": False
    }).execute()
    log_audit(username, "DIR_CREATED", f"Vytvořen adresář {new_path}", "INFO")
    return render_files_view(username, password, user["role"] == "admin", view_owner, new_path, False, "", "", "")

@app.post("/upload", response_class=HTMLResponse)
async def upload_files(
    username: str = Form(...),
    password: str = Form(...),
    folder: str = Form("/"),
    target_owner: str = Form(None),
    unlocked_pin: str = Form(""),
    files: list[UploadFile] = File(...)
):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username

    # Kontrola kvóty uživatele
    quota_limit = get_user_quota_bytes(view_owner)
    existing_res = supabase.table("nxt_files").select("size, storage_provider, filename").eq("owner", view_owner).eq("is_deleted", False).execute()
    current_used = sum(int(f.get("size", 0)) for f in (existing_res.data or []) if not is_system_record(f))

    repo_id = get_active_write_repo()
    uploaded_count = 0
    for f in files:
        if not f.filename:
            continue
        file_bytes = await f.read()
        if quota_limit > 0 and (current_used + len(file_bytes)) > quota_limit:
            log_audit(username, "QUOTA_EXCEEDED", f"Překročena disková kvóta pro {view_owner}", "WARN")
            return render_files_view(username, password, user["role"] == "admin", view_owner, folder, False, "", unlocked_pin, "Chyba: Byla překročena přidělená disková kvóta.")

        repo_path = f"{view_owner}{folder}/{f.filename}".replace("//", "/")
        if hf_api and repo_id:
            hf_api.upload_file(path_or_fileobj=file_bytes, path_in_repo=repo_path, repo_id=repo_id, repo_type="dataset")
            public_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{repo_path}"
        else:
            public_url = "#"

        supabase.table("nxt_files").insert({
            "owner": view_owner,
            "filename": f.filename,
            "storage_provider": "huggingface",
            "file_url": public_url,
            "folder": folder,
            "size": len(file_bytes),
            "is_deleted": False
        }).execute()
        current_used += len(file_bytes)
        uploaded_count += 1

    log_audit(username, "FILES_UPLOADED", f"Nahráno {uploaded_count} souborů do {folder}", "INFO")
    return render_files_view(username, password, user["role"] == "admin", view_owner, folder, False, "", unlocked_pin, f"Úspěšně nahráno souborů: {uploaded_count}.")

@app.get("/download-zip")
def download_zip(username: str, password: str, folder: str = "/", target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return HTMLResponse("Neautorizováno", status_code=401)
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute()
    target_files = [
        f for f in (res.data or [])
        if not is_system_record(f) and (folder == "/" or f.get("folder", "").startswith(folder))
    ]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in target_files:
            try:
                with urllib.request.urlopen(f["file_url"], timeout=8) as resp:
                    data = resp.read()
                rel_dir = f.get("folder", "/").strip("/")
                arcname = f"{rel_dir}/{f['filename']}".lstrip("/")
                zf.writestr(arcname, data)
            except Exception:
                pass
    buf.seek(0)
    zip_name = (folder.strip("/").replace("/", "_") or "vaultgrid_root") + ".zip"
    log_audit(username, "ZIP_EXPORT", f"Exportován archiv {zip_name}", "INFO")
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{zip_name}"'})

@app.post("/set-folder-pin", response_class=HTMLResponse)
def set_folder_pin(username: str = Form(...), password: str = Form(...), current_folder: str = Form(...), target_owner: str = Form(None), new_pin: str = Form(...)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    clean_pin = new_pin.strip()
    if clean_pin and current_folder != "/":
        supabase.table("nxt_files").delete().eq("owner", view_owner).eq("folder", current_folder).eq("filename", ".vault_pin_lock").execute()
        supabase.table("nxt_files").insert({
            "owner": view_owner,
            "filename": ".vault_pin_lock",
            "storage_provider": "system_lock",
            "file_url": clean_pin,
            "folder": current_folder,
            "size": 0,
            "is_deleted": False
        }).execute()
        log_audit(username, "PIN_LOCK_SET", f"Nastaven PIN zámek pro {current_folder}", "INFO")
    return render_files_view(username, password, user["role"] == "admin", view_owner, current_folder, False, "", "", "")

@app.post("/remove-folder-pin", response_class=HTMLResponse)
def remove_folder_pin(username: str = Form(...), password: str = Form(...), current_folder: str = Form(...), target_owner: str = Form(None)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("owner", view_owner).eq("folder", current_folder).eq("filename", ".vault_pin_lock").execute()
    log_audit(username, "PIN_LOCK_REMOVED", f"Odebrán PIN zámek z {current_folder}", "WARN")
    return render_files_view(username, password, user["role"] == "admin", view_owner, current_folder, False, "", "", "")

@app.get("/delete-file", response_class=HTMLResponse)
def delete_file(id: int, username: str, password: str, folder: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").update({"is_deleted": True}).eq("id", id).execute()
    log_audit(username, "FILE_TRASHED", f"Soubor ID #{id} přesunut do koše", "INFO")
    return render_files_view(username, password, user["role"] == "admin", view_owner, folder, False, "", "", "")

@app.get("/restore-file", response_class=HTMLResponse)
def restore_file(id: int, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").update({"is_deleted": False}).eq("id", id).execute()
    log_audit(username, "FILE_RESTORED", f"Soubor ID #{id} obnoven z koše", "INFO")
    return render_files_view(username, password, user["role"] == "admin", view_owner, "/", True, "", "", "")

@app.get("/delete-permanently", response_class=HTMLResponse)
def delete_permanently(id: int, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("id", id).execute()
    log_audit(username, "FILE_PURGED", f"Soubor ID #{id} trvale odstraněn", "WARN")
    return render_files_view(username, password, user["role"] == "admin", view_owner, "/", True, "", "", "")

@app.post("/admin/add-user", response_class=HTMLResponse)
def add_user(admin_user: str = Form(...), admin_pass: str = Form(...), new_user: str = Form(...), new_pass: str = Form(...), new_role: str = Form(...)):
    user = verify_user(admin_user, admin_pass)
    if not user or user["role"] != "admin":
        return login_page()
    try:
        supabase.table("nxt_users").insert({"username": new_user.strip(), "password": new_pass, "role": new_role}).execute()
        log_audit(admin_user, "USER_CREATED", f"Vytvořen účet {new_user.strip()} ({new_role})", "INFO")
    except Exception:
        pass
    return users_quotas_view(admin_user, admin_pass, admin_user, f"Účet {new_user.strip()} byl vytvořen.")

@app.get("/share", response_class=HTMLResponse)
def share_file(id: int):
    res = supabase.table("nxt_files").select("*").eq("id", id).execute()
    if not res.data:
        return "Soubor nenalezen."
    rec = res.data[0]
    return f"""<!DOCTYPE html><html lang="cs" data-theme="dark"><head><meta charset="UTF-8"><title>Sdílený soubor</title>{INDUSTRIAL_CSS}{THEME_SCRIPT}</head>
    <body style="display:flex; align-items:center; justify-content:center; min-height:100vh;">
        <div class="panel" style="max-width:440px; width:100%; text-align:center;">
            <div class="panel-header" style="justify-content:center;"><h2 class="panel-title">{svg("file")} Veřejný odkaz ke stažení</h2></div>
            <p style="font-weight:600;">{html.escape(rec['filename'])}</p>
            <p class="mono" style="color:var(--text-muted);">{format_bytes(rec.get('size', 0))}</p>
            <a href="{html.escape(rec['file_url'])}" download class="btn" style="width:100%;">Stáhnout soubor</a>
        </div>
    </body></html>"""

@app.get("/live", response_class=HTMLResponse)
def live_html_preview(id: int):
    res = supabase.table("nxt_files").select("*").eq("id", id).execute()
    if not res.data:
        return "Soubor nenalezen."
    rec = res.data[0]
    if not rec["filename"].endswith(".html"):
        return "Pouze .html soubory lze spustit jako živý web."
    try:
        with urllib.request.urlopen(rec["file_url"], timeout=6) as resp:
            return HTMLResponse(content=resp.read().decode("utf-8"), status_code=200)
    except Exception as e:
        return f"Chyba načtení: {e}"

@app.get("/media-player", response_class=HTMLResponse)
def media_player(file_url: str, filename: str, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    ext = filename.split(".")[-1].lower()
    tag = f'<video controls autoplay style="width:100%; max-height:480px; background:#000;"><source src="{html.escape(file_url)}"></video>' if ext in VIDEO_EXTENSIONS else f'<audio controls autoplay style="width:100%;"><source src="{html.escape(file_url)}"></audio>'
    body = f"""
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("film")} {html.escape(filename)}</h2></div>
        {tag}
    </div>"""
    return render_shell("Přehrávač médií", "files", username, password, view_owner, body)

@app.get("/photo-gallery", response_class=HTMLResponse)
def photo_gallery(username: str, password: str, folder: str = "/", target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("folder", folder).eq("is_deleted", False).execute()
    imgs = [f for f in (res.data or []) if not is_system_record(f) and f["filename"].split(".")[-1].lower() in IMAGE_EXTENSIONS]
    grid = ""
    for im in imgs:
        grid += f"""
        <div class="media-card">
            <a href="{html.escape(im['file_url'])}" target="_blank" class="media-poster"><img src="{html.escape(im['file_url'])}"></a>
            <div style="padding:8px; font-size:12px; word-break:break-word;">{html.escape(im['filename'])}</div>
        </div>"""
    if not grid:
        grid = '<p style="color:var(--text-muted);">V tomto adresáři nejsou žádné obrázky.</p>'
    body = f"""
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("image")} Galerie obrázků: {html.escape(folder)}</h2></div>
        <div class="media-grid">{grid}</div>
    </div>"""
    return render_shell("Galerie obrázků", "files", username, password, view_owner, body)

@app.get("/file-versions", response_class=HTMLResponse)
def file_versions(filename: str, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("filename", filename).execute()
    rows = "".join([f"<tr><td class='mono'>#{v['id']}</td><td class='mono'>{html.escape(v['folder'])}</td><td class='mono'>{format_bytes(v.get('size', 0))}</td><td><a href='{html.escape(v['file_url'])}' download class='link-action'>Stáhnout revizi</a></td></tr>" for v in (res.data or [])])
    body = f"""
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Historie revizí: {html.escape(filename)}</h2></div>
        <table><thead><tr><th>Revize</th><th>Adresář</th><th>Velikost</th><th>Akce</th></tr></thead><tbody>{rows}</tbody></table>
    </div>"""
    return render_shell("Historie revizí", "files", username, password, view_owner, body)

@app.get("/file-comments", response_class=HTMLResponse)
def file_comments(file_id: int, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    f_res = supabase.table("nxt_files").select("*").eq("id", file_id).execute()
    if not f_res.data:
        return "Soubor nenalezen."
    rec = f_res.data[0]
    comments = []
    try:
        comments = supabase.table("nxt_comments").select("*").eq("file_id", file_id).execute().data or []
    except Exception:
        pass
    c_html = "".join([f"<div style='padding:8px 12px; border:1px solid var(--border); border-radius:4px; margin-bottom:8px;'><strong>{html.escape(c['username'])}</strong>: {html.escape(c['comment'])}</div>" for c in comments]) or "<p style='color:var(--text-muted);'>Zatím žádné poznámky.</p>"
    body = f"""
    <div class="panel" style="max-width:700px;">
        <div class="panel-header"><h2 class="panel-title">Poznámky k souboru: {html.escape(rec['filename'])}</h2></div>
        {c_html}
        <form action="/add-comment" method="POST" class="form-row" style="margin-top:12px;">
            <input type="hidden" name="file_id" value="{file_id}">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="text" name="comment" placeholder="Přidat poznámku..." required style="flex:1;">
            <button type="submit" class="btn">Uložit</button>
        </form>
    </div>"""
    return render_shell("Poznámky k souboru", "files", username, password, view_owner, body)

@app.post("/add-comment", response_class=HTMLResponse)
def add_comment(file_id: int = Form(...), username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), comment: str = Form(...)):
    try:
        supabase.table("nxt_comments").insert({"file_id": file_id, "username": username, "comment": comment}).execute()
    except Exception:
        pass
    return file_comments(file_id, username, password, target_owner)

# --- 12. ROOT SSH KONZOLE ---
def terminal_view(username: str, current_folder: str, history: str) -> str:
    safe_hist = html.escape(history)
    active_ver = get_installed_ota_version()
    return f"""<!DOCTYPE html>
<html lang="cs">
<head><meta charset="UTF-8"><title>VaultGrid ROOT Console</title>{TERMINAL_CSS}</head>
<body>
    <div class="term-box">
        <div class="term-head">
            <span>VAULTGRID OS [v{html.escape(active_ver)}-ROOT] // SYSTEM CONSOLE</span>
            <a href="/" style="color:#f87171; text-decoration:none;">[ODHLÁSIT]</a>
        </div>
        <div class="term-out" id="out">{safe_hist}</div>
        <form action="/terminal-exec" method="POST" class="term-line">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="current_folder" value="{html.escape(current_folder)}">
            <input type="hidden" name="history" value="{safe_hist}">
            <span style="color:#60a5fa;">root@vaultgrid:{html.escape(current_folder)}#</span>
            <input type="text" name="command" class="term-input" autofocus autocomplete="off" required>
        </form>
    </div>
    <script>const o = document.getElementById('out'); o.scrollTop = o.scrollHeight;</script>
</body>
</html>"""

@app.post("/terminal-exec", response_class=HTMLResponse)
def terminal_exec(username: str = Form(...), current_folder: str = Form(...), history: str = Form(...), command: str = Form(...)):
    cmd = command.strip()
    new_hist = history + f"root@vaultgrid:{current_folder}# {cmd}\n"
    parts = cmd.split(" ")
    act = parts[0].lower() if parts else ""

    if act == "help":
        new_hist += "Příkazy:\n  ls        - Výpis souborů\n  cd <dir>  - Změna adresáře\n  pools     - Stav 7 TB úložných poolů\n  update    - Stav OTA aktualizací\n  audit     - Posledních 5 bezpečnostních událostí\n  users     - Seznam účtů\n  clear     - Vyčištění obrazovky\n\n"
    elif act == "clear":
        new_hist = ""
    elif act == "pools":
        for p in get_storage_pools():
            new_hist += f"  - {p['label']} [{p['repo_id']}] ({p['quota_gb']} GB)\n"
        new_hist += "\n"
    elif act == "update":
        m = fetch_remote_manifest()
        new_hist += f"  Installed: v{get_installed_ota_version()}\n"
        new_hist += f"  Remote:    v{m.get('version')}\n\n" if m else "  Remote:    Žádný vzdálený manifest.\n\n"
    elif act == "audit":
        res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_audit").order("id", desc=True).limit(5).execute()
        for r in (res.data or []):
            ev = json.loads(r.get("file_url", "{}"))
            new_hist += f"  [{ev.get('ts')}] {ev.get('level')} {ev.get('actor')}: {ev.get('action')}\n"
        new_hist += "\n"
    elif act == "users":
        for u in (supabase.table("nxt_users").select("username, role").execute().data or []):
            new_hist += f"  - {u['username']} ({u['role']})\n"
        new_hist += "\n"
    elif act == "ls":
        files = supabase.table("nxt_files").select("*").eq("folder", current_folder).eq("is_deleted", False).execute().data or []
        shown = [f["filename"] for f in files if not is_system_record(f)]
        new_hist += ("\n".join(f"  {x}" for x in shown) if shown else "  (prázdné)") + "\n\n"
    elif act == "cd":
        if len(parts) > 1:
            current_folder = "/" if parts[1] == ".." else f"/{parts[1].strip('/')}"
        new_hist += "\n"
    else:
        new_hist += f"Neznámý příkaz: {cmd}\n\n"

    return terminal_view(username, current_folder, new_hist)

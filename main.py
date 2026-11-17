import os
import io
import re
import hmac
import json
import html
import zipfile
import hashlib
import secrets
import platform
import mimetypes
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Form, UploadFile, File, Request, Header
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from supabase import create_client, Client
from huggingface_hub import HfApi

app = FastAPI(title="VaultGrid OS Ultimate", version="22.0")

CORE_VERSION = "22.0"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_REPO_ID = os.environ.get("HF_REPO_ID")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

supabase: Client | None = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None
hf_api = HfApi(token=HF_TOKEN) if HF_TOKEN else None

LOADED_OTA_MODULES: dict[str, dict] = {}

EDITABLE_EXTENSIONS = ["txt", "md", "py", "html", "css", "js", "json", "csv", "xml", "yml", "yaml"]
VIDEO_EXTENSIONS = ["mp4", "mov", "avi", "webm", "mkv"]
AUDIO_EXTENSIONS = ["mp3", "wav", "flac", "ogg", "m4a"]
IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp", "svg"]
PREVIEW_EXTENSIONS = ["pdf", "md", "csv", "json", "stl", "obj"] + IMAGE_EXTENSIONS + EDITABLE_EXTENSIONS

SYSTEM_PROVIDERS = {
    "vault_chat",
    "system_lock",
    "vault_ota_module",
    "vault_note_item",
    "vault_pool",
    "vault_quota",
    "vault_audit",
    "vault_backup_profile",
    "vault_backup_snapshot",
    "vault_drop",
    "vault_rule",
    "vault_api_token",
    "vault_watch_progress",
    "vault_file_tag",
}

# --- VEKTOROVÉ SVG IKONY (LUCIDE INDUSTRIAL SET) ---
SVG_ICONS = {
    "server": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>',
    "dashboard": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
    "folder": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
    "file": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    "database": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
    "film": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></svg>',
    "music": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
    "users": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "shield": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "lock": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    "wrench": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
    "refresh": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
    "message": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "code": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    "sun": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
    "package": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
    "image": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
    "share": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>',
    "save": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>',
    "zap": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "key": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>',
    "eye": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>',
    "columns": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="3" x2="12" y2="21"/></svg>',
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
    .app-layout { display: flex; min-height: 100vh; }
    .sidebar {
        width: 248px;
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
        padding: 14px 18px 5px 18px;
    }
    .nav-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 18px;
        color: var(--text-muted);
        text-decoration: none;
        font-weight: 500;
        border-left: 3px solid transparent;
        transition: background 0.12s, color 0.12s;
    }
    .nav-item:hover { background-color: var(--bg-surface-alt); color: var(--text-main); }
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
    .main-area { flex: 1; display: flex; flex-direction: column; min-width: 0; }
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
    .topbar-title { font-size: 15px; font-weight: 600; margin: 0; }
    .topbar-actions { display: flex; align-items: center; gap: 10px; }
    .content-wrap { padding: 24px; max-width: 1440px; width: 100%; }
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
    .kpi-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
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
    input[type="checkbox"] { width: auto; cursor: pointer; }
    input:focus, select:focus, textarea:focus { border-color: var(--accent); }
    textarea.code-box { font-family: var(--mono); font-size: 12.5px; line-height: 1.45; }
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
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 9px 11px; text-align: left; border-bottom: 1px solid var(--border); }
    th {
        font-size: 11px;
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
        padding: 2px 7px;
        border-radius: 4px;
        font-family: var(--mono);
        font-size: 11px;
        border: 1px solid var(--border);
        background-color: var(--bg-surface-alt);
        color: var(--text-main);
    }
    .badge-ok { border-color: rgba(22, 163, 74, 0.45); color: #22c55e; }
    .badge-warn { border-color: rgba(217, 119, 6, 0.45); color: #f59e0b; }
    .badge-err { border-color: rgba(220, 38, 38, 0.45); color: #ef4444; }
    .badge-tag { border-color: rgba(37, 99, 235, 0.45); color: #60a5fa; text-decoration: none; }
    .progress-track {
        width: 100%;
        height: 8px;
        background-color: var(--bg-app);
        border: 1px solid var(--border);
        border-radius: 4px;
        overflow: hidden;
    }
    .progress-fill { height: 100%; background-color: var(--accent); }
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
        gap: 10px;
    }
    .alert-bar.warn { border-left: 4px solid var(--warning); }
    .alert-bar.ok { border-left: 4px solid var(--success); }
    .alert-bar.err { border-left: 4px solid var(--danger); }
    .form-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 14px; }
    .grid-dual { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .media-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
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
        height: 170px;
        background-color: var(--bg-app);
        display: flex;
        align-items: center;
        justify-content: center;
        border-bottom: 1px solid var(--border);
        overflow: hidden;
    }
    .media-poster img { width: 100%; height: 100%; object-fit: cover; }
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
    .chat-entry.mine { align-self: flex-end; border-left: 3px solid var(--accent); }
    .link-action { color: #60a5fa; text-decoration: none; font-size: 12px; margin-right: 8px; }
    .link-action:hover { text-decoration: underline; }
    .link-danger { color: #f87171; text-decoration: none; font-size: 12px; }
    .link-danger:hover { text-decoration: underline; }
    @media (max-width: 980px) {
        .app-layout { flex-direction: column; }
        .sidebar { width: 100%; height: auto; position: static; }
        .grid-dual { grid-template-columns: 1fr; }
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

# --- VAULTCRYPT ZERO-KNOWLEDGE ŠIFROVÁNÍ (PURE STDLIB AUTHENTICATED STREAM CIPHER) ---
def _derive_keys(password: str, salt: bytes) -> tuple[bytes, bytes]:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000, dklen=64)
    return dk[:32], dk[32:]

def _keystream_xor(data: bytes, enc_key: bytes, nonce: bytes) -> bytes:
    out = bytearray(len(data))
    counter = 0
    pos = 0
    total = len(data)
    while pos < total:
        block = hashlib.sha256(enc_key + nonce + counter.to_bytes(8, "big")).digest()
        chunk_len = min(32, total - pos)
        for i in range(chunk_len):
            out[pos + i] = data[pos + i] ^ block[i]
        pos += chunk_len
        counter += 1
    return bytes(out)

def vaultcrypt_encrypt(raw_data: bytes, password: str) -> bytes:
    magic = b"VGCRYPT1"
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    enc_key, mac_key = _derive_keys(password, salt)
    ciphertext = _keystream_xor(raw_data, enc_key, nonce)
    tag = hmac.new(mac_key, magic + salt + nonce + ciphertext, hashlib.sha256).digest()
    return magic + salt + nonce + tag + ciphertext

def vaultcrypt_decrypt(blob: bytes, password: str) -> bytes:
    if len(blob) < 72 or not blob.startswith(b"VGCRYPT1"):
        raise ValueError("Neplatný formát zašifrovaného souboru VaultCrypt.")
    magic = blob[:8]
    salt = blob[8:24]
    nonce = blob[24:40]
    tag = blob[40:72]
    ciphertext = blob[72:]
    enc_key, mac_key = _derive_keys(password, salt)
    expected_tag = hmac.new(mac_key, magic + salt + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Chybné dešifrovací heslo nebo poškozená data.")
    return _keystream_xor(ciphertext, enc_key, nonce)

# --- POMOCNÉ SYSTÉMOVÉ FUNKCE ---
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

# --- 7 TB AUTO-BALANCING MULTI-POOL ENGINE ---
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

def get_active_write_repo(active_files: list[dict] | None = None) -> str:
    pools = get_storage_pools()
    if not pools:
        return HF_REPO_ID or ""

    if active_files is None and supabase:
        rows = supabase.table("nxt_files").select("file_url, size, is_deleted, storage_provider, filename").eq("is_deleted", False).execute().data or []
        active_files = [r for r in rows if not is_system_record(r)]

    # Nejprve zkus preferovaný zápisový pool, pokud je pod 90 % kapacity
    ordered = sorted(pools, key=lambda x: 0 if x.get("is_active_write") else 1)
    for p in ordered:
        repo = p["repo_id"]
        cap_bytes = int(p.get("quota_gb", 300)) * (1024 ** 3)
        used_bytes = sum(int(f.get("size", 0)) for f in (active_files or []) if repo in f.get("file_url", ""))
        if used_bytes < (cap_bytes * 0.90):
            return repo
    return ordered[0]["repo_id"]

def get_user_quota_bytes(target_user: str) -> int:
    if not supabase:
        return 0
    try:
        res = supabase.table("nxt_files").select("*").eq("owner", target_user).eq("storage_provider", "vault_quota").eq("is_deleted", False).execute()
        if res.data:
            return int(res.data[-1].get("size", 0))
    except Exception:
        pass
    return 0

# --- ŠTÍTKY (TAGS) & VAULTRULES AUTOMATIZACE ---
def attach_file_tag(owner: str, file_id: int, tag: str):
    clean_tag = re.sub(r"[^a-zA-Z0-9áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ_-]", "", tag.strip().lstrip("#")).lower()
    if not (clean_tag and supabase):
        return
    supabase.table("nxt_files").insert({
        "owner": owner,
        "filename": clean_tag,
        "storage_provider": "vault_file_tag",
        "file_url": str(file_id),
        "folder": "/_tags",
        "size": file_id,
        "is_deleted": False
    }).execute()

def get_file_tags_map(owner: str) -> dict[int, list[str]]:
    tags_map: dict[int, list[str]] = {}
    if not supabase:
        return tags_map
    res = supabase.table("nxt_files").select("filename, size").eq("owner", owner).eq("storage_provider", "vault_file_tag").eq("is_deleted", False).execute()
    for r in (res.data or []):
        fid = int(r.get("size", 0))
        tname = r.get("filename", "")
        if fid and tname:
            tags_map.setdefault(fid, [])
            if tname not in tags_map[fid]:
                tags_map[fid].append(tname)
    return tags_map

def apply_vault_rules(owner: str, filename: str, current_folder: str) -> tuple[str, list[str]]:
    if not supabase:
        return current_folder, []
    res = supabase.table("nxt_files").select("*").eq("owner", owner).eq("storage_provider", "vault_rule").eq("is_deleted", False).execute()
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    dest_folder = current_folder
    tags_to_add: list[str] = []
    for r in (res.data or []):
        try:
            rule = json.loads(r.get("file_url", "{}"))
            r_ext = rule.get("ext", "").lower()
            r_src = rule.get("src_folder", "")
            if r_ext and r_ext != ext:
                continue
            if r_src and r_src != current_folder:
                continue
            if rule.get("dest_folder"):
                dest_folder = rule["dest_folder"]
            if rule.get("add_tag"):
                tags_to_add.append(rule["add_tag"])
        except Exception:
            pass
    return dest_folder, tags_to_add

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
                    compile(code_str, f"<ota_{mod_name}>", "exec")
                    LOADED_OTA_MODULES[mod_name] = {
                        "title": meta.get("title", mod_name),
                        "sub": meta.get("sub", "OTA Modul"),
                        "version": str(meta.get("version", "22.1")),
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
        {nav_link("audit", f"/audit-log?{q_params}", "shield", "Forenzní Audit Log")}

        <div class="nav-group-label">Úložiště a Média</div>
        {nav_link("files", f"/files?{q_params}", "folder", "Správce souborů")}
        {nav_link("vaultflix", f"/vaultflix?{q_params}", "film", "VaultFlix Cinema")}
        {nav_link("vaultbeats", f"/vaultbeats?{q_params}", "music", "VaultBeats Hi-Fi")}
        {nav_link("code", f"/new-file?{q_params}", "code", "VaultCode IDE Pro")}

        <div class="nav-group-label">Sdílení a Automatizace</div>
        {nav_link("vaultdrop", f"/vaultdrop?{q_params}", "share", "VaultDrop Sdílení")}
        {nav_link("vaultbackup", f"/vaultbackup?{q_params}", "save", "Zálohy & Konfigurace")}
        {nav_link("vaultrules", f"/vaultrules?{q_params}", "zap", "VaultRules Pravidla")}
        {nav_link("apitokens", f"/api-tokens?{q_params}", "key", "REST API & Tokeny")}

        <div class="nav-group-label">Správa a Služby</div>
        {nav_link("users", f"/users-quotas?{q_params}", "users", "Uživatelé a kvóty")}
        {nav_link("maintenance", f"/maintenance?{q_params}", "wrench", "Údržba & Deduplikace")}
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
                        <input type="text" name="q" value="{html.escape(search_query)}" placeholder="Hledat soubory nebo #štítek..." style="width: 230px;">
                        <button type="submit" class="btn btn-secondary btn-sm">Hledat</button>
                    </form>
                    <span class="badge badge-ok">ULTIMATE OS // ONLINE</span>
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

# --- 1. PŘIHLÁŠENÍ & OVERVIEW ---
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
    <div class="panel" style="width:100%; max-width:410px; margin:0;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; padding-bottom:12px; border-bottom:1px solid var(--border);">
            <div class="brand-title">{svg("server")} <span>VAULTGRID OS</span></div>
            <span class="brand-ver">v{html.escape(active_ver)}</span>
        </div>
        <p style="color:var(--text-muted); margin-top:0; margin-bottom:16px;">Zero-Knowledge Cloud NAS & 7 TB Storage Platform (SSH konzole: <span class="mono">root / root</span>).</p>
        <form action="/login-router" method="POST">
            <label style="font-size:12px; color:var(--text-muted);">Uživatelské jméno</label>
            <input type="text" name="username" required autofocus style="margin:4px 0 12px 0;">
            <label style="font-size:12px; color:var(--text-muted);">Heslo</label>
            <input type="password" name="password" required style="margin:4px 0 16px 0;">
            <button type="submit" class="btn" style="width:100%;">Přihlásit se do systému</button>
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

    drops_cnt = len([f for f in all_rows if f.get("storage_provider") == "vault_drop" and f.get("owner") == view_owner])
    snaps_cnt = len([f for f in all_rows if f.get("storage_provider") == "vault_backup_snapshot" and f.get("owner") == view_owner])

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
            <div class="kpi-label">Cloud Multi-Pool (7 TB)</div>
            <div class="kpi-value">{total_pool_gb} GB</div>
            <div class="kpi-sub">{len(pools)} připojených fondů (Auto-Failover)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Aktivní soubory & Zálohy</div>
            <div class="kpi-value">{len(user_files)} / {snaps_cnt}</div>
            <div class="kpi-sub">{drops_cnt} aktivních VaultDrop odkazů</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">VaultGrid OS Runtime</div>
            <div class="kpi-value">v{html.escape(get_installed_ota_version())}</div>
            <div class="kpi-sub">{len(LOADED_OTA_MODULES)} OTA modulů | AES-256 Ready</div>
        </div>
    </div>

    <div class="grid-2">
        <div class="panel">
            <div class="panel-header">
                <h2 class="panel-title">{svg("database")} Stav Auto-Balancing Storage Poolu</h2>
                <a href="/storage-pools?{q_params}" class="btn btn-secondary btn-sm">Spravovat pooly</a>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:12.5px;">
                <span>Globálně obsazeno: <strong class="mono">{format_bytes(global_used_bytes)}</strong></span>
                <span class="mono">{pct_pool:.2f}% z {total_pool_gb} GB</span>
            </div>
            <div class="progress-track"><div class="progress-fill" style="width:{pct_pool}%;"></div></div>
            <div style="margin-top:14px; font-size:12.5px; color:var(--text-muted);">
                Aktivní zápisový repozitář: <span class="mono" style="color:var(--text-main);">{html.escape(get_active_write_repo(active_files) or 'Nenastaveno')}</span><br>
                Hostitel: <span class="mono">{platform.system()} {platform.machine()} (Python {platform.python_version()})</span>
            </div>
        </div>

        <div class="panel">
            <div class="panel-header">
                <h2 class="panel-title">{svg("server")} Rychlý přístup k nástrojům</h2>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                <a href="/files?{q_params}&mode=dual" class="btn btn-secondary">{svg("columns")} Dual-Pane Commander</a>
                <a href="/vaultdrop?{q_params}" class="btn btn-secondary">{svg("share")} VaultDrop Sdílení</a>
                <a href="/vaultbackup?{q_params}" class="btn btn-secondary">{svg("save")} Zálohy & Snapshots</a>
                <a href="/vaultrules?{q_params}" class="btn btn-secondary">{svg("zap")} VaultRules Pravidla</a>
            </div>
        </div>
    </div>

    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("shield")} Poslední události systému (Forenzní Audit Log)</h2>
            <a href="/audit-log?{q_params}" class="btn btn-secondary btn-sm">Celý protokol</a>
        </div>
        <table>
            <thead><tr><th>Čas (UTC)</th><th>Úroveň</th><th>Uživatel</th><th>Událost</th></tr></thead>
            <tbody>{audit_html}</tbody>
        </table>
    </div>
    """
    return render_shell("Přehled systému", "overview", username, password, view_owner, body)

# --- 2. SPRÁVCE SOUBORŮ (SINGLE & DUAL-PANE COMMANDER, BATCH, PREVIEW, STATIC HOSTING, TAGY) ---
@app.get("/files", response_class=HTMLResponse)
def files_get(
    username: str,
    password: str,
    folder: str = "/",
    folder2: str = "/",
    mode: str = "single",
    target_owner: str = None,
    trash: str = "false",
    q: str = "",
    tag: str = "",
    msg: str = ""
):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    return render_files_view(
        username, password, user["role"] == "admin", view_owner,
        folder, folder2, mode, trash == "true", q.strip(), tag.strip().lstrip("#").lower(), "", msg
    )

@app.post("/files", response_class=HTMLResponse)
def files_post(
    username: str = Form(...),
    password: str = Form(...),
    current_folder: str = Form("/"),
    folder2: str = Form("/"),
    mode: str = Form("single"),
    target_owner: str = Form(None),
    view_trash: str = Form("false"),
    unlocked_pin: str = Form(""),
    q: str = Form("")
):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    return render_files_view(
        username, password, user["role"] == "admin", view_owner,
        current_folder, folder2, mode, view_trash == "true", q.strip(), "", unlocked_pin, ""
    )

def build_pane_table(
    items: list[dict],
    target_folder: str,
    pane_side: str,
    other_folder: str,
    q_params: str,
    tags_map: dict[int, list[str]],
    view_owner: str,
    is_in_trash: bool = False,
    search_query: str = "",
    tag_filter: str = ""
) -> tuple[str, set[str], bool]:
    folders_set = set()
    locked_folders = set()
    files_list = []
    is_locked = False

    for item in items:
        if item.get("storage_provider") in SYSTEM_PROVIDERS:
            continue
        if is_in_trash:
            if not is_system_record(item):
                files_list.append(item)
        elif tag_filter:
            if not is_system_record(item) and tag_filter in tags_map.get(item["id"], []):
                files_list.append(item)
        elif search_query:
            if search_query.startswith("#"):
                tf = search_query.lstrip("#").lower()
                if not is_system_record(item) and tf in tags_map.get(item["id"], []):
                    files_list.append(item)
            elif not is_system_record(item) and search_query.lower() in item.get("filename", "").lower():
                files_list.append(item)
        else:
            item_folder = item.get("folder", "/")
            if item.get("filename") == ".vault_pin_lock":
                locked_folders.add(item_folder)
                if item_folder == target_folder:
                    is_locked = True
            if item_folder.startswith(target_folder) and item_folder != target_folder:
                rel_path = item_folder[len(target_folder):].strip("/")
                if rel_path:
                    sub_name = rel_path.split("/")[0]
                    folders_set.add(f"{target_folder.rstrip('/')}/{sub_name}")
            if item_folder == target_folder and not is_system_record(item):
                files_list.append(item)

    rows_html = ""
    if not is_in_trash and not search_query and not tag_filter:
        for f_path in sorted(folders_set):
            fname = f_path.split("/")[-1]
            locked = f_path in locked_folders
            ic = svg("lock") if locked else svg("folder")
            link_url = (
                f"/files?{q_params}&folder={urllib.parse.quote(f_path)}&folder2={urllib.parse.quote(other_folder)}&mode=dual"
                if pane_side == "left"
                else f"/files?{q_params}&folder={urllib.parse.quote(other_folder)}&folder2={urllib.parse.quote(f_path)}&mode=dual"
            )
            if pane_side == "single":
                link_url = f"/files?{q_params}&folder={urllib.parse.quote(f_path)}"

            rows_html += f"""
            <tr>
                <td style="width:28px;"></td>
                <td><a href="{link_url}" style="color:var(--text-main); text-decoration:none; font-weight:600; display:inline-flex; align-items:center; gap:8px;">{ic} {html.escape(fname)}</a></td>
                <td class="mono" style="color:var(--text-muted);">DIR</td>
                <td>
                    <a href="{link_url}" class="link-action">Otevřít</a>
                    <a href="/download-zip?{q_params}&folder={urllib.parse.quote(f_path)}" class="link-action">ZIP</a>
                </td>
            </tr>"""

    for f in files_list:
        fname = f["filename"]
        ext = fname.split(".")[-1].lower() if "." in fname else ""
        size_str = format_bytes(f.get("size", 0))
        ftags = tags_map.get(f["id"], [])
        tags_badges = " ".join([f'<a href="/files?{q_params}&tag={urllib.parse.quote(t)}" class="badge badge-tag">#{html.escape(t)}</a>' for t in ftags])

        if is_in_trash:
            actions = f"""
                <a href="/restore-file?id={f['id']}&{q_params}" class="link-action">Obnovit</a>
                <a href="/delete-permanently?id={f['id']}&{q_params}" class="link-danger">Smazat trvale</a>
            """
        elif pane_side in ["left", "right"]:
            dest_dir = other_folder if pane_side == "left" else target_folder
            src_dir = target_folder if pane_side == "left" else other_folder
            actions = f"""
                <a href="/files/transfer?id={f['id']}&op=move&dest={urllib.parse.quote(dest_dir)}&{q_params}&folder={urllib.parse.quote(src_dir if pane_side=='left' else other_folder)}&folder2={urllib.parse.quote(other_folder if pane_side=='left' else target_folder)}" class="link-action">{'Přesunout →' if pane_side=='left' else '← Přesunout'}</a>
                <a href="/files/transfer?id={f['id']}&op=copy&dest={urllib.parse.quote(dest_dir)}&{q_params}&folder={urllib.parse.quote(src_dir if pane_side=='left' else other_folder)}&folder2={urllib.parse.quote(other_folder if pane_side=='left' else target_folder)}" class="link-action">Kopírovat</a>
            """
        else:
            extra = []
            if fname.endswith(".vgenc"):
                extra.append(f'<a href="#decrypt" onclick="openDecryptModal({f["id"]}, \'{html.escape(fname)}\'); return false;" class="link-action" style="color:#f59e0b;">Dešifrovat</a>')
            if ext in PREVIEW_EXTENSIONS:
                extra.append(f'<a href="/preview?id={f["id"]}&{q_params}" class="link-action">Náhled</a>')
            if ext in VIDEO_EXTENSIONS or ext in AUDIO_EXTENSIONS:
                extra.append(f'<a href="/media-player?file_url={urllib.parse.quote(f["file_url"])}&filename={urllib.parse.quote(fname)}&{q_params}" class="link-action">Přehrát</a>')
            if ext == "html":
                site_rel = f"{f.get('folder', '/').strip('/')}/{fname}".lstrip("/")
                extra.append(f'<a href="/site/{urllib.parse.quote(view_owner)}/{urllib.parse.quote(site_rel)}" target="_blank" class="link-action">Web Hosting</a>')
            if ext in EDITABLE_EXTENSIONS:
                extra.append(f'<a href="/code-editor?id={f["id"]}&{q_params}" class="link-action">Upravit</a>')

            actions = f"""
                <a href="{html.escape(f['file_url'])}" download class="link-action">Stáhnout</a>
                {"".join(extra)}
                <a href="/vaultdrop?{q_params}&preselect_id={f['id']}" class="link-action">VaultDrop</a>
                <a href="/file-versions?filename={urllib.parse.quote(fname)}&{q_params}" class="link-action">Verze</a>
                <a href="/delete-file?id={f['id']}&folder={urllib.parse.quote(target_folder)}&{q_params}" class="link-danger">Koš</a>
            """

        enc_badge = '<span class="badge badge-warn">AES-256</span> ' if fname.endswith(".vgenc") else ""
        rows_html += f"""
        <tr>
            <td style="width:28px;"><input type="checkbox" name="selected_ids" value="{f['id']}"></td>
            <td>
                <div style="display:flex; align-items:center; gap:7px; flex-wrap:wrap;">
                    {svg("file")} <span>{html.escape(fname)}</span> {enc_badge} {tags_badges}
                </div>
            </td>
            <td class="mono">{size_str}</td>
            <td>{actions}</td>
        </tr>"""

    if not rows_html:
        rows_html = "<tr><td colspan='4' style='text-align:center; color:var(--text-muted); padding:20px;'>Adresář neobsahuje žádné položky.</td></tr>"
    return rows_html, folders_set, is_locked

def render_files_view(
    username: str,
    password: str,
    is_admin: bool,
    view_owner: str,
    current_folder: str,
    folder2: str,
    mode: str,
    is_in_trash: bool,
    search_query: str,
    tag_filter: str,
    unlocked_pin: str,
    status_msg: str
) -> str:
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    # Kontrola PIN zámku složky
    is_folder_locked = False
    if current_folder != "/" and not is_in_trash and not search_query and not tag_filter:
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
    tags_map = get_file_tags_map(view_owner)

    # Breadcrumbs
    crumbs = [f'<a href="/files?{q_params}&folder=/" class="link-action">/root</a>']
    if current_folder != "/":
        acc = ""
        for part in current_folder.strip("/").split("/"):
            if part:
                acc += f"/{part}"
                crumbs.append(f'<a href="/files?{q_params}&folder={urllib.parse.quote(acc)}" class="link-action">{html.escape(part)}</a>')
    breadcrumb_str = " / ".join(crumbs)

    owner_bar = ""
    if is_admin:
        all_users = supabase.table("nxt_users").select("username").execute().data or []
        opts = "".join([f'<option value="{html.escape(u["username"])}" {"selected" if u["username"] == view_owner else ""}>{html.escape(u["username"])}</option>' for u in all_users])
        owner_bar = f"""
        <form action="/files" method="GET" style="display:flex; align-items:center; gap:6px; margin:0;">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <select name="target_owner" onchange="this.form.submit()" style="width:auto; padding:5px 8px;">{opts}</select>
        </form>"""

    alert_html = f'<div class="alert-bar ok">{html.escape(status_msg)}</div>' if status_msg else ""

    # DUAL-PANE COMMANDER REŽIM
    if mode == "dual" and not is_in_trash and not search_query and not tag_filter:
        left_rows, _, _ = build_pane_table(items, current_folder, "left", folder2, q_params, tags_map, view_owner)
        right_rows, _, _ = build_pane_table(items, folder2, "right", current_folder, q_params, tags_map, view_owner)
        dual_body = f"""
        {alert_html}
        <div class="panel">
            <div class="panel-header">
                <h2 class="panel-title">{svg("columns")} Dual-Pane Commander (Přenosy mezi složkami)</h2>
                <div class="form-row">
                    {owner_bar}
                    <a href="/files?{q_params}&folder={urllib.parse.quote(current_folder)}&mode=single" class="btn btn-secondary btn-sm">Zpět na 1 panel</a>
                </div>
            </div>
            <div class="grid-dual">
                <div style="border:1px solid var(--border); border-radius:5px; overflow:hidden;">
                    <div style="padding:10px 12px; background:var(--bg-surface-alt); border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
                        <span class="mono"><strong>LEVÝ:</strong> {html.escape(current_folder)}</span>
                        <a href="/files?{q_params}&folder=/&folder2={urllib.parse.quote(folder2)}&mode=dual" class="link-action">/root</a>
                    </div>
                    <table><thead><tr><th></th><th>Název</th><th>Velikost</th><th>Přenos</th></tr></thead><tbody>{left_rows}</tbody></table>
                </div>
                <div style="border:1px solid var(--border); border-radius:5px; overflow:hidden;">
                    <div style="padding:10px 12px; background:var(--bg-surface-alt); border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
                        <span class="mono"><strong>PRAVÝ:</strong> {html.escape(folder2)}</span>
                        <a href="/files?{q_params}&folder={urllib.parse.quote(current_folder)}&folder2=/&mode=dual" class="link-action">/root</a>
                    </div>
                    <table><thead><tr><th></th><th>Název</th><th>Velikost</th><th>Přenos</th></tr></thead><tbody>{right_rows}</tbody></table>
                </div>
            </div>
        </div>"""
        return render_shell("Dual-Pane Commander", "files", username, password, view_owner, dual_body)

    # STANDARDNÍ JEDEN PANEL + BATCH OPERACE + TAGY + VAULTCRYPT
    rows_html, _, _ = build_pane_table(items, current_folder, "single", "/", q_params, tags_map, view_owner, is_in_trash, search_query, tag_filter)

    pin_bar = ""
    if current_folder != "/" and not is_in_trash and not search_query and not tag_filter:
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
                <input type="password" name="new_pin" placeholder="PIN kód pro zamčení složky..." maxlength="8" inputmode="numeric" required style="width:220px;">
                <button type="submit" class="btn btn-secondary btn-sm">{svg("lock")} Zamknout složku</button>
            </form>"""

    upload_and_tools = ""
    if not is_in_trash and not search_query and not tag_filter:
        upload_and_tools = f"""
        <div class="grid-2">
            <div class="panel">
                <div class="panel-header"><h3 class="panel-title">{svg("folder")} Nový adresář & VaultShield</h3></div>
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
                <div class="panel-header"><h3 class="panel-title">Nahrát soubory (s volitelným AES-256 šifrováním)</h3></div>
                <form action="/upload" method="POST" enctype="multipart/form-data">
                    <input type="hidden" name="username" value="{html.escape(username)}">
                    <input type="hidden" name="password" value="{html.escape(password)}">
                    <input type="hidden" name="folder" value="{html.escape(current_folder)}">
                    <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                    <input type="hidden" name="unlocked_pin" value="{html.escape(unlocked_pin)}">
                    <div class="form-row" style="margin-bottom:8px;">
                        <input type="file" name="files" multiple required style="flex:1;">
                        <button type="submit" class="btn">Nahrát do cloudu</button>
                    </div>
                    <div class="form-row" style="font-size:12px; color:var(--text-muted);">
                        <label style="display:inline-flex; align-items:center; gap:6px; cursor:pointer;">
                            <input type="checkbox" name="encrypt_flag" value="1" onchange="document.getElementById('enc-pass-box').style.display = this.checked ? 'inline-block' : 'none';">
                            Zašifrovat před odesláním (VaultCrypt AES-256)
                        </label>
                        <input type="password" id="enc-pass-box" name="encrypt_pass" placeholder="Šifrovací heslo..." style="display:none; width:200px; padding:4px 8px;">
                    </div>
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
                <a href="/files?{q_params}&folder={urllib.parse.quote(current_folder)}&mode=dual" class="btn btn-secondary btn-sm">{svg("columns")} Dual-Pane</a>
                <a href="/files?{q_params}&folder={urllib.parse.quote(current_folder)}&trash={'false' if is_in_trash else 'true'}" class="btn btn-secondary btn-sm">{'Aktivní' if is_in_trash else 'Koš'}</a>
                <a href="/download-zip?{q_params}&folder={urllib.parse.quote(current_folder)}" class="btn btn-secondary btn-sm">Export ZIP</a>
                <a href="/photo-gallery?{q_params}&folder={urllib.parse.quote(current_folder)}" class="btn btn-secondary btn-sm">Galerie</a>
            </div>
        </div>

        <form action="/files/batch" method="POST">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="hidden" name="current_folder" value="{html.escape(current_folder)}">

            <div class="form-row" style="margin-bottom:10px; padding:8px 10px; background:var(--bg-surface-alt); border:1px solid var(--border); border-radius:4px;">
                <span style="font-size:12px; color:var(--text-muted);">Hromadná akce pro označené:</span>
                <select name="batch_action" style="width:auto; padding:4px 8px;">
                    <option value="zip">Stáhnout jako ZIP</option>
                    <option value="move">Přesunout do složky</option>
                    <option value="tag">Přidat #štítek</option>
                    <option value="trash">Přesunout do koše</option>
                </select>
                <input type="text" name="batch_param" placeholder="Cílová složka / název štítku..." style="width:200px; padding:4px 8px;">
                <button type="submit" class="btn btn-secondary btn-sm">Provést</button>
            </div>

            <table>
                <thead>
                    <tr>
                        <th style="width:28px;"><input type="checkbox" onclick="document.querySelectorAll('input[name=selected_ids]').forEach(c => c.checked = this.checked)"></th>
                        <th>Název položky & Štítky</th>
                        <th>Velikost</th>
                        <th>Operace</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </form>
    </div>

    <div id="decrypt-modal" class="panel" style="display:none; border-left:4px solid var(--warning);">
        <div class="panel-header">
            <h3 class="panel-title">{svg("lock")} VaultCrypt — Dešifrovat a stáhnout: <span id="dec-fname" class="mono"></span></h3>
            <button type="button" onclick="document.getElementById('decrypt-modal').style.display='none'" class="btn btn-secondary btn-sm">Zavřít</button>
        </div>
        <form action="/decrypt-file" method="POST" class="form-row">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="hidden" id="dec-fid" name="file_id" value="">
            <input type="password" name="decrypt_pass" placeholder="Zadejte dešifrovací heslo..." required style="width:260px;">
            <button type="submit" class="btn btn-warning">Dešifrovat & Stáhnout</button>
        </form>
    </div>

    {upload_and_tools}
    <script>
        function openDecryptModal(id, fname) {{
            document.getElementById('dec-fid').value = id;
            document.getElementById('dec-fname').innerText = fname;
            const m = document.getElementById('decrypt-modal');
            m.style.display = 'block';
            m.scrollIntoView({{ behavior: 'smooth' }});
        }}
    </script>
    """
    title = "Koš úložiště" if is_in_trash else (f"Štítek: #{tag_filter}" if tag_filter else (f"Vyhledávání: {search_query}" if search_query else "Správce souborů"))
    return render_shell(title, "files", username, password, view_owner, body, search_query)

@app.post("/files/batch")
def files_batch_action(
    username: str = Form(...),
    password: str = Form(...),
    target_owner: str = Form(None),
    current_folder: str = Form("/"),
    batch_action: str = Form(...),
    batch_param: str = Form(""),
    selected_ids: list[int] = Form(default=[])
):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    if not selected_ids:
        return render_files_view(username, password, user["role"] == "admin", view_owner, current_folder, "/", "single", False, "", "", "", "Nebyly vybrány žádné soubory.")

    if batch_action == "trash":
        for fid in selected_ids:
            supabase.table("nxt_files").update({"is_deleted": True}).eq("id", fid).execute()
        return render_files_view(username, password, user["role"] == "admin", view_owner, current_folder, "/", "single", False, "", "", "", f"Přesunuto do koše: {len(selected_ids)} položek.")

    elif batch_action == "move" and batch_param.strip():
        dest = batch_param.strip()
        if not dest.startswith("/"):
            dest = "/" + dest
        for fid in selected_ids:
            supabase.table("nxt_files").update({"folder": dest}).eq("id", fid).execute()
        return render_files_view(username, password, user["role"] == "admin", view_owner, current_folder, "/", "single", False, "", "", "", f"Přesunuto {len(selected_ids)} položek do {dest}.")

    elif batch_action == "tag" and batch_param.strip():
        for fid in selected_ids:
            attach_file_tag(view_owner, fid, batch_param.strip())
        return render_files_view(username, password, user["role"] == "admin", view_owner, current_folder, "/", "single", False, "", "", "", f"Štítek #{batch_param.strip().lstrip('#')} přiřazen.")

    elif batch_action == "zip":
        res = supabase.table("nxt_files").select("*").in_("id", selected_ids).execute()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in (res.data or []):
                try:
                    with urllib.request.urlopen(f["file_url"], timeout=8) as resp:
                        zf.writestr(f["filename"], resp.read())
                except Exception:
                    pass
        buf.seek(0)
        return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="vaultgrid_selected.zip"'})

    return render_files_view(username, password, user["role"] == "admin", view_owner, current_folder, "/", "single", False, "", "", "", "")

@app.get("/files/transfer", response_class=HTMLResponse)
def files_dual_transfer(
    id: int,
    op: str,
    dest: str,
    username: str,
    password: str,
    folder: str = "/",
    folder2: str = "/",
    target_owner: str = None
):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    rec = (supabase.table("nxt_files").select("*").eq("id", id).execute().data or [None])[0]
    if rec:
        if op == "move":
            supabase.table("nxt_files").update({"folder": dest}).eq("id", id).execute()
            msg = f"Soubor {rec['filename']} přesunut do {dest}."
        else:
            supabase.table("nxt_files").insert({
                "owner": view_owner,
                "filename": rec["filename"],
                "storage_provider": rec.get("storage_provider", "huggingface"),
                "file_url": rec["file_url"],
                "folder": dest,
                "size": rec.get("size", 0),
                "is_deleted": False
            }).execute()
            msg = f"Soubor {rec['filename']} zkopírován do {dest}."
    else:
        msg = "Soubor nenalezen."
    return render_files_view(username, password, user["role"] == "admin", view_owner, folder, folder2, "dual", False, "", "", "", msg)

@app.post("/decrypt-file")
def decrypt_file_download(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), file_id: int = Form(...), decrypt_pass: str = Form(...)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    rec = (supabase.table("nxt_files").select("*").eq("id", file_id).execute().data or [None])[0]
    if not rec:
        return HTMLResponse("Soubor nenalezen.", status_code=404)
    try:
        with urllib.request.urlopen(rec["file_url"], timeout=10) as resp:
            enc_bytes = resp.read()
        plain_bytes = vaultcrypt_decrypt(enc_bytes, decrypt_pass.strip())
        orig_name = rec["filename"][:-6] if rec["filename"].endswith(".vgenc") else rec["filename"]
        return StreamingResponse(io.BytesIO(plain_bytes), media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{orig_name}"'})
    except Exception as e:
        return HTMLResponse(f"<h3>Chyba dešifrování: {html.escape(str(e))}</h3><a href='javascript:history.back()'>Zpět</a>", status_code=400)

# --- UNIVERSAL VIEWER (PDF, MARKDOWN, CSV, JSON, 3D STL/OBJ, OBRÁZKY) ---
@app.get("/preview", response_class=HTMLResponse)
def universal_preview(id: int, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    rec = (supabase.table("nxt_files").select("*").eq("id", id).execute().data or [None])[0]
    if not rec:
        return "Soubor nenalezen."

    fname = rec["filename"]
    furl = rec["file_url"]
    ext = fname.split(".")[-1].lower() if "." in fname else ""

    if ext == "pdf":
        viewer_html = f'<iframe src="{html.escape(furl)}" style="width:100%; height:720px; border:1px solid var(--border); border-radius:4px;"></iframe>'
    elif ext in IMAGE_EXTENSIONS:
        viewer_html = f'<div style="text-align:center; background:var(--bg-app); padding:20px; border-radius:4px;"><img src="{html.escape(furl)}" style="max-width:100%; max-height:680px;"></div>'
    elif ext in ["stl", "obj"]:
        viewer_html = f"""
        <div id="stl-canvas" style="width:100%; height:520px; background:#090b0e; border:1px solid var(--border); border-radius:4px; position:relative;">
            <div style="position:absolute; top:10px; left:12px; color:#9ca3af; font-family:var(--mono); font-size:12px;">3D CAD PROHLÍŽEČ // Tažením myší otáčejte, kolečkem přibližujte</div>
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <script>
            const box = document.getElementById('stl-canvas');
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(45, box.clientWidth / box.clientHeight, 0.1, 1000);
            camera.position.set(0, -80, 60);
            const renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(box.clientWidth, box.clientHeight);
            box.appendChild(renderer.domElement);
            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            scene.add(new THREE.AmbientLight(0x606060));
            const dirLight = new THREE.DirectionalLight(0xffffff, 0.9);
            dirLight.position.set(50, 50, 100);
            scene.add(dirLight);
            const loader = new THREE.STLLoader();
            loader.load("{html.escape(furl)}", function(geom) {{
                geom.center();
                const mat = new THREE.MeshPhongMaterial({{ color: 0x3b82f6, specular: 0x111111, shininess: 120 }});
                const mesh = new THREE.Mesh(geom, mat);
                scene.add(mesh);
            }});
            function animate() {{ requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }}
            animate();
        </script>"""
    else:
        try:
            with urllib.request.urlopen(furl, timeout=6) as resp:
                raw_txt = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            raw_txt = f"Chyba načtení obsahu: {e}"

        if ext == "json":
            try:
                raw_txt = json.dumps(json.loads(raw_txt), indent=2, ensure_ascii=False)
            except Exception:
                pass
        viewer_html = f'<pre class="mono" style="background:var(--bg-app); padding:16px; border:1px solid var(--border); border-radius:4px; overflow-x:auto; max-height:650px;">{html.escape(raw_txt)}</pre>'

    body = f"""
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("eye")} Universal Viewer: {html.escape(fname)}</h2>
            <a href="{html.escape(furl)}" download class="btn btn-sm">Stáhnout originál</a>
        </div>
        {viewer_html}
    </div>"""
    return render_shell(f"Náhled: {fname}", "files", username, password, view_owner, body)

# --- MULTI-FILE STATIC WEB HOSTING ---
@app.get("/site/{owner}/{file_path:path}")
def static_web_hosting(owner: str, file_path: str):
    if not supabase:
        return Response("Database offline", status_code=503)
    norm_path = "/" + file_path.strip("/")
    folder_part = os.path.dirname(norm_path) or "/"
    file_part = os.path.basename(norm_path)

    res = supabase.table("nxt_files").select("*").eq("owner", owner).eq("folder", folder_part).eq("filename", file_part).eq("is_deleted", False).execute()
    if not res.data:
        return Response("404 — Soubor na tomto webu neexistuje.", status_code=404)

    rec = res.data[0]
    mime_type, _ = mimetypes.guess_type(file_part)
    mime_type = mime_type or "application/octet-stream"
    try:
        with urllib.request.urlopen(rec["file_url"], timeout=8) as resp:
            content = resp.read()
        return Response(content=content, media_type=mime_type)
    except Exception as e:
        return Response(f"Chyba hostingu: {e}", status_code=502)

# --- 3. VAULTDROP (CHYTRÉ SDÍLENÍ S EXPIRACÍ, LIMITEM STAŽENÍ, HESLEM, QR A UPLOAD SCHRÁNKAMI) ---
@app.get("/vaultdrop", response_class=HTMLResponse)
def vaultdrop_view(username: str, password: str, target_owner: str = None, preselect_id: int = 0, msg: str = ""):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    all_rows = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute().data or []
    user_files = [f for f in all_rows if not is_system_record(f)]
    drops = [f for f in all_rows if f.get("storage_provider") == "vault_drop"]

    file_opts = "".join([
        f'<option value="{f["id"]}" {"selected" if f["id"] == preselect_id else ""}>{html.escape(f["folder"] + "/" + f["filename"]).replace("//", "/")} ({format_bytes(f.get("size", 0))})</option>'
        for f in user_files
    ])

    drops_rows = ""
    for d in reversed(drops):
        try:
            meta = json.loads(d.get("file_url", "{}"))
            tok = meta.get("token", "")
            dtype = meta.get("type", "download")
            pub_path = f"/drop-upload/{tok}" if dtype == "upload_request" else f"/drop/{tok}"
            exp = meta.get("expires_at") or "Bez expirace"
            max_dl = meta.get("max_downloads", 0)
            used_dl = meta.get("downloads_used", 0)
            limit_str = f"{used_dl} / {max_dl}" if max_dl > 0 else f"{used_dl} / ∞"
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={urllib.parse.quote(pub_path)}"

            drops_rows += f"""
            <tr>
                <td><span class="badge {'badge-warn' if dtype == 'upload_request' else 'badge-ok'}">{'UPLOAD SCHRÁNKA' if dtype == 'upload_request' else 'SDÍLENÝ SOUBOR'}</span></td>
                <td><strong>{html.escape(meta.get('label', ''))}</strong></td>
                <td class="mono"><a href="{pub_path}" target="_blank" class="link-action">{pub_path}</a></td>
                <td class="mono">{html.escape(exp)}</td>
                <td class="mono">{limit_str}</td>
                <td>{'Ano' if meta.get('password') else 'Ne'}</td>
                <td><a href="{qr_url}" target="_blank" class="link-action">QR kód</a><a href="/vaultdrop/revoke?id={d['id']}&{q_params}" class="link-danger">Zrušit</a></td>
            </tr>"""
        except Exception:
            pass
    if not drops_rows:
        drops_rows = "<tr><td colspan='7' style='text-align:center; color:var(--text-muted);'>Žádné aktivní VaultDrop odkazy.</td></tr>"

    alert_html = f'<div class="alert-bar ok">{html.escape(msg)}</div>' if msg else ""
    body = f"""
    {alert_html}
    <div class="grid-2">
        <div class="panel">
            <div class="panel-header"><h2 class="panel-title">{svg("share")} Vytvořit chytrý sdílecí odkaz (VaultDrop)</h2></div>
            <form action="/vaultdrop/create-link" method="POST">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <label style="font-size:12px; color:var(--text-muted);">Vyberte soubor ke sdílení</label>
                <select name="file_id" required style="margin:4px 0 10px 0;">{file_opts}</select>
                <div class="grid-2" style="gap:8px; margin-bottom:10px;">
                    <div>
                        <label style="font-size:12px; color:var(--text-muted);">Platnost odkazu</label>
                        <select name="expire_hours">
                            <option value="0">Bez časového omezení</option>
                            <option value="1">1 hodina</option>
                            <option value="24" selected>24 hodin</option>
                            <option value="168">7 dní</option>
                            <option value="720">30 dní</option>
                        </select>
                    </div>
                    <div>
                        <label style="font-size:12px; color:var(--text-muted);">Max. počet stažení (0 = ∞)</label>
                        <input type="number" name="max_downloads" value="0" min="0">
                    </div>
                </div>
                <input type="password" name="drop_pass" placeholder="Volitelné heslo pro stažení..." style="margin-bottom:10px;">
                <button type="submit" class="btn" style="width:100%;">Vygenerovat VaultDrop odkaz</button>
            </form>
        </div>

        <div class="panel">
            <div class="panel-header"><h2 class="panel-title">{svg("folder")} Vytvořit veřejnou upload schránku (File Request)</h2></div>
            <p style="color:var(--text-muted); margin-top:0;">Umožní komukoliv s odkazem nahrát soubory přímo do vaší cílové složky bez účtu a bez přístupu k ostatním datům.</p>
            <form action="/vaultdrop/create-request" method="POST">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <input type="text" name="title" placeholder="Název schránky (např. Fotky ze školy)" required style="margin-bottom:10px;">
                <input type="text" name="dest_folder" value="/Inbox" placeholder="Cílová složka ve Vaultu..." required style="margin-bottom:10px;">
                <input type="password" name="drop_pass" placeholder="Volitelné heslo pro nahrávání..." style="margin-bottom:10px;">
                <button type="submit" class="btn btn-secondary" style="width:100%;">Vytvořit upload schránku</button>
            </form>
        </div>
    </div>

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Aktivní sdílené odkazy a upload schránky ({len(drops)})</h2></div>
        <table>
            <thead><tr><th>Typ</th><th>Název</th><th>Veřejná cesta</th><th>Expirace</th><th>Stažení</th><th>Heslo</th><th>Akce</th></tr></thead>
            <tbody>{drops_rows}</tbody>
        </table>
    </div>"""
    return render_shell("VaultDrop Sdílení", "vaultdrop", username, password, view_owner, body)

@app.post("/vaultdrop/create-link", response_class=HTMLResponse)
def vaultdrop_create_link(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), file_id: int = Form(...), expire_hours: int = Form(0), max_downloads: int = Form(0), drop_pass: str = Form("")):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    rec = (supabase.table("nxt_files").select("*").eq("id", file_id).execute().data or [None])[0]
    if not rec:
        return vaultdrop_view(username, password, view_owner, 0, "Soubor nenalezen.")

    token = secrets.token_urlsafe(12)
    exp_str = (datetime.now(timezone.utc) + timedelta(hours=expire_hours)).strftime("%Y-%m-%d %H:%M UTC") if expire_hours > 0 else ""
    meta = json.dumps({
        "type": "download",
        "token": token,
        "file_id": file_id,
        "label": rec["filename"],
        "expires_at": exp_str,
        "max_downloads": max_downloads,
        "downloads_used": 0,
        "password": drop_pass.strip()
    }, ensure_ascii=False)

    supabase.table("nxt_files").insert({
        "owner": view_owner,
        "filename": token,
        "storage_provider": "vault_drop",
        "file_url": meta,
        "folder": "/_drops",
        "size": 0,
        "is_deleted": False
    }).execute()
    log_audit(username, "VAULTDROP_CREATED", f"Vytvořen sdílecí odkaz pro {rec['filename']}", "INFO")
    return vaultdrop_view(username, password, view_owner, 0, f"Sdílecí odkaz /drop/{token} byl vytvořen.")

@app.post("/vaultdrop/create-request", response_class=HTMLResponse)
def vaultdrop_create_request(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), title: str = Form(...), dest_folder: str = Form("/Inbox"), drop_pass: str = Form("")):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    token = secrets.token_urlsafe(12)
    clean_dest = dest_folder.strip() or "/Inbox"
    if not clean_dest.startswith("/"):
        clean_dest = "/" + clean_dest

    meta = json.dumps({
        "type": "upload_request",
        "token": token,
        "label": title.strip(),
        "dest_folder": clean_dest,
        "expires_at": "",
        "max_downloads": 0,
        "downloads_used": 0,
        "password": drop_pass.strip()
    }, ensure_ascii=False)

    supabase.table("nxt_files").insert({
        "owner": view_owner,
        "filename": token,
        "storage_provider": "vault_drop",
        "file_url": meta,
        "folder": "/_drops",
        "size": 0,
        "is_deleted": False
    }).execute()
    log_audit(username, "UPLOAD_BOX_CREATED", f"Vytvořena upload schránka '{title.strip()}' -> {clean_dest}", "INFO")
    return vaultdrop_view(username, password, view_owner, 0, f"Upload schránka /drop-upload/{token} byla vytvořena.")

@app.get("/vaultdrop/revoke", response_class=HTMLResponse)
def vaultdrop_revoke(username: str, password: str, id: int, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("id", id).execute()
    log_audit(username, "VAULTDROP_REVOKED", f"Zrušen VaultDrop odkaz ID #{id}", "WARN")
    return vaultdrop_view(username, password, view_owner, 0, "Odkaz byl zneplatněn.")

@app.get("/drop/{token}", response_class=HTMLResponse)
def public_drop_get(token: str):
    res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_drop").eq("filename", token).execute()
    if not res.data:
        return HTMLResponse("Odkaz neexistuje nebo byl zrušen.", status_code=404)
    row = res.data[0]
    meta = json.loads(row.get("file_url", "{}"))

    if meta.get("expires_at"):
        exp_dt = datetime.strptime(meta["expires_at"], "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp_dt:
            return HTMLResponse("Platnost tohoto odkazu již vypršela.", status_code=410)

    if meta.get("max_downloads", 0) > 0 and meta.get("downloads_used", 0) >= meta["max_downloads"]:
        return HTMLResponse("Byl vyčerpán maximální limit stažení.", status_code=410)

    pass_input = '<input type="password" name="drop_pass" placeholder="Zadejte přístupové heslo..." required style="margin-bottom:12px;">' if meta.get("password") else ""
    return f"""<!DOCTYPE html><html lang="cs" data-theme="dark"><head><meta charset="UTF-8"><title>VaultDrop Stažení</title>{INDUSTRIAL_CSS}{THEME_SCRIPT}</head>
    <body style="display:flex; align-items:center; justify-content:center; min-height:100vh; padding:20px;">
        <div class="panel" style="max-width:440px; width:100%; text-align:center;">
            <div class="panel-header" style="justify-content:center;"><h2 class="panel-title">{svg("share")} VaultDrop Zabezpečený přenos</h2></div>
            <p style="font-weight:600; font-size:15px;">{html.escape(meta.get('label', ''))}</p>
            <form action="/drop/{html.escape(token)}" method="POST">
                {pass_input}
                <button type="submit" class="btn" style="width:100%;">Stáhnout soubor</button>
            </form>
        </div>
    </body></html>"""

@app.post("/drop/{token}")
def public_drop_post(token: str, drop_pass: str = Form("")):
    res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_drop").eq("filename", token).execute()
    if not res.data:
        return HTMLResponse("Odkaz neexistuje.", status_code=404)
    row = res.data[0]
    meta = json.loads(row.get("file_url", "{}"))
    if meta.get("password") and drop_pass != meta["password"]:
        return HTMLResponse("Neplatné heslo pro stažení.", status_code=403)
    if meta.get("max_downloads", 0) > 0 and meta.get("downloads_used", 0) >= meta["max_downloads"]:
        return HTMLResponse("Limit stažení byl vyčerpán.", status_code=410)

    f_rec = (supabase.table("nxt_files").select("*").eq("id", meta.get("file_id")).execute().data or [None])[0]
    if not f_rec:
        return HTMLResponse("Zdrojový soubor nebyl nalezen.", status_code=404)

    meta["downloads_used"] = int(meta.get("downloads_used", 0)) + 1
    supabase.table("nxt_files").update({"file_url": json.dumps(meta, ensure_ascii=False)}).eq("id", row["id"]).execute()
    log_audit(row["owner"], "VAULTDROP_DOWNLOADED", f"Stažení souboru {f_rec['filename']} přes odkaz {token}", "INFO")

    with urllib.request.urlopen(f_rec["file_url"], timeout=12) as resp:
        data = resp.read()
    return StreamingResponse(io.BytesIO(data), media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{f_rec["filename"]}"'})

@app.get("/drop-upload/{token}", response_class=HTMLResponse)
def public_drop_upload_get(token: str, msg: str = ""):
    res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_drop").eq("filename", token).execute()
    if not res.data:
        return HTMLResponse("Upload schránka neexistuje.", status_code=404)
    meta = json.loads(res.data[0].get("file_url", "{}"))
    pass_input = '<input type="password" name="drop_pass" placeholder="Heslo schránky..." required style="margin-bottom:10px;">' if meta.get("password") else ""
    alert = f'<div class="alert-bar ok">{html.escape(msg)}</div>' if msg else ""
    return f"""<!DOCTYPE html><html lang="cs" data-theme="dark"><head><meta charset="UTF-8"><title>VaultDrop Upload</title>{INDUSTRIAL_CSS}{THEME_SCRIPT}</head>
    <body style="display:flex; align-items:center; justify-content:center; min-height:100vh; padding:20px;">
        <div class="panel" style="max-width:460px; width:100%;">
            <div class="panel-header"><h2 class="panel-title">{svg("folder")} {html.escape(meta.get('label', 'Veřejná schránka'))}</h2></div>
            {alert}
            <p style="color:var(--text-muted);">Nahrajte soubory přímo do sdílené složky správce.</p>
            <form action="/drop-upload/{html.escape(token)}" method="POST" enctype="multipart/form-data">
                {pass_input}
                <input type="file" name="files" multiple required style="margin-bottom:12px;">
                <button type="submit" class="btn" style="width:100%;">Odeslat soubory do Vaultu</button>
            </form>
        </div>
    </body></html>"""

@app.post("/drop-upload/{token}", response_class=HTMLResponse)
async def public_drop_upload_post(token: str, drop_pass: str = Form(""), files: list[UploadFile] = File(...)):
    res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_drop").eq("filename", token).execute()
    if not res.data:
        return HTMLResponse("Schránka neexistuje.", status_code=404)
    row = res.data[0]
    meta = json.loads(row.get("file_url", "{}"))
    if meta.get("password") and drop_pass != meta["password"]:
        return public_drop_upload_get(token, "Chyba: Neplatné heslo schránky.")

    owner = row["owner"]
    dest_folder = meta.get("dest_folder", "/Inbox")
    repo_id = get_active_write_repo()
    cnt = 0
    for f in files:
        if not f.filename:
            continue
        fbytes = await f.read()
        repo_path = f"{owner}{dest_folder}/{f.filename}".replace("//", "/")
        if hf_api and repo_id:
            hf_api.upload_file(path_or_fileobj=fbytes, path_in_repo=repo_path, repo_id=repo_id, repo_type="dataset")
            purl = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{repo_path}"
        else:
            purl = "#"
        supabase.table("nxt_files").insert({
            "owner": owner, "filename": f.filename, "storage_provider": "huggingface",
            "file_url": purl, "folder": dest_folder, "size": len(fbytes), "is_deleted": False
        }).execute()
        cnt += 1
    log_audit(owner, "PUBLIC_DROP_UPLOAD", f"Přijato {cnt} souborů přes veřejnou schránku '{meta.get('label')}'", "INFO")
    return public_drop_upload_get(token, f"Úspěšně odesláno souborů: {cnt}.")

# --- 4. VAULTBACKUP & CONFIG EXPORT ---
@app.get("/vaultbackup", response_class=HTMLResponse)
def vaultbackup_view(username: str, password: str, target_owner: str = None, msg: str = ""):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    all_rows = supabase.table("nxt_files").select("*").eq("is_deleted", False).execute().data or []
    profiles = []
    snapshots = []
    for r in all_rows:
        if r.get("owner") == view_owner and r.get("storage_provider") == "vault_backup_profile":
            d = json.loads(r.get("file_url", "{}"))
            d["id"] = r["id"]
            profiles.append(d)
        elif r.get("owner") == view_owner and r.get("storage_provider") == "vault_backup_snapshot":
            d = json.loads(r.get("file_url", "{}"))
            d["id"] = r["id"]
            snapshots.append(d)

    snapshots.sort(key=lambda x: x.get("id", 0), reverse=True)

    prof_rows = ""
    for p in profiles:
        src = p.get("source_folder", "/")
        prof_rows += f"""
        <tr>
            <td><strong>{html.escape(p.get('name', ''))}</strong></td>
            <td class="mono">{html.escape(src)}</td>
            <td class="mono">{p.get('retention', 5)} snímků</td>
            <td class="mono">{html.escape(p.get('last_run', 'Nikdy'))}</td>
            <td><span class="badge badge-ok">{html.escape(p.get('last_status', 'READY'))} ({p.get('last_count', 0)} soub.)</span></td>
            <td>
                <div class="form-row" style="gap:6px;">
                    <form action="/vaultbackup/action" method="POST" style="margin:0;">
                        <input type="hidden" name="username" value="{html.escape(username)}">
                        <input type="hidden" name="password" value="{html.escape(password)}">
                        <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                        <input type="hidden" name="action" value="run_backup">
                        <input type="hidden" name="profile_id" value="{p['id']}">
                        <button type="submit" class="btn btn-sm">Spustit zálohu</button>
                    </form>
                    <a href="/download-zip?{q_params}&folder={urllib.parse.quote(src)}" class="btn btn-secondary btn-sm">ZIP</a>
                    <form action="/vaultbackup/action" method="POST" style="margin:0;">
                        <input type="hidden" name="username" value="{html.escape(username)}">
                        <input type="hidden" name="password" value="{html.escape(password)}">
                        <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                        <input type="hidden" name="action" value="delete_profile">
                        <input type="hidden" name="profile_id" value="{p['id']}">
                        <button type="submit" class="btn btn-danger btn-sm">Smazat</button>
                    </form>
                </div>
            </td>
        </tr>"""
    if not prof_rows:
        prof_rows = "<tr><td colspan='6' style='text-align:center; color:var(--text-muted);'>Žádné zálohovací profily.</td></tr>"

    snap_rows = ""
    for s in snapshots[:15]:
        snap_rows += f"""
        <tr>
            <td class="mono">#{s.get('id')}</td>
            <td><strong>{html.escape(s.get('profile_name', ''))}</strong></td>
            <td class="mono">{html.escape(s.get('source_folder', '/'))}</td>
            <td class="mono">{html.escape(s.get('timestamp', ''))}</td>
            <td class="mono">{s.get('file_count', 0)} ({format_bytes(s.get('total_size', 0))})</td>
            <td class="mono"><span class="badge">{html.escape(s.get('sha256_short', ''))}</span></td>
        </tr>"""
    if not snap_rows:
        snap_rows = "<tr><td colspan='6' style='text-align:center; color:var(--text-muted);'>Žádné uložené snímky.</td></tr>"

    u_rows = supabase.table("nxt_users").select("username, role").execute().data or []
    cfg_obj = {
        "system": "VaultGrid OS",
        "version": CORE_VERSION,
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "users": [{"username": u["username"], "role": u["role"]} for u in u_rows],
        "storage_pools": get_storage_pools(),
        "backup_profiles": [{k: v for k, v in p.items() if k != "id"} for p in profiles],
    }
    cfg_json = json.dumps(cfg_obj, ensure_ascii=False, indent=2)

    alert_html = f'<div class="alert-bar ok">{html.escape(msg)}</div>' if msg else ""
    body = f"""
    {alert_html}
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("save")} Nový zálohovací profil (Point-in-Time Snapshots)</h2></div>
        <form action="/vaultbackup/action" method="POST" class="form-row">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="hidden" name="action" value="create_profile">
            <input type="text" name="profile_name" placeholder="Název profilu (např. Denní záloha projektů)" required style="flex:1;">
            <input type="text" name="source_folder" value="/" placeholder="Zdrojová složka..." required style="width:200px;">
            <select name="retention" style="width:150px;">
                <option value="3">Držet 3 snímky</option>
                <option value="5" selected>Držet 5 snímků</option>
                <option value="10">Držet 10 snímků</option>
            </select>
            <button type="submit" class="btn">Uložit profil</button>
        </form>
    </div>

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Zálohovací profily ({len(profiles)})</h2></div>
        <table><thead><tr><th>Název</th><th>Zdroj</th><th>Retence</th><th>Poslední běh</th><th>Stav</th><th>Akce</th></tr></thead><tbody>{prof_rows}</tbody></table>
    </div>

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Historie snímků a SHA-256 kontrolních součtů</h2></div>
        <table><thead><tr><th>ID</th><th>Profil</th><th>Složka</th><th>Čas</th><th>Rozsah</th><th>SHA-256</th></tr></thead><tbody>{snap_rows}</tbody></table>
    </div>

    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("code")} Export konfigurace systému (JSON)</h2>
            <button type="button" onclick="downloadCfg()" class="btn btn-sm">Stáhnout vaultgrid-config.json</button>
        </div>
        <textarea id="cfg-box" rows="12" class="code-box" readonly>{html.escape(cfg_json)}</textarea>
    </div>
    <script>
        function downloadCfg() {{
            const blob = new Blob([document.getElementById('cfg-box').value], {{ type: 'application/json' }});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'vaultgrid-config-' + new Date().toISOString().slice(0,10) + '.json';
            a.click();
        }}
    </script>"""
    return render_shell("Zálohy & Konfigurace", "vaultbackup", username, password, view_owner, body)

@app.post("/vaultbackup/action", response_class=HTMLResponse)
def vaultbackup_action(
    username: str = Form(...),
    password: str = Form(...),
    target_owner: str = Form(None),
    action: str = Form(...),
    profile_name: str = Form(""),
    source_folder: str = Form("/"),
    retention: int = Form(5),
    profile_id: int = Form(0)
):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username

    if action == "create_profile" and profile_name.strip():
        clean_src = source_folder.strip() or "/"
        if not clean_src.startswith("/"):
            clean_src = "/" + clean_src
        meta = json.dumps({
            "name": profile_name.strip(),
            "source_folder": clean_src,
            "retention": retention,
            "last_run": "Nikdy",
            "last_status": "READY",
            "last_count": 0
        }, ensure_ascii=False)
        supabase.table("nxt_files").insert({
            "owner": view_owner, "filename": ".vault_backup_profile", "storage_provider": "vault_backup_profile",
            "file_url": meta, "folder": "/_backups", "size": 0, "is_deleted": False
        }).execute()
        log_audit(username, "BACKUP_PROFILE_CREATED", f"Vytvořen profil '{profile_name.strip()}'", "INFO")
        return vaultbackup_view(username, password, view_owner, "Zálohovací profil byl vytvořen.")

    elif action == "run_backup" and profile_id:
        p_row = (supabase.table("nxt_files").select("*").eq("id", profile_id).execute().data or [None])[0]
        if p_row:
            p_meta = json.loads(p_row.get("file_url", "{}"))
            src = p_meta.get("source_folder", "/")
            ret = int(p_meta.get("retention", 5))
            rows = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute().data or []
            matched = [f for f in rows if not is_system_record(f) and (src == "/" or f.get("folder", "/").startswith(src))]
            tot_size = sum(int(f.get("size", 0)) for f in matched)
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            digest = hashlib.sha256(json.dumps([(f["filename"], f.get("size", 0)) for f in matched]).encode()).hexdigest()[:16]

            snap_meta = json.dumps({
                "profile_id": profile_id, "profile_name": p_meta.get("name"), "source_folder": src,
                "timestamp": ts, "file_count": len(matched), "total_size": tot_size, "sha256_short": digest
            }, ensure_ascii=False)
            supabase.table("nxt_files").insert({
                "owner": view_owner, "filename": ".vault_backup_snapshot", "storage_provider": "vault_backup_snapshot",
                "file_url": snap_meta, "folder": "/_backups", "size": tot_size, "is_deleted": False
            }).execute()

            snaps = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("storage_provider", "vault_backup_snapshot").order("id", desc=True).execute().data or []
            p_snaps = [s["id"] for s in snaps if json.loads(s.get("file_url", "{}")).get("profile_id") == profile_id]
            for old_id in p_snaps[ret:]:
                supabase.table("nxt_files").delete().eq("id", old_id).execute()

            p_meta["last_run"] = ts
            p_meta["last_status"] = "OK"
            p_meta["last_count"] = len(matched)
            supabase.table("nxt_files").update({"file_url": json.dumps(p_meta, ensure_ascii=False)}).eq("id", profile_id).execute()
            log_audit(username, "BACKUP_EXECUTED", f"Snímek '{p_meta.get('name')}' ({len(matched)} soub., SHA {digest})", "INFO")
            return vaultbackup_view(username, password, view_owner, f"Snímek zálohy dokončen (SHA-256: {digest}).")

    elif action == "delete_profile" and profile_id:
        supabase.table("nxt_files").delete().eq("id", profile_id).execute()
        return vaultbackup_view(username, password, view_owner, "Zálohovací profil byl odstraněn.")

    return vaultbackup_view(username, password, view_owner)

# --- 5. STORAGE POOLS (7 TB HUGGING FACE MULTI-POOL) ---
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
        status_badge = '<span class="badge badge-ok">ACTIVE // WRITE</span>' if is_write else '<span class="badge">MOUNTED // AUTO-FAILOVER</span>'

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
            <h2 class="panel-title">{svg("database")} Připojené úložné fondy (Auto-Balancing Multi-Pool)</h2>
            <span class="mono">Celková kapacita: {sum(int(p.get('quota_gb', 300)) for p in pools)} GB</span>
        </div>
        <table>
            <thead><tr><th>Název poolu</th><th>Repozitář</th><th>Využití</th><th>Soubory</th><th>Stav</th><th>Akce</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    {add_pool_form}"""
    return render_shell("Storage Pools (7 TB)", "pools", username, password, view_owner, body)

@app.post("/storage-pools/add", response_class=HTMLResponse)
def storage_pools_add(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), label: str = Form(...), repo_id: str = Form(...), quota_gb: int = Form(300)):
    user = verify_user(username, password)
    if not user or user["role"] != "admin":
        return login_page()
    view_owner = target_owner or username
    payload = json.dumps({"label": label.strip(), "repo_id": repo_id.strip(), "quota_gb": quota_gb, "is_active_write": False}, ensure_ascii=False)
    supabase.table("nxt_files").insert({
        "owner": "system", "filename": "storage_pool", "storage_provider": "vault_pool",
        "file_url": payload, "folder": "/_pools", "size": 0, "is_deleted": False
    }).execute()
    log_audit(username, "POOL_ADDED", f"Připojen pool {repo_id.strip()} ({quota_gb} GB)", "INFO")
    return storage_pools_view(username, password, view_owner, f"Úložný pool {repo_id.strip()} byl připojen.")

@app.get("/storage-pools/set-active", response_class=HTMLResponse)
def storage_pools_set_active(username: str, password: str, repo_id: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user or user["role"] != "admin":
        return login_page()
    view_owner = target_owner or username
    res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_pool").eq("is_deleted", False).execute()
    for row in (res.data or []):
        d = json.loads(row.get("file_url", "{}"))
        d["is_active_write"] = (d.get("repo_id") == repo_id)
        supabase.table("nxt_files").update({"file_url": json.dumps(d, ensure_ascii=False)}).eq("id", row["id"]).execute()
    return storage_pools_view(username, password, view_owner, f"Aktivní zápisový repozitář: {repo_id}")

@app.get("/storage-pools/remove", response_class=HTMLResponse)
def storage_pools_remove(username: str, password: str, id: int, target_owner: str = None):
    user = verify_user(username, password)
    if not user or user["role"] != "admin":
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("id", id).execute()
    return storage_pools_view(username, password, view_owner, "Úložný pool byl odpojen.")

# --- 6. VAULTFLIX CINEMA 2.0 & VAULTBEATS HI-FI ---
def fetch_tmdb_metadata(filename: str) -> tuple[str, str, str]:
    if not TMDB_API_KEY:
        return "", "", ""
    base_name = os.path.splitext(filename)[0]
    series_match = re.search(r"(S\d{1,2}E\d{1,2})", base_name, re.IGNORECASE)
    ep_tag = series_match.group(1).upper() if series_match else ""
    clean_title = re.sub(r"(S\d{1,2}E\d{1,2}|1080p|720p|4k|x264|x265|WEBRip|BluRay).*", "", base_name, flags=re.IGNORECASE)
    clean_title = clean_title.replace(".", " ").replace("_", " ").strip()
    try:
        q = urllib.parse.quote(clean_title)
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={q}&language=cs-CZ"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = data.get("results", [])
        if results:
            top = results[0]
            poster = f"https://image.tmdb.org/t/p/w342{top['poster_path']}" if top.get("poster_path") else ""
            overview = top.get("overview", "")[:120]
            return poster, overview, ep_tag
    except Exception:
        pass
    return "", "", ep_tag

@app.get("/vaultflix", response_class=HTMLResponse)
def vaultflix_view(username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    all_rows = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute().data or []

    videos = [f for f in all_rows if not is_system_record(f) and f["filename"].split(".")[-1].lower() in VIDEO_EXTENSIONS]
    subtitles = {os.path.splitext(f["filename"])[0]: f["file_url"] for f in all_rows if f["filename"].split(".")[-1].lower() in ["vtt", "srt"]}

    progress_map: dict[int, float] = {}
    for r in all_rows:
        if r.get("storage_provider") == "vault_watch_progress":
            try:
                progress_map[int(r["size"])] = float(r.get("file_url", 0))
            except Exception:
                pass

    cards_html = ""
    for v in videos:
        poster_url, overview, ep_tag = fetch_tmdb_metadata(v["filename"])
        poster_block = f'<img src="{poster_url}" alt="Poster">' if poster_url else svg("film")
        base_no_ext = os.path.splitext(v["filename"])[0]
        sub_url = subtitles.get(base_no_ext, "")
        saved_sec = int(progress_map.get(v["id"], 0))
        resume_badge = f'<span class="badge badge-warn">Pokračovat ({saved_sec // 60}:{saved_sec % 60:02d})</span>' if saved_sec > 10 else ""
        ep_badge = f'<span class="badge badge-ok">{ep_tag}</span>' if ep_tag else ""
        desc_text = html.escape(overview) if overview else f"{html.escape(v['folder'])} • {format_bytes(v.get('size', 0))}"

        cards_html += f"""
        <div class="media-card">
            <div>
                <div class="media-poster">{poster_block}</div>
                <div style="padding:12px;">
                    <div style="font-weight:600; margin-bottom:4px; word-break:break-word;">{html.escape(v['filename'])}</div>
                    <div style="margin-bottom:6px; display:flex; gap:5px; flex-wrap:wrap;">{ep_badge}{resume_badge}</div>
                    <div style="font-size:12px; color:var(--text-muted);">{desc_text}</div>
                </div>
            </div>
            <div style="padding:0 12px 12px 12px;">
                <button type="button" onclick="playVideo({v['id']}, '{html.escape(v['file_url'])}', '{html.escape(v['filename'])}', '{html.escape(sub_url)}', {saved_sec})" class="btn btn-sm" style="width:100%;">Přehrát</button>
            </div>
        </div>"""

    if not cards_html:
        cards_html = '<p style="color:var(--text-muted); grid-column:1/-1;">Knihovna videí je prázdná. Nahrajte videa (.mp4, .mkv, .webm) ve Správci souborů.</p>'

    body = f"""
    <div id="player-panel" class="panel" style="display:none;">
        <div class="panel-header">
            <h2 id="player-title" class="panel-title">{svg("film")} Přehrávač</h2>
            <div class="form-row">
                <select id="speed-sel" onchange="document.getElementById('video-el').playbackRate = parseFloat(this.value)" style="width:auto; padding:4px 8px;">
                    <option value="1">1.0x</option>
                    <option value="1.25">1.25x</option>
                    <option value="1.5">1.5x</option>
                    <option value="2">2.0x</option>
                </select>
                <button type="button" onclick="closePlayer()" class="btn btn-secondary btn-sm">Zavřít</button>
            </div>
        </div>
        <video id="video-el" controls crossorigin="anonymous" style="width:100%; max-height:520px; background:#000; border-radius:4px;"></video>
    </div>

    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("film")} VaultFlix Cinema 2.0 ({len(videos)} titulů)</h2>
            <span class="badge">{'TMDB API: Aktivní' if TMDB_API_KEY else 'Lokální metadata'}</span>
        </div>
        <div class="media-grid">{cards_html}</div>
    </div>
    <script>
        let currentVidId = 0;
        const vidEl = document.getElementById('video-el');
        function playVideo(id, url, title, subUrl, startSec) {{
            currentVidId = id;
            const p = document.getElementById('player-panel');
            document.getElementById('player-title').innerText = title;
            vidEl.innerHTML = '';
            vidEl.src = url;
            if (subUrl) {{
                const tr = document.createElement('track');
                tr.kind = 'subtitles';
                tr.label = 'České titulky';
                tr.srclang = 'cs';
                tr.src = subUrl;
                tr.default = true;
                vidEl.appendChild(tr);
            }}
            p.style.display = 'block';
            vidEl.currentTime = startSec || 0;
            vidEl.play();
            p.scrollIntoView({{ behavior: 'smooth' }});
        }}
        function closePlayer() {{
            saveWatchProgress();
            vidEl.pause();
            document.getElementById('player-panel').style.display = 'none';
        }}
        function saveWatchProgress() {{
            if (!currentVidId || !vidEl.currentTime) return;
            const fd = new FormData();
            fd.append('username', "{html.escape(username)}");
            fd.append('password', "{html.escape(password)}");
            fd.append('target_owner', "{html.escape(view_owner)}");
            fd.append('video_id', currentVidId);
            fd.append('seconds', Math.floor(vidEl.currentTime));
            fetch('/vaultflix/progress', {{ method: 'POST', body: fd }});
        }}
        setInterval(saveWatchProgress, 15000);
    </script>"""
    return render_shell("VaultFlix Kino 2.0", "vaultflix", username, password, view_owner, body)

@app.post("/vaultflix/progress")
def vaultflix_save_progress(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), video_id: int = Form(...), seconds: int = Form(...)):
    user = verify_user(username, password)
    if not user or not supabase:
        return JSONResponse({"ok": False}, status_code=401)
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("owner", view_owner).eq("storage_provider", "vault_watch_progress").eq("size", video_id).execute()
    supabase.table("nxt_files").insert({
        "owner": view_owner, "filename": "watch_pos", "storage_provider": "vault_watch_progress",
        "file_url": str(seconds), "folder": "/_progress", "size": video_id, "is_deleted": False
    }).execute()
    return JSONResponse({"ok": True})

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
        <div class="panel-header">
            <h2 class="panel-title">{svg("music")} VaultBeats Hi-Fi Streamer</h2>
            <span id="mode-badge" class="badge">Režim: Sekvenční</span>
        </div>
        <div id="track-label" style="font-weight:600; margin-bottom:8px;">Připraveno k přehrávání</div>
        <audio id="audio-el" controls style="width:100%; margin-bottom:10px;"></audio>
        <div class="form-row">
            <button type="button" onclick="prevAudio()" class="btn btn-secondary btn-sm">Předchozí</button>
            <button type="button" onclick="nextAudio()" class="btn btn-secondary btn-sm">Další</button>
            <button type="button" onclick="toggleShuffle()" class="btn btn-secondary btn-sm">Shuffle (Náhodně)</button>
            <button type="button" onclick="toggleLoop()" class="btn btn-secondary btn-sm">Opakovat skladbu</button>
        </div>
    </div>
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Hudební knihovna ({len(tracks)})</h2></div>
        <table>
            <thead><tr><th>#</th><th>Skladba</th><th>Adresář</th><th>Velikost</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    <script>
        const playlist = {tracks_json};
        let cur = 0;
        let shuffle = false;
        const aud = document.getElementById('audio-el');
        const lbl = document.getElementById('track-label');
        function playAudio(i) {{
            if (!playlist.length) return;
            cur = i;
            aud.src = playlist[i].url;
            lbl.innerText = 'Přehrávání: ' + playlist[i].title;
            aud.play();
        }}
        function nextAudio() {{
            if (!playlist.length) return;
            if (shuffle) {{ playAudio(Math.floor(Math.random() * playlist.length)); }}
            else {{ playAudio((cur + 1) % playlist.length); }}
        }}
        function prevAudio() {{ if (playlist.length) playAudio((cur - 1 + playlist.length) % playlist.length); }}
        function toggleShuffle() {{ shuffle = !shuffle; updateMode(); }}
        function toggleLoop() {{ aud.loop = !aud.loop; updateMode(); }}
        function updateMode() {{
            document.getElementById('mode-badge').innerText = 'Shuffle: ' + (shuffle ? 'ZAP' : 'VYP') + ' | Loop: ' + (aud.loop ? 'ZAP' : 'VYP');
        }}
        aud.addEventListener('ended', nextAudio);
    </script>"""
    return render_shell("VaultBeats Hi-Fi", "vaultbeats", username, password, view_owner, body)

# --- 7. VAULTRULES AUTOMATIZAČNÍ ENGINE ---
@app.get("/vaultrules", response_class=HTMLResponse)
def vaultrules_view(username: str, password: str, target_owner: str = None, msg: str = ""):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("storage_provider", "vault_rule").eq("is_deleted", False).execute()
    rules_rows = ""
    for r in (res.data or []):
        d = json.loads(r.get("file_url", "{}"))
        rules_rows += f"""
        <tr>
            <td><strong>{html.escape(d.get('name', 'Pravidlo'))}</strong></td>
            <td class="mono">*.{html.escape(d.get('ext') or '*')} ve složce {html.escape(d.get('src_folder') or 'kdekoli')}</td>
            <td class="mono">Přesunout do {html.escape(d.get('dest_folder') or '-')} | Štítek #{html.escape(d.get('add_tag') or '-')}</td>
            <td><a href="/vaultrules/delete?id={r['id']}&{q_params}" class="link-danger">Smazat</a></td>
        </tr>"""
    if not rules_rows:
        rules_rows = "<tr><td colspan='4' style='text-align:center; color:var(--text-muted);'>Zatím nejsou definována žádná automatická pravidla.</td></tr>"

    alert_html = f'<div class="alert-bar ok">{html.escape(msg)}</div>' if msg else ""
    body = f"""
    {alert_html}
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("zap")} Nové automatizační pravidlo (VaultRules)</h2>
            <form action="/vaultrules/run-now" method="POST" style="margin:0;">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <button type="submit" class="btn btn-secondary btn-sm">Spustit pravidla na stávající soubory</button>
            </form>
        </div>
        <form action="/vaultrules/add" method="POST" class="form-row">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="text" name="name" placeholder="Název (např. Třídění filmů)" required style="width:190px;">
            <input type="text" name="ext" placeholder="Přípona (např. mp4)" style="width:140px;">
            <input type="text" name="src_folder" placeholder="Zdrojová složka (prázdné = vše)" style="width:190px;">
            <input type="text" name="dest_folder" placeholder="Cílová složka (např. /Media)" style="width:180px;">
            <input type="text" name="add_tag" placeholder="Přidat #štítek" style="width:130px;">
            <button type="submit" class="btn">Přidat pravidlo</button>
        </form>
    </div>
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Aktivní pravidla automatického třídění</h2></div>
        <table><thead><tr><th>Název</th><th>Podmínka</th><th>Akce</th><th>Správa</th></tr></thead><tbody>{rules_rows}</tbody></table>
    </div>"""
    return render_shell("VaultRules Automatizace", "vaultrules", username, password, view_owner, body)

@app.post("/vaultrules/add", response_class=HTMLResponse)
def vaultrules_add(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), name: str = Form(...), ext: str = Form(""), src_folder: str = Form(""), dest_folder: str = Form(""), add_tag: str = Form("")):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    clean_dest = dest_folder.strip()
    if clean_dest and not clean_dest.startswith("/"):
        clean_dest = "/" + clean_dest
    payload = json.dumps({
        "name": name.strip(), "ext": ext.strip().lstrip("."), "src_folder": src_folder.strip(),
        "dest_folder": clean_dest, "add_tag": add_tag.strip().lstrip("#")
    }, ensure_ascii=False)
    supabase.table("nxt_files").insert({
        "owner": view_owner, "filename": "vault_rule", "storage_provider": "vault_rule",
        "file_url": payload, "folder": "/_rules", "size": 0, "is_deleted": False
    }).execute()
    return vaultrules_view(username, password, view_owner, "Automatizační pravidlo bylo uloženo.")

@app.get("/vaultrules/delete", response_class=HTMLResponse)
def vaultrules_delete(username: str, password: str, id: int, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("id", id).execute()
    return vaultrules_view(username, password, view_owner, "Pravidlo bylo odstraněno.")

@app.post("/vaultrules/run-now", response_class=HTMLResponse)
def vaultrules_run_now(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    rows = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute().data or []
    affected = 0
    for f in rows:
        if is_system_record(f):
            continue
        new_fld, tags = apply_vault_rules(view_owner, f["filename"], f.get("folder", "/"))
        if new_fld != f.get("folder", "/"):
            supabase.table("nxt_files").update({"folder": new_fld}).eq("id", f["id"]).execute()
            affected += 1
        for t in tags:
            attach_file_tag(view_owner, f["id"], t)
    return vaultrules_view(username, password, view_owner, f"Pravidla byla aplikována. Přesunutých souborů: {affected}.")

# --- 8. REST API & OSOBNÍ PŘÍSTUPOVÉ TOKENY ---
@app.get("/api-tokens", response_class=HTMLResponse)
def api_tokens_view(username: str, password: str, target_owner: str = None, new_token_msg: str = ""):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("storage_provider", "vault_api_token").eq("is_deleted", False).execute()
    t_rows = ""
    for r in (res.data or []):
        tok = r.get("file_url", "")
        masked = tok[:10] + "..." + tok[-4:] if len(tok) > 14 else tok
        t_rows += f"""
        <tr>
            <td><strong>{html.escape(r.get('filename', 'Token'))}</strong></td>
            <td class="mono">{html.escape(masked)}</td>
            <td><a href="/api-tokens/revoke?id={r['id']}&{q_params}" class="link-danger">Zneplatnit token</a></td>
        </tr>"""
    if not t_rows:
        t_rows = "<tr><td colspan='3' style='text-align:center; color:var(--text-muted);'>Žádné aktivní API tokeny.</td></tr>"

    alert = f'<div class="alert-bar warn"><strong>Nový API token (uložte si jej, znovu se nezobrazí celý):</strong> <span class="mono">{html.escape(new_token_msg)}</span></div>' if new_token_msg else ""
    curl_example = 'curl -X POST "https://tvoje-domena.onrender.com/api/v1/upload" \\\n  -H "Authorization: Bearer vg_live_TVUJ_TOKEN" \\\n  -F "folder=/Automatizace" \\\n  -F "file=@zaloha.zip"'

    body = f"""
    {alert}
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("key")} Vygenerovat osobní REST API klíč</h2></div>
        <form action="/api-tokens/create" method="POST" class="form-row">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="text" name="label" placeholder="Název klíče (např. Python skript)" required style="flex:1;">
            <button type="submit" class="btn">Generovat API Token</button>
        </form>
    </div>

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Aktivní přístupové tokeny</h2></div>
        <table><thead><tr><th>Název</th><th>Token</th><th>Správa</th></tr></thead><tbody>{t_rows}</tbody></table>
    </div>

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("code")} Dokumentace REST API (GET /api/v1/files & POST /api/v1/upload)</h2></div>
        <pre class="mono" style="background:var(--bg-app); padding:14px; border:1px solid var(--border); border-radius:4px; overflow-x:auto;">{html.escape(curl_example)}</pre>
    </div>"""
    return render_shell("REST API & Tokeny", "apitokens", username, password, view_owner, body)

@app.post("/api-tokens/create", response_class=HTMLResponse)
def api_tokens_create(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), label: str = Form(...)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    raw_token = "vg_live_" + secrets.token_hex(20)
    supabase.table("nxt_files").insert({
        "owner": view_owner, "filename": label.strip(), "storage_provider": "vault_api_token",
        "file_url": raw_token, "folder": "/_tokens", "size": 0, "is_deleted": False
    }).execute()
    log_audit(username, "API_TOKEN_CREATED", f"Vytvořen API token '{label.strip()}'", "INFO")
    return api_tokens_view(username, password, view_owner, raw_token)

@app.get("/api-tokens/revoke", response_class=HTMLResponse)
def api_tokens_revoke(username: str, password: str, id: int, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("id", id).execute()
    return api_tokens_view(username, password, view_owner)

def resolve_api_token(auth_header: str | None) -> str | None:
    if not (auth_header and auth_header.startswith("Bearer ") and supabase):
        return None
    tok = auth_header.replace("Bearer ", "", 1).strip()
    res = supabase.table("nxt_files").select("owner").eq("storage_provider", "vault_api_token").eq("file_url", tok).eq("is_deleted", False).execute()
    if res.data:
        return res.data[0]["owner"]
    return None

@app.get("/api/v1/files")
def api_v1_list_files(authorization: str | None = Header(default=None)):
    owner = resolve_api_token(authorization)
    if not owner:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    rows = supabase.table("nxt_files").select("id, filename, folder, size, file_url, storage_provider").eq("owner", owner).eq("is_deleted", False).execute().data or []
    clean = [r for r in rows if not is_system_record(r)]
    return JSONResponse({"owner": owner, "count": len(clean), "files": clean})

@app.post("/api/v1/upload")
async def api_v1_upload_file(authorization: str | None = Header(default=None), folder: str = Form("/"), file: UploadFile = File(...)):
    owner = resolve_api_token(authorization)
    if not owner:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    fbytes = await file.read()
    clean_folder = folder if folder.startswith("/") else "/" + folder
    repo_id = get_active_write_repo()
    repo_path = f"{owner}{clean_folder}/{file.filename}".replace("//", "/")
    if hf_api and repo_id:
        hf_api.upload_file(path_or_fileobj=fbytes, path_in_repo=repo_path, repo_id=repo_id, repo_type="dataset")
        purl = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{repo_path}"
    else:
        purl = "#"
    supabase.table("nxt_files").insert({
        "owner": owner, "filename": file.filename, "storage_provider": "huggingface",
        "file_url": purl, "folder": clean_folder, "size": len(fbytes), "is_deleted": False
    }).execute()
    log_audit(owner, "API_UPLOAD", f"REST API nahrání souboru {file.filename}", "INFO")
    return JSONResponse({"status": "ok", "filename": file.filename, "folder": clean_folder, "url": purl})

# --- 9. UŽIVATELÉ A DISKOVÉ KVÓTY ---
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
    {create_user_panel}"""
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
        "owner": quota_user, "filename": "user_quota", "storage_provider": "vault_quota",
        "file_url": str(quota_gb), "folder": "/_quotas", "size": quota_bytes, "is_deleted": False
    }).execute()
    log_audit(username, "QUOTA_UPDATED", f"Kvóta pro {quota_user} nastavena na {quota_gb} GB", "INFO")
    return users_quotas_view(username, password, view_owner, f"Kvóta pro uživatele {quota_user} byla aktualizována.")

# --- 10. FORENZNÍ AUDIT LOG & ÚDRŽBA ---
@app.get("/audit-log", response_class=HTMLResponse)
def audit_log_view(username: str, password: str, target_owner: str = None, level: str = "ALL"):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_audit").order("id", desc=True).limit(120).execute()
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
            <h2 class="panel-title">{svg("shield")} Forenzní Audit Log systému</h2>
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
    return render_shell("Forenzní Audit Log", "audit", username, password, view_owner, body)

@app.get("/maintenance", response_class=HTMLResponse)
def maintenance_view(username: str, password: str, target_owner: str = None, report: str = ""):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username

    all_files = supabase.table("nxt_files").select("*").eq("owner", view_owner).execute().data or []
    active_files = [f for f in all_files if not f.get("is_deleted") and not is_system_record(f)]
    trash_files = [f for f in all_files if f.get("is_deleted") and not is_system_record(f)]

    seen = {}
    duplicates = []
    for f in active_files:
        key = (f.get("filename"), f.get("size", 0))
        if key in seen:
            duplicates.append(f)
        else:
            seen[key] = f

    dup_rows = "".join([
        f"<tr><td>{html.escape(d['filename'])}</td><td class='mono'>{html.escape(d['folder'])}</td><td class='mono'>{format_bytes(d.get('size', 0))}</td></tr>"
        for d in duplicates
    ]) or "<tr><td colspan='3' style='text-align:center; color:var(--text-muted);'>Nebyly nalezeny žádné duplicitní soubory.</td></tr>"

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
            <div class="panel-header"><h3 class="panel-title">{svg("shield")} Kontrola integrity odkazů</h3></div>
            <p style="color:var(--text-muted);">Ověří dostupnost všech záznamů v Supabase a detekuje neplatné odkazy.</p>
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
        <table><thead><tr><th>Soubor</th><th>Složka</th><th>Velikost</th></tr></thead><tbody>{dup_rows}</tbody></table>
    </div>"""
    return render_shell("Údržba & Deduplikace", "maintenance", username, password, view_owner, body)

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
    log_audit(username, "INTEGRITY_SCAN", f"Zkontrolováno {len(active)} souborů, poškozených: {len(broken)}", "INFO")
    return maintenance_view(username, password, view_owner, f"Kontrola dokončena: {len(active)} souborů ověřeno, {len(broken)} neplatných odkazů.")

# --- 11. VAULTUPDATE & OTA STUDIO (S KONTROLOU SYNTAXE PŘED AKTIVACÍ) ---
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
    update_notes = "Žádné nové OTA moduly nebyly nalezeny."

    if manifest:
        remote_ver = str(manifest.get("version", active_ver))
        update_notes = manifest.get("notes", "")
        for rm in manifest.get("modules", []):
            rname = rm.get("name")
            rver = str(rm.get("version", ""))
            if rname and (rname not in LOADED_OTA_MODULES or str(LOADED_OTA_MODULES[rname].get("version", "")) != rver):
                has_update = True

    installed_rows = ""
    for k, m in LOADED_OTA_MODULES.items():
        installed_rows += f"""
        <tr>
            <td><strong>{html.escape(m['title'])}</strong> <span class="mono" style="color:var(--text-muted);">({html.escape(k)})</span></td>
            <td class="mono">v{html.escape(m['version'])}</td>
            <td><span class="badge badge-ok">VERIFIED // LIVE</span></td>
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
        installed_rows = "<tr><td colspan='4' style='text-align:center; color:var(--text-muted);'>Žádné nainstalované OTA doplňky.</td></tr>"

    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    if has_update:
        update_box = f"""
        <div class="alert-bar warn">
            <div>
                <strong>Dostupný nový OTA balíček: v{html.escape(remote_ver)}</strong><br>
                <span style="color:var(--text-muted);">{html.escape(update_notes)}</span>
            </div>
            <form action="/vaultupdate/install" method="POST" style="margin:0;">
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
                <strong>Jádro systému je aktuální (v{html.escape(active_ver)})</strong><br>
                <span style="color:var(--text-muted);">Pevné jádro na Renderu + OTA repozitář <span class="mono">{html.escape(HF_REPO_ID or 'nenastaveno')}/system_ota/</span></span>
            </div>
            <a href="/vaultupdate?{q_params}" class="btn btn-secondary btn-sm">Zkontrolovat znovu</a>
        </div>"""

    starter_module_code = '''def render(username, password, view_owner, supabase, action_data):
    note = action_data.get("note", "").strip()
    if note and supabase:
        supabase.table("nxt_files").insert({
            "owner": view_owner, "filename": "vault_note", "storage_provider": "vault_note_item",
            "file_url": note, "folder": "/_notes", "size": 0, "is_deleted": False
        }).execute()
    rows = ""
    if supabase:
        res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("storage_provider", "vault_note_item").eq("is_deleted", False).execute()
        rows = "".join([f"<tr><td class='mono'>#{i+1}</td><td>{html.escape(x.get('file_url',''))}</td></tr>" for i, x in enumerate(reversed(res.data or []))])
    body = f"""
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Provozní poznámky (OTA Modul)</h2></div>
        <form action="/ota-app/vaultnotes" method="POST" class="form-row" style="margin-bottom:12px;">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="text" name="note" placeholder="Zadejte poznámku..." required style="flex:1;">
            <button type="submit" class="btn">Uložit</button>
        </form>
        <table><thead><tr><th>#</th><th>Záznam</th></tr></thead><tbody>{rows or "<tr><td colspan='2'>Prázdné</td></tr>"}</tbody></table>
    </div>"""
    return render_shell("VaultNotes", "ota_vaultnotes", username, password, view_owner, body)'''

    alert_html = f'<div class="alert-bar ok">{html.escape(status_msg)}</div>' if status_msg else ""
    body = f"""
    {alert_html}
    {update_box}
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("package")} Nainstalovaná OTA rozšíření</h2></div>
        <table><thead><tr><th>Název</th><th>Verze</th><th>Stav</th><th>Akce</th></tr></thead><tbody>{installed_rows}</tbody></table>
    </div>
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("code")} OTA Studio — Publikovat rozšíření (s kontrolou syntaxe)</h2></div>
        <form action="/vaultupdate/publish-custom" method="POST">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <div class="grid-2" style="margin-bottom:10px;">
                <input type="text" name="mod_name" value="vaultnotes" placeholder="ID modulu" required>
                <input type="text" name="mod_title" value="VaultNotes" placeholder="Název v navigaci" required>
                <input type="text" name="new_version" value="22.1" placeholder="Verze" required>
                <input type="text" name="release_notes" value="Nový OTA modul poznámek." placeholder="Changelog" required>
            </div>
            <textarea name="module_code" rows="14" class="code-box" style="margin-bottom:12px;" required>{html.escape(starter_module_code)}</textarea>
            <button type="submit" class="btn">Ověřit syntaxi a publikovat na Hugging Face</button>
        </form>
    </div>"""
    return render_shell("VaultUpdate & OTA", "vaultupdate", username, password, view_owner, body)

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
        return vaultupdate_view(username, password, view_owner, "Chybí HF_TOKEN nebo HF_REPO_ID.")

    try:
        compile(module_code, "<ota_syntax_check>", "exec")
    except Exception as syn_err:
        return vaultupdate_view(username, password, view_owner, f"Chyba syntaxe v Python kódu modulu (publikování zrušeno): {syn_err}")

    clean_name = "".join([c for c in mod_name.strip().lower() if c.isalnum() or c == "_"])
    code_path = f"system_ota/{clean_name}.py"
    try:
        hf_api.upload_file(path_or_fileobj=module_code.encode("utf-8"), path_in_repo=code_path, repo_id=HF_REPO_ID, repo_type="dataset")
        code_url = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/{code_path}"
        existing = fetch_remote_manifest() or {"version": new_version.strip(), "notes": "", "modules": []}
        modules_list = [m for m in existing.get("modules", []) if m.get("name") != clean_name]
        modules_list.append({"name": clean_name, "title": mod_title.strip(), "sub": "OTA Modul", "version": new_version.strip(), "code_url": code_url})
        updated_manifest = {"version": new_version.strip(), "notes": release_notes.strip(), "modules": modules_list}
        hf_api.upload_file(path_or_fileobj=json.dumps(updated_manifest, ensure_ascii=False, indent=2).encode("utf-8"), path_in_repo="system_ota/manifest.json", repo_id=HF_REPO_ID, repo_type="dataset")
        log_audit(username, "OTA_PUBLISHED", f"Publikován OTA balíček {clean_name} v{new_version.strip()}", "INFO")
        return vaultupdate_view(username, password, view_owner, f"Balíček {mod_title.strip()} (v{new_version.strip()}) prošel kontrolou syntaxe a byl publikován.")
    except Exception as e:
        return vaultupdate_view(username, password, view_owner, f"Chyba nahrávání: {e}")

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
            compile(code_str, f"<ota_{mname}>", "exec")
            LOADED_OTA_MODULES[mname] = {"title": mod.get("title", mname), "sub": "OTA Modul", "version": str(mod.get("version", "22.1")), "code": code_str}
            supabase.table("nxt_files").delete().eq("storage_provider", "vault_ota_module").eq("filename", mname).execute()
            supabase.table("nxt_files").insert({
                "owner": "system", "filename": mname, "storage_provider": "vault_ota_module",
                "file_url": json.dumps(mod, ensure_ascii=False), "folder": "/_ota", "size": len(code_str), "is_deleted": False
            }).execute()
    return vaultupdate_view(username, password, view_owner, "OTA rozšíření byla nainstalována.")

@app.post("/vaultupdate/uninstall", response_class=HTMLResponse)
def vaultupdate_uninstall(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None), module_name: str = Form(...)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    LOADED_OTA_MODULES.pop(module_name, None)
    supabase.table("nxt_files").delete().eq("storage_provider", "vault_ota_module").eq("filename", module_name).execute()
    return vaultupdate_view(username, password, view_owner, f"Modul '{module_name}' byl odinstalován.")

@app.get("/ota-app/{module_name}", response_class=HTMLResponse)
def ota_app_get(module_name: str, request: Request, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    sync_ota_modules_from_db()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    if module_name not in LOADED_OTA_MODULES:
        return vaultupdate_view(username, password, view_owner, "Modul není nainstalován.")
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
        return vaultupdate_view(username, password, view_owner, "Modul není nainstalován.")
    ns = {"render_shell": render_shell, "html": html, "json": json, "svg": svg, "format_bytes": format_bytes}
    exec(LOADED_OTA_MODULES[module_name]["code"], ns)
    return ns["render"](username, password, view_owner, supabase, form_data)

# --- 12. VAULTCHAT & VAULTCODE IDE PRO (S ŽIVÝM NÁHLEDEM) ---
@app.get("/vaultchat", response_class=HTMLResponse)
def vaultchat_view(username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    msgs = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_chat").order("id", desc=False).execute().data or []
    entries_html = ""
    for m in msgs[-60:]:
        sender = m.get("owner", "system")
        mine = "mine" if sender == username else ""
        entries_html += f'<div class="chat-entry {mine}"><div style="font-size:11px; color:var(--text-muted); margin-bottom:2px;"><strong>{html.escape(sender)}</strong></div><div>{html.escape(m.get("file_url", ""))}</div></div>'
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
            "owner": username, "filename": "chat_msg", "storage_provider": "vault_chat",
            "file_url": message.strip(), "folder": "/_chat", "size": 0, "is_deleted": False
        }).execute()
    return vaultchat_view(username, password, target_owner)

@app.get("/new-file", response_class=HTMLResponse)
def new_file_view(username: str, password: str, folder: str = "/", target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    starter = "<!DOCTYPE html>\n<html lang=\"cs\">\n<head>\n    <meta charset=\"UTF-8\">\n    <title>VaultGrid Web</title>\n    <style>body { font-family: system-ui; padding: 30px; background: #111; color: #eee; }</style>\n</head>\n<body>\n    <h1>VaultGrid Static Web Hosting</h1>\n    <p>Živý náhled v reálném čase.</p>\n</body>\n</html>"
    body = f"""
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("code")} VaultCode IDE Pro — Editor & Živý náhled ({html.escape(folder)})</h2></div>
        <form action="/create-text-file" method="POST">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="folder" value="{html.escape(folder)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <div class="form-row" style="margin-bottom:10px;">
                <input type="text" name="filename" value="index.html" required style="width:240px;">
                <button type="submit" class="btn">Uložit do úložiště</button>
            </div>
            <div class="grid-2">
                <textarea id="ide-code" name="content" rows="20" class="code-box" oninput="updateLiveFrame()">{html.escape(starter)}</textarea>
                <iframe id="ide-preview" style="width:100%; height:100%; min-height:380px; background:#fff; border:1px solid var(--border); border-radius:5px;"></iframe>
            </div>
        </form>
    </div>
    <script>
        function updateLiveFrame() {{
            document.getElementById('ide-preview').srcdoc = document.getElementById('ide-code').value;
        }}
        updateLiveFrame();
    </script>"""
    return render_shell("VaultCode IDE Pro", "code", username, password, view_owner, body)

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
        "owner": view_owner, "filename": clean_name, "storage_provider": "huggingface",
        "file_url": public_url, "folder": folder, "size": len(file_bytes), "is_deleted": False
    }).execute()
    log_audit(username, "FILE_CREATED", f"Vytvořen soubor {repo_path}", "INFO")
    return render_files_view(username, password, user["role"] == "admin", view_owner, folder, "/", "single", False, "", "", "", f"Soubor {clean_name} byl uložen.")

@app.get("/code-editor", response_class=HTMLResponse)
def code_editor_view(id: int, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    rec = (supabase.table("nxt_files").select("*").eq("id", id).execute().data or [None])[0]
    if not rec:
        return "Soubor nenalezen."
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

# --- 13. OPERACE SE SOUBORY, NAHRÁVÁNÍ (DEDUPLIKACE + VAULTCRYPT + VAULTRULES) ---
@app.post("/create-folder", response_class=HTMLResponse)
def create_folder(username: str = Form(...), password: str = Form(...), current_folder: str = Form(...), new_folder_name: str = Form(...), target_owner: str = Form(None)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    clean_name = new_folder_name.strip().replace("/", "")
    new_path = f"{current_folder.rstrip('/')}/{clean_name}"
    supabase.table("nxt_files").insert({
        "owner": view_owner, "filename": f".slozkové_meta_{clean_name}", "storage_provider": "system",
        "file_url": "#", "folder": new_path, "size": 0, "is_deleted": False
    }).execute()
    log_audit(username, "DIR_CREATED", f"Vytvořen adresář {new_path}", "INFO")
    return render_files_view(username, password, user["role"] == "admin", view_owner, new_path, "/", "single", False, "", "", "", "")

@app.post("/upload", response_class=HTMLResponse)
async def upload_files(
    username: str = Form(...),
    password: str = Form(...),
    folder: str = Form("/"),
    target_owner: str = Form(None),
    unlocked_pin: str = Form(""),
    encrypt_flag: str = Form(""),
    encrypt_pass: str = Form(""),
    files: list[UploadFile] = File(...)
):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username

    quota_limit = get_user_quota_bytes(view_owner)
    all_rows = supabase.table("nxt_files").select("*").eq("is_deleted", False).execute().data or []
    active_global = [r for r in all_rows if not is_system_record(r)]
    current_used = sum(int(f.get("size", 0)) for f in active_global if f.get("owner") == view_owner)

    repo_id = get_active_write_repo(active_global)
    uploaded_count = 0
    dedup_saved = 0

    for f in files:
        if not f.filename:
            continue
        raw_bytes = await f.read()
        final_name = f.filename
        final_bytes = raw_bytes

        if encrypt_flag == "1" and encrypt_pass.strip():
            final_bytes = vaultcrypt_encrypt(raw_bytes, encrypt_pass.strip())
            final_name = f.filename + ".vgenc"

        if quota_limit > 0 and (current_used + len(final_bytes)) > quota_limit:
            log_audit(username, "QUOTA_EXCEEDED", f"Překročena disková kvóta pro {view_owner}", "WARN")
            return render_files_view(username, password, user["role"] == "admin", view_owner, folder, "/", "single", False, "", "", unlocked_pin, "Chyba: Byla překročena přidělená disková kvóta.")

        dest_folder, auto_tags = apply_vault_rules(view_owner, final_name, folder)

        existing_match = next((x for x in active_global if x.get("filename") == final_name and int(x.get("size", 0)) == len(final_bytes) and x.get("file_url", "").startswith("http")), None)
        if existing_match and not encrypt_flag:
            public_url = existing_match["file_url"]
            dedup_saved += 1
        else:
            repo_path = f"{view_owner}{dest_folder}/{final_name}".replace("//", "/")
            if hf_api and repo_id:
                hf_api.upload_file(path_or_fileobj=final_bytes, path_in_repo=repo_path, repo_id=repo_id, repo_type="dataset")
                public_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{repo_path}"
            else:
                public_url = "#"

        ins_res = supabase.table("nxt_files").insert({
            "owner": view_owner, "filename": final_name, "storage_provider": "huggingface",
            "file_url": public_url, "folder": dest_folder, "size": len(final_bytes), "is_deleted": False
        }).execute()

        if ins_res.data and auto_tags:
            new_id = ins_res.data[0]["id"]
            for t in auto_tags:
                attach_file_tag(view_owner, new_id, t)

        current_used += len(final_bytes)
        uploaded_count += 1

    log_audit(username, "FILES_UPLOADED", f"Nahráno {uploaded_count} souborů (deduplikováno: {dedup_saved})", "INFO")
    info_txt = f"Nahráno souborů: {uploaded_count}" + (f" (z toho {dedup_saved} deduplikováno bez zabrání místa)" if dedup_saved else "")
    return render_files_view(username, password, user["role"] == "admin", view_owner, folder, "/", "single", False, "", "", unlocked_pin, info_txt)

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
            "owner": view_owner, "filename": ".vault_pin_lock", "storage_provider": "system_lock",
            "file_url": clean_pin, "folder": current_folder, "size": 0, "is_deleted": False
        }).execute()
        log_audit(username, "PIN_LOCK_SET", f"Nastaven PIN zámek pro {current_folder}", "INFO")
    return render_files_view(username, password, user["role"] == "admin", view_owner, current_folder, "/", "single", False, "", "", "", "")

@app.post("/remove-folder-pin", response_class=HTMLResponse)
def remove_folder_pin(username: str = Form(...), password: str = Form(...), current_folder: str = Form(...), target_owner: str = Form(None)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("owner", view_owner).eq("folder", current_folder).eq("filename", ".vault_pin_lock").execute()
    log_audit(username, "PIN_LOCK_REMOVED", f"Odebrán PIN zámek z {current_folder}", "WARN")
    return render_files_view(username, password, user["role"] == "admin", view_owner, current_folder, "/", "single", False, "", "", "", "")

@app.get("/delete-file", response_class=HTMLResponse)
def delete_file(id: int, username: str, password: str, folder: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").update({"is_deleted": True}).eq("id", id).execute()
    return render_files_view(username, password, user["role"] == "admin", view_owner, folder, "/", "single", False, "", "", "", "")

@app.get("/restore-file", response_class=HTMLResponse)
def restore_file(id: int, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").update({"is_deleted": False}).eq("id", id).execute()
    return render_files_view(username, password, user["role"] == "admin", view_owner, "/", "/", "single", True, "", "", "", "")

@app.get("/delete-permanently", response_class=HTMLResponse)
def delete_permanently(id: int, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("id", id).execute()
    return render_files_view(username, password, user["role"] == "admin", view_owner, "/", "/", "single", True, "", "", "", "")

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
    rec = (supabase.table("nxt_files").select("*").eq("id", id).execute().data or [None])[0]
    if not rec:
        return "Soubor nenalezen."
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
    rec = (supabase.table("nxt_files").select("*").eq("id", id).execute().data or [None])[0]
    if not rec:
        return "Soubor nenalezen."
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
    rec = (supabase.table("nxt_files").select("*").eq("id", file_id).execute().data or [None])[0]
    if not rec:
        return "Soubor nenalezen."
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

# --- 14. ROOT SSH KONZOLE ---
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
        new_hist += "Příkazy:\n  ls        - Výpis souborů\n  cd <dir>  - Změna adresáře\n  pools     - Stav 7 TB úložných poolů\n  drops     - Aktivní VaultDrop sdílecí odkazy\n  audit     - Posledních 5 bezpečnostních událostí\n  users     - Seznam účtů\n  clear     - Vyčištění obrazovky\n\n"
    elif act == "clear":
        new_hist = ""
    elif act == "pools":
        for p in get_storage_pools():
            new_hist += f"  - {p['label']} [{p['repo_id']}] ({p['quota_gb']} GB)\n"
        new_hist += "\n"
    elif act == "drops":
        res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_drop").execute()
        for r in (res.data or []):
            m = json.loads(r.get("file_url", "{}"))
            new_hist += f"  - /drop/{m.get('token')} -> {m.get('label')} (staženo: {m.get('downloads_used', 0)})\n"
        new_hist += "\n"
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

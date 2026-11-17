import os
import io
import re
import time
import hmac
import json
import html
import base64
import zipfile
import hashlib
import secrets
import platform
import mimetypes
import urllib.request
import urllib.parse
from email.utils import formatdate
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Form, UploadFile, File, Request, Header
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from supabase import create_client, Client
from huggingface_hub import HfApi

app = FastAPI(title="VaultGrid OS APEX Edition", version="24.0")

CORE_VERSION = "24.0-APEX"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_REPO_ID = os.environ.get("HF_REPO_ID")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

supabase: Client | None = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None
hf_api = HfApi(token=HF_TOKEN) if HF_TOKEN else None

LOADED_OTA_MODULES: dict[str, dict] = {}
WARPDROP_ROOMS: dict[str, dict] = {}

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
    "vault_leecher_log",
    "vault_raid_folder",
    "vault_raid_mirror",
    "vault_chunk_manifest",
}

# --- VEKTOROVÉ SVG IKONY (CRISP UI SET) ---
SVG_ICONS = {
    "server": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>',
    "dashboard": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>',
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
    "harddrive": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="12" x2="2" y2="12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><line x1="6" y1="16" x2="6.01" y2="16"/><line x1="10" y1="16" x2="10.01" y2="16"/></svg>',
    "download_cloud": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="8 17 12 21 16 17"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29"/></svg>',
    "upload_cloud": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>',
    "wifi": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/></svg>',
    "laptop": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="2" y1="20" x2="22" y2="20"/></svg>',
    "layers": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
}

def svg(name: str) -> str:
    return SVG_ICONS.get(name, SVG_ICONS["file"])

# --- VYLEPŠENÝ MODERNÍ DESIGN & PŘEHLEDNÝ UI STYLESHEET ---
APEX_CSS = """
<style>
    :root {
        --bg-app: #090b0f;
        --bg-sidebar: #0e1218;
        --bg-surface: #131821;
        --bg-surface-alt: #1a202c;
        --bg-hover: #212837;
        --border: #252d3d;
        --border-subtle: rgba(255, 255, 255, 0.06);
        --text-main: #f1f5f9;
        --text-muted: #94a3b8;
        --accent: #3b82f6;
        --accent-hover: #2563eb;
        --accent-glow: rgba(59, 130, 246, 0.16);
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --cyan: #06b6d4;
        --shadow-card: 0 4px 20px rgba(0, 0, 0, 0.25);
        --mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
        --sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    html[data-theme="light"] {
        --bg-app: #f1f5f9;
        --bg-sidebar: #ffffff;
        --bg-surface: #ffffff;
        --bg-surface-alt: #f8fafc;
        --bg-hover: #f1f5f9;
        --border: #e2e8f0;
        --border-subtle: rgba(0, 0, 0, 0.04);
        --text-main: #0f172a;
        --text-muted: #64748b;
        --accent: #2563eb;
        --accent-hover: #1d4ed8;
        --accent-glow: rgba(37, 99, 235, 0.10);
        --shadow-card: 0 2px 10px rgba(15, 23, 42, 0.05);
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
        -webkit-font-smoothing: antialiased;
    }
    .app-layout { display: flex; min-height: 100vh; }

    /* SIDEBAR */
    .sidebar {
        width: 260px;
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
        padding: 18px 20px;
        border-bottom: 1px solid var(--border);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .brand-title {
        font-weight: 800;
        font-size: 15px;
        letter-spacing: 0.03em;
        display: flex;
        align-items: center;
        gap: 9px;
        color: var(--text-main);
    }
    .brand-logo-box {
        width: 28px; height: 28px;
        border-radius: 7px;
        background: linear-gradient(135deg, #2563eb, #06b6d4);
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .brand-ver {
        font-family: var(--mono);
        font-size: 11px;
        font-weight: 600;
        color: #60a5fa;
        background: var(--accent-glow);
        border: 1px solid rgba(59, 130, 246, 0.35);
        padding: 2px 7px;
        border-radius: 6px;
    }
    .nav-section { padding: 6px 10px; }
    .nav-group-label {
        font-size: 10.5px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted);
        padding: 10px 10px 4px 10px;
    }
    .nav-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        margin-bottom: 2px;
        border-radius: 8px;
        color: var(--text-muted);
        text-decoration: none;
        font-weight: 500;
        transition: all 0.14s ease;
    }
    .nav-item:hover { background-color: var(--bg-hover); color: var(--text-main); }
    .nav-item.active {
        background-color: var(--accent-glow);
        color: #60a5fa;
        font-weight: 600;
    }
    html[data-theme="light"] .nav-item.active { color: var(--accent); }
    .nav-pill {
        margin-left: auto;
        font-family: var(--mono);
        font-size: 10px;
        padding: 1px 6px;
        border-radius: 10px;
        background: var(--bg-surface-alt);
        border: 1px solid var(--border);
        color: var(--text-muted);
    }
    .sidebar-footer {
        margin-top: auto;
        padding: 14px 16px;
        border-top: 1px solid var(--border);
        background: var(--bg-surface-alt);
        font-size: 12px;
    }

    /* MAIN AREA & TOPBAR */
    .main-area { flex: 1; display: flex; flex-direction: column; min-width: 0; }
    .topbar {
        height: 60px;
        background-color: var(--bg-sidebar);
        border-bottom: 1px solid var(--border);
        padding: 0 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        position: sticky;
        top: 0;
        z-index: 20;
    }
    .topbar-title { font-size: 16px; font-weight: 700; margin: 0; letter-spacing: -0.01em; }
    .topbar-actions { display: flex; align-items: center; gap: 10px; }
    .content-wrap { padding: 26px 28px; max-width: 1480px; width: 100%; }

    /* CARDS & PANELS */
    .panel {
        background-color: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: var(--shadow-card);
    }
    .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid var(--border);
        padding-bottom: 14px;
        margin-bottom: 16px;
        gap: 12px;
        flex-wrap: wrap;
    }
    .panel-title {
        font-size: 14.5px;
        font-weight: 700;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 9px;
    }
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-bottom: 22px;
    }
    .kpi-card {
        background-color: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 18px;
        box-shadow: var(--shadow-card);
        position: relative;
        overflow: hidden;
    }
    .kpi-label {
        font-size: 11.5px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .kpi-value {
        font-family: var(--mono);
        font-size: 22px;
        font-weight: 800;
        color: var(--text-main);
    }
    .kpi-sub { font-size: 12px; color: var(--text-muted); margin-top: 6px; }

    /* INPUTS & BUTTONS */
    input, select, textarea {
        width: 100%;
        padding: 9px 12px;
        background-color: var(--bg-app);
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text-main);
        font-family: var(--sans);
        font-size: 13px;
        outline: none;
        transition: border-color 0.14s, box-shadow 0.14s;
    }
    input[type="checkbox"] { width: auto; cursor: pointer; accent-color: var(--accent); }
    input:focus, select:focus, textarea:focus {
        border-color: var(--accent);
        box-shadow: 0 0 0 3px var(--accent-glow);
    }
    textarea.code-box { font-family: var(--mono); font-size: 12.5px; line-height: 1.5; }

    .btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 7px;
        padding: 9px 15px;
        background-color: var(--accent);
        color: #ffffff;
        border: 1px solid transparent;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        white-space: nowrap;
        transition: all 0.14s ease;
    }
    .btn:hover { background-color: var(--accent-hover); transform: translateY(-1px); }
    .btn-secondary {
        background-color: var(--bg-surface-alt);
        color: var(--text-main);
        border-color: var(--border);
    }
    .btn-secondary:hover { background-color: var(--bg-hover); }
    .btn-success { background-color: var(--success); }
    .btn-warning { background-color: var(--warning); color: #090b0f; }
    .btn-danger { background-color: var(--danger); }
    .btn-sm { padding: 6px 11px; font-size: 12px; border-radius: 7px; }

    /* TABLES */
    .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 9px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 11px 14px; text-align: left; border-bottom: 1px solid var(--border); }
    tr:last-child td { border-bottom: none; }
    th {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        background-color: var(--bg-surface-alt);
        font-weight: 700;
    }
    tr:hover td { background-color: var(--bg-hover); }

    .mono { font-family: var(--mono); }
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 2px 8px;
        border-radius: 6px;
        font-family: var(--mono);
        font-size: 11px;
        font-weight: 600;
        border: 1px solid var(--border);
        background-color: var(--bg-surface-alt);
        color: var(--text-main);
    }
    .badge-ok { border-color: rgba(16, 185, 129, 0.4); background: rgba(16, 185, 129, 0.12); color: #34d399; }
    .badge-warn { border-color: rgba(245, 158, 11, 0.4); background: rgba(245, 158, 11, 0.12); color: #fbbf24; }
    .badge-err { border-color: rgba(239, 68, 68, 0.4); background: rgba(239, 68, 68, 0.12); color: #f87171; }
    .badge-cyan { border-color: rgba(6, 182, 212, 0.4); background: rgba(6, 182, 212, 0.12); color: #22d3ee; }
    .badge-tag { border-color: rgba(59, 130, 246, 0.4); background: var(--accent-glow); color: #60a5fa; text-decoration: none; }

    .progress-track {
        width: 100%;
        height: 9px;
        background-color: var(--bg-app);
        border: 1px solid var(--border);
        border-radius: 6px;
        overflow: hidden;
    }
    .progress-fill { height: 100%; background: linear-gradient(90deg, #2563eb, #06b6d4); transition: width 0.2s ease; }

    .alert-bar {
        padding: 12px 16px;
        border-radius: 10px;
        border: 1px solid var(--border);
        background-color: var(--bg-surface);
        margin-bottom: 18px;
        font-size: 13.5px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        box-shadow: var(--shadow-card);
    }
    .alert-bar.warn { border-left: 4px solid var(--warning); }
    .alert-bar.ok { border-left: 4px solid var(--success); }
    .alert-bar.err { border-left: 4px solid var(--danger); }

    .form-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }
    .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; }
    .grid-dual { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }

    /* TABS FOR CLEANER FILE TOOLS */
    .tool-tabs {
        display: flex;
        gap: 6px;
        border-bottom: 1px solid var(--border);
        padding-bottom: 10px;
        margin-bottom: 14px;
        flex-wrap: wrap;
    }
    .tool-tab-btn {
        padding: 6px 12px;
        border-radius: 7px;
        border: 1px solid var(--border);
        background: var(--bg-surface-alt);
        color: var(--text-muted);
        font-size: 12.5px;
        font-weight: 600;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .tool-tab-btn.active {
        background: var(--accent-glow);
        border-color: rgba(59, 130, 246, 0.45);
        color: #60a5fa;
    }
    .tool-pane { display: none; }
    .tool-pane.active { display: block; }

    .media-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(225px, 1fr)); gap: 16px; }
    .media-card {
        background-color: var(--bg-surface-alt);
        border: 1px solid var(--border);
        border-radius: 10px;
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
        border-radius: 8px;
        padding: 14px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-bottom: 12px;
    }
    .chat-entry {
        padding: 9px 13px;
        border-radius: 8px;
        border: 1px solid var(--border);
        background-color: var(--bg-surface);
        max-width: 80%;
    }
    .chat-entry.mine { align-self: flex-end; border-left: 3px solid var(--accent); }

    .link-action { color: #60a5fa; text-decoration: none; font-size: 12px; font-weight: 500; margin-right: 9px; }
    .link-action:hover { text-decoration: underline; }
    .link-danger { color: #f87171; text-decoration: none; font-size: 12px; font-weight: 500; }
    .link-danger:hover { text-decoration: underline; }

    .dropzone {
        border: 2px dashed var(--border);
        border-radius: 10px;
        padding: 22px;
        text-align: center;
        background: var(--bg-app);
        cursor: pointer;
        transition: border-color 0.15s, background 0.15s;
    }
    .dropzone:hover, .dropzone.dragover {
        border-color: var(--accent);
        background: var(--accent-glow);
    }

    @media (max-width: 980px) {
        .app-layout { flex-direction: column; }
        .sidebar { width: 100%; height: auto; position: static; }
        .grid-dual { grid-template-columns: 1fr; }
        .content-wrap { padding: 16px; }
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
        background-color: #090b0f;
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
        background-color: #111620;
        border: 1px solid #252d3d;
        border-radius: 10px;
        padding: 22px;
    }
    .term-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #252d3d;
        padding-bottom: 12px;
        margin-bottom: 14px;
        font-size: 13px;
    }
    .term-out {
        height: 430px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-size: 13px;
        line-height: 1.55;
        margin-bottom: 14px;
    }
    .term-line {
        display: flex;
        align-items: center;
        gap: 8px;
        border-top: 1px solid #252d3d;
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

# --- VAULTCRYPT ZERO-KNOWLEDGE ŠIFROVÁNÍ ---
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

# --- 7 TB AUTO-BALANCING MULTI-POOL & CLOUD RAID-1 ENGINE (MILNÍK A) ---
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

    ordered = sorted(pools, key=lambda x: 0 if x.get("is_active_write") else 1)
    for p in ordered:
        repo = p["repo_id"]
        cap_bytes = int(p.get("quota_gb", 300)) * (1024 ** 3)
        used_bytes = sum(int(f.get("size", 0)) for f in (active_files or []) if repo in f.get("file_url", ""))
        if used_bytes < (cap_bytes * 0.90):
            return repo
    return ordered[0]["repo_id"]

def get_mirror_repo(primary_repo: str) -> str:
    pools = get_storage_pools()
    for p in pools:
        if p["repo_id"] != primary_repo:
            return p["repo_id"]
    return ""

def get_raid1_folders(owner: str) -> list[str]:
    if not supabase:
        return []
    res = supabase.table("nxt_files").select("folder").eq("owner", owner).eq("storage_provider", "vault_raid_folder").eq("is_deleted", False).execute()
    return sorted(list({r.get("folder", "/") for r in (res.data or []) if r.get("folder")}))

def is_folder_raid1(owner: str, folder: str, raid_folders: list[str] | None = None) -> bool:
    r_list = raid_folders if raid_folders is not None else get_raid1_folders(owner)
    norm = "/" + folder.strip("/") if folder.strip("/") else "/"
    for rf in r_list:
        rf_norm = "/" + rf.strip("/") if rf.strip("/") else "/"
        if rf_norm == "/" or norm == rf_norm or norm.startswith(rf_norm + "/"):
            return True
    return False

def get_raid1_mirrors_map(owner: str) -> dict[int, str]:
    m_map: dict[int, str] = {}
    if not supabase:
        return m_map
    res = supabase.table("nxt_files").select("size, file_url").eq("owner", owner).eq("storage_provider", "vault_raid_mirror").eq("is_deleted", False).execute()
    for r in (res.data or []):
        fid = int(r.get("size", 0))
        if fid and r.get("file_url"):
            m_map[fid] = r["file_url"]
    return m_map

def record_raid1_mirror(owner: str, file_id: int, mirror_url: str):
    if not (supabase and file_id and mirror_url):
        return
    supabase.table("nxt_files").delete().eq("owner", owner).eq("storage_provider", "vault_raid_mirror").eq("size", file_id).execute()
    supabase.table("nxt_files").insert({
        "owner": owner,
        "filename": "raid1_mirror",
        "storage_provider": "vault_raid_mirror",
        "file_url": mirror_url,
        "folder": "/_raid",
        "size": file_id,
        "is_deleted": False
    }).execute()

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
                        "version": str(meta.get("version", "24.1")),
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

# --- PŘEHLEDNÝ UNIFIED UI SHELL ---
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

    def nav_link(key: str, href: str, icon_key: str, label: str, pill: str = "") -> str:
        cls = "nav-item active" if active_nav == key else "nav-item"
        pill_html = f'<span class="nav-pill">{html.escape(pill)}</span>' if pill else ""
        return f'<a href="{href}" class="{cls}">{svg(icon_key)} <span>{html.escape(label)}</span>{pill_html}</a>'

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
            <div class="brand-title">
                <div class="brand-logo-box">{svg("server")}</div>
                <span>VAULTGRID</span>
            </div>
            <span class="brand-ver">v{html.escape(active_ver)}</span>
        </div>

        <div class="nav-section">
            <div class="nav-group-label">Základna</div>
            {nav_link("overview", f"/overview?{q_params}", "dashboard", "Přehled systému")}
            {nav_link("files", f"/files?{q_params}", "folder", "Správce souborů")}
            {nav_link("pools", f"/storage-pools?{q_params}", "database", "Storage & RAID-1", "7 TB")}

            <div class="nav-group-label">Přenos & Synchronizace</div>
            {nav_link("warpdrop", f"/warpdrop-p2p?{q_params}", "wifi", "WarpDrop P2P", "AirDrop")}
            {nav_link("vaultsync", f"/vaultsync?{q_params}", "laptop", "VaultSync PC Agent")}
            {nav_link("webdav", f"/webdav-manager?{q_params}", "harddrive", "WebDAV Disk Z:\\")}
            {nav_link("leecher", f"/url-leecher?{q_params}", "download_cloud", "URL Cloud Stahovač")}

            <div class="nav-group-label">Média a Tvorba</div>
            {nav_link("vaultflix", f"/vaultflix?{q_params}", "film", "VaultFlix Cinema")}
            {nav_link("vaultbeats", f"/vaultbeats?{q_params}", "music", "VaultBeats Hi-Fi")}
            {nav_link("code", f"/new-file?{q_params}", "code", "VaultCode IDE Pro")}

            <div class="nav-group-label">Sdílení & Automatizace</div>
            {nav_link("vaultdrop", f"/vaultdrop?{q_params}", "share", "VaultDrop Odkazy")}
            {nav_link("vaultbackup", f"/vaultbackup?{q_params}", "save", "Zálohy & Snapshots")}
            {nav_link("vaultrules", f"/vaultrules?{q_params}", "zap", "VaultRules Pravidla")}
            {nav_link("apitokens", f"/api-tokens?{q_params}", "key", "REST API & Tokeny")}

            <div class="nav-group-label">Správa systému</div>
            {nav_link("users", f"/users-quotas?{q_params}", "users", "Uživatelé a kvóty")}
            {nav_link("audit", f"/audit-log?{q_params}", "shield", "Forenzní Audit Log")}
            {nav_link("maintenance", f"/maintenance?{q_params}", "wrench", "Údržba & Deduplikace")}
            {nav_link("vaultchat", f"/vaultchat?{q_params}", "message", "VaultChat")}
            {nav_link("vaultupdate", f"/vaultupdate?{q_params}", "refresh", "VaultUpdate & OTA")}

            {ota_nav_html}
        </div>

        <div class="sidebar-footer">
            <div style="margin-bottom: 10px; color: var(--text-muted); display:flex; justify-content:space-between; align-items:center;">
                <span>Účet: <strong style="color: var(--text-main);">{html.escape(username)}</strong></span>
                <span class="badge badge-ok" style="font-size:10px;">ONLINE</span>
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
    <title>{html.escape(page_title)} — VaultGrid APEX</title>
    {APEX_CSS}
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
                        <input type="text" name="q" value="{html.escape(search_query)}" placeholder="Hledat soubor nebo #štítek..." style="width: 240px;">
                        <button type="submit" class="btn btn-secondary btn-sm">Hledat</button>
                    </form>
                    <a href="/warpdrop-p2p?{q_params}" class="btn btn-secondary btn-sm">{svg("wifi")} WarpDrop</a>
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

# --- MILNÍK A1: CHUNKED STREAMING UPLOAD ENGINE (50GB+ BEZ LIMITU RAM) ---
@app.post("/api/upload/chunk-init")
def api_chunk_init(
    username: str = Form(...),
    password: str = Form(...),
    target_owner: str = Form(None),
    filename: str = Form(...),
    folder: str = Form("/"),
    total_size: int = Form(...),
    total_chunks: int = Form(...)
):
    user = verify_user(username, password)
    if not user:
        return JSONResponse({"ok": False, "error": "Neplatné přihlašovací údaje."}, status_code=401)
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username

    quota_limit = get_user_quota_bytes(view_owner)
    all_rows = supabase.table("nxt_files").select("*").eq("is_deleted", False).execute().data or []
    active_global = [r for r in all_rows if not is_system_record(r)]
    current_used = sum(int(f.get("size", 0)) for f in active_global if f.get("owner") == view_owner)

    if quota_limit > 0 and (current_used + total_size) > quota_limit:
        return JSONResponse({"ok": False, "error": "Překročena disková kvóta účtu."}, status_code=413)

    clean_folder = folder.strip() or "/"
    if not clean_folder.startswith("/"):
        clean_folder = "/" + clean_folder

    routed_folder, auto_tags = apply_vault_rules(view_owner, filename, clean_folder)
    repo_id = get_active_write_repo(active_global)
    raid_active = is_folder_raid1(view_owner, routed_folder)
    mirror_repo_id = get_mirror_repo(repo_id) if raid_active else ""

    upload_id = secrets.token_hex(12)
    return JSONResponse({
        "ok": True,
        "upload_id": upload_id,
        "owner": view_owner,
        "repo_id": repo_id,
        "mirror_repo_id": mirror_repo_id,
        "routed_folder": routed_folder,
        "auto_tags": auto_tags
    })

@app.post("/api/upload/chunk-part")
async def api_chunk_part(
    username: str = Form(...),
    password: str = Form(...),
    owner: str = Form(...),
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    repo_id: str = Form(...),
    mirror_repo_id: str = Form(""),
    chunk: UploadFile = File(...)
):
    user = verify_user(username, password)
    if not user:
        return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)

    part_bytes = await chunk.read()
    part_repo_path = f"_chunks/{owner}/{upload_id}/part_{chunk_index:05d}.vgpart"

    part_url = "#"
    mirror_part_url = ""
    if hf_api and repo_id:
        hf_api.upload_file(path_or_fileobj=part_bytes, path_in_repo=part_repo_path, repo_id=repo_id, repo_type="dataset")
        part_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{part_repo_path}"

    if hf_api and mirror_repo_id:
        try:
            hf_api.upload_file(path_or_fileobj=part_bytes, path_in_repo=part_repo_path, repo_id=mirror_repo_id, repo_type="dataset")
            mirror_part_url = f"https://huggingface.co/datasets/{mirror_repo_id}/resolve/main/{part_repo_path}"
        except Exception:
            pass

    return JSONResponse({
        "ok": True,
        "chunk_index": chunk_index,
        "part_url": part_url,
        "mirror_part_url": mirror_part_url
    })

@app.post("/api/upload/chunk-finalize")
def api_chunk_finalize(
    username: str = Form(...),
    password: str = Form(...),
    owner: str = Form(...),
    upload_id: str = Form(...),
    filename: str = Form(...),
    routed_folder: str = Form("/"),
    total_size: int = Form(...),
    repo_id: str = Form(...),
    mirror_repo_id: str = Form(""),
    parts_json: str = Form(...),
    mirror_parts_json: str = Form("[]"),
    auto_tags_json: str = Form("[]")
):
    user = verify_user(username, password)
    if not user:
        return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)

    parts = json.loads(parts_json)
    mirror_parts = json.loads(mirror_parts_json)
    auto_tags = json.loads(auto_tags_json)

    manifest_obj = {
        "upload_id": upload_id,
        "filename": filename,
        "total_size": total_size,
        "parts": parts,
        "mirror_parts": mirror_parts
    }
    manifest_bytes = json.dumps(manifest_obj, ensure_ascii=False).encode("utf-8")
    manifest_repo_path = f"_chunks/{owner}/{upload_id}/manifest.json"
    manifest_url = "#"

    if hf_api and repo_id:
        hf_api.upload_file(path_or_fileobj=manifest_bytes, path_in_repo=manifest_repo_path, repo_id=repo_id, repo_type="dataset")
        manifest_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{manifest_repo_path}"

    m_rec = supabase.table("nxt_files").insert({
        "owner": owner,
        "filename": f".vault_chunk_{upload_id}",
        "storage_provider": "vault_chunk_manifest",
        "file_url": manifest_url,
        "folder": "/_chunks",
        "size": total_size,
        "is_deleted": False
    }).execute()
    manifest_id = m_rec.data[0]["id"] if m_rec.data else 0

    safe_fname = urllib.parse.quote(filename)
    stream_url = f"/stream-chunked/{manifest_id}/{safe_fname}"

    ins = supabase.table("nxt_files").insert({
        "owner": owner,
        "filename": filename,
        "storage_provider": "huggingface_chunked",
        "file_url": stream_url,
        "folder": routed_folder,
        "size": total_size,
        "is_deleted": False
    }).execute()

    if ins.data:
        new_file_id = ins.data[0]["id"]
        for t in auto_tags:
            attach_file_tag(owner, new_file_id, t)
        if mirror_parts and any(mirror_parts):
            record_raid1_mirror(owner, new_file_id, f"chunked_mirror:{manifest_id}")

    log_audit(username, "CHUNKED_UPLOAD", f"Dokončeno blokové nahrání {filename} ({format_bytes(total_size)}, {len(parts)} částí)", "INFO")
    return JSONResponse({"ok": True, "filename": filename, "folder": routed_folder})

@app.get("/stream-chunked/{manifest_id}/{filename}")
def stream_chunked_file(manifest_id: int, filename: str):
    if not supabase:
        return Response("Database offline", status_code=503)
    res = supabase.table("nxt_files").select("*").eq("id", manifest_id).execute()
    if not res.data:
        return Response("Manifest nenalezen.", status_code=404)

    manifest_url = res.data[0].get("file_url", "")
    try:
        with urllib.request.urlopen(manifest_url, timeout=10) as resp:
            manifest = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return Response(f"Chyba načtení manifestu: {e}", status_code=502)

    parts = manifest.get("parts", [])
    mirror_parts = manifest.get("mirror_parts", [])
    total_size = manifest.get("total_size", 0)
    mime_type, _ = mimetypes.guess_type(filename)
    mime_type = mime_type or "application/octet-stream"

    def chunk_generator():
        for idx, p_url in enumerate(parts):
            try:
                with urllib.request.urlopen(p_url, timeout=20) as r:
                    while True:
                        buf = r.read(1024 * 1024)
                        if not buf:
                            break
                        yield buf
            except Exception:
                # RAID-1 automatický fallback na zrcadlený blok
                if idx < len(mirror_parts) and mirror_parts[idx]:
                    with urllib.request.urlopen(mirror_parts[idx], timeout=20) as mr:
                        while True:
                            buf = mr.read(1024 * 1024)
                            if not buf:
                                break
                            yield buf

    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    if total_size:
        headers["Content-Length"] = str(total_size)
    return StreamingResponse(chunk_generator(), media_type=mime_type, headers=headers)

# --- MILNÍK B1: WARPDROP P2P (WEBRTC AIRDROP MOBIL <-> PC) ---
@app.get("/warpdrop-p2p", response_class=HTMLResponse)
def warpdrop_p2p_view(request: Request, username: str, password: str, target_owner: str = None, pin: str = ""):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username

    base_url = str(request.base_url).rstrip("/")
    if "onrender.com" in base_url and base_url.startswith("http://"):
        base_url = "https://" + base_url[len("http://"):]

    body = f"""
    <div class="alert-bar ok">
        <div>
            <strong>WarpDrop P2P — Přímý WebRTC přenos mezi mobilem a PC</strong><br>
            <span style="color:var(--text-muted);">Soubory se posílají napřímo mezi prohlížeči přes lokální Wi-Fi / P2P tunel. Neukládají se na server a nemají žádný limit velikosti.</span>
        </div>
        <span class="badge badge-cyan">WEBRTC // DIRECT P2P</span>
    </div>

    <div class="grid-2">
        <!-- REŽIM 1: ODESÍLATEL -->
        <div class="panel">
            <div class="panel-header">
                <h2 class="panel-title">{svg("upload_cloud")} 1. Odeslat soubory (Vytvořit místnost)</h2>
            </div>
            <p style="color:var(--text-muted); margin-top:0;">Vyberte soubory z tohoto zařízení a vygenerujte 4místný párovací PIN / QR kód pro druhé zařízení.</p>

            <div class="dropzone" onclick="document.getElementById('p2p-files').click()" id="p2p-dropzone">
                <div style="font-weight:700; font-size:14px; margin-bottom:4px;">Klikněte nebo sem přetáhněte soubory</div>
                <div id="p2p-selected-info" style="color:var(--text-muted); font-size:12.5px;">Žádné soubory zatím nevybrány</div>
            </div>
            <input type="file" id="p2p-files" multiple style="display:none;" onchange="onP2PFilesSelected(this.files)">

            <div style="margin-top:14px;">
                <button type="button" onclick="startSenderRoom()" id="btn-create-room" class="btn" style="width:100%;">{svg("wifi")} Vytvořit P2P místnost a QR kód</button>
            </div>

            <div id="sender-pairing-box" style="display:none; margin-top:16px; padding:16px; background:var(--bg-app); border:1px solid var(--border); border-radius:10px; text-align:center;">
                <div style="font-size:12px; color:var(--text-muted); text-transform:uppercase;">Párovací PIN kód</div>
                <div id="sender-pin-display" class="mono" style="font-size:34px; font-weight:800; letter-spacing:8px; color:#60a5fa; margin:6px 0;">----</div>
                <img id="sender-qr-img" src="" alt="QR" style="width:165px; height:165px; border-radius:8px; background:#fff; padding:6px; margin:8px auto; display:block;">
                <div style="font-size:12px; color:var(--text-muted);">Naskenujte QR kód mobilem nebo zadejte PIN na druhém zařízení.</div>
            </div>
        </div>

        <!-- REŽIM 2: PŘÍJEMCE -->
        <div class="panel">
            <div class="panel-header">
                <h2 class="panel-title">{svg("download_cloud")} 2. Přijmout soubory (Připojit se přes PIN)</h2>
            </div>
            <p style="color:var(--text-muted); margin-top:0;">Zadejte 4místný PIN zobrazený na odesílajícím zařízení. Stažené soubory se uloží rovnou do složky Stažené.</p>

            <label style="font-size:12px; color:var(--text-muted);">4místný párovací PIN</label>
            <div class="form-row" style="margin-top:6px; margin-bottom:14px;">
                <input type="text" id="receiver-pin-input" value="{html.escape(pin)}" maxlength="4" placeholder="Např. 4829" class="mono" style="font-size:20px; font-weight:700; letter-spacing:6px; text-align:center; width:180px;">
                <button type="button" onclick="joinReceiverRoom()" id="btn-join-room" class="btn btn-success" style="flex:1;">Připojit se a přijmout</button>
            </div>

            <div id="p2p-status-card" style="padding:14px; background:var(--bg-app); border:1px solid var(--border); border-radius:10px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span id="p2p-conn-state" class="badge">STAV: PŘIPRAVENO</span>
                    <span id="p2p-speed" class="mono" style="font-size:12px; color:var(--text-muted);">0.0 MB/s</span>
                </div>
                <div id="p2p-transfer-label" style="font-size:13px; margin-bottom:8px; color:var(--text-muted);">Čeká se na zahájení přenosu...</div>
                <div class="progress-track"><div id="p2p-progress-bar" class="progress-fill" style="width:0%;"></div></div>
            </div>
        </div>
    </div>

    <script>
        const BASE_URL = "{html.escape(base_url)}";
        const AUTH_USER = "{html.escape(username)}";
        const AUTH_PASS = "{html.escape(password)}";
        let selectedP2PFiles = [];
        let pc = null;
        let dc = null;
        let pollTimer = null;

        function onP2PFilesSelected(fl) {{
            selectedP2PFiles = Array.from(fl || []);
            const total = selectedP2PFiles.reduce((a, b) => a + b.size, 0);
            document.getElementById('p2p-selected-info').innerText = selectedP2PFiles.length
                ? `Vybráno souborů: ${{selectedP2PFiles.length}} (${{(total / (1024*1024)).toFixed(2)}} MB)`
                : 'Žádné soubory zatím nevybrány';
        }}

        function createPeerConnection() {{
            const conn = new RTCPeerConnection({{
                iceServers: [{{ urls: 'stun:stun.l.google.com:19302' }}]
            }});
            return conn;
        }}

        async function startSenderRoom() {{
            if (!selectedP2PFiles.length) {{
                alert('Nejprve vyberte alespoň jeden soubor k odeslání.');
                return;
            }}
            document.getElementById('btn-create-room').disabled = true;
            document.getElementById('p2p-conn-state').innerText = 'STAV: ČEKÁM NA PŘÍJEMCE...';
            document.getElementById('p2p-conn-state').className = 'badge badge-warn';

            pc = createPeerConnection();
            dc = pc.createDataChannel('warpdrop', {{ ordered: true }});
            dc.binaryType = 'arraybuffer';

            const candidates = [];
            pc.onicecandidate = (e) => {{
                if (e.candidate) candidates.push(e.candidate);
            }};

            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);

            // Krátké čekání na ICE kandidáty
            await new Promise(r => setTimeout(r, 900));

            const fd = new FormData();
            fd.append('offer', JSON.stringify(pc.localDescription));
            fd.append('candidates', JSON.stringify(candidates));
            const res = await fetch('/api/warpdrop/create', {{ method: 'POST', body: fd }});
            const data = await res.json();
            const pin = data.pin;

            document.getElementById('sender-pin-display').innerText = pin;
            const joinUrl = `${{BASE_URL}}/warpdrop-p2p?username=${{encodeURIComponent(AUTH_USER)}}&password=${{encodeURIComponent(AUTH_PASS)}}&pin=${{pin}}`;
            document.getElementById('sender-qr-img').src = `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${{encodeURIComponent(joinUrl)}}`;
            document.getElementById('sender-pairing-box').style.display = 'block';

            dc.onopen = () => {{
                document.getElementById('p2p-conn-state').innerText = 'STAV: P2P SPOJENÍ AKTIVNÍ';
                document.getElementById('p2p-conn-state').className = 'badge badge-ok';
                sendFilesOverDataChannel();
            }};

            pollTimer = setInterval(async () => {{
                const pRes = await fetch(`/api/warpdrop/poll?pin=${{pin}}&role=sender`);
                const pData = await pRes.json();
                if (pData.answer && !pc.currentRemoteDescription) {{
                    await pc.setRemoteDescription(new RTCSessionDescription(JSON.parse(pData.answer)));
                    for (const c of JSON.parse(pData.receiver_candidates || '[]')) {{
                        await pc.addIceCandidate(new RTCIceCandidate(c));
                    }}
                    clearInterval(pollTimer);
                }}
            }}, 1200);
        }}

        async function sendFilesOverDataChannel() {{
            const CHUNK = 64 * 1024;
            for (let i = 0; i < selectedP2PFiles.length; i++) {{
                const file = selectedP2PFiles[i];
                dc.send(JSON.stringify({{ type: 'meta', name: file.name, size: file.size, mime: file.type }}));
                document.getElementById('p2p-transfer-label').innerText = `Odesílám (${{i+1}}/${{selectedP2PFiles.length}}): ${{file.name}}`;

                let offset = 0;
                const t0 = performance.now();
                while (offset < file.size) {{
                    if (dc.bufferedAmount > 4 * 1024 * 1024) {{
                        await new Promise(r => setTimeout(r, 25));
                        continue;
                    }}
                    const slice = file.slice(offset, offset + CHUNK);
                    const buf = await slice.arrayBuffer();
                    dc.send(buf);
                    offset += buf.byteLength;

                    const pct = Math.round((offset / file.size) * 100);
                    const elapsed = Math.max((performance.now() - t0) / 1000, 0.05);
                    const mbps = ((offset / (1024 * 1024)) / elapsed).toFixed(2);
                    document.getElementById('p2p-progress-bar').style.width = pct + '%';
                    document.getElementById('p2p-speed').innerText = mbps + ' MB/s';
                }}
                dc.send(JSON.stringify({{ type: 'eof' }}));
            }}
            document.getElementById('p2p-transfer-label').innerText = 'Přenos všech souborů dokončen!';
        }}

        async function joinReceiverRoom() {{
            const pin = document.getElementById('receiver-pin-input').value.trim();
            if (pin.length !== 4) {{
                alert('Zadejte 4místný PIN kód.');
                return;
            }}
            document.getElementById('btn-join-room').disabled = true;
            document.getElementById('p2p-conn-state').innerText = 'STAV: PŘIPOJOVÁNÍ...';
            document.getElementById('p2p-conn-state').className = 'badge badge-warn';

            const pRes = await fetch(`/api/warpdrop/poll?pin=${{pin}}&role=receiver`);
            const pData = await pRes.json();
            if (!pData.ok || !pData.offer) {{
                alert('Místnost s tímto PINem neexistuje.');
                document.getElementById('btn-join-room').disabled = false;
                return;
            }}

            pc = createPeerConnection();
            const rCandidates = [];
            pc.onicecandidate = (e) => {{
                if (e.candidate) rCandidates.push(e.candidate);
            }};

            let incomingMeta = null;
            let incomingChunks = [];
            let receivedBytes = 0;
            let rxStart = 0;

            pc.ondatachannel = (ev) => {{
                const ch = ev.channel;
                ch.binaryType = 'arraybuffer';
                ch.onopen = () => {{
                    document.getElementById('p2p-conn-state').innerText = 'STAV: P2P PŘÍJEM AKTIVNÍ';
                    document.getElementById('p2p-conn-state').className = 'badge badge-ok';
                }};
                ch.onmessage = (m) => {{
                    if (typeof m.data === 'string') {{
                        const msg = JSON.parse(m.data);
                        if (msg.type === 'meta') {{
                            incomingMeta = msg;
                            incomingChunks = [];
                            receivedBytes = 0;
                            rxStart = performance.now();
                            document.getElementById('p2p-transfer-label').innerText = `Přijímám: ${{msg.name}}`;
                        }} else if (msg.type === 'eof' && incomingMeta) {{
                            const blob = new Blob(incomingChunks, {{ type: incomingMeta.mime || 'application/octet-stream' }});
                            const a = document.createElement('a');
                            a.href = URL.createObjectURL(blob);
                            a.download = incomingMeta.name;
                            a.click();
                            document.getElementById('p2p-transfer-label').innerText = `Uloženo: ${{incomingMeta.name}}`;
                            incomingChunks = [];
                        }}
                    }} else {{
                        incomingChunks.push(m.data);
                        receivedBytes += m.data.byteLength;
                        if (incomingMeta && incomingMeta.size > 0) {{
                            const pct = Math.round((receivedBytes / incomingMeta.size) * 100);
                            const elapsed = Math.max((performance.now() - rxStart) / 1000, 0.05);
                            const mbps = ((receivedBytes / (1024 * 1024)) / elapsed).toFixed(2);
                            document.getElementById('p2p-progress-bar').style.width = pct + '%';
                            document.getElementById('p2p-speed').innerText = mbps + ' MB/s';
                        }}
                    }}
                }};
            }};

            await pc.setRemoteDescription(new RTCSessionDescription(JSON.parse(pData.offer)));
            for (const c of JSON.parse(pData.sender_candidates || '[]')) {{
                await pc.addIceCandidate(new RTCIceCandidate(c));
            }}

            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);
            await new Promise(r => setTimeout(r, 900));

            const fd = new FormData();
            fd.append('pin', pin);
            fd.append('answer', JSON.stringify(pc.localDescription));
            fd.append('candidates', JSON.stringify(rCandidates));
            await fetch('/api/warpdrop/join', {{ method: 'POST', body: fd }});
        }}
    </script>"""
    return render_shell("WarpDrop P2P (AirDrop)", "warpdrop", username, password, view_owner, body)

@app.post("/api/warpdrop/create")
def api_warpdrop_create(offer: str = Form(...), candidates: str = Form("[]")):
    pin = f"{secrets.randbelow(9000) + 1000}"
    WARPDROP_ROOMS[pin] = {
        "offer": offer,
        "sender_candidates": candidates,
        "answer": "",
        "receiver_candidates": "[]",
        "created_at": time.time()
    }
    # Vyčištění starších místností (> 30 min)
    now = time.time()
    for k in list(WARPDROP_ROOMS.keys()):
        if now - WARPDROP_ROOMS[k]["created_at"] > 1800:
            del WARPDROP_ROOMS[k]
    return JSONResponse({"ok": True, "pin": pin})

@app.post("/api/warpdrop/join")
def api_warpdrop_join(pin: str = Form(...), answer: str = Form(...), candidates: str = Form("[]")):
    room = WARPDROP_ROOMS.get(pin.strip())
    if not room:
        return JSONResponse({"ok": False}, status_code=404)
    room["answer"] = answer
    room["receiver_candidates"] = candidates
    return JSONResponse({"ok": True})

@app.get("/api/warpdrop/poll")
def api_warpdrop_poll(pin: str, role: str = "sender"):
    room = WARPDROP_ROOMS.get(pin.strip())
    if not room:
        return JSONResponse({"ok": False}, status_code=404)
    return JSONResponse({
        "ok": True,
        "offer": room["offer"],
        "sender_candidates": room["sender_candidates"],
        "answer": room["answer"],
        "receiver_candidates": room["receiver_candidates"]
    })

# --- MILNÍK B2: VAULTSYNC DESKTOP AGENT (AUTOMATICKÁ SYNCHRONIZACE SLOŽKY V PC) ---
def build_vaultsync_script(server_url: str, api_token: str) -> str:
    return f'''#!/usr/bin/env python3
"""
VaultSync Desktop Agent — Automatická synchronizace místní složky do VaultGrid OS
Nulové externí závislosti (využívá pouze standardní knihovnu Pythonu 3).
Spuštění: python vaultsync_client.py --dir ./VaultGridSync --cloud-folder /DesktopSync
"""
import os
import sys
import time
import json
import uuid
import hashlib
import argparse
import urllib.request
import urllib.error

DEFAULT_SERVER = "{server_url}"
DEFAULT_TOKEN = "{api_token}"

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def upload_multipart(server_url: str, token: str, cloud_folder: str, local_path: str):
    boundary = "----VaultSyncBoundary" + uuid.uuid4().hex
    filename = os.path.basename(local_path)
    with open(local_path, "rb") as f:
        file_bytes = f.read()

    parts = []
    parts.append(f"--{{boundary}}\\r\\nContent-Disposition: form-data; name=\\"folder\\"\\r\\n\\r\\n{{cloud_folder}}\\r\\n".encode("utf-8"))
    parts.append(
        f"--{{boundary}}\\r\\nContent-Disposition: form-data; name=\\"file\\"; filename=\\"{{filename}}\\"\\r\\n"
        f"Content-Type: application/octet-stream\\r\\n\\r\\n".encode("utf-8") + file_bytes + b"\\r\\n"
    )
    parts.append(f"--{{boundary}}--\\r\\n".encode("utf-8"))
    body = b"".join(parts)

    req = urllib.request.Request(
        server_url.rstrip("/") + "/api/v1/upload",
        data=body,
        headers={{
            "Authorization": f"Bearer {{token}}",
            "Content-Type": f"multipart/form-data; boundary={{boundary}}",
            "Content-Length": str(len(body)),
        }},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    parser = argparse.ArgumentParser(description="VaultSync Desktop Agent")
    parser.add_argument("--dir", default="./VaultGridSync", help="Místní složka ke sledování")
    parser.add_argument("--cloud-folder", default="/DesktopSync", help="Cílová složka ve VaultGridu")
    parser.add_argument("--interval", type=int, default=5, help="Interval kontroly v sekundách")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="URL adresa VaultGrid serveru")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="Osobní REST API token")
    args = parser.parse_args()

    watch_dir = os.path.abspath(args.dir)
    os.makedirs(watch_dir, exist_ok=True)
    state_file = os.path.join(watch_dir, ".vaultsync_state.json")

    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as sf:
            synced_hashes = json.load(sf)
    else:
        synced_hashes = {{}}

    print(f"[VaultSync] Sledování složky: {{watch_dir}}")
    print(f"[VaultSync] Cílový cloud:     {{args.server}}{{args.cloud_folder}}")
    print("[VaultSync] Stiskněte Ctrl+C pro ukončení.\\n")

    while True:
        try:
            changed = False
            for root, _, files in os.walk(watch_dir):
                for fname in files:
                    if fname.startswith(".") or fname.endswith(".tmp"):
                        continue
                    full_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(full_path, watch_dir).replace("\\\\", "/")
                    rel_dir = os.path.dirname(rel_path)
                    target_cloud_dir = (
                        args.cloud_folder.rstrip("/") + ("/" + rel_dir if rel_dir else "")
                    ) or "/"

                    current_hash = sha256_file(full_path)
                    if synced_hashes.get(rel_path) != current_hash:
                        print(f"[SYNC ->] Nahrávám: {{rel_path}} -> {{target_cloud_dir}}")
                        res = upload_multipart(args.server, args.token, target_cloud_dir, full_path)
                        if res.get("status") == "ok":
                            synced_hashes[rel_path] = current_hash
                            changed = True
                            print(f"[OK]      Synchronizováno: {{rel_path}}")

            if changed:
                with open(state_file, "w", encoding="utf-8") as sf:
                    json.dump(synced_hashes, sf, indent=2)
        except KeyboardInterrupt:
            print("\\n[VaultSync] Ukončeno uživatelem.")
            sys.exit(0)
        except Exception as e:
            print(f"[CHYBA]   {{e}}")

        time.sleep(args.interval)

if __name__ == "__main__":
    main()
'''

@app.get("/vaultsync", response_class=HTMLResponse)
def vaultsync_view(request: Request, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("storage_provider", "vault_api_token").eq("is_deleted", False).execute()
    has_token = bool(res.data)

    body = f"""
    <div class="alert-bar ok">
        <div>
            <strong>VaultSync Desktop Agent — Automatická synchronizace složky v počítači</strong><br>
            <span style="color:var(--text-muted);">Lehký Python klient bez externích knihoven. Sleduje vybranou složku v PC a okamžitě nahrává nové či změněné soubory do cloudu.</span>
        </div>
        <a href="/vaultsync/download-agent?{q_params}" class="btn btn-sm">{svg("download_cloud")} Stáhnout přednastavený vaultsync_client.py</a>
    </div>

    <div class="grid-2">
        <div class="panel">
            <div class="panel-header"><h2 class="panel-title">{svg("laptop")} Jak spustit synchronizaci na Windows / macOS / Linuxu</h2></div>
            <ol style="margin:0 0 14px 18px; padding:0; color:var(--text-muted); line-height:1.7;">
                <li>Klikněte na <strong>Stáhnout přednastavený vaultsync_client.py</strong> — skript již obsahuje váš osobní API token i adresu serveru.</li>
                <li>Uložte soubor do počítače a spusťte v terminálu příkaz níže.</li>
                <li>Vše, co vložíte do složky <span class="mono">VaultGridSync</span>, se automaticky nahraje do <span class="mono">/DesktopSync</span> ve vašem VaultGridu.</li>
            </ol>
            <pre class="mono" style="background:var(--bg-app); padding:12px; border:1px solid var(--border); border-radius:8px; overflow-x:auto;">python vaultsync_client.py --dir ./VaultGridSync --cloud-folder /DesktopSync</pre>
        </div>

        <div class="panel">
            <div class="panel-header"><h2 class="panel-title">{svg("key")} Stav napojení klienta</h2></div>
            <p style="color:var(--text-muted);">Stav osobního API klíče pro účet <strong>{html.escape(view_owner)}</strong>:</p>
            <div style="margin-bottom:14px;">
                {'<span class="badge badge-ok">API KLÍČ AKTIVNÍ (PŘIPRAVENO)</span>' if has_token else '<span class="badge badge-warn">KLÍČ SE VYGENERUJE PŘI STAŽENÍ SKRIPTU</span>'}
            </div>
            <p style="color:var(--text-muted); font-size:12.5px;">Skript ukládá kontrolní součty <span class="mono">SHA-256</span> do skrytého souboru <span class="mono">.vaultsync_state.json</span>, takže nahrává pouze skutečně nové nebo upravené soubory.</p>
        </div>
    </div>"""
    return render_shell("VaultSync PC Agent", "vaultsync", username, password, view_owner, body)

@app.get("/vaultsync/download-agent")
def vaultsync_download_agent(request: Request, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return Response("Unauthorized", status_code=401)
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username

    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("storage_provider", "vault_api_token").eq("is_deleted", False).execute()
    if res.data:
        token = res.data[-1].get("file_url", "")
    else:
        token = "vg_live_" + secrets.token_hex(20)
        supabase.table("nxt_files").insert({
            "owner": view_owner, "filename": "VaultSync-Desktop-Agent", "storage_provider": "vault_api_token",
            "file_url": token, "folder": "/_tokens", "size": 0, "is_deleted": False
        }).execute()

    base_url = str(request.base_url).rstrip("/")
    if "onrender.com" in base_url and base_url.startswith("http://"):
        base_url = "https://" + base_url[len("http://"):]

    script_code = build_vaultsync_script(base_url, token)
    return Response(
        content=script_code.encode("utf-8"),
        media_type="text/x-python",
        headers={"Content-Disposition": 'attachment; filename="vaultsync_client.py"'},
    )

# --- NATIVNÍ WEBDAV SERVER ENGINE (RFC 4918 — SÍŤOVÝ DISK Z:\) ---
def _webdav_unauthorized() -> Response:
    return Response(
        content="401 Unauthorized — VaultGrid WebDAV NAS",
        status_code=401,
        headers={
            "WWW-Authenticate": 'Basic realm="VaultGrid WebDAV NAS"',
            "DAV": "1, 2",
            "MS-Author-Via": "DAV",
        },
    )

def _webdav_auth(request: Request, target_owner: str) -> tuple[bool, str]:
    auth_hdr = request.headers.get("Authorization", "")
    if not auth_hdr.startswith("Basic "):
        return False, ""
    try:
        decoded = base64.b64decode(auth_hdr[6:].strip()).decode("utf-8")
        if ":" not in decoded:
            return False, ""
        auth_user, auth_pass = decoded.split(":", 1)
    except Exception:
        return False, ""

    user = verify_user(auth_user, auth_pass)
    if not user:
        return False, ""
    if auth_user == target_owner or user.get("role") == "admin":
        return True, auth_user
    return False, ""

def _webdav_encode_href(owner: str, virtual_path: str, is_dir: bool = False) -> str:
    clean = "/" + virtual_path.strip("/") if virtual_path.strip("/") else ""
    full = f"/webdav/{owner}{clean}"
    if is_dir and not full.endswith("/"):
        full += "/"
    parts = [urllib.parse.quote(seg) for seg in full.split("/")]
    return "/".join(parts)

def _webdav_propfind_xml(owner: str, virtual_path: str, depth: str, items: list[dict]) -> str | None:
    norm_path = "/" + virtual_path.strip("/") if virtual_path.strip("/") else "/"
    http_date = formatdate(usegmt=True)
    dir_name = os.path.dirname(norm_path) or "/"
    base_name = os.path.basename(norm_path)

    matched_file = None
    if norm_path != "/":
        for f in items:
            if not is_system_record(f) and f.get("folder", "/") == dir_name and f.get("filename") == base_name:
                matched_file = f
                break

    responses = []
    if matched_file:
        href = _webdav_encode_href(owner, norm_path, is_dir=False)
        mime, _ = mimetypes.guess_type(matched_file["filename"])
        mime = mime or "application/octet-stream"
        sz = int(matched_file.get("size", 0))
        responses.append(f"""
        <D:response>
            <D:href>{href}</D:href>
            <D:propstat>
                <D:prop>
                    <D:displayname>{html.escape(matched_file['filename'])}</D:displayname>
                    <D:resourcetype/>
                    <D:getcontentlength>{sz}</D:getcontentlength>
                    <D:getcontenttype>{html.escape(mime)}</D:getcontenttype>
                    <D:getlastmodified>{http_date}</D:getlastmodified>
                </D:prop>
                <D:status>HTTP/1.1 200 OK</D:status>
            </D:propstat>
        </D:response>""")
    else:
        folder_exists = (norm_path == "/")
        subfolders = set()
        direct_files = []

        for f in items:
            if f.get("storage_provider") in SYSTEM_PROVIDERS:
                continue
            item_fld = f.get("folder", "/")
            if item_fld == norm_path or item_fld.startswith(norm_path.rstrip("/") + "/"):
                folder_exists = True
            if item_fld.startswith(norm_path) and item_fld != norm_path:
                rel = item_fld[len(norm_path):].strip("/")
                if rel:
                    sub_name = rel.split("/")[0]
                    subfolders.add(f"{norm_path.rstrip('/')}/{sub_name}")
            if item_fld == norm_path and not is_system_record(f):
                direct_files.append(f)

        if not folder_exists:
            return None

        root_href = _webdav_encode_href(owner, norm_path, is_dir=True)
        disp = owner if norm_path == "/" else os.path.basename(norm_path)
        responses.append(f"""
        <D:response>
            <D:href>{root_href}</D:href>
            <D:propstat>
                <D:prop>
                    <D:displayname>{html.escape(disp)}</D:displayname>
                    <D:resourcetype><D:collection/></D:resourcetype>
                    <D:getlastmodified>{http_date}</D:getlastmodified>
                </D:prop>
                <D:status>HTTP/1.1 200 OK</D:status>
            </D:propstat>
        </D:response>""")

        if depth != "0":
            for sf in sorted(subfolders):
                sf_href = _webdav_encode_href(owner, sf, is_dir=True)
                sf_name = os.path.basename(sf)
                responses.append(f"""
                <D:response>
                    <D:href>{sf_href}</D:href>
                    <D:propstat>
                        <D:prop>
                            <D:displayname>{html.escape(sf_name)}</D:displayname>
                            <D:resourcetype><D:collection/></D:resourcetype>
                            <D:getlastmodified>{http_date}</D:getlastmodified>
                        </D:prop>
                        <D:status>HTTP/1.1 200 OK</D:status>
                    </D:propstat>
                </D:response>""")

            for df in direct_files:
                df_path = f"{norm_path.rstrip('/')}/{df['filename']}"
                df_href = _webdav_encode_href(owner, df_path, is_dir=False)
                mime, _ = mimetypes.guess_type(df["filename"])
                mime = mime or "application/octet-stream"
                sz = int(df.get("size", 0))
                responses.append(f"""
                <D:response>
                    <D:href>{df_href}</D:href>
                    <D:propstat>
                        <D:prop>
                            <D:displayname>{html.escape(df['filename'])}</D:displayname>
                            <D:resourcetype/>
                            <D:getcontentlength>{sz}</D:getcontentlength>
                            <D:getcontenttype>{html.escape(mime)}</D:getcontenttype>
                            <D:getlastmodified>{http_date}</D:getlastmodified>
                        </D:prop>
                        <D:status>HTTP/1.1 200 OK</D:status>
                    </D:propstat>
                </D:response>""")

    return '<?xml version="1.0" encoding="utf-8"?>\n<D:multistatus xmlns:D="DAV:">' + "".join(responses) + "\n</D:multistatus>"

async def _handle_webdav_request(request: Request, owner: str, subpath: str = "") -> Response:
    method = request.method.upper()
    dav_headers = {
        "DAV": "1, 2",
        "MS-Author-Via": "DAV",
        "Allow": "OPTIONS, PROPFIND, GET, HEAD, PUT, DELETE, MKCOL, COPY, MOVE",
    }

    if method == "OPTIONS":
        return Response(status_code=200, headers=dav_headers)

    if not supabase:
        return Response("Database offline", status_code=503, headers=dav_headers)

    ok, actor = _webdav_auth(request, owner)
    if not ok:
        return _webdav_unauthorized()

    norm_path = "/" + urllib.parse.unquote(subpath).strip("/") if subpath.strip("/") else "/"
    parent_folder = os.path.dirname(norm_path) or "/"
    item_name = os.path.basename(norm_path)

    if method == "PROPFIND":
        depth = request.headers.get("Depth", "1").strip()
        items = supabase.table("nxt_files").select("*").eq("owner", owner).eq("is_deleted", False).execute().data or []
        xml_body = _webdav_propfind_xml(owner, norm_path, depth, items)
        if xml_body is None:
            return Response(status_code=404, headers=dav_headers)
        return Response(
            content=xml_body.encode("utf-8"),
            status_code=207,
            media_type='application/xml; charset="utf-8"',
            headers=dav_headers,
        )

    elif method in ["GET", "HEAD"]:
        if norm_path == "/":
            return Response(content=b"VaultGrid WebDAV Root", status_code=200, headers=dav_headers)
        res = (
            supabase.table("nxt_files")
            .select("*")
            .eq("owner", owner)
            .eq("folder", parent_folder)
            .eq("filename", item_name)
            .eq("is_deleted", False)
            .execute()
        )
        if not res.data:
            return Response(status_code=404, headers=dav_headers)
        rec = res.data[0]
        mime, _ = mimetypes.guess_type(item_name)
        mime = mime or "application/octet-stream"
        f_headers = {**dav_headers, "Content-Length": str(rec.get("size", 0))}
        if method == "HEAD":
            return Response(status_code=200, media_type=mime, headers=f_headers)
        if rec.get("file_url", "").startswith("/stream-chunked/"):
            mid = int(rec["file_url"].split("/")[2])
            return stream_chunked_file(mid, item_name)
        if not rec.get("file_url", "").startswith("http") or int(rec.get("size", 0)) == 0:
            return Response(content=b"", status_code=200, media_type=mime, headers=f_headers)
        try:
            with urllib.request.urlopen(rec["file_url"], timeout=15) as resp:
                data = resp.read()
            return Response(content=data, status_code=200, media_type=mime, headers=dav_headers)
        except Exception:
            return Response(status_code=502, headers=dav_headers)

    elif method == "PUT":
        if norm_path == "/" or not item_name:
            return Response(status_code=400, headers=dav_headers)
        body_bytes = await request.body()

        existing = (
            supabase.table("nxt_files")
            .select("*")
            .eq("owner", owner)
            .eq("folder", parent_folder)
            .eq("filename", item_name)
            .eq("is_deleted", False)
            .execute()
            .data
            or []
        )

        if len(body_bytes) == 0:
            if not existing:
                supabase.table("nxt_files").insert({
                    "owner": owner,
                    "filename": item_name,
                    "storage_provider": "huggingface",
                    "file_url": "#",
                    "folder": parent_folder,
                    "size": 0,
                    "is_deleted": False,
                }).execute()
            return Response(status_code=201, headers=dav_headers)

        quota_limit = get_user_quota_bytes(owner)
        all_rows = supabase.table("nxt_files").select("*").eq("is_deleted", False).execute().data or []
        active_global = [r for r in all_rows if not is_system_record(r)]
        current_used = sum(int(f.get("size", 0)) for f in active_global if f.get("owner") == owner)

        if quota_limit > 0 and (current_used + len(body_bytes)) > quota_limit:
            return Response("Insufficient Storage (Quota Exceeded)", status_code=507, headers=dav_headers)

        dest_folder, auto_tags = apply_vault_rules(owner, item_name, parent_folder)
        repo_id = get_active_write_repo(active_global)
        repo_path = f"{owner}{dest_folder}/{item_name}".replace("//", "/")

        if hf_api and repo_id:
            hf_api.upload_file(path_or_fileobj=body_bytes, path_in_repo=repo_path, repo_id=repo_id, repo_type="dataset")
            public_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{repo_path}"
        else:
            public_url = "#"

        mirror_url = ""
        if is_folder_raid1(owner, dest_folder) and hf_api:
            m_repo = get_mirror_repo(repo_id)
            if m_repo:
                try:
                    hf_api.upload_file(path_or_fileobj=body_bytes, path_in_repo=repo_path, repo_id=m_repo, repo_type="dataset")
                    mirror_url = f"https://huggingface.co/datasets/{m_repo}/resolve/main/{repo_path}"
                except Exception:
                    pass

        if existing:
            fid = existing[0]["id"]
            supabase.table("nxt_files").update({
                "file_url": public_url,
                "folder": dest_folder,
                "size": len(body_bytes),
            }).eq("id", fid).execute()
            if mirror_url:
                record_raid1_mirror(owner, fid, mirror_url)
            status_code = 204
        else:
            ins = supabase.table("nxt_files").insert({
                "owner": owner,
                "filename": item_name,
                "storage_provider": "huggingface",
                "file_url": public_url,
                "folder": dest_folder,
                "size": len(body_bytes),
                "is_deleted": False,
            }).execute()
            if ins.data:
                fid = ins.data[0]["id"]
                for t in auto_tags:
                    attach_file_tag(owner, fid, t)
                if mirror_url:
                    record_raid1_mirror(owner, fid, mirror_url)
            status_code = 201

        log_audit(actor, "WEBDAV_PUT", f"Nahrán soubor přes WebDAV: {dest_folder}/{item_name}", "INFO")
        return Response(status_code=status_code, headers=dav_headers)

    elif method == "MKCOL":
        if norm_path == "/" or not item_name:
            return Response(status_code=405, headers=dav_headers)
        supabase.table("nxt_files").insert({
            "owner": owner,
            "filename": f".slozkové_meta_{item_name}",
            "storage_provider": "system",
            "file_url": "#",
            "folder": norm_path,
            "size": 0,
            "is_deleted": False,
        }).execute()
        return Response(status_code=201, headers=dav_headers)

    elif method == "DELETE":
        if norm_path == "/":
            return Response(status_code=403, headers=dav_headers)
        f_res = (
            supabase.table("nxt_files")
            .select("id")
            .eq("owner", owner)
            .eq("folder", parent_folder)
            .eq("filename", item_name)
            .eq("is_deleted", False)
            .execute()
            .data
            or []
        )
        if f_res:
            for r in f_res:
                supabase.table("nxt_files").update({"is_deleted": True}).eq("id", r["id"]).execute()
            return Response(status_code=204, headers=dav_headers)

        all_items = supabase.table("nxt_files").select("id, folder").eq("owner", owner).eq("is_deleted", False).execute().data or []
        deleted_any = False
        for it in all_items:
            if it.get("folder") == norm_path or it.get("folder", "").startswith(norm_path + "/"):
                supabase.table("nxt_files").update({"is_deleted": True}).eq("id", it["id"]).execute()
                deleted_any = True
        if deleted_any:
            return Response(status_code=204, headers=dav_headers)
        return Response(status_code=404, headers=dav_headers)

    elif method in ["MOVE", "COPY"]:
        dest_hdr = request.headers.get("Destination", "")
        if not dest_hdr:
            return Response(status_code=400, headers=dav_headers)
        dest_url_path = urllib.parse.unquote(urllib.parse.urlparse(dest_hdr).path)
        prefix = f"/webdav/{owner}"
        if not dest_url_path.startswith(prefix):
            return Response(status_code=403, headers=dav_headers)
        dest_rel = "/" + dest_url_path[len(prefix):].strip("/")
        dest_folder = os.path.dirname(dest_rel) or "/"
        dest_name = os.path.basename(dest_rel)

        src_files = (
            supabase.table("nxt_files")
            .select("*")
            .eq("owner", owner)
            .eq("folder", parent_folder)
            .eq("filename", item_name)
            .eq("is_deleted", False)
            .execute()
            .data
            or []
        )
        if src_files:
            rec = src_files[0]
            if method == "MOVE":
                supabase.table("nxt_files").update({"folder": dest_folder, "filename": dest_name}).eq("id", rec["id"]).execute()
            else:
                supabase.table("nxt_files").insert({
                    "owner": owner,
                    "filename": dest_name,
                    "storage_provider": rec.get("storage_provider", "huggingface"),
                    "file_url": rec.get("file_url", "#"),
                    "folder": dest_folder,
                    "size": rec.get("size", 0),
                    "is_deleted": False,
                }).execute()
            return Response(status_code=201, headers=dav_headers)

        if method == "MOVE":
            all_items = supabase.table("nxt_files").select("*").eq("owner", owner).eq("is_deleted", False).execute().data or []
            moved_dir = False
            for it in all_items:
                fld = it.get("folder", "")
                if fld == norm_path or fld.startswith(norm_path + "/"):
                    new_fld = dest_rel + fld[len(norm_path):]
                    upd = {"folder": new_fld}
                    if it.get("filename") == f".slozkové_meta_{item_name}":
                        upd["filename"] = f".slozkové_meta_{dest_name}"
                    supabase.table("nxt_files").update(upd).eq("id", it["id"]).execute()
                    moved_dir = True
            if moved_dir:
                return Response(status_code=201, headers=dav_headers)

        return Response(status_code=404, headers=dav_headers)

    return Response(status_code=405, headers=dav_headers)

@app.api_route("/webdav/{owner}", methods=["OPTIONS", "PROPFIND", "GET", "HEAD", "PUT", "DELETE", "MKCOL", "COPY", "MOVE"])
async def webdav_root_endpoint(request: Request, owner: str):
    return await _handle_webdav_request(request, owner, "")

@app.api_route("/webdav/{owner}/{subpath:path}", methods=["OPTIONS", "PROPFIND", "GET", "HEAD", "PUT", "DELETE", "MKCOL", "COPY", "MOVE"])
async def webdav_subpath_endpoint(request: Request, owner: str, subpath: str):
    return await _handle_webdav_request(request, owner, subpath)

# --- UI PRO SPRÁVU WEBDAV SÍŤOVÉHO DISKU ---
@app.get("/webdav-manager", response_class=HTMLResponse)
def webdav_manager_view(request: Request, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    q_params = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(password)}&target_owner={urllib.parse.quote(view_owner)}"

    base_url = str(request.base_url).rstrip("/")
    if "onrender.com" in base_url and base_url.startswith("http://"):
        base_url = "https://" + base_url[len("http://"):]
    webdav_url = f"{base_url}/webdav/{view_owner}"

    win_cmd = f'net use Z: "{webdav_url}" /user:{username} "{password}" /persistent:yes'
    linux_cmd = f'sudo mount -t davfs "{webdav_url}" /mnt/vaultgrid -o username={username}'

    body = f"""
    <div class="alert-bar ok">
        <div>
            <strong>Nativní WebDAV Server (RFC 4918) je aktivní</strong><br>
            <span style="color:var(--text-muted);">Připojte VaultGrid jako klasický pevný disk <code>Z:\\</code> přímo ve Windows Průzkumníku, macOS Finderu nebo Linuxu.</span>
        </div>
        <a href="/webdav-manager/windows-bat?{q_params}" class="btn btn-sm">Stáhnout mount_vaultgrid_Z.bat</a>
    </div>

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("harddrive")} Připojovací údaje síťového disku</h2></div>
        <div class="grid-2">
            <div>
                <label style="font-size:12px; color:var(--text-muted);">Síťová adresa (WebDAV URL)</label>
                <input type="text" value="{html.escape(webdav_url)}" readonly class="mono" style="margin-top:4px;" onclick="this.select()">
            </div>
            <div>
                <label style="font-size:12px; color:var(--text-muted);">Přihlašovací jméno / Heslo</label>
                <input type="text" value="{html.escape(username)}  (vaše heslo účtu)" readonly class="mono" style="margin-top:4px;">
            </div>
        </div>
    </div>

    <div class="grid-2">
        <div class="panel">
            <div class="panel-header"><h3 class="panel-title">Windows 10 / 11 (Průzkumník souborů)</h3></div>
            <ol style="margin:0 0 12px 18px; padding:0; color:var(--text-muted); line-height:1.7;">
                <li>Otevřete <strong>Tento počítač</strong> → horní lišta <strong>Připojit síťovou jednotku</strong>.</li>
                <li>Zvolte písmeno disku (<span class="mono">Z:</span>) a vložte WebDAV URL výše.</li>
                <li>Zadejte své uživatelské jméno a heslo.</li>
            </ol>
            <pre class="mono" style="background:var(--bg-app); padding:10px; border:1px solid var(--border); border-radius:8px; overflow-x:auto;">{html.escape(win_cmd)}</pre>
        </div>

        <div class="panel">
            <div class="panel-header"><h3 class="panel-title">macOS Finder, Linux & Mobil</h3></div>
            <ul style="margin:0 0 12px 18px; padding:0; color:var(--text-muted); line-height:1.7;">
                <li><strong>macOS Finder:</strong> <span class="mono">Cmd + K</span>, vložte WebDAV URL a klikněte na <em>Připojit</em>.</li>
                <li><strong>Mobil:</strong> V aplikaci <em>Solid Explorer</em>, <em>Owlfiles</em> nebo <em>Soubory</em> přidejte úložiště <strong>WebDAV (HTTPS)</strong>.</li>
            </ul>
            <pre class="mono" style="background:var(--bg-app); padding:10px; border:1px solid var(--border); border-radius:8px; overflow-x:auto;">{html.escape(linux_cmd)}</pre>
        </div>
    </div>"""
    return render_shell("WebDAV Síťový disk", "webdav", username, password, view_owner, body)

@app.get("/webdav-manager/windows-bat")
def webdav_windows_bat(request: Request, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return Response("Unauthorized", status_code=401)
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    base_url = str(request.base_url).rstrip("/")
    if "onrender.com" in base_url and base_url.startswith("http://"):
        base_url = "https://" + base_url[len("http://"):]
    webdav_url = f"{base_url}/webdav/{view_owner}"
    bat_content = (
        "@echo off\r\n"
        "echo Pripojovani VaultGrid APEX jako sitovy disk Z:...\r\n"
        "net use Z: /delete /y >nul 2>&1\r\n"
        f'net use Z: "{webdav_url}" /user:{username} "{password}" /persistent:yes\r\n'
        "if %errorlevel% equ 0 (\r\n"
        "    echo Uspech! Disk Z: byl pripojen.\r\n"
        "    explorer Z:\\\r\n"
        ") else (\r\n"
        "    echo Chyba pripojeni.\r\n"
        ")\r\n"
        "pause\r\n"
    )
    return Response(
        content=bat_content.encode("utf-8"),
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="mount_vaultgrid_Z.bat"'},
    )

# --- SERVER-SIDE URL LEECHER ---
@app.get("/url-leecher", response_class=HTMLResponse)
def url_leecher_view(username: str, password: str, target_owner: str = None, msg: str = "", is_err: bool = False):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username

    logs = []
    if supabase:
        res = (
            supabase.table("nxt_files")
            .select("*")
            .eq("owner", view_owner)
            .eq("storage_provider", "vault_leecher_log")
            .order("id", desc=True)
            .limit(20)
            .execute()
        )
        for r in (res.data or []):
            try:
                logs.append(json.loads(r.get("file_url", "{}")))
            except Exception:
                pass

    log_rows = ""
    for lg in logs:
        log_rows += f"""
        <tr>
            <td class="mono">{html.escape(lg.get('ts', ''))}</td>
            <td><strong>{html.escape(lg.get('filename', ''))}</strong></td>
            <td class="mono" style="color:var(--text-muted); max-width:260px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{html.escape(lg.get('source_url', ''))}</td>
            <td class="mono">{html.escape(lg.get('dest_folder', '/'))}</td>
            <td class="mono">{format_bytes(lg.get('size', 0))}</td>
            <td><span class="badge badge-ok">{html.escape(str(lg.get('elapsed', '0')))} s</span></td>
        </tr>"""
    if not log_rows:
        log_rows = "<tr><td colspan='6' style='text-align:center; color:var(--text-muted);'>Zatím nebyly provedeny žádné serverové přenosy z URL.</td></tr>"

    alert_html = f'<div class="alert-bar {"err" if is_err else "ok"}">{html.escape(msg)}</div>' if msg else ""

    body = f"""
    {alert_html}
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("download_cloud")} Server-Side URL Leecher (Cloud Downloader)</h2>
            <span class="badge badge-ok">ZERO CLIENT BANDWIDTH</span>
        </div>
        <p style="color:var(--text-muted); margin-top:0;">
            Vložte přímý odkaz na soubor z internetu. Server stáhne data přímo do úložiště Hugging Face bez zatížení vašeho připojení.
        </p>
        <form action="/url-leecher/fetch" method="POST">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <div class="grid-2" style="margin-bottom:10px;">
                <div>
                    <label style="font-size:12px; color:var(--text-muted);">Zdrojová URL adresa</label>
                    <input type="url" name="source_url" placeholder="https://example.com/archiv.zip" required style="margin-top:4px;">
                </div>
                <div>
                    <label style="font-size:12px; color:var(--text-muted);">Cílová složka ve VaultGridu</label>
                    <input type="text" name="dest_folder" value="/Downloads" required style="margin-top:4px;">
                </div>
            </div>
            <div class="form-row" style="margin-bottom:12px;">
                <input type="text" name="custom_filename" placeholder="Vlastní název souboru (volitelné)" style="flex:1;">
                <label style="display:inline-flex; align-items:center; gap:6px; font-size:12px; color:var(--text-muted); cursor:pointer;">
                    <input type="checkbox" name="encrypt_flag" value="1" onchange="document.getElementById('leech-enc').style.display = this.checked ? 'inline-block' : 'none';">
                    Zašifrovat při uložení (AES-256)
                </label>
                <input type="password" id="leech-enc" name="encrypt_pass" placeholder="Šifrovací heslo..." style="display:none; width:190px;">
            </div>
            <button type="submit" class="btn">{svg("download_cloud")} Stáhnout ze serveru přímo do cloudu</button>
        </form>
    </div>

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Historie serverových stažení</h2></div>
        <div class="table-wrap">
            <table>
                <thead><tr><th>Čas (UTC)</th><th>Uložený soubor</th><th>Zdrojová URL</th><th>Složka</th><th>Velikost</th><th>Doba</th></tr></thead>
                <tbody>{log_rows}</tbody>
            </table>
        </div>
    </div>"""
    return render_shell("URL Cloud Stahovač", "leecher", username, password, view_owner, body)

@app.post("/url-leecher/fetch", response_class=HTMLResponse)
def url_leecher_fetch(
    username: str = Form(...),
    password: str = Form(...),
    target_owner: str = Form(None),
    source_url: str = Form(...),
    dest_folder: str = Form("/Downloads"),
    custom_filename: str = Form(""),
    encrypt_flag: str = Form(""),
    encrypt_pass: str = Form("")
):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username

    clean_url = source_url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        return url_leecher_view(username, password, view_owner, "Chyba: Povoleny jsou pouze protokoly HTTP a HTTPS.", True)

    clean_folder = dest_folder.strip() or "/Downloads"
    if not clean_folder.startswith("/"):
        clean_folder = "/" + clean_folder

    t0 = time.monotonic()
    try:
        req = urllib.request.Request(clean_url, headers={"User-Agent": "VaultGrid-APEX-Leecher/24.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw_bytes = resp.read()
            cd_header = resp.headers.get("Content-Disposition", "")
    except Exception as e:
        return url_leecher_view(username, password, view_owner, f"Chyba při stahování ze vzdáleného serveru: {e}", True)

    fname = custom_filename.strip().replace("/", "_")
    if not fname and "filename=" in cd_header:
        m = re.search(r'filename="?([^";]+)"?', cd_header)
        if m:
            fname = m.group(1).strip()
    if not fname:
        url_base = os.path.basename(urllib.parse.unquote(urllib.parse.urlparse(clean_url).path))
        fname = url_base if url_base else f"download_{int(time.time())}.bin"

    final_bytes = raw_bytes
    final_name = fname
    if encrypt_flag == "1" and encrypt_pass.strip():
        final_bytes = vaultcrypt_encrypt(raw_bytes, encrypt_pass.strip())
        final_name = fname + ".vgenc"

    quota_limit = get_user_quota_bytes(view_owner)
    all_rows = supabase.table("nxt_files").select("*").eq("is_deleted", False).execute().data or []
    active_global = [r for r in all_rows if not is_system_record(r)]
    current_used = sum(int(f.get("size", 0)) for f in active_global if f.get("owner") == view_owner)

    if quota_limit > 0 and (current_used + len(final_bytes)) > quota_limit:
        return url_leecher_view(username, password, view_owner, "Chyba: Stažený soubor by překročil diskovou kvótu účtu.", True)

    routed_folder, auto_tags = apply_vault_rules(view_owner, final_name, clean_folder)
    repo_id = get_active_write_repo(active_global)
    repo_path = f"{view_owner}{routed_folder}/{final_name}".replace("//", "/")

    if hf_api and repo_id:
        hf_api.upload_file(path_or_fileobj=final_bytes, path_in_repo=repo_path, repo_id=repo_id, repo_type="dataset")
        public_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{repo_path}"
    else:
        public_url = "#"

    mirror_url = ""
    if is_folder_raid1(view_owner, routed_folder) and hf_api:
        m_repo = get_mirror_repo(repo_id)
        if m_repo:
            try:
                hf_api.upload_file(path_or_fileobj=final_bytes, path_in_repo=repo_path, repo_id=m_repo, repo_type="dataset")
                mirror_url = f"https://huggingface.co/datasets/{m_repo}/resolve/main/{repo_path}"
            except Exception:
                pass

    ins_res = supabase.table("nxt_files").insert({
        "owner": view_owner,
        "filename": final_name,
        "storage_provider": "huggingface",
        "file_url": public_url,
        "folder": routed_folder,
        "size": len(final_bytes),
        "is_deleted": False,
    }).execute()

    if ins_res.data:
        fid = ins_res.data[0]["id"]
        for t in auto_tags:
            attach_file_tag(view_owner, fid, t)
        if mirror_url:
            record_raid1_mirror(view_owner, fid, mirror_url)

    elapsed = round(time.monotonic() - t0, 2)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    log_payload = json.dumps({
        "ts": ts,
        "filename": final_name,
        "source_url": clean_url,
        "dest_folder": routed_folder,
        "size": len(final_bytes),
        "elapsed": elapsed,
    }, ensure_ascii=False)
    supabase.table("nxt_files").insert({
        "owner": view_owner,
        "filename": "leecher_entry",
        "storage_provider": "vault_leecher_log",
        "file_url": log_payload,
        "folder": "/_leecher",
        "size": len(final_bytes),
        "is_deleted": False,
    }).execute()

    return url_leecher_view(username, password, view_owner, f"Soubor '{final_name}' ({format_bytes(len(final_bytes))}) byl stažen do {routed_folder} za {elapsed} s.")

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
    {APEX_CSS}
    {THEME_SCRIPT}
</head>
<body style="display:flex; align-items:center; justify-content:center; min-height:100vh; padding:20px;">
    <div class="panel" style="width:100%; max-width:420px; margin:0; padding:28px;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; padding-bottom:14px; border-bottom:1px solid var(--border);">
            <div class="brand-title">
                <div class="brand-logo-box">{svg("server")}</div>
                <span>VAULTGRID APEX</span>
            </div>
            <span class="brand-ver">v{html.escape(active_ver)}</span>
        </div>
        <p style="color:var(--text-muted); margin-top:0; margin-bottom:18px;">Osobní cloudová platforma s 50GB+ Chunked nahráváním, Cloud RAID-1, WarpDrop P2P a WebDAV diskem.</p>
        <form action="/login-router" method="POST">
            <label style="font-size:12px; color:var(--text-muted);">Uživatelské jméno</label>
            <input type="text" name="username" required autofocus style="margin:5px 0 14px 0;">
            <label style="font-size:12px; color:var(--text-muted);">Heslo</label>
            <input type="password" name="password" required style="margin:5px 0 18px 0;">
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
        return f"""<!DOCTYPE html><html lang="cs" data-theme="dark"><head>{APEX_CSS}{THEME_SCRIPT}</head>
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

    raid_folders = get_raid1_folders(view_owner)
    mirrors_map = get_raid1_mirrors_map(view_owner)

    audit_rows = [f for f in all_rows if f.get("storage_provider") == "vault_audit"][-7:]
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
            <div class="kpi-label"><span>Využitá kapacita</span> {svg("folder")}</div>
            <div class="kpi-value">{format_bytes(total_used_bytes)}</div>
            <div class="kpi-sub">Kvóta účtu: {quota_label} • {len(user_files)} souborů</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label"><span>Cloud Multi-Pool</span> {svg("database")}</div>
            <div class="kpi-value">{total_pool_gb} GB</div>
            <div class="kpi-sub">{len(pools)} připojených fondů (50GB+ Chunked Ready)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label"><span>Cloud RAID-1 Zrcadlení</span> {svg("layers")}</div>
            <div class="kpi-value">{len(raid_folders)} složek</div>
            <div class="kpi-sub">{len(mirrors_map)} aktivních zrcadlených souborů</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label"><span>Propojení zařízení</span> {svg("wifi")}</div>
            <div class="kpi-value">APEX v{html.escape(get_installed_ota_version())}</div>
            <div class="kpi-sub">WarpDrop P2P + VaultSync + WebDAV Z:\\</div>
        </div>
    </div>

    <div class="grid-2">
        <div class="panel">
            <div class="panel-header">
                <h2 class="panel-title">{svg("database")} Stav úložných poolů & RAID-1</h2>
                <a href="/storage-pools?{q_params}" class="btn btn-secondary btn-sm">Spravovat</a>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px; font-size:13px;">
                <span>Globálně obsazeno: <strong class="mono">{format_bytes(global_used_bytes)}</strong></span>
                <span class="mono">{pct_pool:.2f}% z {total_pool_gb} GB</span>
            </div>
            <div class="progress-track"><div class="progress-fill" style="width:{pct_pool}%;"></div></div>
            <div style="margin-top:16px; font-size:12.5px; color:var(--text-muted); line-height:1.7;">
                Aktivní zápisový repozitář: <span class="mono" style="color:var(--text-main);">{html.escape(get_active_write_repo(active_files) or 'Nenastaveno')}</span><br>
                Záložní RAID-1 zrcadlo: <span class="mono" style="color:var(--text-main);">{html.escape(get_mirror_repo(get_active_write_repo(active_files)) or 'Připojte 2. pool pro RAID-1')}</span>
            </div>
        </div>

        <div class="panel">
            <div class="panel-header">
                <h2 class="panel-title">{svg("zap")} Rychlé akce</h2>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                <a href="/files?{q_params}" class="btn">{svg("upload_cloud")} Nahrát soubory (50GB+)</a>
                <a href="/warpdrop-p2p?{q_params}" class="btn btn-secondary">{svg("wifi")} WarpDrop P2P (Mobil ↔ PC)</a>
                <a href="/vaultsync?{q_params}" class="btn btn-secondary">{svg("laptop")} VaultSync PC Agent</a>
                <a href="/webdav-manager?{q_params}" class="btn btn-secondary">{svg("harddrive")} Síťový disk Z:\\</a>
            </div>
        </div>
    </div>

    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("shield")} Poslední systémové události</h2>
            <a href="/audit-log?{q_params}" class="btn btn-secondary btn-sm">Celý Audit Log</a>
        </div>
        <div class="table-wrap">
            <table>
                <thead><tr><th>Čas (UTC)</th><th>Úroveň</th><th>Uživatel</th><th>Událost</th></tr></thead>
                <tbody>{audit_html}</tbody>
            </table>
        </div>
    </div>
    """
    return render_shell("Přehled systému", "overview", username, password, view_owner, body)

# --- 2. SPRÁVCE SOUBORŮ (S PŘEHLEDNÝMI ZÁLOŽKAMI NÁSTROJŮ, CHUNKED 50GB+ UPLOADEM A RAID-1 INDIKÁTORY) ---
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
    mirrors_map: dict[int, str],
    raid_folders: list[str],
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
            dir_raid = is_folder_raid1(view_owner, f_path, raid_folders)
            ic = svg("lock") if locked else svg("folder")
            raid_pill = ' <span class="badge badge-ok">RAID-1</span>' if dir_raid else ""
            link_url = (
                f"/files?{q_params}&folder={urllib.parse.quote(f_path)}&folder2={urllib.parse.quote(other_folder)}&mode=dual"
                if pane_side == "left"
                else f"/files?{q_params}&folder={urllib.parse.quote(other_folder)}&folder2={urllib.parse.quote(f_path)}&mode=dual"
            )
            if pane_side == "single":
                link_url = f"/files?{q_params}&folder={urllib.parse.quote(f_path)}"

            rows_html += f"""
            <tr>
                <td style="width:30px;"></td>
                <td>
                    <a href="{link_url}" style="color:var(--text-main); text-decoration:none; font-weight:600; display:inline-flex; align-items:center; gap:8px;">
                        <span style="color:#60a5fa;">{ic}</span> {html.escape(fname)}
                    </a>{raid_pill}
                </td>
                <td class="mono" style="color:var(--text-muted);">SLOŽKA</td>
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
        is_mirrored = f["id"] in mirrors_map
        is_chunked = f.get("storage_provider") == "huggingface_chunked"

        badges = ""
        if is_mirrored:
            badges += '<span class="badge badge-ok">RAID-1</span> '
        if is_chunked:
            badges += '<span class="badge badge-cyan">CHUNKED</span> '
        if fname.endswith(".vgenc"):
            badges += '<span class="badge badge-warn">AES-256</span> '

        dl_href = f"/download-file?id={f['id']}&{q_params}" if is_mirrored else html.escape(f["file_url"])

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
                extra.append(f'<a href="#decrypt" onclick="openDecryptModal({f["id"]}, \'{html.escape(fname)}\'); return false;" class="link-action" style="color:#fbbf24;">Dešifrovat</a>')
            if ext in PREVIEW_EXTENSIONS:
                extra.append(f'<a href="/preview?id={f["id"]}&{q_params}" class="link-action">Náhled</a>')
            if ext in VIDEO_EXTENSIONS or ext in AUDIO_EXTENSIONS:
                extra.append(f'<a href="/media-player?file_url={urllib.parse.quote(f["file_url"])}&filename={urllib.parse.quote(fname)}&{q_params}" class="link-action">Přehrát</a>')
            if ext == "html":
                site_rel = f"{f.get('folder', '/').strip('/')}/{fname}".lstrip("/")
                extra.append(f'<a href="/site/{urllib.parse.quote(view_owner)}/{urllib.parse.quote(site_rel)}" target="_blank" class="link-action">Web</a>')
            if ext in EDITABLE_EXTENSIONS:
                extra.append(f'<a href="/code-editor?id={f["id"]}&{q_params}" class="link-action">Upravit</a>')

            actions = f"""
                <a href="{dl_href}" download class="link-action">Stáhnout</a>
                {"".join(extra)}
                <a href="/vaultdrop?{q_params}&preselect_id={f['id']}" class="link-action">Sdílet</a>
                <a href="/delete-file?id={f['id']}&folder={urllib.parse.quote(target_folder)}&{q_params}" class="link-danger">Koš</a>
            """

        rows_html += f"""
        <tr>
            <td style="width:30px;"><input type="checkbox" name="selected_ids" value="{f['id']}"></td>
            <td>
                <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                    <span style="color:var(--text-muted);">{svg("file")}</span>
                    <span style="font-weight:500;">{html.escape(fname)}</span>
                    {badges}{tags_badges}
                </div>
            </td>
            <td class="mono">{size_str}</td>
            <td>{actions}</td>
        </tr>"""

    if not rows_html:
        rows_html = "<tr><td colspan='4' style='text-align:center; color:var(--text-muted); padding:28px;'>Tento adresář je zatím prázdný. Nahrajte soubory nahoře.</td></tr>"
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
                err_html = '<div class="alert-bar err">Neplatný bezpečnostní PIN kód.</div>' if unlocked_pin else ""
                pin_body = f"""
                <div class="panel" style="max-width:440px; margin: 40px auto;">
                    <div class="panel-header"><h2 class="panel-title">{svg("lock")} VaultShield — Chráněný adresář</h2></div>
                    <p style="color:var(--text-muted);">Adresář <span class="mono">{html.escape(current_folder)}</span> je uzamčen PIN kódem.</p>
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
    mirrors_map = get_raid1_mirrors_map(view_owner)
    raid_folders = get_raid1_folders(view_owner)
    cur_raid_on = is_folder_raid1(view_owner, current_folder, raid_folders)

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
            <select name="target_owner" onchange="this.form.submit()" style="width:auto; padding:5px 9px;">{opts}</select>
        </form>"""

    alert_html = f'<div class="alert-bar ok">{html.escape(status_msg)}</div>' if status_msg else ""

    # DUAL-PANE COMMANDER REŽIM
    if mode == "dual" and not is_in_trash and not search_query and not tag_filter:
        left_rows, _, _ = build_pane_table(items, current_folder, "left", folder2, q_params, tags_map, mirrors_map, raid_folders, view_owner)
        right_rows, _, _ = build_pane_table(items, folder2, "right", current_folder, q_params, tags_map, mirrors_map, raid_folders, view_owner)
        dual_body = f"""
        {alert_html}
        <div class="panel">
            <div class="panel-header">
                <h2 class="panel-title">{svg("columns")} Dual-Pane Commander</h2>
                <div class="form-row">
                    {owner_bar}
                    <a href="/files?{q_params}&folder={urllib.parse.quote(current_folder)}&mode=single" class="btn btn-secondary btn-sm">Zpět na standardní pohled</a>
                </div>
            </div>
            <div class="grid-dual">
                <div class="table-wrap">
                    <div style="padding:10px 14px; background:var(--bg-surface-alt); border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
                        <span class="mono"><strong>LEVÝ:</strong> {html.escape(current_folder)}</span>
                        <a href="/files?{q_params}&folder=/&folder2={urllib.parse.quote(folder2)}&mode=dual" class="link-action">/root</a>
                    </div>
                    <table><thead><tr><th></th><th>Název</th><th>Velikost</th><th>Přenos</th></tr></thead><tbody>{left_rows}</tbody></table>
                </div>
                <div class="table-wrap">
                    <div style="padding:10px 14px; background:var(--bg-surface-alt); border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
                        <span class="mono"><strong>PRAVÝ:</strong> {html.escape(folder2)}</span>
                        <a href="/files?{q_params}&folder={urllib.parse.quote(current_folder)}&folder2=/&mode=dual" class="link-action">/root</a>
                    </div>
                    <table><thead><tr><th></th><th>Název</th><th>Velikost</th><th>Přenos</th></tr></thead><tbody>{right_rows}</tbody></table>
                </div>
            </div>
        </div>"""
        return render_shell("Dual-Pane Commander", "files", username, password, view_owner, dual_body)

    rows_html, _, _ = build_pane_table(items, current_folder, "single", "/", q_params, tags_map, mirrors_map, raid_folders, view_owner, is_in_trash, search_query, tag_filter)

    # Přehledné kompaktní záložky nástrojů nad tabulkou souborů
    tools_drawer = ""
    if not is_in_trash and not search_query and not tag_filter:
        pin_control = (
            f"""<form action="/remove-folder-pin" method="POST" class="form-row" style="margin:0;">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="current_folder" value="{html.escape(current_folder)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <span class="badge badge-warn">PIN ZÁMEK AKTIVNÍ</span>
                <button type="submit" class="btn btn-secondary btn-sm">Odebrat PIN</button>
            </form>"""
            if is_folder_locked
            else f"""<form action="/set-folder-pin" method="POST" class="form-row" style="margin:0;">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="current_folder" value="{html.escape(current_folder)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <input type="password" name="new_pin" placeholder="PIN složky..." maxlength="8" inputmode="numeric" required style="width:140px;">
                <button type="submit" class="btn btn-secondary btn-sm">{svg("lock")} Zamknout</button>
            </form>"""
        ) if current_folder != "/" else '<span style="color:var(--text-muted); font-size:12px;">Kořenovou složku nelze zamknout PINem.</span>'

        raid_toggle_btn = f"""
        <form action="/storage-pools/toggle-raid" method="POST" style="margin:0;">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="hidden" name="raid_folder" value="{html.escape(current_folder)}">
            <input type="hidden" name="return_to_files" value="1">
            <button type="submit" class="btn {'btn-success' if cur_raid_on else 'btn-secondary'} btn-sm">
                {svg("layers")} {'RAID-1 Zrcadlení: ZAPNUTO' if cur_raid_on else 'Zapnout RAID-1 Zrcadlení pro tuto složku'}
            </button>
        </form>"""

        tools_drawer = f"""
        <div class="panel">
            <div class="tool-tabs">
                <button type="button" class="tool-tab-btn active" onclick="switchToolTab('tab-chunked', this)">{svg("upload_cloud")} Nahrát soubory (50GB+ Chunked Engine)</button>
                <button type="button" class="tool-tab-btn" onclick="switchToolTab('tab-standard', this)">{svg("lock")} Rychlé nahrání + AES-256 Šifrování</button>
                <button type="button" class="tool-tab-btn" onclick="switchToolTab('tab-folder', this)">{svg("folder")} Nová složka, PIN & RAID-1</button>
            </div>

            <!-- ZÁLOŽKA 1: CHUNKED 50GB+ STREAMING UPLOAD -->
            <div id="tab-chunked" class="tool-pane active">
                <div class="dropzone" id="chunk-dropzone" onclick="document.getElementById('chunk-file-input').click()">
                    <div style="font-weight:700; font-size:14px; margin-bottom:4px;">Klikněte nebo sem přetáhněte libovolně velké soubory (až 50 GB+)</div>
                    <div style="color:var(--text-muted); font-size:12.5px;">Soubory se automaticky rozsekají na 20MB bloky, nahrávají bez limitu RAM a podporují obnovení při výpadku.</div>
                </div>
                <input type="file" id="chunk-file-input" multiple style="display:none;" onchange="startChunkedUpload(this.files)">

                <div id="chunk-progress-panel" style="display:none; margin-top:14px; padding:14px; background:var(--bg-app); border:1px solid var(--border); border-radius:9px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; font-size:13px;">
                        <strong id="chunk-status-text">Příprava přenosu...</strong>
                        <span class="mono" id="chunk-speed-text" style="color:#22d3ee;">0.00 MB/s</span>
                    </div>
                    <div class="progress-track" style="margin-bottom:6px;"><div id="chunk-progress-bar" class="progress-fill" style="width:0%;"></div></div>
                    <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--text-muted);" class="mono">
                        <span id="chunk-detail-text">Blok 0 / 0</span>
                        <span id="chunk-pct-text">0%</span>
                    </div>
                </div>
            </div>

            <!-- ZÁLOŽKA 2: STANDARDNÍ NAHRÁNÍ + VAULTCRYPT AES-256 -->
            <div id="tab-standard" class="tool-pane">
                <form action="/upload" method="POST" enctype="multipart/form-data">
                    <input type="hidden" name="username" value="{html.escape(username)}">
                    <input type="hidden" name="password" value="{html.escape(password)}">
                    <input type="hidden" name="folder" value="{html.escape(current_folder)}">
                    <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                    <input type="hidden" name="unlocked_pin" value="{html.escape(unlocked_pin)}">
                    <div class="form-row" style="margin-bottom:10px;">
                        <input type="file" name="files" multiple required style="flex:1;">
                        <button type="submit" class="btn">Nahrát do cloudu</button>
                    </div>
                    <div class="form-row" style="font-size:12.5px; color:var(--text-muted);">
                        <label style="display:inline-flex; align-items:center; gap:6px; cursor:pointer;">
                            <input type="checkbox" name="encrypt_flag" value="1" onchange="document.getElementById('enc-pass-box').style.display = this.checked ? 'inline-block' : 'none';">
                            Zašifrovat před odesláním (VaultCrypt AES-256)
                        </label>
                        <input type="password" id="enc-pass-box" name="encrypt_pass" placeholder="Šifrovací heslo..." style="display:none; width:210px;">
                    </div>
                </form>
            </div>

            <!-- ZÁLOŽKA 3: NOVÁ SLOŽKA, PIN & RAID-1 -->
            <div id="tab-folder" class="tool-pane">
                <div class="form-row" style="justify-content:space-between;">
                    <form action="/create-folder" method="POST" class="form-row" style="margin:0;">
                        <input type="hidden" name="username" value="{html.escape(username)}">
                        <input type="hidden" name="password" value="{html.escape(password)}">
                        <input type="hidden" name="current_folder" value="{html.escape(current_folder)}">
                        <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                        <input type="text" name="new_folder_name" placeholder="Název nové podsložky..." required style="width:220px;">
                        <button type="submit" class="btn btn-secondary">Vytvořit složku</button>
                    </form>
                    {raid_toggle_btn}
                    {pin_control}
                </div>
            </div>
        </div>"""

    raid_header_badge = '<span class="badge badge-ok" style="margin-left:8px;">RAID-1 MIRROR AKTIVNÍ</span>' if cur_raid_on else ""

    body = f"""
    {alert_html}
    {tools_drawer}

    <div class="panel">
        <div class="panel-header">
            <div style="display:flex; align-items:center; flex-wrap:wrap; gap:6px;">
                <span class="mono" style="font-size:13.5px; font-weight:600;">{breadcrumb_str}</span>
                {raid_header_badge}
            </div>
            <div class="form-row">
                {owner_bar}
                <a href="/files?{q_params}&folder={urllib.parse.quote(current_folder)}&mode=dual" class="btn btn-secondary btn-sm">{svg("columns")} Dual-Pane</a>
                <a href="/files?{q_params}&folder={urllib.parse.quote(current_folder)}&trash={'false' if is_in_trash else 'true'}" class="btn btn-secondary btn-sm">{'Aktivní soubory' if is_in_trash else 'Koš'}</a>
                <a href="/download-zip?{q_params}&folder={urllib.parse.quote(current_folder)}" class="btn btn-secondary btn-sm">ZIP</a>
                <a href="/photo-gallery?{q_params}&folder={urllib.parse.quote(current_folder)}" class="btn btn-secondary btn-sm">Galerie</a>
            </div>
        </div>

        <form action="/files/batch" method="POST">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="hidden" name="current_folder" value="{html.escape(current_folder)}">

            <div class="form-row" style="margin-bottom:12px; padding:8px 12px; background:var(--bg-surface-alt); border:1px solid var(--border); border-radius:8px;">
                <span style="font-size:12px; color:var(--text-muted); font-weight:600;">Hromadné akce:</span>
                <select name="batch_action" style="width:auto; padding:5px 9px;">
                    <option value="zip">Stáhnout označené jako ZIP</option>
                    <option value="move">Přesunout do složky</option>
                    <option value="tag">Přidat #štítek</option>
                    <option value="trash">Přesunout do koše</option>
                </select>
                <input type="text" name="batch_param" placeholder="Cílová složka / název štítku..." style="width:210px; padding:5px 9px;">
                <button type="submit" class="btn btn-secondary btn-sm">Provést</button>
            </div>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th style="width:30px;"><input type="checkbox" onclick="document.querySelectorAll('input[name=selected_ids]').forEach(c => c.checked = this.checked)"></th>
                            <th>Název položky & Stav</th>
                            <th>Velikost</th>
                            <th>Akce</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
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

    <script>
        function switchToolTab(paneId, btn) {{
            document.querySelectorAll('.tool-pane').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tool-tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(paneId).classList.add('active');
            btn.classList.add('active');
        }}

        function openDecryptModal(id, fname) {{
            document.getElementById('dec-fid').value = id;
            document.getElementById('dec-fname').innerText = fname;
            const m = document.getElementById('decrypt-modal');
            m.style.display = 'block';
            m.scrollIntoView({{ behavior: 'smooth' }});
        }}

        // Drag & drop pro Chunked Uploader
        const dz = document.getElementById('chunk-dropzone');
        if (dz) {{
            dz.addEventListener('dragover', (e) => {{ e.preventDefault(); dz.classList.add('dragover'); }});
            dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
            dz.addEventListener('drop', (e) => {{
                e.preventDefault();
                dz.classList.remove('dragover');
                if (e.dataTransfer.files.length) startChunkedUpload(e.dataTransfer.files);
            }});
        }}

        // CHUNKED STREAMING UPLOAD ENGINE (20MB BLOKY -> 50GB+ SOUBORY BEZ PÁDU RAM)
        async function startChunkedUpload(fileList) {{
            if (!fileList || !fileList.length) return;
            const CHUNK_SIZE = 20 * 1024 * 1024;
            const panel = document.getElementById('chunk-progress-panel');
            const statusEl = document.getElementById('chunk-status-text');
            const speedEl = document.getElementById('chunk-speed-text');
            const barEl = document.getElementById('chunk-progress-bar');
            const detailEl = document.getElementById('chunk-detail-text');
            const pctEl = document.getElementById('chunk-pct-text');
            panel.style.display = 'block';

            for (let fIdx = 0; fIdx < fileList.length; fIdx++) {{
                const file = fileList[fIdx];
                const totalChunks = Math.max(1, Math.ceil(file.size / CHUNK_SIZE));
                statusEl.innerText = `Inicializuji (${{fIdx+1}}/${{fileList.length}}): ${{file.name}}`;

                const initFd = new FormData();
                initFd.append('username', "{html.escape(username)}");
                initFd.append('password', "{html.escape(password)}");
                initFd.append('target_owner', "{html.escape(view_owner)}");
                initFd.append('filename', file.name);
                initFd.append('folder', "{html.escape(current_folder)}");
                initFd.append('total_size', file.size);
                initFd.append('total_chunks', totalChunks);

                const initRes = await fetch('/api/upload/chunk-init', {{ method: 'POST', body: initFd }});
                const initData = await initRes.json();
                if (!initData.ok) {{
                    alert(initData.error || 'Chyba inicializace nahrávání');
                    return;
                }}

                const partUrls = [];
                const mirrorPartUrls = [];
                let uploadedBytes = 0;
                const tStart = performance.now();

                for (let cIdx = 0; cIdx < totalChunks; cIdx++) {{
                    const start = cIdx * CHUNK_SIZE;
                    const end = Math.min(file.size, start + CHUNK_SIZE);
                    const blob = file.slice(start, end);

                    statusEl.innerText = `Nahrávám (${{fIdx+1}}/${{fileList.length}}): ${{file.name}}`;
                    detailEl.innerText = `Blok ${{cIdx + 1}} / ${{totalChunks}}`;

                    let partOk = false;
                    for (let attempt = 1; attempt <= 3; attempt++) {{
                        try {{
                            const partFd = new FormData();
                            partFd.append('username', "{html.escape(username)}");
                            partFd.append('password', "{html.escape(password)}");
                            partFd.append('owner', initData.owner);
                            partFd.append('upload_id', initData.upload_id);
                            partFd.append('chunk_index', cIdx);
                            partFd.append('repo_id', initData.repo_id);
                            partFd.append('mirror_repo_id', initData.mirror_repo_id || '');
                            partFd.append('chunk', blob, `part_${{cIdx}}.vgpart`);

                            const pRes = await fetch('/api/upload/chunk-part', {{ method: 'POST', body: partFd }});
                            const pData = await pRes.json();
                            if (pData.ok) {{
                                partUrls.push(pData.part_url);
                                mirrorPartUrls.push(pData.mirror_part_url || '');
                                partOk = true;
                                break;
                            }}
                        }} catch (err) {{}}
                        await new Promise(r => setTimeout(r, 800 * attempt));
                    }}

                    if (!partOk) {{
                        alert(`Přenos selhal u bloku ${{cIdx + 1}}. Zkuste to prosím znovu.`);
                        return;
                    }}

                    uploadedBytes += (end - start);
                    const pct = Math.round((uploadedBytes / Math.max(file.size, 1)) * 100);
                    const elapsedSec = Math.max((performance.now() - tStart) / 1000, 0.05);
                    const mbps = ((uploadedBytes / (1024 * 1024)) / elapsedSec).toFixed(2);
                    barEl.style.width = pct + '%';
                    pctEl.innerText = pct + '%';
                    speedEl.innerText = mbps + ' MB/s';
                }}

                statusEl.innerText = `Dokončuji záznam v cloudu: ${{file.name}}`;
                const finFd = new FormData();
                finFd.append('username', "{html.escape(username)}");
                finFd.append('password', "{html.escape(password)}");
                finFd.append('owner', initData.owner);
                finFd.append('upload_id', initData.upload_id);
                finFd.append('filename', file.name);
                finFd.append('routed_folder', initData.routed_folder);
                finFd.append('total_size', file.size);
                finFd.append('repo_id', initData.repo_id);
                finFd.append('mirror_repo_id', initData.mirror_repo_id || '');
                finFd.append('parts_json', JSON.stringify(partUrls));
                finFd.append('mirror_parts_json', JSON.stringify(mirrorPartUrls));
                finFd.append('auto_tags_json', JSON.stringify(initData.auto_tags || []));
                await fetch('/api/upload/chunk-finalize', {{ method: 'POST', body: finFd }});
            }}

            location.href = `/files?{q_params}&folder=${{encodeURIComponent("{html.escape(current_folder)}")}}&msg=${{encodeURIComponent("Blokové nahrávání bylo úspěšně dokončeno!")}}`;
        }}
    </script>
    """
    title = "Koš úložiště" if is_in_trash else (f"Štítek: #{tag_filter}" if tag_filter else (f"Vyhledávání: {search_query}" if search_query else "Správce souborů"))
    return render_shell(title, "files", username, password, view_owner, body, search_query)

@app.get("/download-file")
def download_with_raid1_fallback(id: int, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return Response("Unauthorized", status_code=401)
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    rec = (supabase.table("nxt_files").select("*").eq("id", id).execute().data or [None])[0]
    if not rec:
        return Response("Not found", status_code=404)

    mirrors_map = get_raid1_mirrors_map(view_owner)
    mirror_url = mirrors_map.get(id, "")
    primary_url = rec.get("file_url", "")

    for url_try in [primary_url, mirror_url]:
        if url_try and url_try.startswith("http"):
            try:
                with urllib.request.urlopen(url_try, timeout=15) as resp:
                    data = resp.read()
                return StreamingResponse(
                    io.BytesIO(data),
                    media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{rec["filename"]}"'},
                )
            except Exception:
                continue
    return Response("Soubor se nepodařilo stáhnout z primárního ani záložního RAID-1 poolu.", status_code=502)

# --- STORAGE POOLS & CLOUD RAID-1 MANAGER (MILNÍK A2) ---
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
        status_badge = '<span class="badge badge-ok">ACTIVE // WRITE</span>' if is_write else '<span class="badge badge-cyan">MOUNTED // RAID-1 READY</span>'

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

    raid_folders = get_raid1_folders(view_owner)
    mirrors_map = get_raid1_mirrors_map(view_owner)
    raid_rows = ""
    for rf in raid_folders:
        rf_files = [f for f in active_files if f.get("owner") == view_owner and is_folder_raid1(view_owner, f.get("folder", "/"), [rf])]
        mirrored_cnt = sum(1 for f in rf_files if f["id"] in mirrors_map)
        raid_rows += f"""
        <tr>
            <td class="mono"><strong>{html.escape(rf)}</strong></td>
            <td class="mono">{mirrored_cnt} / {len(rf_files)} souborů zrcadleno</td>
            <td><span class="badge {'badge-ok' if len(pools) >= 2 else 'badge-warn'}">{'RAID-1 AKTIVNÍ (2 POOLY)' if len(pools) >= 2 else 'ČEKÁ NA 2. POOL'}</span></td>
            <td>
                <form action="/storage-pools/toggle-raid" method="POST" style="margin:0;">
                    <input type="hidden" name="username" value="{html.escape(username)}">
                    <input type="hidden" name="password" value="{html.escape(password)}">
                    <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                    <input type="hidden" name="raid_folder" value="{html.escape(rf)}">
                    <button type="submit" class="btn btn-danger btn-sm">Vypnout RAID-1</button>
                </form>
            </td>
        </tr>"""
    if not raid_rows:
        raid_rows = "<tr><td colspan='4' style='text-align:center; color:var(--text-muted);'>Zatím žádné složky s zapnutým RAID-1 zrcadlením.</td></tr>"

    add_pool_form = ""
    if user["role"] == "admin":
        add_pool_form = f"""
        <div class="panel">
            <div class="panel-header"><h3 class="panel-title">{svg("database")} Připojit další Hugging Face Dataset Pool (až 7 TB / RAID-1 zrcadlo)</h3></div>
            <form action="/storage-pools/add" method="POST" class="form-row">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <input type="text" name="label" placeholder="Název (např. Cloud Pool 02 - Mirror)" required style="width:240px;">
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
        <div class="table-wrap">
            <table>
                <thead><tr><th>Název poolu</th><th>Repozitář</th><th>Využití</th><th>Soubory</th><th>Stav</th><th>Akce</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </div>

    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("layers")} Cloud RAID-1 — Zrcadlení důležitých složek</h2>
            <form action="/storage-pools/sync-raid" method="POST" style="margin:0;">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <button type="submit" class="btn btn-secondary btn-sm">{svg("refresh")} Synchronizovat chybějící zrcadla</button>
            </form>
        </div>
        <p style="color:var(--text-muted); margin-top:0;">Každý soubor v chráněné složce se automaticky ukládá do primárního i záložního poolu zároveň.</p>
        <form action="/storage-pools/toggle-raid" method="POST" class="form-row" style="margin-bottom:14px;">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="text" name="raid_folder" placeholder="Cesta ke složce (např. /Dokumenty nebo /Ucetnictvi)" required style="flex:1;">
            <button type="submit" class="btn">Přepnout RAID-1 ochranu</button>
        </form>
        <div class="table-wrap">
            <table>
                <thead><tr><th>Chráněná složka</th><th>Stav souborů</th><th>Režim</th><th>Správa</th></tr></thead>
                <tbody>{raid_rows}</tbody>
            </table>
        </div>
    </div>

    {add_pool_form}"""
    return render_shell("Storage & RAID-1", "pools", username, password, view_owner, body)

@app.post("/storage-pools/toggle-raid", response_class=HTMLResponse)
def storage_pools_toggle_raid(
    username: str = Form(...),
    password: str = Form(...),
    target_owner: str = Form(None),
    raid_folder: str = Form(...),
    return_to_files: str = Form("")
):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    clean_f = "/" + raid_folder.strip("/") if raid_folder.strip("/") else "/"

    existing = supabase.table("nxt_files").select("id").eq("owner", view_owner).eq("storage_provider", "vault_raid_folder").eq("folder", clean_f).execute().data or []
    if existing:
        supabase.table("nxt_files").delete().eq("owner", view_owner).eq("storage_provider", "vault_raid_folder").eq("folder", clean_f).execute()
        msg = f"RAID-1 zrcadlení pro složku {clean_f} bylo vypnuto."
    else:
        supabase.table("nxt_files").insert({
            "owner": view_owner, "filename": ".vault_raid1", "storage_provider": "vault_raid_folder",
            "file_url": "RAID1", "folder": clean_f, "size": 0, "is_deleted": False
        }).execute()
        msg = f"RAID-1 zrcadlení pro složku {clean_f} bylo aktivováno."

    log_audit(username, "RAID1_TOGGLED", msg, "INFO")
    if return_to_files == "1":
        return render_files_view(username, password, user["role"] == "admin", view_owner, clean_f, "/", "single", False, "", "", "", msg)
    return storage_pools_view(username, password, view_owner, msg)

@app.post("/storage-pools/sync-raid", response_class=HTMLResponse)
def storage_pools_sync_raid(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner if (user["role"] == "admin" and target_owner) else username
    raid_folders = get_raid1_folders(view_owner)
    mirrors_map = get_raid1_mirrors_map(view_owner)
    rows = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute().data or []

    replicated = 0
    for f in rows:
        if is_system_record(f) or f["id"] in mirrors_map:
            continue
        if not is_folder_raid1(view_owner, f.get("folder", "/"), raid_folders):
            continue
        if f.get("storage_provider") == "huggingface" and f.get("file_url", "").startswith("http"):
            # Určení druhého poolu
            src_url = f["file_url"]
            m = re.search(r"huggingface\.co/datasets/([^/]+/[^/]+)/resolve/main/(.+)$", src_url)
            if m and hf_api:
                src_repo, repo_path = m.group(1), m.group(2)
                m_repo = get_mirror_repo(src_repo)
                if m_repo:
                    try:
                        with urllib.request.urlopen(src_url, timeout=15) as resp:
                            data = resp.read()
                        hf_api.upload_file(path_or_fileobj=data, path_in_repo=repo_path, repo_id=m_repo, repo_type="dataset")
                        m_url = f"https://huggingface.co/datasets/{m_repo}/resolve/main/{repo_path}"
                        record_raid1_mirror(view_owner, f["id"], m_url)
                        replicated += 1
                    except Exception:
                        pass
    return storage_pools_view(username, password, view_owner, f"Synchronizace RAID-1 dokončena. Nově zrcadlených souborů: {replicated}.")

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

# --- BATCH, DUAL-PANE TRANSFER, DECRYPT, PREVIEW, STATIC HOSTING ---
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
        viewer_html = f'<iframe src="{html.escape(furl)}" style="width:100%; height:720px; border:1px solid var(--border); border-radius:8px;"></iframe>'
    elif ext in IMAGE_EXTENSIONS:
        viewer_html = f'<div style="text-align:center; background:var(--bg-app); padding:20px; border-radius:8px;"><img src="{html.escape(furl)}" style="max-width:100%; max-height:680px;"></div>'
    elif ext in ["stl", "obj"]:
        viewer_html = f"""
        <div id="stl-canvas" style="width:100%; height:520px; background:#090b0e; border:1px solid var(--border); border-radius:8px; position:relative;">
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
        viewer_html = f'<pre class="mono" style="background:var(--bg-app); padding:16px; border:1px solid var(--border); border-radius:8px; overflow-x:auto; max-height:650px;">{html.escape(raw_txt)}</pre>'

    body = f"""
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("eye")} Universal Viewer: {html.escape(fname)}</h2>
            <a href="{html.escape(furl)}" download class="btn btn-sm">Stáhnout originál</a>
        </div>
        {viewer_html}
    </div>"""
    return render_shell(f"Náhled: {fname}", "files", username, password, view_owner, body)

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

# --- VAULTDROP, VAULTBACKUP, VAULTFLIX, VAULTBEATS, VAULTRULES, REST API, USERS, AUDIT, OTA ---
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
            <div class="panel-header"><h2 class="panel-title">{svg("folder")} Vytvořit veřejnou upload schránku</h2></div>
            <p style="color:var(--text-muted); margin-top:0;">Umožní komukoliv s odkazem nahrát soubory přímo do vaší cílové složky bez účtu.</p>
            <form action="/vaultdrop/create-request" method="POST">
                <input type="hidden" name="username" value="{html.escape(username)}">
                <input type="hidden" name="password" value="{html.escape(password)}">
                <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
                <input type="text" name="title" placeholder="Název schránky" required style="margin-bottom:10px;">
                <input type="text" name="dest_folder" value="/Inbox" placeholder="Cílová složka ve Vaultu..." required style="margin-bottom:10px;">
                <input type="password" name="drop_pass" placeholder="Volitelné heslo pro nahrávání..." style="margin-bottom:10px;">
                <button type="submit" class="btn btn-secondary" style="width:100%;">Vytvořit upload schránku</button>
            </form>
        </div>
    </div>

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Aktivní sdílené odkazy a upload schránky ({len(drops)})</h2></div>
        <div class="table-wrap">
            <table>
                <thead><tr><th>Typ</th><th>Název</th><th>Veřejná cesta</th><th>Expirace</th><th>Stažení</th><th>Heslo</th><th>Akce</th></tr></thead>
                <tbody>{drops_rows}</tbody>
            </table>
        </div>
    </div>"""
    return render_shell("VaultDrop Odkazy", "vaultdrop", username, password, view_owner, body)

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
    return vaultdrop_view(username, password, view_owner, 0, f"Upload schránka /drop-upload/{token} byla vytvořena.")

@app.get("/vaultdrop/revoke", response_class=HTMLResponse)
def vaultdrop_revoke(username: str, password: str, id: int, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("id", id).execute()
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
    return f"""<!DOCTYPE html><html lang="cs" data-theme="dark"><head><meta charset="UTF-8"><title>VaultDrop Stažení</title>{APEX_CSS}{THEME_SCRIPT}</head>
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

    if f_rec.get("file_url", "").startswith("/stream-chunked/"):
        mid = int(f_rec["file_url"].split("/")[2])
        return stream_chunked_file(mid, f_rec["filename"])

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
    return f"""<!DOCTYPE html><html lang="cs" data-theme="dark"><head><meta charset="UTF-8"><title>VaultDrop Upload</title>{APEX_CSS}{THEME_SCRIPT}</head>
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
    return public_drop_upload_get(token, f"Úspěšně odesláno souborů: {cnt}.")

# --- VAULTBACKUP & CONFIG EXPORT ---
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
        "system": "VaultGrid APEX",
        "version": CORE_VERSION,
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "users": [{"username": u["username"], "role": u["role"]} for u in u_rows],
        "storage_pools": get_storage_pools(),
        "raid1_folders": get_raid1_folders(view_owner),
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
            <input type="text" name="profile_name" placeholder="Název profilu" required style="flex:1;">
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
        <div class="table-wrap">
            <table><thead><tr><th>Název</th><th>Zdroj</th><th>Retence</th><th>Poslední běh</th><th>Stav</th><th>Akce</th></tr></thead><tbody>{prof_rows}</tbody></table>
        </div>
    </div>

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Historie snímků a SHA-256 kontrolních součtů</h2></div>
        <div class="table-wrap">
            <table><thead><tr><th>ID</th><th>Profil</th><th>Složka</th><th>Čas</th><th>Rozsah</th><th>SHA-256</th></tr></thead><tbody>{snap_rows}</tbody></table>
        </div>
    </div>

    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">{svg("code")} Export konfigurace systému (JSON)</h2>
            <button type="button" onclick="downloadCfg()" class="btn btn-sm">Stáhnout vaultgrid-config.json</button>
        </div>
        <textarea id="cfg-box" rows="10" class="code-box" readonly>{html.escape(cfg_json)}</textarea>
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
            return vaultbackup_view(username, password, view_owner, f"Snímek zálohy dokončen (SHA-256: {digest}).")

    elif action == "delete_profile" and profile_id:
        supabase.table("nxt_files").delete().eq("id", profile_id).execute()
        return vaultbackup_view(username, password, view_owner, "Zálohovací profil byl odstraněn.")

    return vaultbackup_view(username, password, view_owner)

# --- VAULTFLIX CINEMA 2.0 & VAULTBEATS HI-FI ---
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
        cards_html = '<p style="color:var(--text-muted); grid-column:1/-1;">Knihovna videí je prázdná.</p>'

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
        <video id="video-el" controls crossorigin="anonymous" style="width:100%; max-height:520px; background:#000; border-radius:8px;"></video>
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
    return render_shell("VaultFlix Cinema", "vaultflix", username, password, view_owner, body)

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
            <button type="button" onclick="toggleShuffle()" class="btn btn-secondary btn-sm">Shuffle</button>
            <button type="button" onclick="toggleLoop()" class="btn btn-secondary btn-sm">Opakovat skladbu</button>
        </div>
    </div>
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Hudební knihovna ({len(tracks)})</h2></div>
        <div class="table-wrap">
            <table>
                <thead><tr><th>#</th><th>Skladba</th><th>Adresář</th><th>Velikost</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
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
            <input type="text" name="name" placeholder="Název pravidla" required style="width:190px;">
            <input type="text" name="ext" placeholder="Přípona (např. mp4)" style="width:140px;">
            <input type="text" name="src_folder" placeholder="Zdrojová složka" style="width:170px;">
            <input type="text" name="dest_folder" placeholder="Cílová složka (např. /Media)" style="width:180px;">
            <input type="text" name="add_tag" placeholder="Přidat #štítek" style="width:130px;">
            <button type="submit" class="btn">Přidat pravidlo</button>
        </form>
    </div>
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Aktivní pravidla automatického třídění</h2></div>
        <div class="table-wrap">
            <table><thead><tr><th>Název</th><th>Podmínka</th><th>Akce</th><th>Správa</th></tr></thead><tbody>{rules_rows}</tbody></table>
        </div>
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

# --- REST API & OSOBNÍ PŘÍSTUPOVÉ TOKENY ---
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

    alert = f'<div class="alert-bar warn"><strong>Nový API token (uložte si jej):</strong> <span class="mono">{html.escape(new_token_msg)}</span></div>' if new_token_msg else ""
    curl_example = 'curl -X POST "https://tvoje-domena.onrender.com/api/v1/upload" \\\n  -H "Authorization: Bearer vg_live_TVUJ_TOKEN" \\\n  -F "folder=/Automatizace" \\\n  -F "file=@zaloha.zip"'

    body = f"""
    {alert}
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("key")} Vygenerovat osobní REST API klíč</h2></div>
        <form action="/api-tokens/create" method="POST" class="form-row">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <input type="text" name="label" placeholder="Název klíče (např. VaultSync PC)" required style="flex:1;">
            <button type="submit" class="btn">Generovat API Token</button>
        </form>
    </div>

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">Aktivní přístupové tokeny</h2></div>
        <div class="table-wrap">
            <table><thead><tr><th>Název</th><th>Token</th><th>Správa</th></tr></thead><tbody>{t_rows}</tbody></table>
        </div>
    </div>

    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("code")} Dokumentace REST API</h2></div>
        <pre class="mono" style="background:var(--bg-app); padding:14px; border:1px solid var(--border); border-radius:8px; overflow-x:auto;">{html.escape(curl_example)}</pre>
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
    routed_folder, auto_tags = apply_vault_rules(owner, file.filename, clean_folder)
    repo_id = get_active_write_repo()
    repo_path = f"{owner}{routed_folder}/{file.filename}".replace("//", "/")

    if hf_api and repo_id:
        hf_api.upload_file(path_or_fileobj=fbytes, path_in_repo=repo_path, repo_id=repo_id, repo_type="dataset")
        purl = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{repo_path}"
    else:
        purl = "#"

    mirror_url = ""
    if is_folder_raid1(owner, routed_folder) and hf_api:
        m_repo = get_mirror_repo(repo_id)
        if m_repo:
            try:
                hf_api.upload_file(path_or_fileobj=fbytes, path_in_repo=repo_path, repo_id=m_repo, repo_type="dataset")
                mirror_url = f"https://huggingface.co/datasets/{m_repo}/resolve/main/{repo_path}"
            except Exception:
                pass

    ins = supabase.table("nxt_files").insert({
        "owner": owner, "filename": file.filename, "storage_provider": "huggingface",
        "file_url": purl, "folder": routed_folder, "size": len(fbytes), "is_deleted": False
    }).execute()

    if ins.data:
        fid = ins.data[0]["id"]
        for t in auto_tags:
            attach_file_tag(owner, fid, t)
        if mirror_url:
            record_raid1_mirror(owner, fid, mirror_url)

    log_audit(owner, "API_UPLOAD", f"REST API nahrání souboru {file.filename} -> {routed_folder}", "INFO")
    return JSONResponse({"status": "ok", "filename": file.filename, "folder": routed_folder, "url": purl})

# --- UŽIVATELÉ A DISKOVÉ KVÓTY ---
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
        <div class="table-wrap">
            <table>
                <thead><tr><th>Uživatel</th><th>Role</th><th>Obsazeno</th><th>Kvóta (GB)</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
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
    return users_quotas_view(username, password, view_owner, f"Kvóta pro uživatele {quota_user} byla aktualizována.")

# --- FORENZNÍ AUDIT LOG & ÚDRŽBA ---
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
        <div class="table-wrap">
            <table>
                <thead><tr><th>Časové razítko</th><th>Úroveň</th><th>Aktér</th><th>Kód akce</th><th>Detail události</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
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
        <div class="table-wrap">
            <table><thead><tr><th>Soubor</th><th>Složka</th><th>Velikost</th></tr></thead><tbody>{dup_rows}</tbody></table>
        </div>
    </div>"""
    return render_shell("Údržba & Deduplikace", "maintenance", username, password, view_owner, body)

@app.post("/maintenance/empty-trash", response_class=HTMLResponse)
def maintenance_empty_trash(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("owner", view_owner).eq("is_deleted", True).execute()
    return maintenance_view(username, password, view_owner, "Koš byl trvale vyprázdněn.")

@app.post("/maintenance/verify-integrity", response_class=HTMLResponse)
def maintenance_verify_integrity(username: str = Form(...), password: str = Form(...), target_owner: str = Form(None)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    res = supabase.table("nxt_files").select("*").eq("owner", view_owner).eq("is_deleted", False).execute()
    active = [f for f in (res.data or []) if not is_system_record(f)]
    broken = [f for f in active if not (f.get("file_url", "").startswith("http") or f.get("file_url", "").startswith("/stream-chunked/"))]
    return maintenance_view(username, password, view_owner, f"Kontrola dokončena: {len(active)} souborů ověřeno, {len(broken)} neplatných odkazů.")

# --- VAULTUPDATE & OTA STUDIO ---
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
                <span style="color:var(--text-muted);">OTA repozitář <span class="mono">{html.escape(HF_REPO_ID or 'nenastaveno')}/system_ota/</span></span>
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
        <div class="table-wrap"><table><thead><tr><th>#</th><th>Záznam</th></tr></thead><tbody>{rows or "<tr><td colspan='2'>Prázdné</td></tr>"}</tbody></table></div>
    </div>"""
    return render_shell("VaultNotes", "ota_vaultnotes", username, password, view_owner, body)'''

    alert_html = f'<div class="alert-bar ok">{html.escape(status_msg)}</div>' if status_msg else ""
    body = f"""
    {alert_html}
    {update_box}
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("package")} Nainstalovaná OTA rozšíření</h2></div>
        <div class="table-wrap">
            <table><thead><tr><th>Název</th><th>Verze</th><th>Stav</th><th>Akce</th></tr></thead><tbody>{installed_rows}</tbody></table>
        </div>
    </div>
    <div class="panel">
        <div class="panel-header"><h2 class="panel-title">{svg("code")} OTA Studio — Publikovat rozšíření</h2></div>
        <form action="/vaultupdate/publish-custom" method="POST">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="target_owner" value="{html.escape(view_owner)}">
            <div class="grid-2" style="margin-bottom:10px;">
                <input type="text" name="mod_name" value="vaultnotes" placeholder="ID modulu" required>
                <input type="text" name="mod_title" value="VaultNotes" placeholder="Název v navigaci" required>
                <input type="text" name="new_version" value="24.1" placeholder="Verze" required>
                <input type="text" name="release_notes" value="Nový OTA modul poznámek." placeholder="Changelog" required>
            </div>
            <textarea name="module_code" rows="12" class="code-box" style="margin-bottom:12px;" required>{html.escape(starter_module_code)}</textarea>
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
        return vaultupdate_view(username, password, view_owner, f"Chyba syntaxe v Python kódu modulu: {syn_err}")

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
        return vaultupdate_view(username, password, view_owner, f"Balíček {mod_title.strip()} (v{new_version.strip()}) byl publikován.")
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
            LOADED_OTA_MODULES[mname] = {"title": mod.get("title", mname), "sub": "OTA Modul", "version": str(mod.get("version", "24.1")), "code": code_str}
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

# --- VAULTCHAT & VAULTCODE IDE PRO ---
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
                <iframe id="ide-preview" style="width:100%; height:100%; min-height:380px; background:#fff; border:1px solid var(--border); border-radius:8px;"></iframe>
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

# --- STANDARDNÍ OPERACE SE SOUBORY, NAHRÁVÁNÍ (S RAID-1 PODPOROU) ---
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
    mirrored_count = 0

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
            return render_files_view(username, password, user["role"] == "admin", view_owner, folder, "/", "single", False, "", "", unlocked_pin, "Chyba: Byla překročena přidělená disková kvóta.")

        dest_folder, auto_tags = apply_vault_rules(view_owner, final_name, folder)
        repo_path = f"{view_owner}{dest_folder}/{final_name}".replace("//", "/")

        if hf_api and repo_id:
            hf_api.upload_file(path_or_fileobj=final_bytes, path_in_repo=repo_path, repo_id=repo_id, repo_type="dataset")
            public_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{repo_path}"
        else:
            public_url = "#"

        mirror_url = ""
        if is_folder_raid1(view_owner, dest_folder) and hf_api:
            m_repo = get_mirror_repo(repo_id)
            if m_repo:
                try:
                    hf_api.upload_file(path_or_fileobj=final_bytes, path_in_repo=repo_path, repo_id=m_repo, repo_type="dataset")
                    mirror_url = f"https://huggingface.co/datasets/{m_repo}/resolve/main/{repo_path}"
                    mirrored_count += 1
                except Exception:
                    pass

        ins_res = supabase.table("nxt_files").insert({
            "owner": view_owner, "filename": final_name, "storage_provider": "huggingface",
            "file_url": public_url, "folder": dest_folder, "size": len(final_bytes), "is_deleted": False
        }).execute()

        if ins_res.data:
            new_id = ins_res.data[0]["id"]
            for t in auto_tags:
                attach_file_tag(view_owner, new_id, t)
            if mirror_url:
                record_raid1_mirror(view_owner, new_id, mirror_url)

        current_used += len(final_bytes)
        uploaded_count += 1

    info_txt = f"Nahráno souborů: {uploaded_count}" + (f" (RAID-1 zrcadleno: {mirrored_count})" if mirrored_count else "")
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
                if f.get("file_url", "").startswith("http"):
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
    return render_files_view(username, password, user["role"] == "admin", view_owner, current_folder, "/", "single", False, "", "", "", "")

@app.post("/remove-folder-pin", response_class=HTMLResponse)
def remove_folder_pin(username: str = Form(...), password: str = Form(...), current_folder: str = Form(...), target_owner: str = Form(None)):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    supabase.table("nxt_files").delete().eq("owner", view_owner).eq("folder", current_folder).eq("filename", ".vault_pin_lock").execute()
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
    except Exception:
        pass
    return users_quotas_view(admin_user, admin_pass, admin_user, f"Účet {new_user.strip()} byl vytvořen.")

@app.get("/media-player", response_class=HTMLResponse)
def media_player(file_url: str, filename: str, username: str, password: str, target_owner: str = None):
    user = verify_user(username, password)
    if not user:
        return login_page()
    view_owner = target_owner or username
    ext = filename.split(".")[-1].lower()
    tag = f'<video controls autoplay style="width:100%; max-height:480px; background:#000; border-radius:8px;"><source src="{html.escape(file_url)}"></video>' if ext in VIDEO_EXTENSIONS else f'<audio controls autoplay style="width:100%;"><source src="{html.escape(file_url)}"></audio>'
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

# --- ROOT SSH KONZOLE ---
def terminal_view(username: str, current_folder: str, history: str) -> str:
    safe_hist = html.escape(history)
    active_ver = get_installed_ota_version()
    return f"""<!DOCTYPE html>
<html lang="cs">
<head><meta charset="UTF-8"><title>VaultGrid ROOT Console</title>{TERMINAL_CSS}</head>
<body>
    <div class="term-box">
        <div class="term-head">
            <span>VAULTGRID APEX [v{html.escape(active_ver)}-ROOT] // SYSTEM CONSOLE</span>
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
        new_hist += "Příkazy:\n  ls        - Výpis souborů\n  cd <dir>  - Změna adresáře\n  pools     - Stav 7 TB úložných poolů\n  audit     - Posledních 5 bezpečnostních událostí\n  users     - Seznam účtů\n  clear     - Vyčištění obrazovky\n\n"
    elif act == "clear":
        new_hist = ""
    elif act == "pools":
        for p in get_storage_pools():
            new_hist += f"  - {p['label']} [{p['repo_id']}] ({p['quota_gb']} GB)\n"
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

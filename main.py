import os
import json
import html
import hashlib
import urllib.request
from datetime import datetime, timezone
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_client, Client
from huggingface_hub import HfApi

app = FastAPI(title="VaultGrid Micro-Bootloader", version="1.0-BOOT")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_REPO_ID = os.environ.get("HF_REPO_ID")
ROOT_PASSWORD = os.environ.get("ROOT_PASSWORD", "root")

supabase: Client | None = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None
hf_api = HfApi(token=HF_TOKEN) if HF_TOKEN else None

# Globální stav načteného jádra v paměti
KERNEL_STATE = {
    "version": "UNINITIALIZED",
    "sha256": "",
    "code": "",
    "handler": None,
    "last_error": ""
}

def fetch_url_text(url: str, timeout: int = 8) -> str:
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")

def fetch_remote_manifest() -> dict | None:
    if not HF_REPO_ID:
        return None
    url = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/system_ota/manifest.json"
    try:
        return json.loads(fetch_url_text(url, timeout=6))
    except Exception:
        return None

def activate_kernel_code(code_str: str, version: str) -> tuple[bool, str]:
    """Ověří syntaxi, zkompiluje jádro a živě přepne obsluhu celého OS."""
    try:
        compiled = compile(code_str, f"<vaultgrid_os_kernel_v{version}>", "exec")
        namespace = {
            "__name__": "vaultgrid_os_kernel",
            "app": app,
            "supabase": supabase,
            "hf_api": hf_api,
            "HF_REPO_ID": HF_REPO_ID,
            "HF_TOKEN": HF_TOKEN,
            "ROOT_PASSWORD": ROOT_PASSWORD,
            "BOOTLOADER_VERSION": "1.0-BOOT",
            "ACTIVE_OS_VERSION": version,
            "HOT_SWAP_CALLBACK": perform_full_system_update,
            "ROLLBACK_CALLBACK": rollback_to_snapshot,
        }
        exec(compiled, namespace)
        if "dispatch_request" not in namespace or not callable(namespace["dispatch_request"]):
            return False, "Chyba jádra: Chybí vstupní funkce dispatch_request(request)."

        KERNEL_STATE["version"] = version
        KERNEL_STATE["sha256"] = hashlib.sha256(code_str.encode("utf-8")).hexdigest()
        KERNEL_STATE["code"] = code_str
        KERNEL_STATE["handler"] = namespace["dispatch_request"]
        KERNEL_STATE["last_error"] = ""
        return True, f"Jádro OS v{version} úspěšně aktivováno."
    except Exception as e:
        KERNEL_STATE["last_error"] = str(e)
        return False, f"Kompilace jádra selhala: {e}"

def persist_kernel_snapshot(version: str, code_str: str, sha: str):
    """Uloží aktivní jádro a zálohu předchozí verze do Supabase (přežije restart Renderu)."""
    if not supabase:
        return
    try:
        # Označit předchozí aktivní jádro jako zálohu (snapshot)
        prev = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_os_kernel_active").execute()
        for row in (prev.data or []):
            supabase.table("nxt_files").update({"storage_provider": "vault_os_kernel_backup"}).eq("id", row["id"]).execute()

        meta = json.dumps({
            "version": version,
            "sha256": sha,
            "installed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "code": code_str
        }, ensure_ascii=False)

        supabase.table("nxt_files").insert({
            "owner": "system",
            "filename": f"os_kernel_v{version}.py",
            "storage_provider": "vault_os_kernel_active",
            "file_url": meta,
            "folder": "/_system_core",
            "size": len(code_str),
            "is_deleted": False
        }).execute()
    except Exception:
        pass

def perform_full_system_update() -> tuple[bool, str]:
    """Stáhne kompletně nový OS z Hugging Face, ověří ho a provede Atomic Hot-Swap."""
    manifest = fetch_remote_manifest()
    if not manifest:
        return False, "Nepodařilo se načíst system_ota/manifest.json z Hugging Face."

    core_info = manifest.get("core_kernel")
    if not core_info or not core_info.get("code_url"):
        return False, "Manifest neobsahuje definici jádra (core_kernel.code_url)."

    target_ver = str(manifest.get("version", "21.0"))
    expected_sha = core_info.get("sha256", "")

    try:
        new_code = fetch_url_text(core_info["code_url"], timeout=12)
    except Exception as e:
        return False, f"Chyba stahování jádra: {e}"

    actual_sha = hashlib.sha256(new_code.encode("utf-8")).hexdigest()
    if expected_sha and expected_sha != actual_sha:
        return False, f"Bezpečnostní chyba: Nesouhlasí SHA-256 kontrolní součet ({actual_sha[:12]} != {expected_sha[:12]})."

    ok, msg = activate_kernel_code(new_code, target_ver)
    if not ok:
        return False, msg

    persist_kernel_snapshot(target_ver, new_code, actual_sha)
    return True, f"Celý systém byl úspěšně aktualizován na verzi v{target_ver} (SHA-256: {actual_sha[:12]})."

def rollback_to_snapshot(snapshot_id: int) -> tuple[bool, str]:
    """Vrátí celý operační systém na uloženou předchozí verzi."""
    if not supabase:
        return False, "Databáze není připojena."
    res = supabase.table("nxt_files").select("*").eq("id", snapshot_id).execute()
    if not res.data:
        return False, "Požadovaný snímek systému nebyl nalezen."
    try:
        meta = json.loads(res.data[0].get("file_url", "{}"))
        ver = meta.get("version", "rollback")
        code_str = meta.get("code", "")
        ok, msg = activate_kernel_code(code_str, ver)
        if ok:
            persist_kernel_snapshot(ver, code_str, meta.get("sha256", ""))
        return ok, msg
    except Exception as e:
        return False, f"Chyba při obnově ze zálohy: {e}"

@app.on_event("startup")
def boot_sequence():
    """Startovací sekvence: 1. Načte aktivní jádro ze Supabase, 2. Jinak stáhne z Hugging Face."""
    if supabase:
        try:
            res = supabase.table("nxt_files").select("*").eq("storage_provider", "vault_os_kernel_active").order("id", desc=True).limit(1).execute()
            if res.data:
                meta = json.loads(res.data[0].get("file_url", "{}"))
                if meta.get("code"):
                    ok, _ = activate_kernel_code(meta["code"], meta.get("version", "21.0"))
                    if ok:
                        return
        except Exception:
            pass
    perform_full_system_update()

# --- NOUZOVÝ ZÁCHRANNÝ REŽIM (VŽDY DOSTUPNÝ V BOOTLOADERU) ---
RECOVERY_CSS = """
<style>
    body { background:#0d0f12; color:#e5e7eb; font-family:system-ui,-apple-system,sans-serif; margin:0; padding:24px; font-size:13.5px; }
    .box { max-width:860px; margin:0 auto; background:#181c23; border:1px solid #2a303c; border-radius:6px; padding:20px; }
    h1 { font-size:16px; margin:0 0 12px 0; padding-bottom:10px; border-bottom:1px solid #2a303c; display:flex; justify-content:space-between; }
    .mono { font-family:monospace; }
    .btn { background:#2563eb; color:#fff; border:none; padding:8px 14px; border-radius:5px; cursor:pointer; font-size:13px; text-decoration:none; display:inline-block; }
    .btn-warn { background:#d97706; }
    .btn-sec { background:#1f242d; border:1px solid #2a303c; }
    input { background:#0d0f12; border:1px solid #2a303c; color:#fff; padding:8px 10px; border-radius:5px; width:240px; }
    table { width:100%; border-collapse:collapse; margin-top:12px; }
    th, td { padding:9px 10px; border-bottom:1px solid #2a303c; text-align:left; }
    th { color:#9ca3af; font-size:11.5px; text-transform:uppercase; }
    .alert { padding:10px 12px; background:#1f242d; border-left:4px solid #2563eb; margin-bottom:14px; }
</style>
"""

@app.get("/recovery", response_class=HTMLResponse)
def recovery_get(auth: str = "", msg: str = ""):
    if auth != ROOT_PASSWORD:
        return f"""<!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid Bootloader Recovery</title>{RECOVERY_CSS}</head>
        <body><div class="box" style="max-width:420px; margin-top:60px;">
            <h1><span>BOOTLOADER RECOVERY</span><span class="mono">v1.0</span></h1>
            <p style="color:#9ca3af;">Nouzová servisní konzole jádra. Zadejte heslo správce (<span class="mono">root</span>).</p>
            <form action="/recovery" method="GET">
                <input type="password" name="auth" placeholder="Heslo správce..." required autofocus>
                <button type="submit" class="btn">Vstoupit</button>
            </form>
        </div></body></html>"""

    backups_html = ""
    if supabase:
        b_res = supabase.table("nxt_files").select("*").in_("storage_provider", ["vault_os_kernel_active", "vault_os_kernel_backup"]).order("id", desc=True).limit(10).execute()
        for r in (b_res.data or []):
            try:
                m = json.loads(r.get("file_url", "{}"))
                st = "ACTIVE" if r["storage_provider"] == "vault_os_kernel_active" else "BACKUP"
                backups_html += f"""
                <tr>
                    <td class="mono">#{r['id']}</td>
                    <td class="mono">v{html.escape(str(m.get('version', '?')))}</td>
                    <td class="mono">{html.escape(m.get('sha256', '')[:16])}</td>
                    <td class="mono">{html.escape(m.get('installed_at', ''))}</td>
                    <td>{st}</td>
                    <td>
                        <form action="/recovery/rollback" method="POST" style="margin:0;">
                            <input type="hidden" name="auth" value="{html.escape(auth)}">
                            <input type="hidden" name="snapshot_id" value="{r['id']}">
                            <button type="submit" class="btn btn-warn" style="padding:4px 10px; font-size:12px;">Obnovit tuto verzi</button>
                        </form>
                    </td>
                </tr>"""
            except Exception:
                pass
    if not backups_html:
        backups_html = "<tr><td colspan='6' style='color:#9ca3af;'>Žádné uložené snímky jádra v databázi.</td></tr>"

    alert = f'<div class="alert">{html.escape(msg)}</div>' if msg else ""
    err_box = f'<div class="alert" style="border-left-color:#dc2626;">Poslední chyba jádra: <span class="mono">{html.escape(KERNEL_STATE["last_error"])}</span></div>' if KERNEL_STATE["last_error"] else ""

    return f"""<!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid Bootloader Recovery</title>{RECOVERY_CSS}</head>
    <body><div class="box">
        <h1><span>VAULTGRID BOOTLOADER // RECOVERY CONSOLE</span><span class="mono">ACTIVE: v{html.escape(KERNEL_STATE['version'])}</span></h1>
        {alert}
        {err_box}
        <p style="color:#9ca3af;">Aktivní SHA-256 jádra: <span class="mono">{html.escape(KERNEL_STATE['sha256'] or 'N/A')}</span></p>
        <div style="display:flex; gap:10px; margin-bottom:18px;">
            <form action="/recovery/pull" method="POST" style="margin:0;">
                <input type="hidden" name="auth" value="{html.escape(auth)}">
                <button type="submit" class="btn">Stáhnout a aktivovat nejnovější OS z Hugging Face</button>
            </form>
            <a href="/" class="btn btn-sec">Přejít do hlavního systému</a>
        </div>
        <table>
            <thead><tr><th>ID</th><th>Verze OS</th><th>SHA-256</th><th>Instalováno</th><th>Stav</th><th>Akce</th></tr></thead>
            <tbody>{backups_html}</tbody>
        </table>
    </div></body></html>"""

@app.post("/recovery/pull", response_class=HTMLResponse)
def recovery_pull(auth: str = Form(...)):
    if auth != ROOT_PASSWORD:
        return RedirectResponse("/recovery", status_code=303)
    _, msg = perform_full_system_update()
    return recovery_get(auth=auth, msg=msg)

@app.post("/recovery/rollback", response_class=HTMLResponse)
def recovery_rollback(auth: str = Form(...), snapshot_id: int = Form(...)):
    if auth != ROOT_PASSWORD:
        return RedirectResponse("/recovery", status_code=303)
    _, msg = rollback_to_snapshot(snapshot_id)
    return recovery_get(auth=auth, msg=msg)

# --- UNIVERZÁLNÍ ROUTER PRO CELÝ OPERAČNÍ SYSTÉM ---
@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def os_kernel_gateway(request: Request, full_path: str):
    if KERNEL_STATE["handler"] is None:
        ok, msg = perform_full_system_update()
        if not ok:
            return HTMLResponse(
                content=f"""<!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><title>VaultGrid Bootloader</title>{RECOVERY_CSS}</head>
                <body><div class="box" style="max-width:560px; margin-top:60px;">
                    <h1><span>VAULTGRID MICRO-BOOTLOADER</span><span class="mono">READY</span></h1>
                    <p>Bootloader je spuštěn, ale na Hugging Face zatím není publikováno jádro systému (<span class="mono">system_ota/os_kernel.py</span>).</p>
                    <div class="alert" style="border-left-color:#d97706;">Stav: {html.escape(msg)}</div>
                    <a href="/recovery" class="btn">Otevřít Recovery konzoli</a>
                </div></body></html>""",
                status_code=200
            )
    return await KERNEL_STATE["handler"](request)

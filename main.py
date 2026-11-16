import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client

app = FastAPI(title="Můj Reálný Server", version="1.0")

# Připojení ke Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Definice struktury příchozích dat (co uživatel pošle)
class Poznamka(BaseModel):
    text: str
    autor: str

@app.get("/")
def hlavni_stranka():
    return {
        "stav": "Server běží!",
        "zprava": "Ahoj z mého vlastního Python serveru!",
        "supabase_pripojeno": supabase is not None
    }

# 1. API endpoint pro ULOŽENÍ dat do Supabase databáze
@app.post("/pridat-poznamku")
def pridat_poznamku(poznamka: Poznamka):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase není připojena!")
    
    # Uložení dat do tabulky 'poznamky' v Supabase
    data = {"text": poznamka.text, "autor": poznamka.autor}
    response = supabase.table("poznamky").insert(data).execute()
    
    return {"status": "Uloženo!", "zaznam": response.data}

# 2. API endpoint pro ČTENÍ dat ze Supabase databáze
@app.get("/zobrazit-poznamky")
def zobrazit_poznamky():
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase není připojena!")
    
    # Stažení všech záznamů z tabulky 'poznamky'
    response = supabase.table("poznamky").select("*").execute()
    
    return {"poznamky": response.data}

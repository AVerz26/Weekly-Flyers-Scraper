import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.config import (
    load_config, save_config, mask_secret, 
    BASE_DIR, DATA_DIR, OUTPUT_DIR
)
from core.task_runner import task_manager
from core.exporter import get_latest_results, list_history_runs

app = FastAPI(
    title="Instagram Supermarket Flyers Scraper",
    description="Interface moderna e leve para automação de scraping de encartes de supermercados e extração com IA",
    version="1.0.0"
)

# Monta arquivos estáticos e templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- Modelos de Dados Pydantic ---
class ConfigUpdate(BaseModel):
    apify_token: Optional[str] = None
    vision_provider: Optional[str] = "gemini"
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_model: Optional[str] = "gemini-1.5-flash"
    date_mode: Optional[str] = "yesterday_today"
    custom_start_date: Optional[str] = ""
    custom_end_date: Optional[str] = ""
    results_limit: Optional[int] = 3

class ProfileItem(BaseModel):
    name: str
    url: str
    enabled: bool = True

class ProfilesUpdate(BaseModel):
    profiles: List[ProfileItem]

class StartScrapeRequest(BaseModel):
    date_mode: Optional[str] = None
    custom_start_date: Optional[str] = None
    custom_end_date: Optional[str] = None
    results_limit: Optional[int] = None
    vision_provider: Optional[str] = None

# --- Rotas da Aplicação ---

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """Página principal da interface web."""
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/config")
async def get_configuration():
    """Retorna a configuração com chaves mascaradas para visualização segura."""
    cfg = load_config()
    safe_cfg = dict(cfg)
    safe_cfg["apify_token_masked"] = mask_secret(cfg.get("apify_token"))
    safe_cfg["gemini_api_key_masked"] = mask_secret(cfg.get("gemini_api_key"))
    safe_cfg["openai_api_key_masked"] = mask_secret(cfg.get("openai_api_key"))
    safe_cfg["has_apify_token"] = bool(cfg.get("apify_token"))
    safe_cfg["has_gemini_key"] = bool(cfg.get("gemini_api_key"))
    safe_cfg["has_openai_key"] = bool(cfg.get("openai_api_key"))
    return safe_cfg

@app.post("/api/config")
async def update_configuration(data: ConfigUpdate):
    """Atualiza configurações de credenciais e parâmetros."""
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    saved = save_config(updates)
    return {"status": "success", "message": "Configurações salvas com sucesso!"}

@app.get("/api/profiles")
async def get_profiles():
    """Retorna a lista de perfis de supermercados."""
    cfg = load_config()
    return {"profiles": cfg.get("profiles", [])}

@app.post("/api/profiles")
async def update_profiles(data: ProfilesUpdate):
    """Atualiza a lista completa de perfis."""
    profiles_list = [p.model_dump() for p in data.profiles]
    save_config({"profiles": profiles_list})
    return {"status": "success", "message": f"{len(profiles_list)} perfis atualizados!", "profiles": profiles_list}

@app.post("/api/scrape/start")
async def start_scraping(req: Optional[StartScrapeRequest] = None):
    """Inicia o processo de scraping em segundo plano."""
    if task_manager.is_running:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Um processo já está em andamento."})
        
    custom_params = {}
    if req:
        custom_params = {k: v for k, v in req.model_dump().items() if v is not None}
        
    started = task_manager.start_task(custom_params)
    if started:
        return {"status": "success", "message": "Scraping iniciado em segundo plano!"}
    else:
        return JSONResponse(status_code=500, content={"status": "error", "message": "Falha ao iniciar processo."})

@app.post("/api/scrape/stop")
async def stop_scraping():
    """Cancela o processo em andamento."""
    task_manager.cancel_task()
    return {"status": "success", "message": "Solicitação de cancelamento enviada."}

@app.get("/api/scrape/status")
async def get_scrape_status():
    """Retorna o status atual da execução."""
    return task_manager.get_status()

@app.get("/api/scrape/logs/stream")
async def stream_logs():
    """Endpoint de Server-Sent Events (SSE) para streaming de logs em tempo real."""
    async def event_generator():
        q = task_manager.subscribe_logs()
        try:
            # Envia status inicial
            yield f"data: {json.dumps({'type': 'init', 'status': task_manager.get_status()})}\n\n"
            
            while True:
                # Checa se há novas mensagens na fila
                try:
                    line = q.get_nowait()
                    yield f"data: {json.dumps({'type': 'log', 'text': line})}\n\n"
                except Exception:
                    await asyncio.sleep(0.3)
                    # Envia ping de status periódico
                    st = task_manager.get_status()
                    yield f"data: {json.dumps({'type': 'status', 'status': st})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            task_manager.unsubscribe_logs(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/results/latest")
async def get_latest_data():
    """Retorna o último conjunto de ofertas extraído."""
    data = get_latest_results()
    if not data:
        return {"total_itens": 0, "supermercados": [], "items": []}
    return data

@app.get("/api/results/history")
async def get_history():
    """Retorna arquivos de execuções anteriores."""
    return {"history": list_history_runs()}

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download de planilhas Excel ou CSV geradas."""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
        
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if filename.endswith(".csv"):
        media_type = "text/csv"
    elif filename.endswith(".json"):
        media_type = "application/json"
        
    return FileResponse(path=file_path, filename=filename, media_type=media_type)

if __name__ == "__main__":
    import uvicorn
    cfg = load_config()
    port = int(os.getenv("SERVER_PORT", 8000))
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    print(f"🚀 Iniciando servidor em http://localhost:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=True)

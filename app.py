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
    load_scraped_images, save_scraped_images,
    BASE_DIR, DATA_DIR, OUTPUT_DIR
)
from core.task_runner import task_manager
from core.vision_ai import process_image_offers
from core.categorizer import categorizar_produto
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
    gemini_model: Optional[str] = "gemini-flash-lite-latest"
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
    mode: Optional[str] = "full" # "full", "scrape_only", "vision_only"
    date_mode: Optional[str] = None
    custom_start_date: Optional[str] = None
    custom_end_date: Optional[str] = None
    results_limit: Optional[int] = None
    vision_provider: Optional[str] = None
    gemini_model: Optional[str] = None
    openai_model: Optional[str] = None

class SingleTestRequest(BaseModel):
    image_url: str
    supermercado: Optional[str] = "Supermercado"
    vision_provider: Optional[str] = None
    model_name: Optional[str] = None

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

@app.get("/api/scraped-images")
async def get_scraped_images():
    """Retorna a lista de imagens de encartes salvas na última coleta."""
    images = load_scraped_images()
    return {"total": len(images), "images": images}

@app.post("/api/vision/test-single")
async def test_single_image(req: SingleTestRequest):
    """Executa a extração por IA em uma única imagem de encarte em tempo real."""
    cfg = load_config()
    provider = req.vision_provider or cfg.get("vision_provider", "gemini")
    gemini_key = cfg.get("gemini_api_key", "")
    openai_key = cfg.get("openai_api_key", "")
    model_name = req.model_name or (cfg.get("gemini_model", "gemini-flash-lite-latest") if provider == "gemini" else "gpt-4o-mini")

    try:
        result = process_image_offers(
            image_url=req.image_url,
            provider=provider,
            gemini_key=gemini_key,
            openai_key=openai_key,
            model_name=model_name
        )
        if not result:
            return {
                "status": "warning",
                "message": "Nenhum dado retornado pela IA ou a imagem não pôde ser baixada do CDN.",
                "ofertas": []
            }

        ofertas_processadas = []
        for of in result.get("ofertas", []):
            nome = of.get("item") or of.get("nome", "")
            val = of.get("valor", 0.0)
            if not nome:
                continue
            cat_ia = of.get("categoria", "")
            if not cat_ia or cat_ia.lower() == "outros":
                cat = categorizar_produto(nome)
            else:
                cat = cat_ia
            
            ofertas_processadas.append({
                "item": nome,
                "valor": val,
                "categoria": cat
            })

        return {
            "status": "success",
            "supermercado": req.supermercado,
            "provider": provider,
            "model": model_name,
            "total_ofertas": len(ofertas_processadas),
            "ofertas": ofertas_processadas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar encarte com IA: {str(e)}")

@app.post("/api/scrape/start")
async def start_scraping(req: Optional[StartScrapeRequest] = None):
    """Inicia o processo de scraping ou extração em segundo plano."""
    if task_manager.is_running:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Um processo já está em andamento."})
        
    custom_params = {}
    if req:
        custom_params = {k: v for k, v in req.model_dump().items() if v is not None}
        
    started = task_manager.start_task(custom_params)
    if started:
        mode_names = {"full": "Pipeline Completo", "scrape_only": "Coleta de Encartes", "vision_only": "Extração com IA"}
        m_name = mode_names.get(custom_params.get("mode", "full"), "Processo")
        return {"status": "success", "message": f"{m_name} iniciado em segundo plano!"}
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

from core.db import (
    init_db, get_price_comparison, get_database_stats, 
    get_product_price_history
)
from core.exporter import get_latest_results, list_history_runs, export_comparison_excel

# Inicializa banco de dados ao carregar a aplicação
init_db()

@app.get("/api/database/stats")
async def get_db_stats():
    """Retorna estatísticas gerais das ofertas e produtos armazenados no banco SQLite."""
    return get_database_stats()

@app.get("/api/database/comparison")
async def get_db_comparison(
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_markets: int = 1
):
    """
    Retorna comparativo de preços agrupado por Produto Padronizado com destaque
    para menor preço, maior preço, economia e lista de supermercados.
    """
    items = get_price_comparison(category=category, search=search, min_markets=min_markets)
    return {
        "total_produtos": len(items),
        "comparison": items
    }

@app.get("/api/database/product-history")
async def get_product_history(product_name: str):
    """Retorna histórico de preços de um produto específico."""
    return {"history": get_product_price_history(product_name)}

class ExportComparisonRequest(BaseModel):
    category: Optional[str] = None
    search: Optional[str] = None
    min_markets: int = 1

@app.post("/api/database/export-comparison")
async def export_comparison(req: ExportComparisonRequest):
    """Gera planilha Excel com matriz comparativa de preços entre supermercados."""
    items = get_price_comparison(category=req.category, search=req.search, min_markets=req.min_markets)
    filename = export_comparison_excel(items)
    return {"status": "success", "filename": filename, "download_url": f"/api/download/{filename}"}

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

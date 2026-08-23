import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Diretório base
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
ENV_FILE = BASE_DIR / ".env"
CONFIG_FILE = DATA_DIR / "config.json"

# Carrega .env se existir
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=False)

DEFAULT_PROFILES = [
    {"name": "Supermercado Tuiuiú", "url": "https://www.instagram.com/supermercado_tuiuiu/", "enabled": True},
    {"name": "Super São Pedro", "url": "https://www.instagram.com/supersaopedroo/", "enabled": True},
    {"name": "Parceirão PVA", "url": "https://www.instagram.com/parceiraopva/", "enabled": True},
    {"name": "Super Compras", "url": "https://www.instagram.com/supercompras_supermercado/", "enabled": True},
    {"name": "Rede Mercado Bom Jesus", "url": "https://www.instagram.com/redemercadobomjesus/", "enabled": True},
    {"name": "Mercado Cordeirão", "url": "https://www.instagram.com/mercadocordeirao_pva/", "enabled": True},
    {"name": "Machadão Atacadista", "url": "https://www.instagram.com/machadaoatacadista/", "enabled": True},
    {"name": "Mercado Talismã", "url": "https://www.instagram.com/mercadotalismapva/", "enabled": True},
    {"name": "Paranaense Supermercado", "url": "https://www.instagram.com/paranaensesupermercado/", "enabled": True},
    {"name": "Ramin Supermercado", "url": "https://www.instagram.com/raminsupermercado/", "enabled": True},
    {"name": "Bianchi Supermercado", "url": "https://www.instagram.com/bianchi_supermercado/", "enabled": True}
]

def mask_secret(secret: Optional[str]) -> str:
    """Mascara chaves de API para exibição segura na interface."""
    if not secret:
        return ""
    if len(secret) <= 8:
        return "********"
    return secret[:4] + "*" * (len(secret) - 8) + secret[-4:]

def get_default_config() -> Dict[str, Any]:
    """Retorna configuração padrão mesclando com variáveis de ambiente."""
    return {
        "apify_token": os.getenv("APIFY_TOKEN", ""),
        "vision_provider": os.getenv("VISION_PROVIDER", "gemini"),
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        "date_mode": "yesterday_today", # "today", "yesterday_today", "last_3_days", "last_7_days", "custom"
        "custom_start_date": "",
        "custom_end_date": "",
        "results_limit": 3,
        "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_TOKEN", "")),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
        "telegram_enabled": os.getenv("TELEGRAM_ENABLED", "true").lower() in ("true", "1", "yes"),
        "telegram_send_excel": os.getenv("TELEGRAM_SEND_EXCEL", "true").lower() in ("true", "1", "yes"),
        "profiles": DEFAULT_PROFILES
    }

def load_config() -> Dict[str, Any]:
    """Carrega configuração do arquivo JSON ou cria padrão."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    defaults = get_default_config()
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                # Mescla chaves salvas com os defaults
                for key, val in defaults.items():
                    if key not in saved:
                        saved[key] = val
                    elif key in ["apify_token", "gemini_api_key", "openai_api_key", "telegram_token"]:
                        # Se estiver vazio no JSON mas presente no .env, usa do .env
                        if not saved[key] and val:
                            saved[key] = val
                return saved
        except Exception:
            pass
            
    # Salva configuração inicial
    save_config(defaults)
    return defaults

def save_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
    """Salva configurações no arquivo JSON local e atualiza .env se necessário."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    current = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                current = json.load(f)
        except Exception:
            current = {}
            
    # Preserva chaves confidenciais se o usuário enviou valor mascarado ou em branco
    for secret_key in ["apify_token", "gemini_api_key", "openai_api_key", "telegram_token"]:
        if secret_key in new_config:
            val = new_config[secret_key]
            if not val or "*" in val:
                new_config[secret_key] = current.get(secret_key, os.getenv(secret_key.upper(), ""))

    current.update(new_config)
    
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)
        
    return current

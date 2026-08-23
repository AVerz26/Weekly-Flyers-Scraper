import re
import json
import base64
import time
import requests
from typing import Optional, Dict, Any, List

SYSTEM_PROMPT = """Você é um especialista em análise e extração de encartes, panfletos e ofertas de supermercados brasileiros.
Analise a imagem com máxima precisão e extraia TODOS os produtos e seus respectivos preços promocionais.

Retorne EXCLUSIVAMENTE um objeto JSON no seguinte formato:
{
  "ofertas": [
    {
      "item": "Nome completo do produto (com marca, tipo e peso/volume se visível no encarte)",
      "valor": 9.99
    }
  ]
}

Regras:
1. O campo "valor" DEVE ser um número float (ex: 12.99 e não "R$ 12,99").
2. Se a imagem não contiver ofertas ou preços (ex: apenas logotipo, foto de evento ou aviso), retorne: {"ofertas": []}.
3. Não invente produtos nem adicione texto fora do JSON.
"""

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extrai e valida JSON contido em respostas de IA."""
    if not text:
        return None
    try:
        # Tenta carregar diretamente
        return json.loads(text.strip())
    except Exception:
        pass
        
    # Tenta encontrar bloco ```json ... ```
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
            
    # Tenta regex amplo para capturar chaves {}
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
            
    return None

def download_image_as_base64(image_url: str) -> Optional[tuple[str, str]]:
    """Baixa imagem da URL e retorna (base64_str, mime_type)."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
    }
    for attempt in range(2):
        try:
            resp = requests.get(image_url, headers=headers, timeout=25, allow_redirects=True)
            if resp.status_code == 200 and resp.content:
                mime_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
                if not mime_type.startswith("image/"):
                    mime_type = "image/jpeg"
                b64 = base64.b64encode(resp.content).decode("utf-8")
                return b64, mime_type
        except Exception as e:
            time.sleep(1)
    return None

def process_with_gemini(image_url: str, api_key: str, model_name: str = "gemini-2.5-flash") -> Optional[Dict[str, Any]]:
    """Processa imagem de encarte usando a API do Google Gemini com fallback automático de modelos."""
    img_data = download_image_as_base64(image_url)
    if not img_data:
        return None
        
    b64_img, mime_type = img_data
    
    # Modelos candidatos em ordem de prioridade
    candidate_models = []
    if model_name:
        candidate_models.append(model_name)
    for fallback in ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-1.5-flash"]:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_img
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    for current_model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key}"
        for attempt in range(2):
            try:
                resp = requests.post(url, json=payload, timeout=40)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            text = parts[0].get("text", "")
                            res_json = extract_json_from_text(text)
                            if res_json is not None:
                                return res_json
                elif resp.status_code == 404:
                    # Modelo não suportado nesta versão de API, pula para o próximo modelo candidato
                    break
                elif resp.status_code in (429, 503):
                    time.sleep(2 * (attempt + 1))
            except Exception:
                time.sleep(1)

    return None

def process_with_openai(image_url: str, api_key: str, model_name: str = "gpt-4o-mini") -> Optional[Dict[str, Any]]:
    """Processa imagem de encarte usando a API da OpenAI."""
    img_data = download_image_as_base64(image_url)
    if not img_data:
        return None
        
    b64_img, mime_type = img_data
    data_url = f"data:{mime_type};base64,{b64_img}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SYSTEM_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}}
                ]
            }
        ],
        "max_tokens": 1500
    }
    
    try:
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=45)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return extract_json_from_text(content)
        else:
            print(f"⚠️ Erro OpenAI ({resp.status_code}): {resp.text[:120]}")
    except Exception as e:
        print(f"⚠️ Exceção OpenAI: {e}")
        
    return None

def process_image_offers(
    image_url: str,
    provider: str,
    gemini_key: str = "",
    openai_key: str = "",
    model_name: str = "gemini-1.5-flash"
) -> Optional[Dict[str, Any]]:
    """
    Roteador principal para extração de ofertas via IA de visão.
    """
    if provider == "gemini" or (not provider and gemini_key):
        if not gemini_key:
            raise ValueError("Chave da API do Google Gemini não configurada.")
        return process_with_gemini(image_url, gemini_key, model_name or "gemini-1.5-flash")
    elif provider == "openai":
        if not openai_key:
            raise ValueError("Chave da API da OpenAI não configurada.")
        return process_with_openai(image_url, openai_key)
    elif provider == "qwen":
        # Fallback para Qwen local se configurado
        try:
            from core.qwen_local import process_qwen_local
            return process_qwen_local(image_url)
        except ImportError:
            # Fallback para Gemini se Qwen não estiver disponível
            if gemini_key:
                return process_with_gemini(image_url, gemini_key, "gemini-1.5-flash")
            raise ValueError("Qwen local não disponível e chave Gemini ausente.")
    else:
        # Padrão
        if gemini_key:
            return process_with_gemini(image_url, gemini_key, "gemini-1.5-flash")
        elif openai_key:
            return process_with_openai(image_url, openai_key)
        else:
            raise ValueError("Nenhuma chave de API de IA fornecida (Gemini ou OpenAI).")

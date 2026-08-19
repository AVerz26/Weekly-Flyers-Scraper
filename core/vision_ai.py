import re
import json
import base64
import time
import requests
from typing import Optional, Dict, Any, List

SYSTEM_PROMPT = """Você é um especialista em análise e extração de encartes, panfletos e ofertas promocionais de supermercados brasileiros.
Analise a imagem com máxima precisão e extraia TODOS os produtos, preços promocionais, marcas e nomes padronizados para comparação de preços.

Categorias padronizadas permitidas para o campo "categoria":
- "Carnes / Bovina"
- "Carnes / Aves"
- "Carnes / Suína e Embutidos"
- "Carnes / Peixes"
- "Bebidas / Cervejas"
- "Bebidas / Refrigerantes"
- "Bebidas / Sucos e Diversos"
- "Bebidas / Alcoólicos Diversos"
- "Laticínios / Leites e Derivados"
- "Hortifruti / Ovos"
- "Mercearia / Arroz"
- "Mercearia / Grãos e Conservas"
- "Mercearia / Óleos e Azeites"
- "Mercearia / Café"
- "Mercearia / Açúcar"
- "Mercearia / Farináceos"
- "Mercearia / Molhos e Condimentos"
- "Mercearia / Massas"
- "Mercearia / Biscoitos e Doces"
- "Padaria / Pães"
- "Padaria / Congelados"
- "Congelados e Sobremesas"
- "Limpeza / Lavanderia e Louça"
- "Limpeza / Cuidados com a Casa"
- "Higiene / Cuidados Pessoais"
- "Higiene / Papelaria"
- "Pet Shop"
- "Bazar / Eletro"
- "Outros"

Retorne EXCLUSIVAMENTE um objeto JSON no seguinte formato:
{
  "ofertas": [
    {
      "item": "Texto original completo do produto com detalhes no encarte",
      "produto_padronizado": "Nome limpo e canônico do produto (ex: Cerveja Heineken Lata 350ml)",
      "marca": "Marca do produto (ex: Heineken, Omo, Tio João)",
      "valor": 9.99,
      "categoria": "Bebidas / Cervejas"
    }
  ]
}

Regras:
1. O campo "valor" DEVE ser um número float (ex: 12.99 e não "R$ 12,99").
2. O campo "produto_padronizado" DEVE ser um nome conciso e limpo no padrão: [Produto Base] [Marca] [Volume/Peso/Tipo] sem termos promocionais ("oferta", "super preço", "cada", etc.).
3. O campo "categoria" DEVE conter uma das categorias padronizadas acima que melhor classifique o produto.
4. Se a imagem não contiver ofertas ou preços (ex: apenas logotipo, foto institucional, aviso ou sorteio), retorne: {"ofertas": []}.
5. Não invente produtos nem adicione texto fora do JSON.
"""

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extrai e valida JSON contido em respostas de IA."""
    if not text:
        return None
    try:
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

def download_image_as_base64(image_url: str, max_retries: int = 3) -> Optional[tuple[str, str]]:
    """Baixa imagem da URL e retorna (base64_str, mime_type) com retries resilientes para CDNs."""
    if not image_url:
        return None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.instagram.com/'
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(image_url, headers=headers, timeout=(10, 30))
            if resp.status_code == 200:
                mime_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
                if not mime_type.startswith("image/"):
                    mime_type = "image/jpeg"
                b64 = base64.b64encode(resp.content).decode("utf-8")
                return b64, mime_type
            elif resp.status_code in (403, 429, 502, 503):
                time.sleep(1.5 * attempt)
        except Exception as e:
            if attempt == max_retries:
                print(f"⚠️ Erro ao baixar imagem após {max_retries} tentativas ({image_url[:50]}...): {e}")
            time.sleep(1.5 * attempt)

    return None

def process_with_gemini(image_url: str, api_key: str, model_name: str = "gemini-flash-lite-latest") -> Optional[Dict[str, Any]]:
    """Processa imagem de encarte usando a API do Google Gemini com fallback automático de modelos."""
    img_data = download_image_as_base64(image_url)
    if not img_data:
        return None
        
    b64_img, mime_type = img_data
    
    # Ordem de tentativa: modelo solicitado seguido dos modelos ativos no endpoint
    candidate_models = [model_name or "gemini-flash-lite-latest", "gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3-flash-preview"]
    seen = set()
    models_to_try = [m for m in candidate_models if m and not (m in seen or seen.add(m))]

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
    
    for active_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={api_key}"
        for attempt in range(2):
            try:
                resp = requests.post(url, json=payload, timeout=35)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = extract_json_from_text(text)
                    if parsed:
                        return parsed
                elif resp.status_code in (404, 400):
                    # Modelo indisponível nesta versão/região, tenta próximo modelo
                    break
                elif resp.status_code in (429, 503):
                    time.sleep(1.5 * (attempt + 1))
                else:
                    print(f"⚠️ Erro Gemini ({active_model} - {resp.status_code}): {resp.text[:100]}")
                    time.sleep(1)
            except Exception as e:
                print(f"⚠️ Exceção Gemini ({active_model} tentativa {attempt+1}): {e}")
                time.sleep(1.5)
            
    return None

def process_with_openai(image_url: str, api_key: str, model_name: str = "gpt-4o-mini") -> Optional[Dict[str, Any]]:
    """Processa imagem de encarte usando a API da OpenAI."""
    img_data = download_image_as_base64(image_url)
    if not img_data:
        return None
        
    b64_img, mime_type = img_data
    data_url = f"data:{mime_type};base64,{b64_img}"
    
    active_model = model_name or "gpt-4o-mini"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": active_model,
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
        "max_tokens": 2000
    }
    
    for attempt in range(3):
        try:
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return extract_json_from_text(content)
            elif resp.status_code == 429:
                time.sleep(2 * (attempt + 1))
            else:
                print(f"⚠️ Erro OpenAI ({resp.status_code}): {resp.text[:120]}")
                time.sleep(1)
        except Exception as e:
            print(f"⚠️ Exceção OpenAI (tentativa {attempt+1}): {e}")
            time.sleep(2)
            
    return None

def process_image_offers(
    image_url: str,
    provider: str,
    gemini_key: str = "",
    openai_key: str = "",
    model_name: str = "gemini-1.5-flash"
) -> Optional[Dict[str, Any]]:
    """
    Roteador principal para extração de ofertas e categorização via IA de visão.
    """
    if provider == "gemini" or (not provider and gemini_key):
        if not gemini_key:
            raise ValueError("Chave da API do Google Gemini não configurada.")
        return process_with_gemini(image_url, gemini_key, model_name or "gemini-1.5-flash")
    elif provider == "openai":
        if not openai_key:
            raise ValueError("Chave da API da OpenAI não configurada.")
        return process_with_openai(image_url, openai_key, model_name or "gpt-4o-mini")
    else:
        # Fallback inteligente
        if gemini_key:
            return process_with_gemini(image_url, gemini_key, model_name or "gemini-1.5-flash")
        elif openai_key:
            return process_with_openai(image_url, openai_key, model_name or "gpt-4o-mini")
        else:
            raise ValueError("Nenhuma chave de API de IA fornecida (Gemini ou OpenAI).")

import os
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

TELEGRAM_API_BASE = "https://api.telegram.org/bot"

def send_telegram_message(
    token: str,
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True
) -> Tuple[bool, str]:
    """
    Envia uma mensagem de texto para o Telegram (usuário, canal ou grupo).
    Se a mensagem for maior que 4000 caracteres, divide em partes automaticamente.
    """
    if not token or not chat_id:
        return False, "Token ou Chat ID do Telegram não configurados."

    url = f"{TELEGRAM_API_BASE}{token.strip()}/sendMessage"
    
    # Limite do Telegram por mensagem é 4096 caracteres
    max_len = 3900
    chunks = []
    if len(text) <= max_len:
        chunks = [text]
    else:
        # Divide por linhas mantendo blocos
        lines = text.split("\n")
        current_chunk = ""
        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_len:
                chunks.append(current_chunk)
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"
        if current_chunk:
            chunks.append(current_chunk)

    success_all = True
    last_err = ""

    for chunk in chunks:
        payload = {
            "chat_id": chat_id.strip(),
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }
        try:
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code != 200:
                success_all = False
                last_err = f"Erro Telegram ({resp.status_code}): {resp.text}"
        except Exception as e:
            success_all = False
            last_err = str(e)

    if success_all:
        return True, "Mensagem enviada com sucesso ao Telegram!"
    return False, last_err

def send_telegram_document(
    token: str,
    chat_id: str,
    file_path: Path | str,
    caption: str = ""
) -> Tuple[bool, str]:
    """Envia um arquivo (planilha Excel, CSV, etc.) para o Telegram."""
    if not token or not chat_id:
        return False, "Token ou Chat ID do Telegram não configurados."

    p = Path(file_path)
    if not p.exists() or not p.is_file():
        return False, f"Arquivo não encontrado: {file_path}"

    url = f"{TELEGRAM_API_BASE}{token.strip()}/sendDocument"

    try:
        with open(p, "rb") as f:
            files = {"document": (p.name, f)}
            data = {
                "chat_id": chat_id.strip(),
                "caption": caption[:1024],
                "parse_mode": "HTML"
            }
            resp = requests.post(url, data=data, files=files, timeout=40)
            if resp.status_code == 200:
                return True, "Documento enviado com sucesso!"
            else:
                return False, f"Erro Telegram ({resp.status_code}): {resp.text}"
    except Exception as e:
        return False, str(e)

def test_telegram_connection(token: str, chat_id: str) -> Tuple[bool, str]:
    """Testa se as credenciais do bot do Telegram estão funcionando."""
    if not token:
        return False, "Token do Telegram não informado."
    if not chat_id:
        return False, "Chat ID do Telegram não informado."

    # 1. Valida o bot com getMe
    try:
        me_resp = requests.get(f"{TELEGRAM_API_BASE}{token.strip()}/getMe", timeout=10)
        if me_resp.status_code != 200:
            return False, f"Token do bot inválido ({me_resp.status_code}): {me_resp.text}"
        bot_info = me_resp.json().get("result", {})
        bot_username = bot_info.get("username", "Bot")
    except Exception as e:
        return False, f"Falha ao conectar com API do Telegram: {e}"

    # 2. Envia mensagem de teste
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    msg = (
        f"🤖 <b>Teste de Conexão com Sucesso!</b>\n\n"
        f"✅ Bot: <b>@{bot_username}</b>\n"
        f"🕒 Horário: {agora}\n"
        f"🚀 As notificações de encartes de supermercados estão prontas para envio neste chat."
    )
    return send_telegram_message(token, chat_id, msg)

def format_daily_digest(
    novas_ofertas: List[Dict[str, Any]],
    total_scraped: int,
    total_duplicadas: int,
    excel_filename: Optional[str] = None
) -> str:
    """Formata o resumo diário em HTML elegante para o Telegram."""
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    total_novas = len(novas_ofertas)

    header = [
        "🛒 <b>RELATÓRIO DIÁRIO DE ENCARTES & OFERTAS</b>",
        f"📅 <i>{agora}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"🔍 <b>Itens Analisados:</b> {total_scraped}",
        f"✨ <b>Novas Ofertas:</b> {total_novas}",
        f"♻️ <b>Repetidos (Ignorados):</b> {total_duplicadas}",
        "━━━━━━━━━━━━━━━━━━━━━━\n"
    ]

    if total_novas == 0:
        header.append("ℹ️ <i>Nenhuma oferta nova detectada hoje nos encartes monitorados.</i>")
        return "\n".join(header)

    # Agrupa por supermercado
    por_mercado: Dict[str, List[Dict[str, Any]]] = {}
    for of in novas_ofertas:
        mercado = of.get("supermercado", "Supermercado")
        if mercado not in por_mercado:
            por_mercado[mercado] = []
        por_mercado[mercado].append(of)

    body = []
    for mercado, itens in por_mercado.items():
        body.append(f"🏪 <b>{mercado}</b> (<i>{len(itens)} novas</i>)")
        # Mostra até 15 itens por mercado para manter conciso
        for item in itens[:15]:
            nome = item.get("item", "Produto").strip()
            preco = item.get("valor", 0)
            categoria = item.get("categoria", "")
            cat_tag = f" [{categoria}]" if categoria and categoria != "Geral" else ""
            body.append(f" • <b>R$ {preco:,.2f}</b> - {nome}{cat_tag}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        if len(itens) > 15:
            body.append(f" <i>... e mais {len(itens) - 15} produtos na planilha anexa.</i>")
        body.append("")

    return "\n".join(header) + "\n" + "\n".join(body)

def send_daily_notification(
    token: str,
    chat_id: str,
    novas_ofertas: List[Dict[str, Any]],
    total_scraped: int,
    total_duplicadas: int,
    excel_path: Optional[Path | str] = None,
    send_excel: bool = True
) -> Tuple[bool, str]:
    """
    Função principal que envia o resumo e opcionalmente o arquivo Excel.
    """
    if not token or not chat_id:
        return False, "Credenciais do Telegram não configuradas."

    # 1. Envia o texto formatado
    texto = format_daily_digest(novas_ofertas, total_scraped, total_duplicadas)
    ok_msg, err_msg = send_telegram_message(token, chat_id, texto)

    # 2. Se houver planilha e opção de envio de excel ativa, anexa
    if ok_msg and send_excel and excel_path and Path(excel_path).exists():
        caption = f"📊 Planilha consolidada com {total_scraped} produtos extraídos ({datetime.now().strftime('%d/%m/%Y')})"
        send_telegram_document(token, chat_id, excel_path, caption=caption)

    return ok_msg, err_msg

#!/usr/bin/env python3
"""
Script de automação para execução diária / agendada em nuvem ou linha de comando.
Executa todo o ciclo de raspagem, extração com IA, persistência no Banco de Dados (com deduplicação),
exportação para Excel/CSV e envio de alertas no Telegram.

Uso:
    python cron_job.py
    python cron_job.py --date-mode yesterday_today --limit 3
    python cron_job.py --no-telegram
"""

import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

# Adiciona diretório raiz ao path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.config import load_config, OUTPUT_DIR
from core.scraper import scrape_instagram_flyers
from core.vision_ai import process_image_offers
from core.categorizer import categorizar_produto
from core.product_normalizer import normalize_product_name
from core.exporter import export_offers_data
from core.database import save_offers, init_db, get_db_stats
from core.telegram_notifier import send_daily_notification

def log(msg: str):
    """Log formatado para stdout."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)

def run_automation(
    date_mode: str = "yesterday_today",
    custom_start: str = "",
    custom_end: str = "",
    results_limit: int = 3,
    vision_provider_override: str = "",
    skip_telegram: bool = False
) -> bool:
    """Executa o pipeline completo de ponta a ponta."""
    log("=" * 60)
    log("🤖 INICIANDO AUTOMAÇÃO DIÁRIA DE ENCARTES & OFERTAS")
    log("=" * 60)

    # 1. Carrega configurações
    config = load_config()
    init_db()

    apify_token = os.getenv("APIFY_TOKEN") or config.get("apify_token", "").strip()
    if not apify_token:
        log("❌ ERRO: Token do Apify não configurado. Defina APIFY_TOKEN no .env ou nas variáveis de ambiente.")
        return False

    vision_provider = vision_provider_override or config.get("vision_provider", "gemini")
    gemini_key = os.getenv("GEMINI_API_KEY") or config.get("gemini_api_key", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("openai_api_key", "").strip()
    gemini_model = config.get("gemini_model", "gemini-1.5-flash")

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or config.get("telegram_token", "").strip()
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID") or str(config.get("telegram_chat_id", "")).strip()
    telegram_enabled = config.get("telegram_enabled", True) and not skip_telegram
    telegram_send_excel = config.get("telegram_send_excel", True)

    profiles = config.get("profiles", [])
    active_urls = [p["url"] for p in profiles if p.get("enabled", True) and p.get("url")]

    if not active_urls:
        log("❌ ERRO: Nenhum perfil de supermercado ativo encontrado na configuração.")
        return False

    log(f"📋 Perfis ativos: {len(active_urls)}")
    log(f"🧠 Provedor de IA: {vision_provider.upper()} ({gemini_model if vision_provider == 'gemini' else 'OpenAI'})")
    log(f"📅 Modo de data: {date_mode}")
    log(f"📱 Notificação Telegram: {'Ativada' if (telegram_enabled and telegram_token and telegram_chat_id) else 'Desativada/Não Configurada'}")

    # 2. Raspagem no Instagram
    log("\n📥 [FASE 1/4] Raspando encartes no Instagram via Apify...")
    try:
        imagens_coletadas = scrape_instagram_flyers(
            apify_token=apify_token,
            profile_urls=active_urls,
            date_mode=date_mode,
            custom_start=custom_start,
            custom_end=custom_end,
            results_limit=results_limit,
            log_callback=log
        )
    except Exception as e:
        log(f"❌ ERRO na raspagem do Apify: {e}")
        return False

    if not imagens_coletadas:
        log("ℹ️ Nenhuma nova postagem com encarte encontrada para o filtro de data.")
        # Mantém o dashboard e a planilha populados com os dados acumulados no banco
        db_records = get_recent_offers(limit=500)
        if db_records and db_records.get("items"):
            log(f"📊 Sincronizando dashboard com {len(db_records['items'])} ofertas acumuladas no banco de dados...")
            export_offers_data(db_records["items"])
        return True

    # 3. Processamento de Visão com IA
    total_imgs = len(imagens_coletadas)
    log(f"\n🧠 [FASE 2/4] Analisando {total_imgs} imagens de encartes com IA de Visão...")

    dados_extraidos = []
    for i, item_img in enumerate(imagens_coletadas, start=1):
        mercado = item_img["supermercado"]
        log(f"🔍 [{i}/{total_imgs}] Extraindo produtos: {mercado}...")

        try:
            resultado = process_image_offers(
                image_url=item_img["imagem"],
                provider=vision_provider,
                gemini_key=gemini_key,
                openai_key=openai_key,
                model_name=gemini_model
            )

            if resultado and "ofertas" in resultado and isinstance(resultado["ofertas"], list):
                ofertas = resultado["ofertas"]
                log(f"   ✨ {len(ofertas)} ofertas identificadas!")
                for of in ofertas:
                    raw_nome = of.get("item") or of.get("nome")
                    val = of.get("valor")
                    if not raw_nome or val is None:
                        continue
                    
                    nome_prod = normalize_product_name(raw_nome)
                    if not nome_prod:
                        continue

                    try:
                        val_float = float(str(val).replace("R$", "").replace("$", "").replace(",", ".").strip())
                    except Exception:
                        continue

                    cat = categorizar_produto(nome_prod)
                    dados_extraidos.append({
                        "supermercado": mercado,
                        "categoria": cat,
                        "item": nome_prod,
                        "valor": val_float,
                        "data_postagem": item_img["data_formatada"],
                        "link": item_img["imagem"],
                        "post_url": item_img["post_url"]
                    })
            else:
                log("   ℹ️ Nenhuma oferta com preço legível nesta imagem.")
        except Exception as ex:
            log(f"   ⚠️ Erro ao processar IA para {mercado}: {ex}")

        time.sleep(0.5)

    log(f"\n🏷️ Total de itens extraídos: {len(dados_extraidos)}")

    # 4. Banco de Dados e Deduplicação
    log("\n💾 [FASE 3/4] Persistindo no Banco de Dados SQLite e Deduplicando...")
    run_id = datetime.now().strftime("cron_%Y%m%d_%H%M%S")
    total_novas, total_duplicadas, novas_ofertas = save_offers(dados_extraidos, run_id=run_id)

    log(f"   ✨ Novas ofertas inseridas no BD: {total_novas}")
    log(f"   ♻️ Ofertas repetidas/duplicadas ignoradas: {total_duplicadas}")

    # 5. Exportação de Planilhas
    log("\n📊 [FASE 4/4] Gerando planilhas e relatórios...")
    res_export = export_offers_data(dados_extraidos)
    excel_file = res_export.get("excel_file")
    log(f"   📁 Planilha gerada: output/{excel_file}")

    # 6. Notificação Telegram
    if telegram_enabled and telegram_token and telegram_chat_id:
        log("\n📲 Disparando relatório para o canal/grupo do Telegram...")
        excel_path = (OUTPUT_DIR / excel_file) if excel_file else None
        ok_tg, msg_tg = send_daily_notification(
            token=telegram_token,
            chat_id=telegram_chat_id,
            novas_ofertas=novas_ofertas,
            total_scraped=len(dados_extraidos),
            total_duplicadas=total_duplicadas,
            excel_path=excel_path,
            send_excel=telegram_send_excel
        )
        if ok_tg:
            log("   ✅ Mensagem e arquivos enviados com sucesso para o Telegram!")
        else:
            log(f"   ⚠️ Falha no envio para o Telegram: {msg_tg}")

    # Resumo Final
    stats = get_db_stats()
    log("\n" + "=" * 60)
    log("🎉 EXECUÇÃO CONCLUÍDA COM SUCESSO!")
    log(f"📊 Total no BD acumulado: {stats.get('total_offers', 0)} ofertas")
    log(f"✨ Novas hoje: {total_novas} | ♻️ Duplicadas: {total_duplicadas}")
    log("=" * 60)

    return True

def main():
    parser = argparse.ArgumentParser(description="Automação Diária de Coleta de Encartes")
    parser.add_argument("--date-mode", default="yesterday_today", choices=["today", "yesterday_today", "last_3_days", "last_7_days", "custom"], help="Filtro de data")
    parser.add_argument("--start-date", default="", help="Data inicial YYYY-MM-DD (se date-mode=custom)")
    parser.add_argument("--end-date", default="", help="Data final YYYY-MM-DD (se date-mode=custom)")
    parser.add_argument("--limit", type=int, default=3, help="Limite de posts por perfil")
    parser.add_argument("--provider", default="", choices=["", "gemini", "openai"], help="Provedor de IA")
    parser.add_argument("--no-telegram", action="store_true", help="Desativa envio ao Telegram")

    args = parser.parse_args()

    success = run_automation(
        date_mode=args.date_mode,
        custom_start=args.start_date,
        custom_end=args.end_date,
        results_limit=args.limit,
        vision_provider_override=args.provider,
        skip_telegram=args.no_telegram
    )

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
CLI Runner para Raspagem de Encartes e Extração com IA
Permite execução autônoma (headless) localmente, via cron ou no GitHub Actions.
"""

import os
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.config import (
    load_config, save_scraped_images, load_scraped_images,
    BASE_DIR, DATA_DIR, OUTPUT_DIR, DOCS_DIR
)
from core.scraper import scrape_instagram_flyers
from core.vision_ai import process_image_offers
from core.categorizer import categorizar_produto
from core.normalizer import padronizar_produto
from core.db import init_db, save_run_and_offers, sync_database_to_exports
from core.exporter import export_offers_data

def log(msg: str):
    """Exibe mensagem formatada com timestamp no terminal."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)

def parse_args():
    parser = argparse.ArgumentParser(
        description="FlyerScout AI - Executável de linha de comando para raspagem e extração de encartes"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "scrape_only", "vision_only"],
        default=os.getenv("SCRAPER_MODE", "full"),
        help="Modo de execução: 'full' (coleta + IA), 'scrape_only' (apenas coleta), 'vision_only' (apenas IA nas fotos salvas)"
    )
    parser.add_argument(
        "--date-mode",
        choices=["today", "yesterday_today", "last_3_days", "last_7_days", "custom"],
        default=os.getenv("DATE_MODE", "yesterday_today"),
        help="Filtro de data para as publicações do Instagram"
    )
    parser.add_argument(
        "--start-date",
        default=os.getenv("CUSTOM_START_DATE", ""),
        help="Data inicial no formato YYYY-MM-DD (para date-mode custom)"
    )
    parser.add_argument(
        "--end-date",
        default=os.getenv("CUSTOM_END_DATE", ""),
        help="Data final no formato YYYY-MM-DD (para date-mode custom)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=int(os.getenv("RESULTS_LIMIT", "3")),
        help="Limite de posts por perfil do Instagram (padrão: 3)"
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "openai"],
        default=os.getenv("VISION_PROVIDER", "gemini"),
        help="Provedor de IA de visão (gemini ou openai)"
    )
    parser.add_argument(
        "--model",
        default=os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"),
        help="Modelo de IA de visão (ex: gemini-flash-lite-latest, gemini-2.5-flash, gpt-4o-mini)"
    )
    return parser.parse_args()

def run_pipeline(
    mode: str = "full",
    date_mode: str = "yesterday_today",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    results_limit: int = 3,
    vision_provider: str = "gemini",
    model_name: Optional[str] = None
) -> int:
    """Executa o pipeline completo de forma síncrona."""
    log("=================================================================")
    log("🛒 FlyerScout AI • Execução Autônoma do Pipeline de Encartes")
    log("=================================================================")

    # Inicializa banco SQLite
    init_db()

    config = load_config()

    apify_token = os.getenv("APIFY_TOKEN") or config.get("apify_token", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY") or config.get("gemini_api_key", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("openai_api_key", "").strip()

    active_model = model_name or (config.get("gemini_model") if vision_provider == "gemini" else config.get("openai_model", "gpt-4o-mini"))
    if not active_model:
        active_model = "gemini-flash-lite-latest" if vision_provider == "gemini" else "gpt-4o-mini"

    profiles = config.get("profiles", [])
    active_urls = [p["url"] for p in profiles if p.get("enabled", True) and p.get("url")]

    log(f"⚙️ Configurações da Execução:")
    log(f"   • Modo: {mode.upper()}")
    log(f"   • Filtro de Data: {date_mode}")
    log(f"   • Limite de posts/perfil: {results_limit}")
    log(f"   • Motor de IA: {vision_provider.upper()} ({active_model})")
    log(f"   • Perfis Ativos: {len(active_urls)}")
    log(f"   • Token Apify: {'Configurado ✅' if apify_token else 'NÃO CONFIGURADO ❌'}")
    log(f"   • Chave IA ({vision_provider}): {'Configurada ✅' if (gemini_key if vision_provider == 'gemini' else openai_key) else 'NÃO CONFIGURADA ❌'}")
    log("=================================================================")

    imagens_coletadas = []

    # --- ETAPA 1: RASPAGEM DO INSTAGRAM ---
    if mode in ("full", "scrape_only"):
        if not apify_token:
            log("❌ ERRO: Token do Apify (APIFY_TOKEN) não foi informado.")
            return 1
        if not active_urls:
            log("❌ ERRO: Nenhum perfil de supermercado ativo encontrado.")
            return 1

        log("\n📥 [FASE 1/3] Iniciando coleta de encartes via Apify Instagram Scraper...")
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
            log(f"❌ Erro na raspagem do Apify: {e}")
            return 1

        save_scraped_images(imagens_coletadas)
        log(f"💾 Salvas {len(imagens_coletadas)} imagens no cache local.")

        if mode == "scrape_only":
            log(f"✅ Modo 'scrape_only' concluído com sucesso ({len(imagens_coletadas)} imagens salvas)!")
            return 0

    # --- ETAPA 2: CARREGAMENTO DE IMAGENS SALVAS (Para 'vision_only') ---
    elif mode == "vision_only":
        log("\n📂 [FASE 1/3] Carregando imagens de encartes do cache local...")
        imagens_coletadas = load_scraped_images()
        if not imagens_coletadas:
            log("❌ Nenhuma imagem salva encontrada no cache local. Execute primeiro a coleta!")
            return 1
        log(f"📂 {len(imagens_coletadas)} imagens carregadas do disco para processamento.")

    if not imagens_coletadas:
        log("\nℹ️ Nenhuma imagem de encarte encontrada para o período selecionado.")
        log("🔄 Atualizando exportações vazias e encerrando graciosamente...")
        sync_database_to_exports()
        return 0

    # --- ETAPA 3: PROCESSAMENTO COM IA DE VISÃO ---
    total_imgs = len(imagens_coletadas)
    log(f"\n🧠 [FASE 2/3] Iniciando extração com IA ({vision_provider.upper()}) em {total_imgs} encarte(s)...")

    dados_extraidos = []
    for i, item_img in enumerate(imagens_coletadas, start=1):
        mercado = item_img.get("supermercado", "Supermercado")
        log(f"🔍 [{i}/{total_imgs}] Analisando encarte de: {mercado} ...")

        try:
            resultado = process_image_offers(
                image_url=item_img["imagem"],
                provider=vision_provider,
                gemini_key=gemini_key,
                openai_key=openai_key,
                model_name=active_model
            )

            if resultado and "ofertas" in resultado and isinstance(resultado["ofertas"], list):
                ofertas = resultado["ofertas"]
                log(f"   ✨ {len(ofertas)} oferta(s) identificada(s) com sucesso!")

                for of in ofertas:
                    nome_prod = of.get("item") or of.get("nome")
                    val = of.get("valor")
                    if not nome_prod or val is None:
                        continue
                    try:
                        val_float = float(str(val).replace("R$", "").replace("$", "").replace(",", ".").strip())
                    except Exception:
                        continue

                    # Categoria: usa a que a IA identificou ou fallback nas regras especializadas
                    cat_ia = of.get("categoria")
                    if cat_ia and cat_ia.strip() and cat_ia.strip().lower() != "outros":
                        cat = cat_ia.strip()
                    else:
                        cat = categorizar_produto(nome_prod)

                    # Padronização Canônica do Produto
                    sugestao_ia = of.get("produto_padronizado") or nome_prod
                    marca_ia = of.get("marca") or ""
                    prod_canon, marca_canon, emb_canon = padronizar_produto(sugestao_ia, fallback_brand=marca_ia)

                    dados_extraidos.append({
                        "supermercado": mercado,
                        "categoria": cat,
                        "item": nome_prod,
                        "produto_padronizado": prod_canon,
                        "marca": marca_canon,
                        "embalagem": emb_canon,
                        "valor": val_float,
                        "data_postagem": item_img.get("data_formatada", "-"),
                        "link": item_img["imagem"],
                        "post_url": item_img.get("post_url", "")
                    })
            else:
                log(f"   ℹ️ Nenhuma oferta legível identificada nesta imagem.")

        except Exception as ex_ia:
            log(f"   ⚠️ Erro ao processar imagem de {mercado}: {str(ex_ia)[:100]}")

        time.sleep(0.4)

    # --- ETAPA 4: EXPORTAÇÃO, PERSISTÊNCIA EM BD E GITHUB PAGES ---
    log(f"\n📊 [FASE 3/3] Consolidando {len(dados_extraidos)} ofertas e atualizando histórico...")

    res_export = export_offers_data(dados_extraidos)

    try:
        res_db = save_run_and_offers(
            mode=mode,
            provider=vision_provider,
            model=active_model,
            excel_file=res_export.get('excel_file', ''),
            offers_list=dados_extraidos
        )
        log(f"💾 Banco SQLite Atualizado:")
        log(f"   • Novas ofertas inseridas: {res_db['inserted_count']}")
        log(f"   • Ofertas duplicadas ignoradas: {res_db['duplicate_count']}")
        log(f"   • Acervo total no banco: {res_db['total_db_offers']} ofertas ({res_db['total_db_products']} produtos)")
    except Exception as e_db:
        log(f"⚠️ Erro ao gravar no banco SQLite: {e_db}")

    # Sincroniza dados com GitHub Pages
    try:
        sync_payload = sync_database_to_exports()
        log(f"🌐 Sincronização com GitHub Pages (docs/data/latest_results.json): {sync_payload.get('total_itens', 0)} ofertas ativas.")
    except Exception as e_sync:
        log(f"⚠️ Erro na sincronização com GitHub Pages: {e_sync}")

    log("\n=================================================================")
    log("🎉 PIPELINE CONCLUÍDO COM SUCESSO!")
    log(f"📁 Planilha Gerada: output/{res_export.get('excel_file', '')}")
    log(f"🏷️ Total de ofertas catalogadas nesta rodada: {len(dados_extraidos)}")
    log("=================================================================")
    return 0

if __name__ == "__main__":
    args = parse_args()
    status_code = run_pipeline(
        mode=args.mode,
        date_mode=args.date_mode,
        custom_start=args.start_date,
        custom_end=args.end_date,
        results_limit=args.limit,
        vision_provider=args.provider,
        model_name=args.model
    )
    sys.exit(status_code)

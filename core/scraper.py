import time
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Callable, Optional
from apify_client import ApifyClient

def compute_date_filter(
    date_mode: str,
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None
) -> tuple[Optional[date], Optional[date]]:
    """Calcula o intervalo de datas (min_date, max_date) com base no modo selecionado."""
    hoje = date.today()
    
    if date_mode == "today":
        return hoje, hoje
    elif date_mode == "yesterday_today":
        return hoje - timedelta(days=1), hoje
    elif date_mode == "last_3_days":
        return hoje - timedelta(days=2), hoje
    elif date_mode == "last_7_days":
        return hoje - timedelta(days=6), hoje
    elif date_mode == "custom" and custom_start:
        try:
            d_start = datetime.strptime(custom_start, "%Y-%m-%d").date()
            d_end = datetime.strptime(custom_end, "%Y-%m-%d").date() if custom_end else hoje
            return d_start, d_end
        except Exception:
            return hoje - timedelta(days=1), hoje
    else:
        return hoje - timedelta(days=1), hoje

def scrape_instagram_flyers(
    apify_token: str,
    profile_urls: List[str],
    date_mode: str = "yesterday_today",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    results_limit: int = 3,
    log_callback: Optional[Callable[[str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None
) -> List[Dict[str, Any]]:
    """
    Executa o scraper do Apify para perfis do Instagram e filtra posts por data e encartes.
    Retorna uma lista de dicionários com {supermercado, imagem, data, perfil_url, post_url, legenda}.
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    if not apify_token:
        raise ValueError("Token do Apify não fornecido.")
        
    if not profile_urls:
        log("⚠️ Nenhum perfil do Instagram selecionado para raspagem.")
        return []

    client = ApifyClient(apify_token)
    min_date, max_date = compute_date_filter(date_mode, custom_start, custom_end)
    
    date_desc = f"{min_date.strftime('%d/%m/%Y')} até {max_date.strftime('%d/%m/%Y')}"
    log(f"📅 Filtrando publicações entre: {date_desc}")
    log(f"🎯 Total de perfis a processar: {len(profile_urls)}")

    lista_imagens: List[Dict[str, Any]] = []
    total_perfis = len(profile_urls)

    for idx, url_perfil in enumerate(profile_urls, start=1):
        if is_cancelled and is_cancelled():
            log("🛑 Processamento cancelado pelo usuário.")
            break

        url_clean = url_perfil.strip()
        if not url_clean:
            continue

        nome_simplificado = url_clean.rstrip("/").split("/")[-1] or url_clean
        log(f"[{idx}/{total_perfis}] 🔍 Raspando perfil: @{nome_simplificado} ...")

        try:
            # Chama o actor oficial do Apify para Instagram
            run_input = {
                "directUrls": [url_clean],
                "resultsType": "posts",
                "resultsLimit": results_limit
            }
            
            run = client.actor("apify/instagram-scraper").call(run_input=run_input)
            if not run:
                log(f"   ⚠️ Falha na execução do Apify para @{nome_simplificado}.")
                continue

            # Suporte para Run object (apify-client >= 1.8 / 3.x) e dicionário
            dataset_id = None
            if hasattr(run, "default_dataset_id"):
                dataset_id = getattr(run, "default_dataset_id")
            elif isinstance(run, dict):
                dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
            elif hasattr(run, "defaultDatasetId"):
                dataset_id = getattr(run, "defaultDatasetId")

            if not dataset_id:
                log(f"   ⚠️ Dataset não localizado na execução do Apify para @{nome_simplificado}.")
                continue

            dataset_items = list(client.dataset(dataset_id).iterate_items())
            
            log(f"   📥 @{nome_simplificado}: {len(dataset_items)} posts obtidos do Instagram.")

            posts_no_periodo = 0
            for post in dataset_items:
                if is_cancelled and is_cancelled():
                    break

                ts_str = post.get("timestamp")
                if not ts_str:
                    continue

                try:
                    data_postagem = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).date()
                except Exception:
                    continue

                # Checagem de intervalo de datas
                if min_date <= data_postagem <= max_date:
                    posts_no_periodo += 1
                    mercado = post.get("ownerFullName") or post.get("ownerUsername") or nome_simplificado
                    
                    # Coleta URLs únicas da imagem principal e carrossel
                    urls_unicas = set()
                    if post.get("displayUrl"):
                        urls_unicas.add(post.get("displayUrl"))
                    for extra_img in post.get("images", []) or []:
                        if extra_img:
                            urls_unicas.add(extra_img)

                    for url_img in urls_unicas:
                        lista_imagens.append({
                            "supermercado": mercado,
                            "imagem": url_img,
                            "data": ts_str,
                            "data_formatada": data_postagem.strftime("%d/%m/%Y"),
                            "perfil_url": url_clean,
                            "post_url": post.get("url", ""),
                            "caption": post.get("caption", "")
                        })
                else:
                    log(f"   ⏩ Post de {data_postagem.strftime('%d/%m/%Y')} fora do filtro.")

            if posts_no_periodo == 0:
                log(f"   ℹ️ Nenhum post encontrado dentro do período para @{nome_simplificado}.")
            else:
                log(f"   ✅ @{nome_simplificado}: {posts_no_periodo} post(s) no período com imagens extraídas.")

        except Exception as e:
            log(f"   ⚠️ Erro ao raspar @{nome_simplificado}: {str(e)}")

        time.sleep(0.5)

    log(f"🎉 Coleta concluída! Total de {len(lista_imagens)} imagens de encartes prontas para análise visual.")
    return lista_imagens

import threading
import queue
import time
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import asyncio

from core.config import load_config, load_scraped_images, save_scraped_images
from core.scraper import scrape_instagram_flyers
from core.vision_ai import process_image_offers
from core.categorizer import categorizar_produto
from core.normalizer import padronizar_produto
from core.db import save_run_and_offers
from core.exporter import export_offers_data

class TaskManager:
    """Gerenciador singleton de execução em segundo plano com streaming de logs em tempo real."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.is_running = False
        self.should_cancel = False
        self.status = "idle" # idle, running, completed, error, cancelled
        self.progress = 0 # 0 to 100
        self.current_step = "Aguardando início"
        self.step_detail = ""
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None
        self.error_message: Optional[str] = None
        
        # Histórico de logs da sessão atual
        self.logs: List[str] = []
        # Filas de assinantes SSE
        self.subscribers: List[queue.Queue] = []
        
        # Dados gerados
        self.last_result: Optional[Dict[str, Any]] = None
        self._thread: Optional[threading.Thread] = None

    def add_log(self, message: str, level: str = "INFO"):
        """Adiciona log e despacha para todos os clientes conectados ao SSE."""
        now = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{now}] {message}"
        
        with self.lock:
            self.logs.append(log_entry)
            # Mantém no máximo 5000 linhas na memória
            if len(self.logs) > 5000:
                self.logs.pop(0)
                
            # Notifica filas
            dead_subscribers = []
            for q in self.subscribers:
                try:
                    q.put_nowait(log_entry)
                except queue.Full:
                    dead_subscribers.append(q)
            for q in dead_subscribers:
                if q in self.subscribers:
                    self.subscribers.remove(q)

    def subscribe_logs(self) -> queue.Queue:
        """Cria uma nova fila para streaming de logs via SSE."""
        q = queue.Queue(maxsize=500)
        with self.lock:
            # Envia os últimos logs para sincronizar o cliente
            for l in self.logs[-50:]:
                try:
                    q.put_nowait(l)
                except Exception:
                    pass
            self.subscribers.append(q)
        return q

    def unsubscribe_logs(self, q: queue.Queue):
        """Remove a fila de assinante."""
        with self.lock:
            if q in self.subscribers:
                self.subscribers.remove(q)

    def get_status(self) -> Dict[str, Any]:
        """Retorna o estado atual da tarefa."""
        with self.lock:
            return {
                "is_running": self.is_running,
                "status": self.status,
                "progress": self.progress,
                "current_step": self.current_step,
                "step_detail": self.step_detail,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "error_message": self.error_message,
                "last_result": self.last_result
            }

    def cancel_task(self):
        """Sinaliza cancelamento para a execução em andamento."""
        with self.lock:
            if self.is_running:
                self.should_cancel = True
                self.add_log("🛑 Solicitado cancelamento da tarefa...", "WARN")

    def start_task(self, custom_params: Optional[Dict[str, Any]] = None) -> bool:
        """Inicia o pipeline em uma thread separada."""
        with self.lock:
            if self.is_running:
                return False
                
            self.is_running = True
            self.should_cancel = False
            self.status = "running"
            self.progress = 0
            self.current_step = "Iniciando pipeline"
            self.step_detail = "Carregando configurações e perfis..."
            self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.end_time = None
            self.error_message = None
            self.logs.clear()

        self._thread = threading.Thread(target=self._run_pipeline, args=(custom_params,), daemon=True)
        self._thread.start()
        return True

    def _run_pipeline(self, custom_params: Optional[Dict[str, Any]] = None):
        """Execução flexível do processo de scraping e/ou IA."""
        try:
            config = load_config()
            if custom_params:
                config.update(custom_params)

            mode = config.get("mode", "full")  # "full", "scrape_only", "vision_only"
            apify_token = config.get("apify_token", "").strip()
            vision_provider = config.get("vision_provider", "gemini")
            gemini_key = config.get("gemini_api_key", "").strip()
            openai_key = config.get("openai_api_key", "").strip()
            gemini_model = config.get("gemini_model", "gemini-flash-lite-latest")
            date_mode = config.get("date_mode", "yesterday_today")
            custom_start = config.get("custom_start_date")
            custom_end = config.get("custom_end_date")
            results_limit = int(config.get("results_limit", 3))

            profiles = config.get("profiles", [])
            active_urls = [p["url"] for p in profiles if p.get("enabled", True) and p.get("url")]

            active_model_desc = gemini_model if vision_provider == "gemini" else config.get("openai_model", "gpt-4o-mini")

            self.add_log("🚀 ===============================================")
            if mode == "scrape_only":
                self.add_log("📥 MODO: APENAS COLETAR E SALVAR ENCARTES (SCRAPER)")
            elif mode == "vision_only":
                self.add_log("🧠 MODO: EXTRAÇÃO COM IA EM ENCARTES SALVOS")
                self.add_log(f"⚙️ Motor de IA: {vision_provider.upper()} ({active_model_desc})")
            else:
                self.add_log("🚀 MODO: PIPELINE COMPLETO (SCRAPER + IA)")
                self.add_log(f"⚙️ Motor de IA: {vision_provider.upper()} ({active_model_desc})")
            
            if mode in ("full", "scrape_only"):
                self.add_log(f"👥 Perfis ativos selecionados: {len(active_urls)}")
            self.add_log("🚀 ===============================================")

            imagens_coletadas = []

            # --- ETAPA 1: RASPAGEM DO INSTAGRAM (Executa em 'full' ou 'scrape_only') ---
            if mode in ("full", "scrape_only"):
                if not apify_token:
                    raise ValueError("Token do Apify não configurado nas configurações.")
                if not active_urls:
                    raise ValueError("Nenhum perfil de supermercado ativo selecionado.")

                self.current_step = "Fase 1: Raspando Instagram (Apify)"
                self.step_detail = f"Buscando posts em {len(active_urls)} perfis..."
                self.progress = 10 if mode == "scrape_only" else 5

                imagens_coletadas = scrape_instagram_flyers(
                    apify_token=apify_token,
                    profile_urls=active_urls,
                    date_mode=date_mode,
                    custom_start=custom_start,
                    custom_end=custom_end,
                    results_limit=results_limit,
                    log_callback=self.add_log,
                    is_cancelled=lambda: self.should_cancel
                )

                if self.should_cancel:
                    self.status = "cancelled"
                    self.current_step = "Cancelado"
                    self.add_log("🛑 Processo cancelado pelo usuário.")
                    return

                # Salva imagens coletadas no cache local
                save_scraped_images(imagens_coletadas)
                self.add_log(f"💾 Salvas {len(imagens_coletadas)} imagens no repositório local de encartes.")

                if mode == "scrape_only":
                    self.progress = 100
                    self.status = "completed"
                    self.current_step = "Coleta de Encartes Concluída!"
                    self.step_detail = f"{len(imagens_coletadas)} imagens obtidas e salvas com sucesso."
                    self.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.add_log(f"✅ Coleta finalizada com sucesso! Você pode agora visualizá-las na aba 'Encartes Coletados' ou rodar a Extração por IA.")
                    return

            # --- ETAPA 2: CARREGAMENTO DE IMAGENS SALVAS (Para 'vision_only') ---
            elif mode == "vision_only":
                self.current_step = "Carregando encartes salvos"
                self.step_detail = "Lendo imagens previamente coletadas..."
                self.progress = 5
                
                imagens_coletadas = load_scraped_images()
                if not imagens_coletadas:
                    raise ValueError("Nenhuma imagem salva encontrada. Execute primeiro a coleta de encartes!")
                
                self.add_log(f"📂 {len(imagens_coletadas)} imagens salvas carregadas do disco para análise.")

            if not imagens_coletadas:
                self.progress = 100
                self.status = "completed"
                self.current_step = "Concluído sem imagens"
                self.step_detail = "Nenhum encarte novo encontrado no período selecionado."
                self.add_log("ℹ️ Nenhum encarte recente encontrado para processar.")
                self.last_result = export_offers_data([])
                return

            # --- ETAPA 3: PROCESSAMENTO IA VISÃO & CATEGORIZAÇÃO ---
            total_imgs = len(imagens_coletadas)
            self.current_step = "Fase 2: Análise Visual com Inteligência Artificial"
            self.step_detail = f"Processando 0 de {total_imgs} imagens..."
            self.progress = 30 if mode == "vision_only" else 40

            self.add_log(f"\n🧠 Iniciando extração visual de {total_imgs} imagens com o modelo {active_model_desc}...")

            dados_extraidos = []
            for i, item_img in enumerate(imagens_coletadas, start=1):
                if self.should_cancel:
                    break

                base_p = 30 if mode == "vision_only" else 40
                span_p = 60 if mode == "vision_only" else 50
                self.progress = base_p + int((i / total_imgs) * span_p)
                
                mercado = item_img.get("supermercado", "Supermercado")
                self.step_detail = f"Analisando encarte [{i}/{total_imgs}]: {mercado}"
                self.add_log(f"🔍 [{i}/{total_imgs}] Analisando encarte de: {mercado}...")

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
                        self.add_log(f"   ✨ {len(ofertas)} ofertas identificadas com sucesso!")
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

                            # Padronização Canônica do Produto para Comparação de Preços
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
                        self.add_log(f"   ℹ️ Nenhuma oferta com preço legível nesta imagem.")
                except Exception as ex_ia:
                    self.add_log(f"   ⚠️ Erro ao processar imagem de {mercado}: {str(ex_ia)[:80]}")

                time.sleep(0.3)

            if self.should_cancel:
                self.status = "cancelled"
                self.current_step = "Cancelado"
                self.add_log("🛑 Processamento cancelado.")
                return

            # --- ETAPA 4: EXPORTAÇÃO, PERSISTÊNCIA EM BD E CONSOLIDAÇÃO ---
            self.current_step = "Fase 3: Formatando e Gerando Planilhas"
            self.step_detail = f"Estruturando {len(dados_extraidos)} ofertas extraídas..."
            self.progress = 95
            self.add_log(f"\n📊 Consolidando {len(dados_extraidos)} ofertas e gerando planilhas...")

            res_export = export_offers_data(dados_extraidos)
            self.last_result = res_export

            # Salva no Banco de Dados SQLite Histórico
            try:
                run_id = save_run_and_offers(
                    mode=mode,
                    provider=vision_provider,
                    model=active_model_desc,
                    excel_file=res_export.get('excel_file', ''),
                    offers_list=dados_extraidos
                )
                self.add_log(f"💾 {len(dados_extraidos)} ofertas salvas com sucesso no banco de dados SQLite (Lote #{run_id}).")
            except Exception as e_db:
                self.add_log(f"⚠️ Aviso: Não foi possível gravar no banco SQLite: {e_db}")

            self.progress = 100
            self.status = "completed"
            self.current_step = "Concluído com Sucesso!"
            self.step_detail = f"{len(dados_extraidos)} produtos catalogados e padronizados."
            self.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self.add_log("🎉 ===============================================")
            self.add_log(f"✅ SUCESSO! Extração concluída!")
            self.add_log(f"📁 Planilha Excel gerada: {res_export.get('excel_file')}")
            self.add_log(f"🏷️ Total de produtos encontrados: {len(dados_extraidos)}")
            self.add_log("🎉 ===============================================")

        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            self.current_step = "Erro na Execução"
            self.step_detail = str(e)
            self.add_log(f"❌ ERRO CRÍTICO NO PIPELINE: {str(e)}", "ERROR")
        finally:
            with self.lock:
                self.is_running = False

# Instância única global
task_manager = TaskManager()

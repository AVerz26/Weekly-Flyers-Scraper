import threading
import queue
import time
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import asyncio

from core.config import load_config, OUTPUT_DIR
from core.scraper import scrape_instagram_flyers
from core.vision_ai import process_image_offers
from core.categorizer import categorizar_produto
from core.exporter import export_offers_data
from core.database import save_offers
from core.telegram_notifier import send_daily_notification

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
        """Execução completa do processo de scraping e IA."""
        try:
            config = load_config()
            if custom_params:
                config.update(custom_params)

            apify_token = config.get("apify_token", "").strip()
            if not apify_token:
                raise ValueError("Token do Apify não configurado. Por favor, adicione seu token nas configurações.")

            vision_provider = config.get("vision_provider", "gemini")
            gemini_key = config.get("gemini_api_key", "").strip()
            openai_key = config.get("openai_api_key", "").strip()
            gemini_model = config.get("gemini_model", "gemini-1.5-flash")
            date_mode = config.get("date_mode", "yesterday_today")
            custom_start = config.get("custom_start_date")
            custom_end = config.get("custom_end_date")
            results_limit = int(config.get("results_limit", 3))

            profiles = config.get("profiles", [])
            active_urls = [p["url"] for p in profiles if p.get("enabled", True) and p.get("url")]

            if not active_urls:
                raise ValueError("Nenhum perfil de supermercado ativo selecionado.")

            self.add_log("🚀 ===============================================")
            self.add_log("🚀 INICIANDO SCRAPER E EXTRAÇÃO DE ENCARTES")
            self.add_log(f"⚙️ Motor de IA: {vision_provider.upper()} ({gemini_model if vision_provider=='gemini' else 'gpt-4o'})")
            self.add_log(f"👥 Perfis ativos selecionados: {len(active_urls)}")
            self.add_log("🚀 ===============================================")

            # --- FASE 1: RASPAGEM DE POSTS (0% a 40%) ---
            self.current_step = "Fase 1: Raspando Instagram (Apify)"
            self.step_detail = f"Buscando posts em {len(active_urls)} perfis..."
            self.progress = 5

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

            if not imagens_coletadas:
                self.progress = 100
                self.status = "completed"
                self.current_step = "Concluído sem imagens"
                self.step_detail = "Nenhum encarte novo encontrado no período selecionado."
                self.add_log("ℹ️ Nenhum post/encarte recente encontrado para as datas selecionadas.")
                self.last_result = export_offers_data([])
                return

            # --- FASE 2: PROCESSAMENTO IA VISÃO (40% a 90%) ---
            total_imgs = len(imagens_coletadas)
            self.current_step = "Fase 2: Análise Visual com Inteligência Artificial"
            self.step_detail = f"Processando 0 de {total_imgs} imagens..."
            self.progress = 40

            self.add_log(f"\n🧠 Iniciando extração visual de {total_imgs} imagens de encartes com IA...")

            dados_extraidos = []
            for i, item_img in enumerate(imagens_coletadas, start=1):
                if self.should_cancel:
                    break

                progresso_ia = 40 + int((i / total_imgs) * 50)
                self.progress = progresso_ia
                mercado = item_img["supermercado"]
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

                            # Categorização automática
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
                        self.add_log(f"   ℹ️ Nenhuma oferta com preço legível nesta imagem.")
                except Exception as ex_ia:
                    self.add_log(f"   ⚠️ Erro ao processar imagem de {mercado}: {str(ex_ia)[:80]}")

                time.sleep(0.5)

            if self.should_cancel:
                self.status = "cancelled"
                self.current_step = "Cancelado"
                self.add_log("🛑 Processamento cancelado.")
                return

            # --- FASE 3: BANCO DE DADOS & DEDUPLICAÇÃO (88% a 93%) ---
            self.current_step = "Fase 3: Salvando no Banco de Dados"
            self.step_detail = f"Deduplicando e persistindo {len(dados_extraidos)} ofertas..."
            self.progress = 90
            self.add_log(f"\n💾 Verificando ofertas existentes e salvando no banco de dados SQLite...")

            run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
            total_novas, total_duplicadas, novas_ofertas = save_offers(dados_extraidos, run_id=run_id)

            self.add_log(f"   ✨ Novas ofertas inseridas no banco: {total_novas}")
            self.add_log(f"   ♻️ Ofertas repetidas/duplicadas ignoradas: {total_duplicadas}")

            # --- FASE 4: EXPORTAÇÃO E CONSOLIDAÇÃO (93% a 97%) ---
            self.current_step = "Fase 4: Formatando e Gerando Planilhas"
            self.step_detail = f"Estruturando {len(dados_extraidos)} ofertas extraídas..."
            self.progress = 94
            self.add_log(f"\n📊 Consolidando {len(dados_extraidos)} ofertas e gerando arquivos de saída...")

            res_export = export_offers_data(dados_extraidos)
            res_export["total_novas"] = total_novas
            res_export["total_duplicadas"] = total_duplicadas
            self.last_result = res_export

            # --- FASE 5: NOTIFICAÇÃO TELEGRAM (97% a 100%) ---
            telegram_token = config.get("telegram_token", "").strip()
            telegram_chat_id = str(config.get("telegram_chat_id", "")).strip()
            telegram_enabled = config.get("telegram_enabled", True)
            telegram_send_excel = config.get("telegram_send_excel", True)

            if telegram_enabled and telegram_token and telegram_chat_id:
                self.current_step = "Fase 5: Enviando Notificação Telegram"
                self.step_detail = "Disparando relatório para o Telegram..."
                self.progress = 97
                self.add_log(f"\n📲 Enviando relatório de ofertas para o Telegram (Chat: {telegram_chat_id})...")

                excel_path = (OUTPUT_DIR / res_export["excel_file"]) if res_export.get("excel_file") else None
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
                    self.add_log("   ✅ Relatório enviado com sucesso ao Telegram!")
                else:
                    self.add_log(f"   ⚠️ Aviso ao enviar para Telegram: {msg_tg}", "WARN")

            self.progress = 100
            self.status = "completed"
            self.current_step = "Concluído com Sucesso!"
            self.step_detail = f"{len(dados_extraidos)} produtos ({total_novas} novos) extraídos de {len(active_urls)} supermercados."
            self.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self.add_log("🎉 ===============================================")
            self.add_log(f"✅ SUCESSO! Extração concluída!")
            self.add_log(f"📁 Planilha Excel gerada: {res_export.get('excel_file')}")
            self.add_log(f"🏷️ Total de produtos encontrados: {len(dados_extraidos)}")
            self.add_log(f"✨ Novas ofertas adicionadas ao BD: {total_novas}")
            self.add_log(f"♻️ Duplicadas evitadas: {total_duplicadas}")
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

import asyncio
import os
import uuid
import html
import logging
from typing import Dict, List
from datetime import datetime, timedelta

from .scheduler import SchedulingManager
from .history import HistoryManager
from .task_queue import AsyncTaskQueue

class AutoTubePipeline:
    def __init__(self, real_api, ai_generator, youtube_manager, telegram_bot, download_dir="downloads"):
        self.real_api = real_api
        self.ai_generator = ai_generator
        self.youtube_manager = youtube_manager
        self.telegram_bot = telegram_bot
        self.download_dir = download_dir
        self.scheduler = SchedulingManager()
        self.history = HistoryManager()
        self.is_scheduling = False
        self.task_queue = AsyncTaskQueue(num_workers=3)
        self.logger = logging.getLogger("AutoTubePipeline")

        self.telegram_bot.on_skip_short = self._handle_skip_command
        self.telegram_bot.on_get_status = self._get_status_report
        self.telegram_bot.on_start_scheduling = self.start_scheduling_flow
        self.telegram_bot.on_resume_scheduling = self.resume_scheduling
        self.telegram_bot.on_cancel_scheduling = self.cancel_current_scheduling

        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

        self.current_skip_id = None
        self.stats = {"total_processed": 0, "total_errors": 0, "last_video_url": None}

    def _handle_skip_command(self, short_id: str):
        self.current_skip_id = short_id
        self.logger.info(f"Comando recebido: pular clipe {short_id}")

    def _get_status_report(self) -> str:
        report = "📊 <b>Status do Sistema</b>\n\n"
        report += f"✅ Processados (Sessão): {self.stats['total_processed']}\n"
        report += f"❌ Erros (Sessão): {self.stats['total_errors']}\n"
        
        pending_queue = self.task_queue.queue.qsize()
        report += f"⚙️ Vídeos na Fila de Processamento: {pending_queue}\n"

        if self.is_scheduling:
            report += "\n📅 <b>Modo de Agendamento em Lote:</b> ATIVO\n"
            report += self.scheduler.get_scheduling_summary()
        else:
            report += "\n🤖 <b>Modo de Agendamento em Lote:</b> INATIVO\n"

        if self.stats["last_video_url"]:
            report += f"\n📺 <b>Último vídeo:</b> {self.stats['last_video_url']}"
            
        return report

    async def start_scheduling_flow(self, config: Dict):
        """Inicia o fluxo recebendo as opções do bot."""
        session_id = str(uuid.uuid4())
        days = config['days']
        posts_per_day = config['posts_per_day']
        start_hour = config.get('start_hour') or 0
        interval_hours = config.get('interval_hours') or 0
        custom_hours = config.get('custom_hours')
        use_template = config.get('use_template', False)
        selected_projects = config['projects']
        start_date_offset = config.get('start_date_offset', 0)
        
        # Valida canal — obrigatório
        channel_name = config.get('channel_name')
        if not channel_name:
            await self.telegram_bot.send_notification("❌ Agendamento abortado: canal não selecionado.")
            return
        if channel_name not in self.youtube_manager.list_channels():
            await self.telegram_bot.send_notification(f"❌ Agendamento abortado: canal <b>{channel_name}</b> não existe nas credenciais.")
            return
        profile_name = config.get('profile_name', 'viral')
        config['profile_name'] = profile_name

        self.task_queue.clear()
        
        slots = self.scheduler.generate_slots(days, posts_per_day, start_hour, interval_hours, custom_hours, use_template, start_date_offset)
        self.scheduler.save_state(session_id, config, slots)

        await self.telegram_bot.send_notification(
            f"📅 <b>Agendamento Configurado!</b>\n"
            f"Sessão: <code>{session_id[:8]}</code>\n"
            f"Projetos: {len(selected_projects)}\n"
            f"Total de Slots: {len(slots)}\n\n"
            f"O Maestro já está separando os conteúdos e injetando na fila de background.\n\nVocê será avisado à medida que as postagens concluírem."
        )

        self.is_scheduling = True
        await self._dispatch_scheduling_slots(slots, selected_projects, session_id)
        self.is_scheduling = False

    async def cancel_current_scheduling(self):
        if not self.is_scheduling and not self.scheduler.state:
            await self.telegram_bot.send_notification("ℹ️ Não há agendamentos ativos na memória.")
            return

        self.is_scheduling = False
        self.task_queue.clear()
        self.scheduler.clear_state()
        await self.telegram_bot.send_notification("🛑 **Operação Cancelada!**\nA fila atual foi abortada instantaneamente e a memória foi limpa.")

    async def resume_scheduling(self):
        slots = self.scheduler.get_pending_slots()
        if not slots:
            await self.telegram_bot.send_notification("ℹ️ Não há agendamentos pendentes para retomar.")
            return

        config = self.scheduler.state["config"]
        session_id = self.scheduler.state.get("session_id")
        selected_projects = config['projects']
        self.is_scheduling = True
        
        await self.telegram_bot.send_notification(f"🔄 **Retomando Injeção de Agendamentos...**\n" + self.scheduler.get_scheduling_summary())
        await self._dispatch_scheduling_slots(slots, selected_projects, session_id)
        self.is_scheduling = False

    async def _dispatch_scheduling_slots(self, slots: List[Dict], selected_projects: List[str], session_id: str):
        """Despacha os slots para a TaskQueue. Não processa sincronamente."""
        project_index = 0
        project_shorts_cache = {}
        slots_filled = 0
        slots_skipped = 0
        
        config = self.scheduler.state.get("config", {})
        channel_name = config.get('channel_name')
        # ... validation code ...
        if not channel_name:
            await self.telegram_bot.send_notification("❌ Despacho abortado: canal não definido na configuração salva.")
            return
        if channel_name not in self.youtube_manager.list_channels():
            await self.telegram_bot.send_notification(f"❌ Despacho abortado: canal <b>{channel_name}</b> não encontrado nas credenciais.")
            return

        profile_name = config.get('profile_name', 'viral')

        for slot in slots:
            if not self.is_scheduling:
                break

            slot_idx = slot['index']
            if slot['status'] == 'agendado_api':
                continue

            attempts = 0
            short_to_process = None
            assigned_project_id = None

            while attempts < len(selected_projects):
                project_id = selected_projects[project_index]
                if project_id not in project_shorts_cache:
                    project_shorts_cache[project_id] = await asyncio.to_thread(self.real_api.get_shorts, project_id)
                
                shorts = project_shorts_cache[project_id]
                for s in shorts:
                    if not self.history.is_processed(s.get("id")):
                        is_already_slotted = any(sl.get('short_id') == s.get('id') for sl in self.scheduler.state.get('slots', []))
                        if not is_already_slotted:
                            short_to_process = s
                            assigned_project_id = project_id
                            break
                
                project_index = (project_index + 1) % len(selected_projects)
                if short_to_process:
                    break
                attempts += 1

            if not short_to_process:
                self.scheduler.log_error(slot_idx, slot['scheduled_time'], "N/A", "despacho", f"Nenhum clipe disponível no projeto {selected_projects[project_index-1]}")
                self.scheduler.update_slot(slot_idx, {"status": "pendente_log"})
                slots_skipped += 1
                continue

            slots_filled += 1
            # Persistência atômica: Marca no histórico e no slot IMEDIATAMENTE para evitar duplicados em caso de reinício
            self.history.mark_as_processed(short_to_process['id'])
            self.scheduler.update_slot(slot_idx, {
                "short_id": short_to_process['id'],
                "status": "enfileirado",
                "project_id": assigned_project_id
            })
            
            # Enfileirar a tarefa pesada para background passando a session_id
            await self.task_queue.enqueue(
                self.process_single_video, 
                short_data=short_to_process, 
                project_id=assigned_project_id, 
                channel_name=channel_name, 
                profile=profile_name, 
                slot_idx=slot_idx,
                session_id=session_id
            )
            
        msg = f"🚀 **Despacho Automático Concluído!**\n✅ {slots_filled} vídeos na fila."
        if slots_skipped > 0:
            msg += f"\n⚠️ {slots_skipped} slots ficaram vagos por falta de conteúdo novo nos projetos."
        
        await self.telegram_bot.send_notification(msg)

    async def process_project(self, project_id: str, channel_name: str = "default", profile: str = "viral", short_id: str = "all"):
        """Despacha todos os shorts (ou um específico) de um projeto manualmente aprovado."""
        self.logger.info(f"Iniciando despacho manual do projeto {project_id}")
        shorts = await asyncio.to_thread(self.real_api.get_shorts, project_id)
        
        if not shorts:
            await self.telegram_bot.send_notification(f"ℹ️ Nenhum corte encontrado para o projeto <code>{project_id}</code>.")
            return

        if short_id != "all":
            to_process = [s for s in shorts if s.get("id") == short_id]
            if not to_process:
                await self.telegram_bot.send_notification(f"❌ O corte solicitado ({short_id}) não foi localizado.")
                return
        else:
            to_process = [s for s in shorts if not self.history.is_processed(s.get("id"))]
            
        if not to_process:
            await self.telegram_bot.send_notification(f"ℹ️ Nenhum corte disponível do projeto <code>{project_id}</code> (já postados).")
            return

        if short_id == "all":
            await self.telegram_bot.send_notification(f"⏳ Despachando {len(to_process)} novos cortes para a Fila em Background (Canal: {channel_name}).")
        else:
            await self.telegram_bot.send_notification(f"🎯 Vídeo Específico ({short_id}) adicionado à Fila de Processamento (Canal: {channel_name}).")
        
        for short in to_process:
            self.history.mark_as_processed(short['id']) # Evitar concorrência duplicada antes mesmo de processar
            await self.task_queue.enqueue(
                self.process_single_video, 
                short_data=short, 
                project_id=project_id, 
                channel_name=channel_name, 
                profile=profile
            )
            self.logger.info(f"Tarefa de vídeo {'único' if short_id != 'all' else 'em lote'} ({short['id']}) foi postada na TaskQueue.")

    async def process_single_video(self, short_data: dict, project_id: str, channel_name: str, profile: str, slot_idx: int = None, session_id: str = None):
        """O Core Master de renderização, metadados e upload. Executado concorrentemente por um Worker na Queue."""
        short_id = short_data['id']
        is_scheduled = slot_idx is not None
        
        # Validação de Sessão: Se for agendado, garante que a sessão ainda é a ativa
        if is_scheduled and session_id:
            current_session = self.scheduler.state.get("session_id")
            if session_id != current_session:
                self.logger.warning(f"Tarefa descartada: SessionID {session_id[:8]} obsoleta. Sessão atual: {current_session[:8] if current_session else 'Nenhuma'}")
                return
        
        self.logger.info(f"[process_single_video] Canal: '{channel_name}' | Short: {short_id} | Agendado: {is_scheduled}")
        uploader = self.youtube_manager.get_channel(channel_name)
        if not uploader:
            err_msg = f"❌ Upload cancelado. Canal '{channel_name}' não encontrado nas credenciais. O vídeo NÃO será postado em outro canal."
            self.logger.error(err_msg)
            await self.telegram_bot.send_notification(err_msg)
            return

        video_path = None

        try:
            # 1. Renderização
            render_id = None
            for retry in range(3):
                render_id = await asyncio.to_thread(self.real_api.render_short, project_id, short_id)
                if render_id: break
                await asyncio.sleep(2)
            
            if not render_id:
                raise Exception("Falha ao iniciar renderização na API Real")

            video_url = None
            for _ in range(60): # Até 10 minutos
                if self.current_skip_id == short_id:
                    self.current_skip_id = None
                    raise Exception("Skipped pelo Usuário")

                status_data = await asyncio.to_thread(self.real_api.get_render_status, render_id)
                if status_data.get("status") == "done":
                    video_url = status_data.get("download_url")
                    break
                await asyncio.sleep(10)

            if not video_url:
                raise Exception("Timeout na renderização")

            # 2. Download
            postfix = f"sch_{slot_idx}" if is_scheduled else "man"
            video_filename = f"{short_id}_{postfix}.mp4"
            video_path = os.path.join(self.download_dir, video_filename)
            
            success_down = await asyncio.to_thread(self.real_api.download_video, video_url, video_path)
            if not success_down:
                # Se não baixou, falha permanente
                raise Exception("Falha 404/Network no download (Link inválido)")

            # Atualiza o slot se for batch
            if is_scheduled:
                self.scheduler.update_slot(slot_idx, {
                    "status": "processado", 
                    "project_id": project_id,
                    "short_id": short_id,
                    "video_path": video_path,
                })

            # 3. Metadados (IA)
            context_string = f"Projeto: {project_id}. Título: {short_data.get('title')}. Descrição: {short_data.get('description', '')}"
            meta = await asyncio.to_thread(self.ai_generator.generate_shorts_metadata, context_string, profile)

            # 4. Upload Youtube
            if is_scheduled:
                publish_time = self.scheduler.state['slots'][slot_idx]['scheduled_time']
                
                # Checa The past date bounds
                scheduled_dt = datetime.fromisoformat(publish_time)
                # Ambos devem ser aware (com timezone) para comparação
                if scheduled_dt < datetime.now().astimezone() + timedelta(minutes=60):
                    scheduled_dt = datetime.now().astimezone() + timedelta(minutes=65)
                    publish_time = scheduled_dt.isoformat()
                    # Persiste o novo horário corrigido no JSON para não ficar "zumbi"
                    self.scheduler.update_slot(slot_idx, {"scheduled_time": publish_time})
                
                video_id = await asyncio.to_thread(
                    uploader.upload_short,
                    video_path, meta['title'], meta['description'], meta['hashtags'].replace("#", "").split(), "22", publish_time, "private"
                )
            else:
                video_id = await asyncio.to_thread(
                    uploader.upload_short,
                    video_path, meta['title'], meta['description'], meta['hashtags'].replace("#", "").split(), "22", None, "public"
                )

            if not video_id:
                raise Exception("Upload final retornou nulo sem estourar limites.")

            # 5. Fechamento de Sucesso
            self.history.mark_as_processed(short_id)
            self.stats["total_processed"] += 1
            self.stats["last_video_url"] = f"https://youtu.be/{video_id}"

            if is_scheduled:
                self.scheduler.update_slot(slot_idx, {"status": "agendado_api", "video_id": video_id})
                f_date = datetime.fromisoformat(publish_time).strftime("%d/%m/%Y %H:%M")
                title_esc = html.escape(meta.get('title', 'Sem título'))
                await self.telegram_bot.send_notification(
                    f"✅ <b>[{channel_name}]</b> Vídeo Agendado!\n\n"
                    f"📌 <b>Titulo:</b> <code>{title_esc}</code>\n"
                    f"⏳ <b>Aparece em:</b> <code>{f_date}</code>\n"
                    f"🔗 https://youtu.be/{video_id}"
                )
            else:
                title_esc = html.escape(meta.get('title', 'Sem título'))
                await self.telegram_bot.send_notification(
                    f"🎉 <b>[{channel_name}]</b> Vídeo Publicado Imediatamente!\n"
                    f"📌 <b>Titulo:</b> <code>{title_esc}</code>\n"
                    f"🔗 https://youtu.be/{video_id}"
                )

        except Exception as e:
            self.stats["total_errors"] += 1
            if is_scheduled:
                try:
                    sch_time = self.scheduler.state['slots'][slot_idx]['scheduled_time']
                    self.scheduler.log_error(slot_idx, sch_time, project_id, "background_queue", str(e))
                except: pass
                
                if "YouTubeQuotaError" in str(e):
                    await self.telegram_bot.send_notification("🚨 Limite Diário (Cota) do YouTube atingido! A fila reagendou os pendentes.")
                    self.scheduler.reschedule_pending_slots()
            else:
                self.logger.error(f"Erro em publicação manual ({short_id}): {e}")
                await self.telegram_bot.send_notification(f"❌ Erro na submissão de {short_id} para {channel_name}:\n{e}")
        finally:
            # 6. GC: Limpeza do Disco Seguro
            if video_path and os.path.exists(video_path):
                import gc, time as _time
                gc.collect()  # Libera handles do MediaFileUpload do Google
                for _attempt in range(3):
                    try:
                        os.remove(video_path)
                        self.logger.info(f"🗑️ CleanUp: deletado {video_path}")
                        break
                    except Exception as ex:
                        if _attempt < 2:
                            _time.sleep(1)
                        else:
                            self.logger.warning(f"Não foi possível remover cache de MP4: {ex}")

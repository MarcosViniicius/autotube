import asyncio
import logging
import time
import schedule
import sys
from threading import Thread

# Força o console do Windows a aceitar emojis (UTF-8) para evitar crash de UnicodeEncodeError no logging
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from config.settings import Settings
from real_api.client import RealOficialAPI
from ai.generator import ContentGenerator
from youtube.manager import YouTubeChannelManager
from telegram_bot.bot import AutoTubeBot
from core.pipeline import AutoTubePipeline

# Configuração de Logging
logging.basicConfig(
    level=Settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/autotube.log", encoding='utf-8')
    ]
)

class AutoTubeSystem:
    def __init__(self):
        self.settings = Settings()
        self.real_api = RealOficialAPI(
            email=self.settings.REAL_API_EMAIL,
            password=self.settings.REAL_API_PASSWORD,
            token=self.settings.REAL_API_TOKEN,
            base_url=self.settings.REAL_API_BASE_URL
        )
        self.ai_generator = ContentGenerator(self.settings.OPENROUTER_API_KEY, self.settings.OPENROUTER_MODEL)
        self.youtube_manager = YouTubeChannelManager("channels")
        self.bot = AutoTubeBot(
            token=self.settings.TELEGRAM_BOT_TOKEN,
            chat_id=self.settings.TELEGRAM_CHAT_ID,
            on_list_projects=self.real_api.get_projects,
            on_approve_project=self.approve_project,
            on_toggle_auto=self.toggle_auto,
            on_startup=self.on_bot_startup,
            on_list_channels=self.youtube_manager.list_channels,
            on_list_project_shorts=self.real_api.get_shorts,
            on_get_schedule_state=lambda: getattr(self, 'pipeline').scheduler.state if hasattr(self, 'pipeline') else {}
        )
        self.pipeline = AutoTubePipeline(
            self.real_api, 
            self.ai_generator, 
            self.youtube_manager, 
            self.bot, 
            self.settings.DOWNLOAD_PATH
        )
        self.auto_mode = self.settings.MODO_DEFAULT == "auto"
        self.bot_loop = None
        self.logger = logging.getLogger("AutoTubeSystem")

    async def on_bot_startup(self):
        """Callback executado quando o bot inicializa. Verifica agendamentos pendentes."""
        self.bot_loop = asyncio.get_running_loop()
        await self.pipeline.task_queue.start()
        
        pending = self.pipeline.scheduler.get_pending_slots()
        if pending:
            # Ativa modo de agendamento e reinjeta na fila em background
            asyncio.create_task(self.pipeline.resume_scheduling())
            
            await self.bot.send_notification(
                "♻️ **Sistema AutoTube Reiniciado: Retomada Automática** ♻️\n\n"
                f"Identificamos **{len(pending)}** agendamentos pendentes da sessão anterior.\n"
                "Eles foram reinjetados na fila de processamento automaticamente.\n\n"
                "Para consultar o progresso, digite /status."
            )
        else:
            await self.bot.send_notification("✅ **AutoTube Online**\nSistema reiniciado e pronto para uso.")

    async def approve_project(self, project_id: str, channel_name: str, profile: str, short_id: str = "all"):
        """Callback do Bot para aprovação manual com seleção de canal, IA e short específico."""
        self.logger.info(f"Projeto {project_id} aprovado. Canal: {channel_name}. Perfil IA: {profile}. Short: {short_id}")
        try:
            await self.pipeline.process_project(project_id, channel_name, profile, short_id)
        except Exception as e:
            self.logger.error(f"Erro ao agendar processamento manual: {e}")

    def toggle_auto(self, status: bool):
        """Ativa/Desativa o modo automático."""
        self.auto_mode = status
        self.logger.info(f"Modo Automático: {'Ativado' if status else 'Desativado'}")

    def run_auto_job(self):
        """Tarefa periódica para buscar novos projetos no modo automático."""
        if not self.auto_mode:
            return

        self.logger.info("🤖 Modo Automático: Iniciando busca por novos cortes em todos os projetos...")
        try:
            projects = self.real_api.get_projects()
            if not projects:
                return

            for project in projects:
                p_id = project.get("id")
                p_name = project.get("name") or project.get("title")
                
                # O pipeline já tem lógica interna para pular vídeos já processados
                channels = self.youtube_manager.list_channels()
                if not channels:
                    self.logger.warning("AutoMode pulado: Nenhum canal cadastrado.")
                    break
                
                target_channel = channels[0] # Posta no primeiro canal da lista
                
                self.logger.info(f"AutoMode despachando {p_name} ({p_id}) para {target_channel}")
                
                if self.bot_loop:
                    asyncio.run_coroutine_threadsafe(
                        self.pipeline.process_project(p_id, target_channel, "viral"), 
                        self.bot_loop
                    )
                else:
                    self.logger.error("AutoMode falhou: bot_loop não iniciado.")
                    
        except Exception as e:
            self.logger.error(f"Erro no job automático: {e}")

    def check_pending_resume(self):
        """Verifica periodicamente se há slots reagendados (ex: por falha de limite) que já podem ser retomados."""
        if not self.bot_loop:
            return
            
        pending = self.pipeline.scheduler.get_pending_slots()
        if not pending or self.pipeline.is_scheduling or not self.pipeline.task_queue.queue.empty():
            return
            
        from datetime import datetime
        now = datetime.now().astimezone()
        
        # Se pelo menos 1 slot já estiver na hora de processar (agendado pro passado ou exato momento)
        should_resume = any(datetime.fromisoformat(p['scheduled_time']) <= now for p in pending)
        if should_resume:
            self.logger.info("⏳ Slot atingiu horário de retomada automática. Reativando fila em background.")
            asyncio.run_coroutine_threadsafe(self.pipeline.resume_scheduling(), self.bot_loop)

    def start_scheduler(self):
        """Inicia o agendador de tarefas."""
        schedule.every(self.settings.CRON_INTERVAL).minutes.do(self.run_auto_job)
        schedule.every(15).minutes.do(self.check_pending_resume)
        
        while True:
            schedule.run_pending()
            time.sleep(1)

    def start(self):
        self.logger.info("Iniciando Sistema AutoTube...")
        
        # Inicia o agendador em uma thread separada
        scheduler_thread = Thread(target=self.start_scheduler, daemon=True)
        scheduler_thread.start()

        # Inicia o bot do Telegram
        self.bot.run()

if __name__ == "__main__":
    system = AutoTubeSystem()
    system.start()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import logging
import html
import asyncio
from typing import Callable, List, Dict
from datetime import datetime, timedelta

class AutoTubeBot:
    def __init__(self, token: str, chat_id: str, 
                 on_list_projects: Callable = None, 
                 on_approve_project: Callable = None, 
                 on_toggle_auto: Callable = None,
                 on_get_status: Callable = None,
                 on_start_scheduling: Callable = None,
                 on_resume_scheduling: Callable = None,
                 on_cancel_scheduling: Callable = None,
                 on_startup: Callable = None,
                 on_list_channels: Callable = None,
                 on_list_project_shorts: Callable = None,
                 on_skip_short: Callable = None):
        
        self.token = token
        self.chat_id = chat_id
        self.on_list_projects = on_list_projects
        self.on_approve_project = on_approve_project
        self.on_toggle_auto = on_toggle_auto
        self.on_skip_short = on_skip_short
        self.on_get_status = on_get_status
        self.on_start_scheduling = on_start_scheduling
        self.on_resume_scheduling = on_resume_scheduling
        self.on_cancel_scheduling = on_cancel_scheduling
        self.on_startup = on_startup
        self.on_list_channels = on_list_channels or (lambda: ["default"])
        self.on_list_project_shorts = on_list_project_shorts
        
        self.logger = logging.getLogger("AutoTubeBot")
        self.user_data = {}
        
        self.app = ApplicationBuilder().token(self.token).post_init(self._post_init).build()
        self._setup_handlers()

    async def _post_init(self, application):
        if self.on_startup:
            await self.on_startup()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self._start))
        self.app.add_handler(CommandHandler("ajuda", self._start))
        self.app.add_handler(CommandHandler("menu", self._start))
        self.app.add_handler(CommandHandler("listar", self._list_projects_cmd))
        self.app.add_handler(CommandHandler("auto_on", self._auto_on))
        self.app.add_handler(CommandHandler("auto_off", self._auto_off))
        self.app.add_handler(CommandHandler("status", self._status))
        self.app.add_handler(CommandHandler("agendamentos", self._status))
        self.app.add_handler(CommandHandler("agendamento", self._start_scheduling))
        self.app.add_handler(CommandHandler("agendamento_retomar", self._resume_scheduling))
        self.app.add_handler(CommandHandler("cancelar_agendamento", self._cancel_scheduling))
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

    # --- COMANDOS BÁSICOS E MENU ---
    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_text = (
            "🚀 <b>Bem-vindo ao Maestro do AutoTube!</b> 🚀\n\n"
            "Gerencie todos os seus canais do YouTube através deste painel de controle interativo. "
            "Selecione uma opção:"
        )
        keyboard = [
            [InlineKeyboardButton("📂 Listar Projetos da API", callback_data="menu_cmd_listar")],
            [InlineKeyboardButton("📅 Novo Agendamento Lote", callback_data="menu_cmd_agendar")],
            [InlineKeyboardButton("📊 Relatório de Fila & Sistema", callback_data="menu_cmd_status")],
            [
                InlineKeyboardButton("🤖 Ligar Auto", callback_data="menu_cmd_autoon"),
                InlineKeyboardButton("🛑 Desligar Auto", callback_data="menu_cmd_autooff")
            ],
            [InlineKeyboardButton("❌ Interromper Filas", callback_data="menu_cmd_cancelar")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg_func = update.message.reply_text if update.message else update.callback_query.message.reply_text
        await msg_func(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

    async def _status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.on_get_status:
            msg_func = update.message.reply_text if update.message else update.callback_query.message.reply_text
            await msg_func(self.on_get_status(), parse_mode='HTML')

    async def _cancel_scheduling(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.on_cancel_scheduling:
            await self.on_cancel_scheduling()

    async def _resume_scheduling(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.on_resume_scheduling:
            await self.on_resume_scheduling()

    async def _auto_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.on_toggle_auto:
            self.on_toggle_auto(True)
            msg_func = update.message.reply_text if update.message else update.callback_query.message.reply_text
            await msg_func("🤖 <b>Modo Automático ATIVADO.</b>", parse_mode='HTML')

    async def _auto_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.on_toggle_auto:
            self.on_toggle_auto(False)
            msg_func = update.message.reply_text if update.message else update.callback_query.message.reply_text
            await msg_func("🛑 <b>Modo Automático DESATIVADO.</b>", parse_mode='HTML')

    # --- FLUXO DE APROVAÇÃO MANUAL (LISTAR) ---
    async def _list_projects_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.on_list_projects: return
        msg = update.message if update.message else update.callback_query.message
        temporario = await msg.reply_text("⏳ Conectando à API Real Oficial...")
        
        try:
            projects = await asyncio.to_thread(self.on_list_projects)
        except Exception as e:
            await temporario.edit_text(f"❌ Erro ao conectar na API: {e}")
            return
            
        await temporario.delete()
        if not projects:
            await msg.reply_text("Nenhum projeto disponível no momento.")
            return

        for p in projects:
            if isinstance(p, dict):
                p_id = p.get('id')
                p_name = html.escape(p.get('title') or p.get('name') or 'Sem nome')
                kb = [[InlineKeyboardButton("🚀 Iniciar Processamento", callback_data=f"man_ch_{p_id}")]]
                await msg.reply_text(
                    f"📁 <b>Projeto:</b> <code>{p_name}</code>\n🆔 <b>ID:</b> <code>{p_id}</code>\n---",
                    reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
                )

    # --- FLUXO AGENDAMENTO EM LOTE (100% INLINE) ---
    async def _start_scheduling(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.user_data.clear() # Limpa resíduos
        msg_text = "📅 <b>PASSO 1:</b> Quantos **dias** de frente deseja cobrir com esse lote?"
        kb = [
            [InlineKeyboardButton("1 Dia", callback_data="sch_days_1"), InlineKeyboardButton("3 Dias", callback_data="sch_days_3")],
            [InlineKeyboardButton("7 Dias (Semana)", callback_data="sch_days_7"), InlineKeyboardButton("15 Dias", callback_data="sch_days_15")],
            [InlineKeyboardButton("30 Dias", callback_data="sch_days_30")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")]
        ]
        
        if update.message:
            await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        else:
            await update.callback_query.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

    # --- FALLBACK TEXT MESSAGE ---
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if text.lower().startswith('pular '):
            short_id = text.lower().replace('pular ', '').strip()
            if self.on_skip_short:
                self.on_skip_short(short_id)
                await update.message.reply_text(f"⏭ O clipe `{short_id}` será pulado da fila atual.", parse_mode='Markdown')
            return
            
        await update.message.reply_text(
            "Oi! Essa função não usa mais chat de texto. 😊\n"
            "Use o comando /menu para interagir através dos botões clicáveis!"
        )

    # --- HOT CALLBACKS (BOTOES MESTRES) ---
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        try:
            await query.answer()
        except Exception as e:
            self.logger.warning(f"Não foi possível responder ao callback (expirado ou inválido): {e}")
        data = query.data

        # ---------------- HUB MENU ROUTES ----------------
        if data.startswith("menu_cmd_"):
            action = data.split("_")[2]
            if action == "listar": await self._list_projects_cmd(update, context)
            elif action == "agendar": await self._start_scheduling(update, context)
            elif action == "status": await self._status(update, context)
            elif action == "cancelar": await self._cancel_scheduling(update, context)
            elif action == "autoon": await self._auto_on(update, context)
            elif action == "autooff": await self._auto_off(update, context)
            elif action == "cancel_flow":
                self.user_data.clear()
                await query.edit_message_text("❌ Operação cancelada. Voltamos pro controle manual!")
            return

        # ---------------- MANUAL APPROVE WORKFLOW ----------------
        if data.startswith("man_ch_"):
            # Ação de "Iniciar Processamento" no hub de listar projetos
            p_id = data.split("_")[2]
            self.user_data['man_p_id'] = p_id
            kb = [
                [InlineKeyboardButton("🚀 Enviar TODOS OS VÍDEOS não postados", callback_data="man_chopt_all")],
                [InlineKeyboardButton("🎯 Escolher um VÍDEO ESPECÍFICO", callback_data="man_chopt_one")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")]
            ]
            await query.edit_message_text(f"Projeto <code>{p_id}</code>.\nO que deseja fazer:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        elif data == "man_chopt_one":
            p_id = self.user_data.get('man_p_id')
            if not getattr(self, "on_list_project_shorts", None):
                await query.edit_message_text("Função offline.")
                return
            await query.edit_message_text("⏳ Buscando cortes do projeto...", parse_mode='HTML')
            
            try:
                shorts = await asyncio.to_thread(self.on_list_project_shorts, p_id)
            except Exception:
                shorts = []
            
            if not shorts:
                await query.edit_message_text("❌ Nenhum vídeo encontrado neste projeto.")
                return
                
            kb = []
            for s in shorts:
                s_id = s.get('id')
                s_name = html.escape(s.get('title', 'Sem titulo'))[:35]
                kb.append([InlineKeyboardButton(f"🎬 {s_name}", callback_data=f"man_sel_{s_id}")])
            kb.append([InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")])
            await query.edit_message_text(f"Projeto <code>{p_id}</code>.\nSelecione o corte que deseja priorizar:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        elif data == "man_chopt_all" or data.startswith("man_sel_"):
            p_id = self.user_data.get('man_p_id')
            s_id = "all" if data == "man_chopt_all" else data.split("_")[2]
            self.user_data['man_s_id'] = s_id
            
            channels = self.on_list_channels()
            kb = [[InlineKeyboardButton(f"📺 {ch}", callback_data=f"man_pr_{ch}")] for ch in channels]
            kb.append([InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")])
            await query.edit_message_text(f"Projeto <code>{p_id}</code> (Alvo: <code>{s_id[:8]}...</code>).\n📺 Selecione o **Canal**:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        elif data.startswith("man_pr_"):
            ch_name = data.split("man_pr_")[1]
            self.user_data['man_ch_name'] = ch_name
            kb = [
                [InlineKeyboardButton("🔥 Viral / Polêmico", callback_data="man_do_viral")],
                [InlineKeyboardButton("📚 Educativo / Valor", callback_data="man_do_educativo")],
                [InlineKeyboardButton("😂 Entretenimento", callback_data="man_do_entretenimento")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")]
            ]
            await query.edit_message_text(f"Canal escolhido: <b>{ch_name}</b>\n\n🎯 Qual **Estilo de IA** deve dominar este lote?", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        elif data.startswith("man_do_"):
            profile = data.split("man_do_")[1]
            p_id = self.user_data.get('man_p_id')
            s_id = self.user_data.get('man_s_id')
            ch_name = self.user_data.get('man_ch_name')
            
            target_str = "TODOS OS VÍDEOS" if s_id == "all" else f"Vídeo {s_id[:8]}..."
            await query.edit_message_text(f"✅ Execução iniciada no canal <b>{ch_name}</b> (Perfil IA: <b>{profile}</b>, Alvo: <b>{target_str}</b>)!\nConsulte `/status` para acompanhar.", parse_mode='HTML')
            if self.on_approve_project:
                # Dispara async no bot_loop
                await self.on_approve_project(p_id, ch_name, profile, s_id)
            self.user_data.clear()

        # 1. Dias -> Data de Inicio
        elif data.startswith("sch_days_"):
            days = int(data.split("_")[2])
            self.user_data['cfg_days'] = days
            
            now = datetime.now()
            # Nomes dos dias em português
            pt_days = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            
            kb = []
            for i in range(10):  # Oferece os próximos 10 dias
                target_dt = now + timedelta(days=i)
                day_name = pt_days[target_dt.weekday()]
                date_str = target_dt.strftime("%d/%m")
                
                label = f"📅 {day_name} ({date_str})"
                if i == 0: label = f"🗓️ Hoje ({day_name}, {date_str})"
                elif i == 1: label = f"🌅 Amanhã ({day_name}, {date_str})"
                
                kb.append([InlineKeyboardButton(label, callback_data=f"sch_start_{i}")])

            kb.append([InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")])
            await query.edit_message_text("📅 <b>PASSO 2:</b> Quando as postagens devem iniciar?", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        # 2. Data -> Canal
        elif data.startswith("sch_start_"):
            offset = int(data.split("_")[2])
            self.user_data['cfg_start_offset'] = offset
            
            channels = self.on_list_channels()
            kb = [[InlineKeyboardButton(f"📺 {ch}", callback_data=f"sch_ch_{ch}")] for ch in channels]
            kb.append([InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")])
            await query.edit_message_text("📺 <b>PASSO 3:</b> Selecione o **Canal de Destino**:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        # 3. Canal -> IA Profile
        elif data.startswith("sch_ch_"):
            ch_name = data.split("_")[2]
            self.user_data['cfg_channel'] = ch_name
            
            kb = [
                [InlineKeyboardButton("🔥 Viral TikTok", callback_data="sch_pr_viral")],
                [InlineKeyboardButton("📚 Educativo", callback_data="sch_pr_educativo")],
                [InlineKeyboardButton("😂 Entretenimento", callback_data="sch_pr_entretenimento")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")]
            ]
            await query.edit_message_text(f"✅ Canal <b>{ch_name}</b>.\n\n🎯 <b>PASSO 4:</b> Qual **Estilo de IA**?", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        # 4. IA -> Projetos
        elif data.startswith("sch_pr_"):
            profile = data.split("_")[2]
            self.user_data['cfg_profile'] = profile
            
            await query.edit_message_text(f"✅ Perfil <b>{profile}</b>.\n⏳ Buscando projetos na API...")
            try:
                projects = await asyncio.to_thread(self.on_list_projects)
            except Exception:
                projects = []
            
            kb = []
            if projects:
                kb.append([InlineKeyboardButton("🌐 TODOS OS PROJETOS (Misturar)", callback_data="sch_proj_todos")])
                for p in projects:
                    p_name = html.escape(p.get('title') or p.get('name') or 'Sem Nome')
                    kb.append([InlineKeyboardButton(f"🎬 {p_name[:30]}", callback_data=f"sch_proj_{p['id']}")])
            kb.append([InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")])
            
            await query.edit_message_text(f"📂 <b>PASSO 5:</b> Quais projetos deseja incluir no roteiro?", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        # 5. Projetos -> Qtd Posts
        elif data.startswith("sch_proj_"):
            p_val = data.split("sch_proj_")[1]
            if p_val == "todos":
                try:
                    all_projects = await asyncio.to_thread(self.on_list_projects)
                    self.user_data['cfg_projects'] = [p['id'] for p in all_projects]
                except:
                    self.user_data['cfg_projects'] = []
            else:
                self.user_data['cfg_projects'] = [p_val]
            
            kb = [
                [InlineKeyboardButton("1 Vídeo por Dia", callback_data="sch_qtd_1"), InlineKeyboardButton("2 Vídeos", callback_data="sch_qtd_2")],
                [InlineKeyboardButton("3 Vídeos", callback_data="sch_qtd_3"), InlineKeyboardButton("4 Vídeos", callback_data="sch_qtd_4")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")]
            ]
            await query.edit_message_text("⏰ <b>PASSO 6:</b> Quantos posts **por dia**?", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        # 6. Qtd Selecionada -> Template Magico
        elif data.startswith("sch_qtd_"):
            qtd = int(data.split("_")[2])
            self.user_data['cfg_posts'] = qtd
            
            kb = [
                [InlineKeyboardButton("✅ Sim, Template Automático (Picos Youtube)", callback_data="sch_tpl_yes")],
                [InlineKeyboardButton("⚙️ Não, Horários Manuais", callback_data="sch_tpl_no")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")]
            ]
            await query.edit_message_text("📈 <b>PASSO FINAL:</b> Usar a tabela mágica de engajamento do Maestro?", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        # 6. Template
        elif data == "sch_tpl_yes":
            self.user_data['cfg_use_template'] = True
            await self._dispatch_final_schedule(query)
            
        elif data == "sch_tpl_no":
            self.user_data['cfg_use_template'] = False
            kb = [
                [InlineKeyboardButton("08:00", callback_data="sch_hr_8"), InlineKeyboardButton("10:00", callback_data="sch_hr_10")],
                [InlineKeyboardButton("12:00", callback_data="sch_hr_12"), InlineKeyboardButton("15:00", callback_data="sch_hr_15")],
                [InlineKeyboardButton("18:00", callback_data="sch_hr_18"), InlineKeyboardButton("20:00", callback_data="sch_hr_20")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")]
            ]
            await query.edit_message_text("🕒 A partir de que **HORA** começar?", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        # 7. Hora -> Intervalo
        elif data.startswith("sch_hr_"):
            hr = int(data.split("_")[2])
            self.user_data['cfg_start_hour'] = hr
            
            kb = [
                [InlineKeyboardButton("1h de Intervalo", callback_data="sch_int_1"), InlineKeyboardButton("2h de Intervalo", callback_data="sch_int_2")],
                [InlineKeyboardButton("4h de Intervalo", callback_data="sch_int_4"), InlineKeyboardButton("6h de Intervalo", callback_data="sch_int_6")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_cmd_cancel_flow")]
            ]
            await query.edit_message_text("⏳ Qual o intervalo (em horas) entre cada vídeo diário?", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        # 8. Intervalo Final
        elif data.startswith("sch_int_"):
            interval = int(data.split("_")[2])
            self.user_data['cfg_interval'] = interval
            await self._dispatch_final_schedule(query)

    async def _dispatch_final_schedule(self, query):
        if self.on_start_scheduling:
            await query.edit_message_text("✅ <b>O Maestro montou o Roteiro!</b>\nAguarde o processamento em background...", parse_mode='HTML')
            
            # Formata config
            cfg = {
                "days": self.user_data.get('cfg_days', 7),
                "posts_per_day": self.user_data.get('cfg_posts', 1),
                "start_hour": self.user_data.get('cfg_start_hour', 0),
                "interval_hours": self.user_data.get('cfg_interval', 0),
                "custom_hours": None,
                "use_template": self.user_data.get('cfg_use_template', False),
                "start_date_offset": self.user_data.get('cfg_start_offset', 0),
                "projects": self.user_data.get('cfg_projects', []),
                "channel_name": self.user_data.get('cfg_channel'),
                "profile_name": self.user_data.get('cfg_profile', 'viral')
            }
            self.user_data.clear()
            await self.on_start_scheduling(cfg)

    async def send_notification(self, message: str, reply_markup=None):
        try:
            try:
                await self.app.bot.send_message(chat_id=self.chat_id, text=message, reply_markup=reply_markup, parse_mode='HTML')
            except Exception:
                await self.app.bot.send_message(chat_id=self.chat_id, text=message, reply_markup=reply_markup)
        except Exception as e:
            self.logger.error(f"Erro ao enviar notificação: {e}")

    async def send_photo(self, photo_url: str, caption: str, reply_markup=None):
        try:
            await self.app.bot.send_photo(chat_id=self.chat_id, photo=photo_url, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
        except Exception:
            await self.send_notification(caption, reply_markup=reply_markup)

    def run(self):
        self.logger.info("Bot do Telegram iniciado fluídico multi-canal...")
        self.app.run_polling()

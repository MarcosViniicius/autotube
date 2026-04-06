from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import logging
import html
import asyncio
from typing import Callable, List, Dict
from datetime import datetime, timedelta



# ─────────────────────────────────────────────
#  HELPERS DE MENU
# ─────────────────────────────────────────────

def _menu(icon: str, title: str, body: str) -> str:
    """Monta o cabeçalho padrão de todos os menus."""
    return f"{icon} <b>{title}</b>\n\n{body}"


BTN_CANCEL = [InlineKeyboardButton("✖️  Cancelar", callback_data="menu_cmd_cancel_flow")]

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
                 on_get_schedule_state: Callable = None,
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
        self.on_get_schedule_state = on_get_schedule_state

        self.logger = logging.getLogger("AutoTubeBot")
        self.user_data = {}

        self.app = ApplicationBuilder().token(self.token).post_init(self._post_init).build()
        self._setup_handlers()

    async def _post_init(self, application):
        if self.on_startup:
            await self.on_startup()
        
        # Envia automaticamente o dashboard principal no boot
        await self.send_dashboard()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start",                 self._start))
        self.app.add_handler(CommandHandler("help",                  self._help_command))
        self.app.add_handler(CommandHandler("ajuda",                 self._help_command))
        self.app.add_handler(CommandHandler("menu",                  self._start))
        self.app.add_handler(CommandHandler("listar",                self._list_projects_cmd))
        self.app.add_handler(CommandHandler("auto_on",               self._auto_on))
        self.app.add_handler(CommandHandler("auto_off",              self._auto_off))
        self.app.add_handler(CommandHandler("status",                self._status))
        self.app.add_handler(CommandHandler("agendamentos",          self._status))
        self.app.add_handler(CommandHandler("agendamento",           self._start_scheduling))
        self.app.add_handler(CommandHandler("agendamento_retomar",   self._resume_scheduling))
        self.app.add_handler(CommandHandler("cancelar_agendamento",  self._cancel_scheduling))
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

    # ─────────────────────────────────────────
    #  MENU PRINCIPAL
    # ─────────────────────────────────────────
    

    def _get_dashboard_kwargs(self):
        state = self.on_get_schedule_state() if self.on_get_schedule_state else {}
        alert = state.get("alert")
        
        body = "Painel de controle dos seus canais YouTube.\n\n"
        body += "<i>Escolha uma opção abaixo:</i>\n\n"
        body += "📂 <b>Listar Projetos:</b> Ver vídeos cru da API e enviá-los manualmente.\n"
        body += "📅 <b>Criar Agendamento:</b> IA empacota múltiplos vídeos e programa todos os dias automaticamente.\n"
        body += "🗓️ <b>Ver Agendamentos:</b> Fiscalizar o status e data dos vídeos recém criados.\n"
        body += "▶️ <b>Retomar Pendentes:</b> Forçar upload dos projetos que caíram na malha da cota diária.\n"
        
        if alert:
            body += f"\n⚠️ <b>ATENÇÃO:</b>\n{alert}\n\n"

        text = _menu("🎬", "AutoTube Maestro", body)
        kb = [
            [InlineKeyboardButton("📂  Listar Projetos",    callback_data="menu_cmd_listar")],
            [InlineKeyboardButton("📅  Criar Agendamento",  callback_data="menu_cmd_agendar")],
            [InlineKeyboardButton("🗓️  Ver Agendamentos",   callback_data="menu_cmd_veragend")],
            [InlineKeyboardButton("▶️  Retomar Pendentes",  callback_data="menu_cmd_retomar")],
            [InlineKeyboardButton("📊  Status & Fila",      callback_data="menu_cmd_status")],
            [
                InlineKeyboardButton("🤖  Ligar Auto",      callback_data="menu_cmd_autoon"),
                InlineKeyboardButton("⏹  Desligar Auto",   callback_data="menu_cmd_autooff"),
            ],
            [InlineKeyboardButton("🚫  Interromper Filas", callback_data="menu_cmd_cancelar")],
        ]
        return {"text": text, "reply_markup": InlineKeyboardMarkup(kb), "parse_mode": 'HTML'}

    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "📖 <b>Manual Prático AutoTube</b>\n\n"
            "Sou o seu assistente de automação. Aqui vão dicas de uso:\n\n"
            "<b>1. Envio Manual vs Agendamento</b>\n"
            "Em 'Listar Projetos' você aprova vídeos manualmente, um a um. Em 'Criar Agendamento' você gera dezenas de vídeos com IA configurada.\n\n"
            "<b>2. Alertas de Quota</b>\n"
            "O YouTube possui limite de uploads. Se travar, não se preocupe! Retomamos automaticamente no outro dia, ou clique em 'Retomar Pendentes'.\n\n"
            "<b>3. Modo Auto</b>\n"
            "Ligar a Automação faz o sistema buscar shorts infinitamente a cada hora. Desligue se quiser gerir pacotes de vídeos com cuidado.\n\n"
            "Comandos rápidos: /menu, /status."
        )
        send = update.message.reply_text if update.message else update.callback_query.message.reply_text
        await send(help_text, parse_mode='HTML')

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        kwargs = self._get_dashboard_kwargs()
        send = update.message.reply_text if update.message else update.callback_query.message.reply_text
        await send(**kwargs)
        
    async def send_dashboard(self):
        kwargs = self._get_dashboard_kwargs()
        try:
            await self.app.bot.send_message(chat_id=self.chat_id, **kwargs)
        except Exception as e:
            self.logger.error(f"Erro ao enviar dashboard de boot: {e}")

    # ─────────────────────────────────────────
    #  STATUS
    # ─────────────────────────────────────────

    async def _status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.on_get_status:
            return
        send = update.message.reply_text if update.message else update.callback_query.message.reply_text
        await send(self.on_get_status(), parse_mode='HTML')

    # ─────────────────────────────────────────
    #  AUTO ON / OFF
    # ─────────────────────────────────────────

    async def _auto_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = _menu("🤖", "Configuração da Automação", "A cada quantas <b>horas</b> o bot deve varrer os projetos procurando shorts para postar?")
        kb = [
            [
                InlineKeyboardButton("1 Hora", callback_data="auto_interval_1"),
                InlineKeyboardButton("2 Horas", callback_data="auto_interval_2"),
                InlineKeyboardButton("3 Horas", callback_data="auto_interval_3"),
            ],
            [
                InlineKeyboardButton("4 Horas", callback_data="auto_interval_4"),
                InlineKeyboardButton("6 Horas", callback_data="auto_interval_6"),
                InlineKeyboardButton("12 Horas", callback_data="auto_interval_12"),
            ],
            [
                InlineKeyboardButton("24 Horas", callback_data="auto_interval_24"),
            ],
            BTN_CANCEL
        ]
        send = update.message.reply_text if update.message else update.callback_query.message.reply_text
        if update.callback_query and update.message is None: # fix for edit message
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        else:
            await send(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

    async def _auto_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.on_toggle_auto:
            self.on_toggle_auto(False, 1)
        text = _menu("⏹", "Modo Automático", "Status: <b>DESATIVADO 🔴</b>")
        kb = [[InlineKeyboardButton("↩️  Voltar ao Menu", callback_data="menu_cmd_voltar")]]
        send = update.message.reply_text if update.message else update.callback_query.message.reply_text
        await send(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

    async def _cancel_scheduling(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.on_cancel_scheduling:
            await self.on_cancel_scheduling()

    async def _resume_scheduling(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.on_resume_scheduling:
            await self.on_resume_scheduling()

    # ─────────────────────────────────────────
    #  VER AGENDAMENTOS
    # ─────────────────────────────────────────

    async def _view_schedules(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
        if not self.on_get_schedule_state:
            return
            
        state = self.on_get_schedule_state()
        slots = state.get("slots", [])
        
        msg = update.message if update.message else update.callback_query.message
        
        if not slots:
            kb = [[InlineKeyboardButton("↩️  Voltar ao Menu", callback_data="menu_cmd_voltar")]]
            await msg.edit_text(
                _menu("🗓️", "Ver Agendamentos", "Nenhum agendamento ativo ou pendente."),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )
            return

        per_page = 10
        total_pages = (len(slots) + per_page - 1) // per_page
        start_idx = page * per_page
        page_slots = slots[start_idx:start_idx + per_page]

        kb = []
        for s in page_slots:
            dt = datetime.fromisoformat(s['scheduled_time']).strftime("%d/%m %H:%M")
            st = s['status']
            if st == "agendado_api": icon = "✅"
            elif st == "processado": icon = "📦"
            elif st == "pendente":   icon = "⏳"
            else:                    icon = "⚠️"
            
            kb.append([InlineKeyboardButton(f"{icon} {dt} - {st.upper()}", callback_data=f"vw_slot_{s['index']}_{page}")])

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Ant", callback_data=f"vw_pag_{page-1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("Próx ➡️", callback_data=f"vw_pag_{page+1}"))
        if nav:
            kb.append(nav)

        kb.append([InlineKeyboardButton("↩️ Voltar ao Menu", callback_data="menu_cmd_voltar")])
        
        await msg.edit_text(
            _menu("🗓️", f"Listagem (Pág. {page+1}/{total_pages})", f"**Total de slots:** {len(slots)}"),
            reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
        )

    async def _view_slot_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, index: int, page: int):
        state = self.on_get_schedule_state()
        slots = state.get("slots", [])
        slot = next((s for s in slots if s['index'] == index), None)
        
        if not slot:
            return await self._view_schedules(update, context, page)
            
        dt = datetime.fromisoformat(slot['scheduled_time']).strftime("%d/%m/%Y às %H:%M")
        
        text = _menu(
            "🔎", f"Detalhe do Slot #{index}",
            f"📅 <b>Data:</b> {dt}\n"
            f"📊 <b>Status:</b> {slot.get('status', 'N/A')}\n"
            f"📂 <b>Projeto:</b> {slot.get('project_id') or 'Não definido'}\n"
            f"🔗 <b>Vídeo ID:</b> {slot.get('short_id') or 'N/A'}\n"
            f"▶️ <b>YT ID:</b> {f'https://youtu.be/{slot.get(chr(118)+chr(105)+chr(100)+chr(101)+chr(111)+chr(95)+chr(105)+chr(100))}' if slot.get('video_id') else 'Ainda não postado'}\n"
        )
        
        kb = [[InlineKeyboardButton("⬅️ Voltar pra Lista", callback_data=f"vw_pag_{page}")], [BTN_CANCEL[0]]]
        await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

    # ─────────────────────────────────────────
    #  LISTAR PROJETOS
    # ─────────────────────────────────────────

    async def _list_projects_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.on_list_projects:
            return
        msg = update.message if update.message else update.callback_query.message
        loading = await msg.reply_text(
            _menu("📂", "Listar Projetos", "⏳ Conectando à API…"),
            parse_mode='HTML'
        )
        try:
            projects = await asyncio.to_thread(self.on_list_projects)
        except Exception as e:
            await loading.edit_text(
                _menu("❌", "Erro na API", f"Não foi possível conectar:\n<code>{e}</code>"),
                parse_mode='HTML'
            )
            return

        await loading.delete()

        if not projects:
            kb = [[InlineKeyboardButton("↩️  Voltar ao Menu", callback_data="menu_cmd_voltar")]]
            await msg.reply_text(
                _menu("📂", "Listar Projetos", "Nenhum projeto disponível no momento."),
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode='HTML'
            )
            return

        for p in projects:
            if isinstance(p, dict):
                p_id   = p.get('id')
                p_name = html.escape(p.get('title') or p.get('name') or 'Sem nome')
                text   = _menu("📁", p_name, f"ID: <code>{p_id}</code>")
                kb     = [[InlineKeyboardButton("▶️  Iniciar Processamento", callback_data=f"man_ch_{p_id}")]]
                await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

    # ─────────────────────────────────────────
    #  INÍCIO DO AGENDAMENTO
    # ─────────────────────────────────────────

    async def _start_scheduling(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.user_data.clear()
        text = _menu(
            "📅", "Novo Agendamento — Passo 1 de 6",
            "Quantos <b>dias</b> deseja cobrir neste lote?"
        )
        kb = [
            [
                InlineKeyboardButton("1 dia",   callback_data="sch_days_1"),
                InlineKeyboardButton("3 dias",  callback_data="sch_days_3"),
                InlineKeyboardButton("7 dias",  callback_data="sch_days_7"),
            ],
            [
                InlineKeyboardButton("15 dias", callback_data="sch_days_15"),
                InlineKeyboardButton("30 dias", callback_data="sch_days_30"),
            ],
            BTN_CANCEL,
        ]
        send = update.message.reply_text if update.message else update.callback_query.message.reply_text
        await send(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

    # ─────────────────────────────────────────
    #  FALLBACK DE TEXTO
    # ─────────────────────────────────────────

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if text.lower().startswith('pular '):
            short_id = text.lower().replace('pular ', '').strip()
            if self.on_skip_short:
                self.on_skip_short(short_id)
                await update.message.reply_text(
                    _menu("⏭", "Clipe Pulado", f"O clipe <code>{short_id}</code> foi removido da fila."),
                    parse_mode='HTML'
                )
            return

        kb = [[InlineKeyboardButton("📋  Abrir Menu", callback_data="menu_cmd_voltar")]]
        await update.message.reply_text(
            _menu("💡", "Use os Botões", "Este bot funciona por menus interativos."),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode='HTML'
        )

    # ─────────────────────────────────────────
    #  CALLBACKS
    # ─────────────────────────────────────────

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        try:
            await query.answer()
        except Exception as e:
            self.logger.warning(f"Callback expirado: {e}")
        data = query.data

        # ── MENU PRINCIPAL ────────────────────────────────────────────────────
        if data.startswith("menu_cmd_"):
            action = data.split("_", 2)[2]
            if   action == "listar":      await self._list_projects_cmd(update, context)
            elif action == "agendar":     await self._start_scheduling(update, context)
            elif action == "veragend":    await self._view_schedules(update, context, page=0)
            elif action == "retomar":     await self._resume_scheduling(update, context)
            elif action == "status":      await self._status(update, context)
            elif action == "cancelar":    await self._cancel_scheduling(update, context)
            elif action == "autoon":      await self._auto_on(update, context)
            elif action == "autooff":     await self._auto_off(update, context)
            elif action in ("voltar", "cancel_flow"):
                self.user_data.clear()
                await self._start(update, context)
            return

        elif data == "sch_back_1":
            await self._start_scheduling(update, context)
            return

        # ── CONFIGURAÇÃO DE AUTO MODE ─────────────────────────────────────────
        elif data.startswith("auto_interval_"):
            interval = int(data.split("_")[2])
            if self.on_toggle_auto:
                self.on_toggle_auto(True, interval)
            text = _menu("🤖", "Modo Automático", f"Status: <b>ATIVADO ✅</b>\n\nVarreduras programadas a cada: <b>{interval} hora(s)</b>.")
            kb = [[InlineKeyboardButton("↩️  Voltar ao Menu", callback_data="menu_cmd_voltar")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
            return

        # ── NAVEGAÇÃO DE LISTA ───────────────────────────────────────────────
        elif data.startswith("vw_pag_"):
            page = int(data.split("_")[2])
            await self._view_schedules(update, context, page)
            return

        elif data.startswith("vw_slot_"):
            parts = data.split("_")
            idx = int(parts[2])
            page = int(parts[3])
            await self._view_slot_detail(update, context, idx, page)
            return

        # ── APROVAÇÃO MANUAL — escolha de ação ───────────────────────────────
        if data.startswith("man_ch_"):
            p_id = data.split("_")[2]
            self.user_data['man_p_id'] = p_id
            text = _menu("📁", "Processamento de Projeto", "O que deseja fazer?")
            kb = [
                [InlineKeyboardButton("📤  Todos os vídeos não postados", callback_data="man_chopt_all")],
                [InlineKeyboardButton("🎯  Escolher um vídeo específico", callback_data="man_chopt_one")],
                BTN_CANCEL,
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        # ── APROVAÇÃO MANUAL — listar cortes ─────────────────────────────────
        elif data == "man_chopt_one":
            p_id = self.user_data.get('man_p_id')
            await query.edit_message_text(
                _menu("🎬", "Buscando Cortes", "⏳ Aguarde…"),
                parse_mode='HTML'
            )
            try:
                shorts = await asyncio.to_thread(self.on_list_project_shorts, p_id)
            except Exception:
                shorts = []

            if not shorts:
                await query.edit_message_text(
                    _menu("📭", "Sem Vídeos", "Nenhum corte encontrado neste projeto."),
                    reply_markup=InlineKeyboardMarkup([BTN_CANCEL]), parse_mode='HTML'
                )
                return

            kb = [
                [InlineKeyboardButton(f"🎬  {html.escape(s.get('title', 'Sem título'))[:40]}", callback_data=f"man_sel_{s.get('id')}")]
                for s in shorts
            ]
            kb.append(BTN_CANCEL)
            await query.edit_message_text(
                _menu("🎬", "Escolher Vídeo", "Selecione o corte que deseja priorizar:"),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )

        # ── APROVAÇÃO MANUAL — escolher canal ────────────────────────────────
        elif data == "man_chopt_all" or data.startswith("man_sel_"):
            p_id = self.user_data.get('man_p_id')
            s_id = "all" if data == "man_chopt_all" else data.split("_")[2]
            self.user_data['man_s_id'] = s_id

            alvo = "Todos os vídeos" if s_id == "all" else f"Vídeo <code>{s_id[:10]}…</code>"
            channels = self.on_list_channels()
            kb = [
                [InlineKeyboardButton(f"📺  {ch}", callback_data=f"man_pr_{ch}")]
                for ch in channels
            ]
            kb.append(BTN_CANCEL)
            await query.edit_message_text(
                _menu("📺", "Canal de Destino", f"Alvo: {alvo}\n\nSelecione o canal:"),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )

        # ── APROVAÇÃO MANUAL — escolher estilo IA ────────────────────────────
        elif data.startswith("man_pr_"):
            ch_name = data.split("man_pr_")[1]
            self.user_data['man_ch_name'] = ch_name
            kb = [
                [InlineKeyboardButton("🔥  Viral / Polêmico",   callback_data="man_do_viral")],
                [InlineKeyboardButton("📚  Educativo / Valor",  callback_data="man_do_educativo")],
                [InlineKeyboardButton("😂  Entretenimento",     callback_data="man_do_entretenimento")],
                BTN_CANCEL,
            ]
            await query.edit_message_text(
                _menu("🎯", "Estilo de IA", f"Canal: <b>{ch_name}</b>\n\nQual estilo domina este lote?"),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )

        # ── APROVAÇÃO MANUAL — confirmar e disparar ───────────────────────────
        elif data.startswith("man_do_"):
            profile = data.split("man_do_")[1]
            p_id    = self.user_data.get('man_p_id')
            s_id    = self.user_data.get('man_s_id')
            ch_name = self.user_data.get('man_ch_name')
            alvo    = "Todos os vídeos" if s_id == "all" else f"Vídeo {s_id[:10]}…"

            kb = [[InlineKeyboardButton("↩️  Voltar ao Menu", callback_data="menu_cmd_voltar")]]
            await query.edit_message_text(
                _menu(
                    "✅", "Execução Iniciada",
                    f"📺 Canal: <b>{ch_name}</b>\n"
                    f"🎯 Estilo IA: <b>{profile}</b>\n"
                    f"📦 Alvo: {alvo}\n\n"
                    f"Use /status para acompanhar o progresso."
                ),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )
            if self.on_approve_project:
                await self.on_approve_project(p_id, ch_name, profile, s_id)
            self.user_data.clear()

        # ── AGENDAMENTO — PASSO 2: Data de início ────────────────────────────
        elif data.startswith("sch_days_") or data == "sch_back_2":
            if data.startswith("sch_days_"):
                days = int(data.split("_")[2])
                self.user_data['cfg_days'] = days
            else:
                days = self.user_data.get('cfg_days', 1)

            now     = datetime.now()
            pt_days = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            kb = []
            for i in range(10):
                dt  = now + timedelta(days=i)
                dia = pt_days[dt.weekday()]
                fmt = dt.strftime("%d/%m")
                if   i == 0: label = f"🗓  Hoje — {dia}, {fmt}"
                elif i == 1: label = f"🌅  Amanhã — {dia}, {fmt}"
                else:        label = f"📅  {dia}, {fmt}"
                kb.append([InlineKeyboardButton(label, callback_data=f"sch_start_{i}")])
            
            kb.append([
                InlineKeyboardButton("⬅️  Voltar", callback_data="sch_back_1"),
                InlineKeyboardButton("✖️  Cancelar", callback_data="menu_cmd_cancel_flow")
            ])

            await query.edit_message_text(
                _menu(
                    "📅", "Novo Agendamento — Passo 2 de 6",
                    f"Lote de <b>{days} dia(s)</b>.\n\nQuando as postagens devem <b>iniciar</b>?"
                ),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )

        # ── AGENDAMENTO — PASSO 3: Canal ─────────────────────────────────────
        elif data.startswith("sch_start_") or data == "sch_back_3":
            if data.startswith("sch_start_"):
                offset = int(data.split("_")[2])
                self.user_data['cfg_start_offset'] = offset

            channels = self.on_list_channels()
            kb = [
                [InlineKeyboardButton(f"📺  {ch}", callback_data=f"sch_ch_{ch}")]
                for ch in channels
            ]
            kb.append([
                InlineKeyboardButton("⬅️  Voltar", callback_data="sch_back_2"),
                InlineKeyboardButton("✖️  Cancelar", callback_data="menu_cmd_cancel_flow")
            ])
            await query.edit_message_text(
                _menu("📺", "Novo Agendamento — Passo 3 de 6", "Selecione o <b>canal de destino</b>:"),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )

        # ── AGENDAMENTO — PASSO 4: Estilo IA ─────────────────────────────────
        elif data.startswith("sch_ch_") or data == "sch_back_4":
            if data.startswith("sch_ch_"):
                ch_name = data.split("sch_ch_")[1]
                self.user_data['cfg_channel'] = ch_name
            ch_name = self.user_data.get('cfg_channel', 'default')

            kb = [
                [InlineKeyboardButton("🔥  Viral TikTok",   callback_data="sch_pr_viral")],
                [InlineKeyboardButton("📚  Educativo",      callback_data="sch_pr_educativo")],
                [InlineKeyboardButton("😂  Entretenimento", callback_data="sch_pr_entretenimento")],
                [
                    InlineKeyboardButton("⬅️  Voltar", callback_data="sch_back_3"),
                    InlineKeyboardButton("✖️  Cancelar", callback_data="menu_cmd_cancel_flow")
                ]
            ]
            await query.edit_message_text(
                _menu(
                    "🎯", "Novo Agendamento — Passo 4 de 6",
                    f"Canal: <b>{ch_name}</b>\n\nQual <b>estilo de IA</b> domina este lote?"
                ),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )

        # ── AGENDAMENTO — PASSO 5: Projetos ──────────────────────────────────
        elif data.startswith("sch_pr_") or data == "sch_back_5":
            if data.startswith("sch_pr_"):
                profile = data.split("_")[2]
                self.user_data['cfg_profile'] = profile
            profile = self.user_data.get('cfg_profile', 'viral')

            await query.edit_message_text(
                _menu("📂", "Buscando Projetos", "⏳ Conectando à API…"),
                parse_mode='HTML'
            )
            try:
                projects = await asyncio.to_thread(self.on_list_projects)
            except Exception:
                projects = []

            kb = []
            if projects:
                kb.append([InlineKeyboardButton("🌐  Todos os projetos", callback_data="sch_proj_todos")])
                for p in projects:
                    p_name = html.escape(p.get('title') or p.get('name') or 'Sem Nome')
                    kb.append([InlineKeyboardButton(f"🎬  {p_name[:38]}", callback_data=f"sch_proj_{p['id']}")])
            
            kb.append([
                InlineKeyboardButton("⬅️  Voltar", callback_data="sch_back_4"),
                InlineKeyboardButton("✖️  Cancelar", callback_data="menu_cmd_cancel_flow")
            ])

            await query.edit_message_text(
                _menu(
                    "📂", "Novo Agendamento — Passo 5 de 6",
                    f"Estilo IA: <b>{profile}</b>\n\nQuais projetos incluir no lote?"
                ),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )

        # ── AGENDAMENTO — PASSO 6: Posts por dia ─────────────────────────────
        elif data.startswith("sch_proj_") or data == "sch_back_6":
            if data.startswith("sch_proj_"):
                p_val = data.split("sch_proj_")[1]
                if p_val == "todos":
                    try:
                        all_p = await asyncio.to_thread(self.on_list_projects)
                        self.user_data['cfg_projects'] = [p['id'] for p in all_p]
                    except Exception:
                        self.user_data['cfg_projects'] = []
                else:
                    self.user_data['cfg_projects'] = [p_val]

            kb = [
                [
                    InlineKeyboardButton("1 / dia",  callback_data="sch_qtd_1"),
                    InlineKeyboardButton("2 / dia",  callback_data="sch_qtd_2"),
                    InlineKeyboardButton("3 / dia",  callback_data="sch_qtd_3"),
                    InlineKeyboardButton("4 / dia",  callback_data="sch_qtd_4"),
                ],
                [
                    InlineKeyboardButton("⬅️  Voltar", callback_data="sch_back_5"),
                    InlineKeyboardButton("✖️  Cancelar", callback_data="menu_cmd_cancel_flow")
                ]
            ]
            await query.edit_message_text(
                _menu("⏰", "Novo Agendamento — Passo 6 de 6", "Quantos posts <b>por dia</b>?"),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )

        # ── AGENDAMENTO — PASSO FINAL: Horários ──────────────────────────────
        elif data.startswith("sch_qtd_") or data == "sch_back_7":
            if data.startswith("sch_qtd_"):
                qtd = int(data.split("_")[2])
                self.user_data['cfg_posts'] = qtd
            qtd = self.user_data.get('cfg_posts', 1)

            kb = [
                [InlineKeyboardButton("✨  Template automático (horários de pico)", callback_data="sch_tpl_yes")],
                [InlineKeyboardButton("⚙️   Horários manuais",                      callback_data="sch_tpl_no")],
                [
                    InlineKeyboardButton("⬅️  Voltar", callback_data="sch_back_6"),
                    InlineKeyboardButton("✖️  Cancelar", callback_data="menu_cmd_cancel_flow")
                ]
            ]
            await query.edit_message_text(
                _menu(
                    "📈", "Novo Agendamento — Horários",
                    f"<b>{qtd} post(s) / dia</b>.\n\nQual estratégia de horários?"
                ),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )

        elif data == "sch_tpl_yes":
            self.user_data['cfg_use_template'] = True
            await self._dispatch_final_schedule(query)

        elif data == "sch_tpl_no" or data == "sch_back_8":
            self.user_data['cfg_use_template'] = False
            kb = [
                [
                    InlineKeyboardButton("08:00", callback_data="sch_hr_8"),
                    InlineKeyboardButton("10:00", callback_data="sch_hr_10"),
                    InlineKeyboardButton("12:00", callback_data="sch_hr_12"),
                ],
                [
                    InlineKeyboardButton("15:00", callback_data="sch_hr_15"),
                    InlineKeyboardButton("18:00", callback_data="sch_hr_18"),
                    InlineKeyboardButton("20:00", callback_data="sch_hr_20"),
                ],
                [
                    InlineKeyboardButton("⬅️  Voltar", callback_data="sch_back_7"),
                    InlineKeyboardButton("✖️  Cancelar", callback_data="menu_cmd_cancel_flow")
                ]
            ]
            await query.edit_message_text(
                _menu("🕒", "Horário de Início", "A partir de que hora começar?"),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )

        elif data.startswith("sch_hr_") or data == "sch_back_9":
            if data.startswith("sch_hr_"):
                hr = int(data.split("_")[2])
                self.user_data['cfg_start_hour'] = hr
            hr = self.user_data.get('cfg_start_hour', 8)

            kb = [
                [
                    InlineKeyboardButton("1h",  callback_data="sch_int_1"),
                    InlineKeyboardButton("2h",  callback_data="sch_int_2"),
                    InlineKeyboardButton("4h",  callback_data="sch_int_4"),
                    InlineKeyboardButton("6h",  callback_data="sch_int_6"),
                ],
                [
                    InlineKeyboardButton("⬅️  Voltar", callback_data="sch_back_8"),
                    InlineKeyboardButton("✖️  Cancelar", callback_data="menu_cmd_cancel_flow")
                ]
            ]
            await query.edit_message_text(
                _menu(
                    "⏳", "Intervalo entre Vídeos",
                    f"Início às <b>{hr:02d}:00</b>.\n\nQual o intervalo entre cada vídeo?"
                ),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
            )

        elif data.startswith("sch_int_"):
            interval = int(data.split("_")[2])
            self.user_data['cfg_interval'] = interval
            await self._dispatch_final_schedule(query)

    # ─────────────────────────────────────────
    #  DISPATCH FINAL DO AGENDAMENTO
    # ─────────────────────────────────────────

    async def _dispatch_final_schedule(self, query):
        if not self.on_start_scheduling:
            return

        cfg = {
            "days":              self.user_data.get('cfg_days', 7),
            "posts_per_day":     self.user_data.get('cfg_posts', 1),
            "start_hour":        self.user_data.get('cfg_start_hour', 0),
            "interval_hours":    self.user_data.get('cfg_interval', 0),
            "custom_hours":      None,
            "use_template":      self.user_data.get('cfg_use_template', False),
            "start_date_offset": self.user_data.get('cfg_start_offset', 0),
            "projects":          self.user_data.get('cfg_projects', []),
            "channel_name":      self.user_data.get('cfg_channel'),
            "profile_name":      self.user_data.get('cfg_profile', 'viral'),
        }
        self.user_data.clear()

        days    = cfg['days']
        posts   = cfg['posts_per_day']
        channel = cfg['channel_name'] or '—'
        profile = cfg['profile_name']
        total   = days * posts
        horario = "Horários de pico automáticos" if cfg['use_template'] \
                  else f"Início {cfg['start_hour']:02d}:00 · intervalo {cfg['interval_hours']}h"

        kb = [[InlineKeyboardButton("↩️  Voltar ao Menu", callback_data="menu_cmd_voltar")]]
        await query.edit_message_text(
            _menu(
                "✅", "Agendamento Criado",
                f"📺 Canal: <b>{channel}</b>\n"
                f"🎯 Estilo IA: <b>{profile}</b>\n"
                f"📅 Duração: <b>{days} dia(s)</b> · <b>{posts}/dia</b> · <b>{total} vídeos</b>\n"
                f"🕒 {horario}\n\n"
                f"O Maestro está montando o roteiro.\n"
                f"Use /status para acompanhar."
            ),
            reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
        )
        await self.on_start_scheduling(cfg)

    # ─────────────────────────────────────────
    #  NOTIFICAÇÕES
    # ─────────────────────────────────────────

    async def send_notification(self, message: str, reply_markup=None):
        try:
            try:
                await self.app.bot.send_message(
                    chat_id=self.chat_id, text=message,
                    reply_markup=reply_markup, parse_mode='HTML'
                )
            except Exception:
                await self.app.bot.send_message(
                    chat_id=self.chat_id, text=message, reply_markup=reply_markup
                )
        except Exception as e:
            self.logger.error(f"Erro ao enviar notificação: {e}")

    async def send_photo(self, photo_url: str, caption: str, reply_markup=None):
        try:
            await self.app.bot.send_photo(
                chat_id=self.chat_id, photo=photo_url,
                caption=caption, reply_markup=reply_markup, parse_mode='HTML'
            )
        except Exception:
            await self.send_notification(caption, reply_markup=reply_markup)

    def run(self):
        self.logger.info("AutoTube Maestro iniciado.")
        self.app.run_polling()
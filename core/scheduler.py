import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import uuid

TEMPLATE_HOURS = {
    0: [18, 19, 20, 21],          # Segunda
    1: [14, 18, 19, 20, 21, 22],  # Terça
    2: [18, 19, 20, 21, 22],      # Quarta
    3: [18, 19, 20, 21],          # Quinta
    4: [15, 16, 17],              # Sexta
    5: [15, 16, 17, 18],          # Sábado
    6: [12, 13, 14, 15]           # Domingo
}

class SchedulingManager:
    def __init__(self, state_file: str = "scheduling_state.json", log_file: str = "scheduling_log.txt"):
        self.state_file = state_file
        self.log_file = log_file
        self.logger = logging.getLogger("SchedulingManager")
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Erro ao carregar estado de agendamento: {e}")
        return {}

    def save_state(self, session_id: str, config: Dict, slots: List[Dict]):
        """Salva um novo estado completo."""
        self.state = {
            "session_id": session_id,
            "created_at": datetime.now().astimezone().isoformat(),
            "config": config,
            "slots": slots
        }
        self._persist()

    def clear_state(self):
        """Limpa todo o estado do agendamento da memória e do disco."""
        self.state = {}
        self._persist()
        self.logger.info("Estado do agendamento completamente apagado.")

    def update_slot(self, slot_index: int, updates: Dict):
        if self.state and "slots" in self.state:
            self.state["slots"][slot_index].update(updates)
            self.state["slots"][slot_index]["last_update"] = datetime.now().astimezone().isoformat()
            self._persist()

    def _persist(self):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erro ao persistir estado: {e}")

    def log_alert(self, message: str):
        self.state["alert"] = message
        self._persist()

    def clear_alert(self):
        if "alert" in self.state:
            self.state.pop("alert")
            self._persist()

    def log_error(self, slot_index: int, scheduled_time: str, path: str, stage: str, error: str):
        with open(self.log_file, 'a', encoding='utf-8') as f:
            log_entry = (
                f"[{datetime.now().astimezone().isoformat()}] SLOT: {slot_index} | "
                f"TIME: {scheduled_time} | PATH: {path} | "
                f"STAGE: {stage} | ERROR: {error}\n"
            )
            f.write(log_entry)

    def generate_slots(self, days: int, posts_per_day: int, start_hour: int, interval_hours: int, custom_hours: List[int] = None, use_template: bool = False, start_date_offset: int = 0) -> List[Dict]:
        """Gera a fila inicial de slots baseada nas configurações providas."""
        slots = []
        now = datetime.now().astimezone()
        
        target_total = days * posts_per_day
        if custom_hours:
            target_total = days * len(custom_hours)
            
        # Inicia hoje (0), amanhã (1), etc.
        start_date = now.date() + timedelta(days=start_date_offset)
        
        d = 0
        while len(slots) < target_total:
            current_day = start_date + timedelta(days=d)
            day_slots = []
            
            if use_template:
                hours = TEMPLATE_HOURS.get(current_day.weekday(), [18, 19])
                for p in range(posts_per_day):
                    hour_idx = p % len(hours)
                    hour = hours[hour_idx]
                    minute = (p // len(hours)) * 15
                    scheduled_time = datetime.combine(current_day, datetime.min.time().replace(hour=hour, minute=minute)).astimezone()
                    
                    if current_day == now.date() and scheduled_time < now:
                        continue
                    day_slots.append(scheduled_time)
                    
            elif custom_hours:
                for hour in custom_hours:
                    scheduled_time = datetime.combine(current_day, datetime.min.time().replace(hour=hour)).astimezone()
                    if current_day == now.date() and scheduled_time < now:
                        continue
                    day_slots.append(scheduled_time)
            else:
                for p in range(posts_per_day):
                    hour = start_hour + (p * interval_hours)
                    if hour >= 24:
                        break
                    scheduled_time = datetime.combine(current_day, datetime.min.time().replace(hour=hour)).astimezone()
                    if current_day == now.date() and scheduled_time < now:
                        continue
                    day_slots.append(scheduled_time)

            for st in day_slots:
                if len(slots) < target_total:
                    slots.append(self._create_slot_dict(len(slots), st))
            
            d += 1
            if d > days + 30: # Safety break
                break
                
        return slots

    @staticmethod
    def get_next_rounded_time(from_dt: datetime, min_minutes_ahead: int = 60) -> datetime:
        """
        Retorna o próximo horário redondo (minutos 00 ou 30) 
        pelo menos `min_minutes_ahead` no futuro.
        """
        target = from_dt + timedelta(minutes=min_minutes_ahead)
        if target.minute == 0:
            return target.replace(second=0, microsecond=0)
        elif target.minute <= 30:
            return target.replace(minute=30, second=0, microsecond=0)
        else:
            return (target + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    def _create_slot_dict(self, index: int, scheduled_time: datetime) -> Dict:
        return {
            "index": index,
            "scheduled_time": scheduled_time.astimezone().isoformat(),
            "status": "pendente",
            "project_id": None,
            "video_path": None,
            "metadata": None,
            "video_id": None,
            "last_update": datetime.now().astimezone().isoformat()
        }

    def get_pending_slots(self) -> List[Dict]:
        if not self.state or "slots" not in self.state:
            return []
        return [s for s in self.state["slots"] if s["status"] in ["pendente", "pendente_log", "processado", "rotulado", "enfileirado"]]

    def reschedule_pending_slots(self):
        """Reagita todos os slots pendentes para os próximos horários disponíveis começando amanhã."""
        pending = self.get_pending_slots()
        if not pending or "config" not in self.state:
            return

        config = self.state["config"]
        start_hour = config.get("start_hour", 8)
        interval_hours = config.get("interval_hours", 4)
        custom_hours = config.get("custom_hours")
        posts_per_day = config.get("posts_per_day", 1)
        use_template = config.get("use_template", False)

        now = datetime.now().astimezone()
        # Começa amanhã
        start_date = now.date() + timedelta(days=1)
        
        # Gerar os novos horários, assim como no generate_slots
        new_times = []
        
        d = 0
        while len(new_times) < len(pending):
            current_day = start_date + timedelta(days=d)
            day_times = []
            
            if use_template:
                hours = TEMPLATE_HOURS.get(current_day.weekday(), [18, 19])
                for p in range(posts_per_day):
                    hour_idx = p % len(hours)
                    hour = hours[hour_idx]
                    minute = (p // len(hours)) * 15
                    scheduled_time = datetime.combine(current_day, datetime.min.time().replace(hour=hour, minute=minute)).astimezone()
                    day_times.append(scheduled_time)
            elif custom_hours:
                for hour in custom_hours:
                    scheduled_time = datetime.combine(current_day, datetime.min.time().replace(hour=hour)).astimezone()
                    day_times.append(scheduled_time)
            else:
                for p in range(posts_per_day):
                    hour = start_hour + (p * interval_hours)
                    if hour >= 24:
                        break
                    scheduled_time = datetime.combine(current_day, datetime.min.time().replace(hour=hour)).astimezone()
                    day_times.append(scheduled_time)

            for dt in day_times:
                if len(new_times) < len(pending):
                    new_times.append(dt)
            d += 1
            if d > 100: break # Safety

        # Atualizar os slots
        for i, slot in enumerate(pending):
            idx = slot["index"]
            if i < len(new_times):
                self.state["slots"][idx]["scheduled_time"] = new_times[i].astimezone().isoformat()
                self.state["slots"][idx]["last_update"] = datetime.now().astimezone().isoformat()
        
        self._persist()

    def get_scheduling_summary(self) -> str:
        """Gera um resumo claro do agendamento em andamento."""
        if not self.state or "slots" not in self.state:
            return "Nenhuma sessão de agendamento em andamento."
            
        slots = self.state["slots"]
        total = len(slots)
        agendados = len([s for s in slots if s['status'] == 'agendado_api'])
        pending_slots = self.get_pending_slots()
        pendentes = len(pending_slots)
        
        summary = (
            f"📈 <b>Progresso da Sessão:</b> {agendados}/{total} concluídos.\n"
            f"⏳ <b>Restantes:</b> {pendentes} slots pendentes.\n"
        )
        
        if pending_slots:
            # Pega o primeiro agendamento pendente
            proximo = sorted([s['scheduled_time'] for s in pending_slots])[0]
            dt_next = datetime.fromisoformat(proximo)
            summary += f"📅 <b>Próximo agendado para:</b> <code>{dt_next.strftime('%d/%m/%Y %H:%M')}</code>"
            
        return summary

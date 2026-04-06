import json
import os
import logging
from typing import List, Set

class HistoryManager:
    def __init__(self, history_file: str = "history.json"):
        self.history_file = history_file
        self.logger = logging.getLogger("HistoryManager")
        self.processed_ids: Set[str] = self._load_history()

    def _load_history(self) -> Set[str]:
        """Carrega os IDs processados do arquivo JSON."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return set(data)
            except Exception as e:
                self.logger.error(f"Erro ao carregar histórico: {e}")
        return set()

    def _save_history(self):
        """Salva a lista atual de IDs no arquivo JSON."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.processed_ids), f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erro ao salvar histórico: {e}")

    def is_processed(self, item_id: str) -> bool:
        """Verifica se um ID já foi processado."""
        return str(item_id) in self.processed_ids

    def mark_as_processed(self, item_id: str):
        """Adiciona um ID ao histórico e salva."""
        self.processed_ids.add(str(item_id))
        self._save_history()

    def unmark_as_processed(self, item_id: str):
        """Desmarca o histórico devolvendo o vídeo à prateleira em caso de erros."""
        if str(item_id) in self.processed_ids:
            self.processed_ids.remove(str(item_id))
            self._save_history()

    def get_all_processed(self) -> List[str]:
        """Retorna todos os IDs processados."""
        return list(self.processed_ids)

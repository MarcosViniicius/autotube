import asyncio
import logging
from typing import Callable

class AsyncTaskQueue:
    """Fila de processamento assíncrona para gerenciar múltiplas tarefas pesadas sem travar a aplicação."""
    
    def __init__(self, num_workers: int = 3):
        self.queue = asyncio.Queue()
        self.num_workers = num_workers
        self.workers = []
        self.logger = logging.getLogger("AsyncTaskQueue")
        self.is_running = False

    async def start(self):
        """Inicia os workers em plano de fundo."""
        if self.is_running:
            return
        self.is_running = True
        for i in range(self.num_workers):
            task = asyncio.create_task(self._worker(f"Worker-{i+1}"))
            self.workers.append(task)
        self.logger.info(f"Fila de Arquitetura Assíncrona iniciada com {self.num_workers} workers.")

    async def stop(self):
        """Para todos os workers graciosamente."""
        self.is_running = False
        # Envia sinal de veneno (None) para cada worker parar
        for _ in range(self.num_workers):
            await self.queue.put(None)
        
        if self.workers:
            await asyncio.gather(*self.workers)
        self.workers.clear()
        self.logger.info("Fila de processamento pausada/finalizada.")

    async def enqueue(self, task_func: Callable, *args, **kwargs):
        """Adiciona uma nova tarefa à fila. `task_func` deve ser uma coroutine (async func)."""
        await self.queue.put((task_func, args, kwargs))
        self.logger.debug(f"Tarefa injetada na fila: {task_func.__name__} (Pendentes: {self.queue.qsize()})")

    def clear(self):
        """Limpa todas as tarefas pendentes da fila (esvazia a Queue)."""
        try:
            while not self.queue.empty():
                self.queue.get_nowait()
                self.queue.task_done()
            self.logger.info("Fila de processamento limpa (Tasks descartadas).")
        except Exception as e:
            self.logger.error(f"Erro ao limpar fila: {e}")

    async def _worker(self, name: str):
        self.logger.debug(f"{name} está online e aguardando tarefas.")
        while self.is_running:
            try:
                item = await self.queue.get()
                if item is None:
                    # Sinal de parada
                    self.queue.task_done()
                    break
                
                task_func, args, kwargs = item
                
                self.logger.info(f"{name} assumiu a tarefa: {task_func.__name__}")
                try:
                    await task_func(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Erro crasso no {name} ao processar {task_func.__name__}: {e}")
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Erro estrutural no {name}: {e}")

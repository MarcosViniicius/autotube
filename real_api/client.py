import requests
import logging
import time
from typing import List, Dict, Optional

class RealOficialAPI:
    def __init__(self, email: str = None, password: str = None, token: str = None, base_url: str = "https://api.realoficial.com.br/api/v1"):
        self.email = email
        self.password = password
        self.base_url = base_url
        self.token = token
        self.logger = logging.getLogger("RealOficialAPI")

    def login(self) -> bool:
        """Tenta login se o token não for fornecido."""
        if self.token:
            return True
        
        if not self.email or not self.password:
            self.logger.error("Credenciais de login ausentes e nenhum token fornecido.")
            return False

        try:
            url = f"{self.base_url}/login"
            payload = {"email": self.email, "password": self.password}
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            self.token = data.get("token")
            if self.token:
                self.logger.info("Login bem-sucedido na API Real Oficial.")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Erro ao fazer login: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def get_projects(self) -> List[Dict]:
        """Lista todos os projetos disponíveis."""
        try:
            if not self.token and not self.login():
                return []
            
            url = f"{self.base_url}/projects"
            self.logger.info(f"Chamando API: {url}")
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            
            if response.status_code != 200:
                self.logger.error(f"Erro na API ({response.status_code}): {response.text}")
                return []

            data = response.json()
            
            # A API Real Oficial retorna os projetos dentro da chave 'data'
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.error(f"Erro ao listar projetos: {e}")
            return []

    def get_shorts(self, project_id: str) -> List[Dict]:
        """Lista os cortes (shorts) gerados para um projeto específico."""
        try:
            # Conforme doc: GET /shorts/{projectId}?limit=100&sort=score
            url = f"{self.base_url}/shorts/{project_id}?limit=100&sort=score"
            self.logger.info(f"Buscando shorts: {url}")
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Conforme o exemplo da doc: a lista real está em data['data']['data']
            if isinstance(data, dict):
                # 1. Estrutura detectada na doc: {"data": {"data": [shorts]}}
                if 'data' in data and isinstance(data['data'], dict):
                    inner_data = data['data']
                    if 'data' in inner_data and isinstance(inner_data['data'], list):
                        shorts_list = inner_data['data']
                        if shorts_list:
                            self.logger.debug(f"Primeiro short encontrado: {shorts_list[0]}")
                        return shorts_list
                
                # 2. Estrutura detectada anteriormente: {"data": [shorts]}
                if 'data' in data and isinstance(data['data'], list):
                    return data['data']
                
                # 3. Fallback para 'shorts'
                if 'shorts' in data and isinstance(data['shorts'], list):
                    return data['shorts']

            return []
        except Exception as e:
            self.logger.error(f"Erro ao buscar shorts do projeto {project_id}: {e}")
            return []

    def render_short(self, project_id: str, short_id: str) -> Optional[str]:
        """Inicia a renderização de um corte específico."""
        try:
            url = f"{self.base_url}/shorts/{project_id}/{short_id}/render"
            # Tenta enviar com um corpo vazio caso a API exija
            response = requests.post(url, headers=self._get_headers(), json={}, timeout=60)
            
            # Se der erro 400, tenta sem o corpo (apenas o post)
            if response.status_code == 400:
                self.logger.warning("Renderização falhou com 400 (com body {}), tentando sem body...")
                response = requests.post(url, headers=self._get_headers(), timeout=60)

            response.raise_for_status()
            data = response.json()
            
            # Conforme doc: data.render_id ou data.data.render_id
            if isinstance(data, dict):
                render_id = data.get("render_id") or data.get("data", {}).get("render_id")
                if render_id:
                    return render_id
                # Fallback: a doc às vezes usa message ou outros campos
                self.logger.warning(f"Resposta de renderização sem render_id explícito: {data}")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao iniciar renderização do short {short_id}: {e}")
            return None

    def get_render_status(self, render_id: str) -> Dict:
        """Verifica o status e obtém a URL do vídeo renderizado listando os renders."""
        try:
            url = f"{self.base_url}/renders"
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            data = response.json()
            
            renders = []
            if isinstance(data, dict):
                # 1. Estrutura data.data.data
                if 'data' in data and isinstance(data['data'], dict) and 'data' in data['data']:
                    renders = data['data']['data']
                # 2. Estrutura data.data
                elif 'data' in data and isinstance(data['data'], list):
                    renders = data['data']
            elif isinstance(data, list):
                renders = data
                
            # Procura o render específico na lista com verificação de tipo
            if isinstance(renders, list):
                for r in renders:
                    if isinstance(r, dict) and r.get('id') == render_id:
                        return {
                            "status": r.get("status"), # done, processing, pending
                            "download_url": r.get("download_url")
                        }
            
            return {}
        except Exception as e:
            self.logger.error(f"Erro ao verificar status do render {render_id}: {e}")
            return {}

    def download_video(self, video_url: str, output_path: str) -> bool:
        """Faz o download do vídeo renderizado, com suporte a retentativas caso a CDN atrase (404)."""
        for tentativa in range(3):
            try:
                response = requests.get(video_url, stream=True, timeout=30)
                response.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                self.logger.info(f"Vídeo baixado com sucesso: {output_path}")
                return True
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Tentativa {tentativa+1}/3 de baixar vídeo ({video_url}) falhou: {e}")
                if tentativa < 2:
                    time.sleep(5)
            except Exception as e:
                self.logger.error(f"Erro ao baixar vídeo: {e}")
                return False
        
        self.logger.error("Download falhou após múltiplas tentativas.")
        return False

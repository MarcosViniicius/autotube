import os
import socket
# Evita deadlocks de socket na biblioteca httplib2 do Google API
socket.setdefaulttimeout(180)
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import googleapiclient.errors
import logging
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Escopos para API do YouTube
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

class YouTubeUploader:
    def __init__(self, client_secret_file: str, token_file: str = "token.json"):
        self.client_secret_file = client_secret_file
        self.token_file = token_file
        self.logger = logging.getLogger(f"YouTubeUploader-{os.path.basename(token_file)}")
        self.youtube = self._authenticate()

    def _authenticate(self):
        """Autenticação via OAuth2 para upload no YouTube com persistência de token."""
        creds = None
        # O arquivo token.json armazena os tokens de acesso e atualização do usuário
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except Exception as e:
                self.logger.warning(f"Arquivo {self.token_file} inválido ou corrompido: {e}. Solicitando novo login.")
                # Tenta remover o arquivo corrompido para não dar erro na gravação futura
                try:
                    os.remove(self.token_file)
                except:
                    pass
        
        # Se não houver credenciais válidas, deixa o usuário logar.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Salva as credenciais para a próxima execução
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

        return build("youtube", "v3", credentials=creds, static_discovery=False)

    def upload_short(self, video_path: str, title: str, description: str, tags: list = None, category_id: str = "22", publish_at: str = None, privacy_status: str = "public") -> Optional[str]:
        """Faz o upload de um vídeo como Shorts, com suporte a agendamento."""
        try:
            body = {
                "snippet": {
                    "title": title,
                    "description": f"{description}\n\n{' '.join(f'#{t}' for t in tags) if tags else ''}",
                    "tags": tags,
                    "categoryId": category_id
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False
                }
            }

            if publish_at:
                body["status"]["publishAt"] = publish_at
                # Se houver agendamento, o status de privacidade deve ser privado inicialmente
                body["status"]["privacyStatus"] = "private"

            media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
            
            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            import ssl, time as _t
            response = None
            _ssl_retries = 0
            _max_ssl_retries = 5
            while response is None:
                try:
                    status, response = request.next_chunk(num_retries=0)
                    if status:
                        self.logger.info(f"Upload em progresso: {int(status.progress() * 100)}%")
                    _ssl_retries = 0  # reset on success
                except (ssl.SSLError, TimeoutError, OSError) as ssl_err:
                    _ssl_retries += 1
                    if _ssl_retries > _max_ssl_retries:
                        raise
                    wait_sec = min(10 * _ssl_retries, 60)
                    self.logger.warning(f"SSL/Timeout transitório (tentativa {_ssl_retries}/{_max_ssl_retries}), aguardando {wait_sec}s antes de retentar chunk...")
                    _t.sleep(wait_sec)

            video_id = response.get("id")
            self.logger.info(f"Upload concluído com sucesso! Video ID: {video_id}")
            return video_id
        except googleapiclient.errors.HttpError as e:
            self.logger.error(f"Erro HTTP do YouTube: {e}")
            if e.resp.status == 403 and "quota" in str(e).lower():
                self.logger.critical("Cota do YouTube diária atingida (QuotaExceeded)!")
                raise ValueError("YouTubeQuotaError: Limite de cota atingido")
            # Se for 5xx, levantamos o erro genérico para que o tenacity tente novamente
            if e.resp.status >= 500:
                raise e
            return None
        except ValueError as ve:
            # Não tenta novamente os erros de cota (raise propaga)
            raise ve
        except Exception as e:
            self.logger.error(f"Erro ao fazer upload no YouTube: {e}")
            raise e

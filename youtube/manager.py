import os
import glob
import logging
from typing import Dict, List
from .uploader import YouTubeUploader

class YouTubeChannelManager:
    def __init__(self, channels_dir: str = "channels"):
        self.channels_dir = channels_dir
        self.logger = logging.getLogger("YouTubeChannelManager")
        self.channels: Dict[str, YouTubeUploader] = {}
        
        if not os.path.exists(self.channels_dir):
            os.makedirs(self.channels_dir)
            
        self.load_channels()

    def load_channels(self):
        """Escaneia o diretório channels/ por arquivos client_secret_NOME.json"""
        self.channels.clear()
        pattern = os.path.join(self.channels_dir, "client_secret_*.json")
        secret_files = glob.glob(pattern)
        
        if not secret_files:
            self.logger.warning(f"Nenhum canal encontrado em {self.channels_dir}/. Adicione arquivos client_secret_NOME.json.")
            return

        for secret_file in secret_files:
            # Extrair o NOME do arquivo client_secret_NOME.json
            basename = os.path.basename(secret_file)
            name_part = basename.replace("client_secret_", "").replace(".json", "")
            channel_name = name_part if name_part else "default"
            
            token_file = os.path.join(self.channels_dir, f"token_{channel_name}.json")
            
            self.logger.info(f"Carregando canal YouTube: {channel_name}")
            try:
                uploader = YouTubeUploader(client_secret_file=secret_file, token_file=token_file)
                self.channels[channel_name] = uploader
            except Exception as e:
                self.logger.error(f"Erro ao inicializar uploader para o canal {channel_name}: {e}")

    def get_channel(self, channel_name: str) -> YouTubeUploader:
        return self.channels.get(channel_name)

    def list_channels(self) -> List[str]:
        return list(self.channels.keys())

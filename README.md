# AutoTube - Automação para YouTube Shorts

Sistema completo em Python para automação de criação e publicação de YouTube Shorts integrando a API Real Oficial, OpenRouter (IA) e a API do YouTube.

## 🚀 Funcionalidades

- **Integração Real Oficial**: Login, listagem de projetos, geração de cortes automáticos, renderização e download.
- **IA com OpenRouter**: Geração automática de títulos, descrições e hashtags otimizados para Shorts.
- **Upload YouTube**: Publicação automática dos vídeos renderizados com metadados via API oficial.
- **Bot do Telegram**: Controle total do sistema via Telegram. Receba notificações de progresso e aprove projetos manualmente.
- **Dois Modos de Operação**:
  - **Manual (Auditoria)**: Você escolhe quais projetos processar via Telegram.
  - **Automático**: O sistema busca e processa novos projetos continuamente.

## 📁 Estrutura do Projeto

- `real_api/`: Módulo de integração com a API Real Oficial.
- `ai/`: Geração de conteúdo usando OpenRouter.
- `youtube/`: Lógica de upload para o YouTube.
- `telegram_bot/`: Bot de controle e notificações.
- `core/`: Pipeline principal e lógica de processamento.
- `config/`: Gerenciamento de configurações e variáveis de ambiente.
- `downloads/`: Pasta temporária para vídeos processados.
- `logs/`: Registros de execução do sistema.

## 🛠️ Instalação

1. Clone o repositório.
2. Crie um ambiente virtual e instale as dependências:
   ```bash
   python -m venv venv
   source venv/bin/activate  # ou venv\Scripts\activate no Windows
   pip install -r requirements.txt
   ```
3. Configure o arquivo `.env` (use o `.env.example` como base).
4. Configure o `client_secret.json` da API do YouTube na raiz do projeto.

## ⚙️ Configuração (.env)

| Variável | Descrição |
|----------|-----------|
| `REAL_API_EMAIL` | Email da conta Real Oficial |
| `REAL_API_PASSWORD` | Senha da conta Real Oficial |
| `OPENROUTER_API_KEY` | Chave de API do OpenRouter |
| `TELEGRAM_BOT_TOKEN` | Token do Bot do Telegram |
| `TELEGRAM_CHAT_ID` | ID do chat para notificações |
| `MODO_DEFAULT` | `manual` ou `auto` |
| `CRON_INTERVAL` | Intervalo de busca no modo automático (minutos) |

## 🤖 Comandos do Bot

- `/start`: Inicia o bot e exibe comandos.
- `/listar`: Lista projetos disponíveis para aprovação manual.
- `/auto_on`: Ativa o modo de processamento automático.
- `/auto_off`: Desativa o modo de processamento automático.

## 📝 Licença

Este projeto é para fins educacionais e de automação pessoal. Certifique-se de seguir os termos de uso das APIs integradas.

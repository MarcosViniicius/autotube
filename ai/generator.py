import openai
import logging
from typing import Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, wait_random

class ContentGenerator:
    def __init__(self, api_key: str, model: str = "google/gemini-2.0-flash-lite-001"):
        self.api_key = api_key
        self.model = model
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        self.logger = logging.getLogger("AIContentGenerator")

    def generate_shorts_metadata(self, video_description: str, content_profile: str = "viral") -> Dict[str, str]:
        """Gera metadados (título, descrição, hashtags) otimizados para YouTube Shorts."""
        try:
            self.logger.info(f"Gerando metadados para: {video_description[:50]}...")
            PROFILES = {
                "viral": "Você é um especialista em SEO focado em MAXIMIZAR o CTR para Cortes Virais e Polêmicos.\nRegras Específicas: Use gatilhos mentais de curiosidade extrema, caixa alta nas palavras de impacto, urgência e emojis que chamem muita atenção (ex: 🔥, 😱).",
                "educativo": "Você é um professor focado em Edu-Tainment (Educação + Entretenimento) para Shorts.\nRegras Específicas: Título claro focando na dor ou problema que o vídeo resolve ('Como...', 'O segredo de...'). Tom professoral e acessível, convidando para salvar o vídeo ou aprender mais.",
                "entretenimento": "Você é um criador focado em retenção via Storytelling e Comédia para Shorts.\nRegras Específicas: Títulos intrigantes que contam o início de uma situação. Evite caça-cliques agressivo, foque na diversão do contexto (ex: 😂, 👀)."
            }
            
            perfil_ativo = PROFILES.get(content_profile.lower(), PROFILES["viral"])

            prompt = f"""
            {perfil_ativo}
            Sua tarefa é extrair e criar metadados para este Short.

            CONTEÚDO DO VÍDEO (CONTEXTO):
            "{video_description}"

            INSTRUÇÕES:
            1. TÍTULO: Deve ser curto (máximo 80 caracteres), obedecendo seu perfil acima. É OBRIGATÓRIO incluir 1 ou 2 hashtags ultra-relevantes exatamente no final do título. NÃO use títulos genéricos.
            2. DESCRIÇÃO: Deve ser uma frase curta e impactante que resuma o valor do vídeo, seguida de uma chamada para ação coerente com o perfil.
            3. HASHTAGS: Escolha as 5 hashtags mais relevantes e de alto volume para esse nicho. Respeite o perfil.

            REGRAS CRÍTICAS:
            - O título DEVE ser focado nesse contexto relatado e OBRIGATORIAMENTE terminar com hashtags (ex: Título Impactante #shorts #futebol).
            - Se o contexto possuir nomes próprios ou locais marcantes, inclua no título e hashtags.

            RETORNE APENAS UM JSON NO FORMATO:
            {{
                "title": "TÍTULO IMPACTANTE AQUI",
                "description": "DESCRIÇÃO ESTRATÉGICA AQUI",
                "hashtags": "#tag1 #tag2 #tag3 #tag4 #tag5"
            }}
            """
            
            content = self._call_ai_with_retry(prompt)
            import json
            if not content:
                raise ValueError("Resposta da IA vazia")
            
            # Limpeza básica caso a IA retorne blocos de código markdown
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()
                
            metadata = json.loads(content)
            
            # Validação básica para evitar campos vazios
            if not metadata.get("title") or metadata.get("title") == "Novo Short Viral":
                self.logger.warning("IA retornou título genérico ou vazio, tentando ajustar...")
                # Poderíamos tentar um retry ou apenas logar
            
            self.logger.info(f"Metadados gerados com sucesso: {metadata.get('title')}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar metadados via IA: {str(e)}")
            # Fallback mais inteligente baseado na descrição se disponível
            base_title = video_description[:50] if video_description else "Corte Especial"
            return {
                "title": f"{base_title} #shorts",
                "description": f"Confira este conteúdo sobre {video_description[:100]}...",
                "hashtags": "#shorts #viral #autotube #conteudo"
            }

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10) + wait_random(0, 2),
        stop=stop_after_attempt(4),
        reraise=True
    )
    def _call_ai_with_retry(self, prompt: str) -> str:
        self.logger.debug("Chamando API da OpenRouter/Gemini...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Você é um assistente de IA focado em marketing digital e YouTube Shorts. Você SEMPRE responde em JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

import openai
import logging
import re
import json
from typing import Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, wait_random


# ─────────────────────────────────────────────────────────────────────────────
#  PERFIS DE GERAÇÃO
#  Cada perfil define: persona da IA, técnica de título e critério de hashtag
# ─────────────────────────────────────────────────────────────────────────────

PROFILES = {
    "viral": {
        "persona": (
            "Você é um redator sênior especializado em conteúdo viral para YouTube Shorts e TikTok. "
            "Já viralizou centenas de vídeos estudando gatilhos cognitivos: curiosidade, dissonância, "
            "choque de expectativa e urgência emocional."
        ),
        "titulo_tecnica": (
            "TÉCNICA DE TÍTULO VIRAL:\n"
            "- Crie dissonância: junte dois conceitos que o público não espera juntos\n"
            "- Use números ou tempo quando possível ('em 30 segundos', '3x mais')\n"
            "- Gatilhos que funcionam: 'Ninguém te contou...', 'Pare tudo e...', 'O motivo real...', "
            "'Isso muda tudo', 'A verdade sobre...'\n"
            "- PROIBIDO: 'Novo vídeo', 'Confira', 'Incrível', 'Veja isso' — são fracos e genéricos\n"
            "- O título deve gerar uma pergunta na cabeça de quem lê, não respondê-la"
        ),
        "hashtag_criterio": (
            "CRITÉRIO DE HASHTAGS VIRAIS:\n"
            "- 1 hashtag de NICHO ESPECÍFICO do tema (ex: #psicologia, #investimentos, #fitness)\n"
            "- 1 hashtag de TENDÊNCIA relacionada ao assunto\n"
            "- 1 hashtag de FORMATO (#shorts, #reels, #viral)\n"
            "- PROIBIDO: hashtags genéricas como #video #conteudo #brasil #dicas sem relação direta\n"
            "- PROIBIDO repetir variações da mesma palavra"
        ),
    },
    "educativo": {
        "persona": (
            "Você é um educador digital especialista em transformar conteúdo complexo em aprendizado "
            "rápido e satisfatório. Seu público quer sair do vídeo sabendo mais do que entrou, "
            "em menos de 60 segundos."
        ),
        "titulo_tecnica": (
            "TÉCNICA DE TÍTULO EDUCATIVO:\n"
            "- Aponte a DOR ou LACUNA de conhecimento do público ('Por que você erra...', 'O erro que...', "
            "'Como realmente funciona...')\n"
            "- Prometa transformação concreta e rápida\n"
            "- Formatos que convertem: 'Como X sem Y', 'O segredo que profissionais usam', "
            "'Aprenda X em 60 segundos'\n"
            "- PROIBIDO: ser vago — diga exatamente O QUE o espectador vai aprender"
        ),
        "hashtag_criterio": (
            "CRITÉRIO DE HASHTAGS EDUCATIVAS:\n"
            "- 1 hashtag da ÁREA DE CONHECIMENTO (ex: #programacao, #financas, #culinaria)\n"
            "- 1 hashtag do PÚBLICO-ALVO ou situação (ex: #parainiciantes, #dicas, #aprender)\n"
            "- 1 hashtag de formato (#shorts ou #aprenda)\n"
            "- PROIBIDO: hashtags que não têm relação direta com o que é ensinado no vídeo"
        ),
    },
    "entretenimento": {
        "persona": (
            "Você é um roteirista de conteúdo curto especializado em retenção e storytelling. "
            "Sabe que os primeiros 2 segundos decidem tudo e que o título é o trailer do vídeo."
        ),
        "titulo_tecnica": (
            "TÉCNICA DE TÍTULO ENTRETENIMENTO:\n"
            "- Comece no meio da ação, nunca no começo ('Quando ele percebeu...', 'No momento em que...')\n"
            "- Crie tensão ou situação incompleta que o cérebro precisa resolver\n"
            "- Use perspectiva em primeira ou segunda pessoa quando cabível\n"
            "- Emojis devem reforçar emoção, não decorar — máximo 2\n"
            "- PROIBIDO: spoiler do desfecho no título"
        ),
        "hashtag_criterio": (
            "CRITÉRIO DE HASHTAGS DE ENTRETENIMENTO:\n"
            "- 1 hashtag do GÊNERO do conteúdo (ex: #humor, #drama, #reactvideos)\n"
            "- 1 hashtag do TEMA ou UNIVERSO (ex: #futebol, #gaming, #animais)\n"
            "- 1 hashtag de FORMATO (#shorts, #storytime, #pov)\n"
            "- PROIBIDO: hashtags que não fazem sentido para alguém que nunca viu o vídeo"
        ),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  GERADOR PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class ContentGenerator:
    def __init__(self, api_key: str, model: str = "google/gemini-2.0-flash-lite-001"):
        self.api_key = api_key
        self.model = model
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        self.logger = logging.getLogger("ContentGenerator")

    # ── ENTRADA PRINCIPAL ─────────────────────────────────────────────────────

    def generate_shorts_metadata(
        self,
        video_description: str,
        content_profile: str = "viral",
    ) -> Dict[str, str]:
        """
        Gera metadados otimizados para YouTube Shorts em dois estágios:
          1. Análise do conteúdo para extrair tema, emoção e público
          2. Geração de título, descrição e hashtags com base nessa análise

        Retorna dict com: title, description, hashtags
        """
        profile = PROFILES.get(content_profile.lower(), PROFILES["viral"])

        try:
            # ESTÁGIO 1 — entender o que o vídeo realmente é
            analysis = self._analyze_content(video_description)

            # ESTÁGIO 2 — gerar metadados com contexto rico
            metadata = self._generate_metadata(video_description, analysis, profile)

            # Validação e fallback por campo
            metadata = self._validate_and_fix(metadata, video_description, profile)

            self.logger.info(f"Metadados finais → título: '{metadata['title']}'")
            return metadata

        except Exception as e:
            self.logger.error(f"Erro na geração de metadados: {e}")
            return self._fallback(video_description)

    # ── ESTÁGIO 1: ANÁLISE ────────────────────────────────────────────────────

    def _analyze_content(self, video_description: str) -> Dict[str, str]:
        """
        Pede à IA que analise o vídeo antes de gerar qualquer texto.
        Isso enriquece o contexto do estágio 2 e melhora muito a qualidade.
        """
        prompt = f"""
Analise o conteúdo do vídeo abaixo e extraia as seguintes informações.
Responda SOMENTE em JSON válido, sem markdown ou texto extra.

DESCRIÇÃO DO VÍDEO:
"{video_description}"

RETORNE EXATAMENTE ESTE JSON:
{{
    "tema_principal": "em uma frase curta, qual o assunto central do vídeo",
    "emocao_dominante": "uma palavra: curiosidade | choque | inspiracao | humor | aprendizado | polêmica",
    "publico_alvo": "quem vai se interessar por esse conteúdo (ex: jovens, investidores, fãs de esporte)",
    "palavras_chave": ["3 a 5 palavras-chave relevantes do tema, em português, sem #"],
    "gancho_central": "o elemento mais intrigante ou surpreendente do vídeo em uma frase"
}}
"""
        try:
            raw = self._call_ai_with_retry(prompt)
            return self._parse_json(raw)
        except Exception as e:
            self.logger.warning(f"Análise falhou, prosseguindo sem ela: {e}")
            return {}

    # ── ESTÁGIO 2: GERAÇÃO ────────────────────────────────────────────────────

    def _generate_metadata(
        self,
        video_description: str,
        analysis: Dict,
        profile: Dict,
    ) -> Dict[str, str]:
        """Gera título, descrição e hashtags usando a análise como contexto."""

        analysis_block = ""
        if analysis:
            analysis_block = f"""
ANÁLISE PRÉVIA DO CONTEÚDO (use como base):
- Tema: {analysis.get('tema_principal', '—')}
- Emoção dominante: {analysis.get('emocao_dominante', '—')}
- Público-alvo: {analysis.get('publico_alvo', '—')}
- Palavras-chave do tema: {', '.join(analysis.get('palavras_chave', []))}
- Gancho central: {analysis.get('gancho_central', '—')}
"""

        prompt = f"""
{profile['persona']}

{analysis_block}

DESCRIÇÃO ORIGINAL DO VÍDEO:
"{video_description}"

{profile['titulo_tecnica']}

{profile['hashtag_criterio']}

REGRAS ABSOLUTAS:
- TÍTULO: máximo 60 caracteres (conte os caracteres). Sem ponto final.
- DESCRIÇÃO: 1 frase impactante + 1 Call-To-Action claro. Máximo 120 caracteres.
- HASHTAGS: exatamente 3, separadas por espaço, começando com #. 
  Devem ser específicas ao conteúdo — NUNCA use #video #conteudo #brasil sem razão direta.

Responda SOMENTE com JSON válido, sem markdown, sem explicações.

FORMATO OBRIGATÓRIO:
{{
    "title": "título aqui",
    "description": "descrição aqui",
    "hashtags": "#hashtag1 #hashtag2 #hashtag3"
}}
"""
        raw = self._call_ai_with_retry(prompt)
        return self._parse_json(raw)

    # ── VALIDAÇÃO ─────────────────────────────────────────────────────────────

    def _validate_and_fix(
        self,
        metadata: Dict,
        video_description: str,
        profile: Dict,
    ) -> Dict[str, str]:
        """Corrige problemas comuns sem precisar chamar a IA novamente."""

        title = metadata.get("title", "").strip()
        description = metadata.get("description", "").strip()
        hashtags = metadata.get("hashtags", "").strip()

        # Título muito longo → trunca na última palavra inteira
        if len(title) > 60:
            self.logger.warning(f"Título longo ({len(title)} chars), truncando: '{title}'")
            title = title[:57].rsplit(' ', 1)[0] + "…"

        # Título genérico conhecido → usa gancho da descrição
        TITULOS_RUINS = {"novo vídeo", "novo short", "confira", "incrível", "veja isso", ""}
        if title.lower() in TITULOS_RUINS or not title:
            self.logger.warning("Título genérico detectado, usando fallback de título.")
            title = (video_description[:55] + "…") if len(video_description) > 55 else video_description

        # Hashtags — remove duplicatas e garante o # em cada uma
        tags = [t.strip() for t in hashtags.split() if t.strip()]
        tags = [t if t.startswith("#") else f"#{t}" for t in tags]
        tags = list(dict.fromkeys(tags))  # remove duplicatas mantendo ordem

        # Garante pelo menos #shorts se ficou sem nada
        if not tags:
            tags = ["#shorts", "#viral", "#conteudo"]

        # Limita a 3 hashtags
        tags = tags[:3]

        return {
            "title": title,
            "description": description or "Inscreva-se para não perder o próximo! 🔔",
            "hashtags": " ".join(tags),
        }

    # ── FALLBACK ──────────────────────────────────────────────────────────────

    def _fallback(self, video_description: str) -> Dict[str, str]:
        """Retornado apenas se tudo falhar — melhor que um crash."""
        base = video_description[:55] if video_description else "Corte especial"
        return {
            "title": base + ("…" if len(video_description) > 55 else ""),
            "description": "Inscreva-se para não perder os próximos vídeos! 🔔",
            "hashtags": "#shorts #viral #conteudo",
        }

    # ── UTILITÁRIOS ───────────────────────────────────────────────────────────

    def _parse_json(self, raw: str) -> Dict:
        """Extrai JSON de uma resposta da IA mesmo que venha com markdown."""
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"JSON não encontrado na resposta: {raw[:200]}")

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10) + wait_random(0, 2),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _call_ai_with_retry(self, prompt: str) -> str:
        self.logger.debug("Chamando OpenRouter…")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente especializado em marketing digital e YouTube Shorts. "
                        "Responda SEMPRE em JSON válido, sem markdown, sem texto adicional."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
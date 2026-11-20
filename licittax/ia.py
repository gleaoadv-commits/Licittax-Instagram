"""Chamadas ao Claude. Resumo e gancho têm fallback; a verificação falha fechada."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

import anthropic

MODELO_RAPIDO = "claude-sonnet-5-5"
MODELO_RIGOROSO = "claude-opus-5-5"

SISTEMA_RESUMO = (
    "Você resume objetos de licitações brasileiras para posts de Instagram. "
    "Escreva em português do Brasil, linguagem simples, no máximo 90 caracteres, "
    "sem inventar nada que não esteja no texto. Responda só com o resumo, sem aspas."
)
SISTEMA_GANCHO = (
    "Você escreve o gancho (primeira frase) da legenda de um post de dicas sobre "
    "licitações para ME/EPP. Português do Brasil, uma única frase de até 150 caracteres, "
    "sem citar números de lei, artigos ou telefones. Responda só com a frase."
)
SISTEMA_REVISOR = (
    "Você é revisor jurídico. Responda apenas se o texto de lei fornecido sustenta "
    "integralmente a afirmação. Se a afirmação for mais ampla, diferente ou não estiver "
    "no texto, sustenta deve ser false. Não use conhecimento externo ao texto fornecido."
)
SISTEMA_DICAS = (
    "Você é consultor especialista em licitações públicas brasileiras (Lei 14.133/2021, "
    "LC 123/2006 e decretos) e cria dicas práticas para microempresas e empresas de "
    "pequeno porte (ME/EPP) em posts de carrossel do Instagram. Escreva em português do "
    "Brasil. Toda afirmação jurídica deve constar em 'afirmacoes' com citação precisa "
    "(norma, artigo, dispositivo). Para decretos, informe a url do Planalto. "
    "Nunca inclua números de telefone em nenhum texto."
)

SCHEMA_VERIFICACAO = {
    "type": "object",
    "properties": {"sustenta": {"type": "boolean"}, "motivo": {"type": "string"}},
    "required": ["sustenta", "motivo"],
    "additionalProperties": False,
}

_CITACAO = {
    "type": "object",
    "properties": {
        "norma": {"type": "string"},
        "artigo": {"type": "string"},
        "dispositivo": {"type": "string"},
        "url": {"type": ["string", "null"]},
    },
    "required": ["norma", "artigo", "dispositivo", "url"],
    "additionalProperties": False,
}
SCHEMA_DICAS = {
    "type": "object",
    "properties": {
        "dicas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "trilha": {"type": "integer"},
                    "titulo": {"type": "string"},
                    "slides": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "titulo": {"type": "string"},
                                "itens": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["titulo", "itens"],
                            "additionalProperties": False,
                        },
                    },
                    "frase_story": {"type": "string"},
                    "legenda_base": {"type": "string"},
                    "afirmacoes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"texto": {"type": "string"}, "citacao": _CITACAO},
                            "required": ["texto", "citacao"],
                            "additionalProperties": False,
                        },
                    },
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                    "status": {"type": "string"},
                },
                "required": ["id", "trilha", "titulo", "slides", "frase_story",
                             "legenda_base", "afirmacoes", "hashtags", "status"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["dicas"],
    "additionalProperties": False,
}

PROMPT_DICAS = """Crie {quantidade} dicas novas para a trilha "{trilha_nome}".
Temas da trilha: {trilha_temas}

Regras:
- Dicas práticas para ME/EPP, em português do Brasil.
- Cada dica: id único no formato "<trilha>-<nn>", titulo de até 60 caracteres, de 3 a 6 slides
  (cada slide com titulo e lista de itens curtos), frase_story de até 120 caracteres,
  legenda_base, hashtags e status "pendente".
- Toda afirmação jurídica usada nos slides deve aparecer em "afirmacoes" com citação precisa:
  norma (ex.: "Lei 14.133/2021", "LC 123/2006", "Decreto 12.343/2024"), artigo (ex.: "55" ou "3-A"),
  dispositivo (ex.: "inciso I", ou "" se for o próprio artigo) e url (obrigatória para decretos:
  link do Planalto; caso contrário null).
- Não invente artigos. Não inclua números de telefone em nenhum texto."""


def encurtar(texto: str, limite: int) -> str:
    texto = " ".join(texto.split())
    if len(texto) <= limite:
        return texto
    corte = texto[: limite - 1]
    if texto[limite - 1] != " ":
        pos = corte.rfind(" ")
        corte = corte[:pos] if pos > 0 else corte
    return corte.rstrip(" ,;:.-") + "…"


def _chamar(cliente, modelo: str, sistema: str, prompt: str, max_tokens: int,
            esforco: str, schema: dict | None = None) -> tuple[str, str | None]:
    saida: dict = {"effort": esforco}
    if schema is not None:
        saida["format"] = {"type": "json_schema", "schema": schema}
    resp = cliente.messages.create(
        model=modelo,
        max_tokens=max_tokens,
        system=sistema,
        output_config=saida,
        messages=[{"role": "user", "content": prompt}],
    )
    texto = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    return texto, getattr(resp, "stop_reason", None)


def resumir_objeto(objeto: str, cliente) -> str:
    try:
        texto, _ = _chamar(cliente, MODELO_RAPIDO, SISTEMA_RESUMO,
                           f"Objeto da licitação:\n{objeto}", 1024, "low")
        r = " ".join(texto.split())
        if r and len(r) <= 90:
            return r
    except Exception:
        pass
    return encurtar(objeto, 90)


def gancho_legenda(titulo: str, legenda_base: str, cliente) -> str:
    try:
        texto, _ = _chamar(cliente, MODELO_RAPIDO, SISTEMA_GANCHO,
                           f"Título do post: {titulo}\nLegenda base:\n{legenda_base}",
                           1024, "low")
        r = " ".join(texto.split())
        if r and len(r) <= 150:
            return r
    except Exception:
        pass
    return ""


@dataclass(frozen=True)
class Verificacao:
    sustenta: bool
    motivo: str


def verificar_afirmacao(afirmacao: str, dispositivo: str, texto_lei: str, cliente) -> Verificacao:
    try:
        prompt = (f"Dispositivo: {dispositivo}\n\nTEXTO DE LEI:\n{texto_lei}\n\n"
                  f"AFIRMAÇÃO:\n{afirmacao}\n\n"
                  "O texto de lei sustenta integralmente a afirmação?")
        bruto, parada = _chamar(cliente, MODELO_RIGOROSO, SISTEMA_REVISOR, prompt, 2048,
                                "high", SCHEMA_VERIFICACAO)
        if parada in ("max_tokens", "refusal"):
            raise ValueError(f"resposta incompleta: {parada}")
        dados = json.loads(bruto)
        if not isinstance(dados["sustenta"], bool) or not isinstance(dados["motivo"], str):
            raise ValueError("formato inválido")
        return Verificacao(dados["sustenta"], dados["motivo"])
    except Exception:
        return Verificacao(False, "erro na verificação")


class ErroGeracaoDicas(Exception):
    """Falha ao gerar dicas (truncamento, recusa ou resposta inválida)."""


TAMANHO_LOTE = 5


def _gerar_lote(trilha_nome: str, trilha_temas: str, quantidade: int,
                existentes: list[str], cliente) -> list[dict]:
    prompt = PROMPT_DICAS.format(quantidade=quantidade, trilha_nome=trilha_nome,
                                 trilha_temas=trilha_temas)
    if existentes:
        prompt += ("\n- Já existem dicas com estes títulos; não repita nem reformule os temas: "
                   + "; ".join(existentes))
    bruto, parada = _chamar(cliente, MODELO_RIGOROSO, SISTEMA_DICAS, prompt, 16000,
                            "high", SCHEMA_DICAS)
    if parada == "max_tokens":
        raise ErroGeracaoDicas("A geração de dicas foi cortada por limite de tokens.")
    if parada == "refusal":
        raise ErroGeracaoDicas("O modelo recusou gerar as dicas.")
    if not bruto:
        raise ErroGeracaoDicas("A resposta do modelo veio vazia.")
    try:
        dados = json.loads(bruto)
    except ValueError as e:
        raise ErroGeracaoDicas("A resposta do modelo não é um JSON válido.") from e
    if not isinstance(dados, dict) or not isinstance(dados.get("dicas"), list):
        raise ErroGeracaoDicas('A resposta do modelo não contém a lista "dicas".')
    if not all(isinstance(d, dict) for d in dados["dicas"]):
        raise ErroGeracaoDicas("A lista de dicas contém itens inválidos.")
    return dados["dicas"]


def gerar_dicas(trilha_nome: str, trilha_temas: str, quantidade: int, cliente) -> list[dict]:
    """Gera `quantidade` dicas em lotes de até 5 chamadas; ids e status são forçados."""
    dicas: list[dict] = []
    while len(dicas) < quantidade:
        lote = _gerar_lote(trilha_nome, trilha_temas, min(TAMANHO_LOTE, quantidade - len(dicas)),
                           [str(d.get("titulo", "")) for d in dicas], cliente)
        if not lote:
            raise ErroGeracaoDicas("O modelo não devolveu nenhuma dica no lote.")
        dicas.extend(lote[: quantidade - len(dicas)])
    for n, d in enumerate(dicas, start=1):
        d["id"] = f"t{d.get('trilha', 0)}-{n:02d}"
        d["status"] = "pendente"
    return dicas


def criar_cliente(env=os.environ):
    return anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"])

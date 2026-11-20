"""Texto oficial de artigos de lei, extraído do Planalto.

Usado pela checagem jurídica automática: dado o artigo citado por uma dica,
devolve o texto vigente (sem trechos revogados/riscados) para verificação.

Erros: `ArtigoNaoEncontrado` só quando a norma/artigo não existe. Falhas de
rede/HTTP propagam como exceções do `requests` (quem chama trata qualquer erro
como "descartar a dica").
"""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

FONTES: dict[str, str] = {
    "Lei 14.133/2021": "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm",
    "LC 123/2006": "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm",
}

_CACHE: dict[str, str] = {}
_UA = {"User-Agent": "Mozilla/5.0 (compatible; licittax-bot)"}

# Início de parágrafo: "Art. 55.", "Art. 1º", "Art. 3o-A", "Art. 1.048"
_ART = re.compile(r"^Art\.?\s*(\d[\d.]*)\s*(?:[º°]|o\b)?\s*(?:-\s*([A-Za-z])\b)?")
_CABECALHO = re.compile(r"^(T[ÍI]TULO|CAP[ÍI]TULO|SE[ÇC][ÃA]O|SUBSE[ÇC][ÃA]O|LIVRO)\b", re.I)


class ArtigoNaoEncontrado(Exception):
    pass


def _chave(artigo: str) -> str:
    """'55' -> '55'; '3º-A' / '3-a' -> '3-A'; '1.048' -> '1048'."""
    m = _ART.match("Art. " + artigo.strip())
    if not m:
        raise ArtigoNaoEncontrado(f"Número de artigo inválido: {artigo!r}")
    return _formata(m)


def _formata(m: re.Match) -> str:
    num = m.group(1).replace(".", "")
    return f"{num}-{m.group(2).upper()}" if m.group(2) else num


def _limpa(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.replace("\xa0", " ")).strip()


def extrair_artigo(html: str, artigo: str) -> str:
    """Texto do `Art. <artigo>` até antes do próximo artigo/cabeçalho.

    Remove `<strike>`/`<s>` (redação revogada). Só reconhece "Art." no início
    de um parágrafo, para não confundir referências cruzadas com artigos.
    """
    alvo = _chave(artigo)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["strike", "s", "del"]):
        tag.decompose()

    partes: list[str] = []
    dentro = False
    for p in soup.find_all("p"):
        texto = _limpa(p.get_text(" "))
        if not texto:
            continue  # parágrafo que só tinha texto riscado
        m = _ART.match(texto)
        if m:
            if dentro:
                break
            if _formata(m) == alvo:
                dentro = True
        elif dentro and _CABECALHO.match(texto):
            break
        if dentro:
            partes.append(texto)
    if not partes:
        raise ArtigoNaoEncontrado(f"Art. {artigo} não encontrado")
    return "\n".join(partes)


def _baixa(url: str, sessao=None) -> str:
    if url in _CACHE:
        return _CACHE[url]
    r = (sessao or requests).get(url, headers=_UA, timeout=60)
    r.raise_for_status()
    if "charset" in r.headers.get("content-type", "").lower():
        html = r.text
    else:
        html = r.content.decode("windows-1252", errors="replace")
    _CACHE[url] = html
    return html


def texto_artigo(norma: str, artigo: str, url: str | None = None, sessao=None) -> str:
    """Texto oficial do artigo. `url` é obrigatória para normas fora de FONTES."""
    alvo = url or FONTES.get(norma)
    if not alvo:
        raise ArtigoNaoEncontrado(f"Sem fonte conhecida para {norma!r}")
    return extrair_artigo(_baixa(alvo, sessao), artigo)

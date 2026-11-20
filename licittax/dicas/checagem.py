from __future__ import annotations

import re
from dataclasses import replace
from decimal import Decimal

from licittax.ia import verificar_afirmacao, verificar_cobertura
from licittax.leis import texto_artigo
from licittax.dicas.modelo import Dica

TELEFONE = re.compile(r"\(?\d{2}\)?\s?\d{4,5}-\d{4}")


_NUM = r"(\d[\d.]*(?:,\d+)?)"
_MULT = r"(mil|milh(?:ão|ões|ao|oes))"
DINHEIRO = [
    re.compile(r"R\$\s*" + _NUM + r"(?:\s*" + _MULT + r"\b)?", re.I),
    re.compile(_NUM + r"\s*(?:" + _MULT + r"\s+)?reais\b", re.I),
]
LC123 = "LC 123/2006"


def _valores(texto: str) -> set[Decimal]:
    achados: set[Decimal] = set()
    for rx in DINHEIRO:
        for m in rx.finditer(texto):
            try:
                v = Decimal(m.group(1).rstrip(".").replace(".", "").replace(",", "."))
            except Exception:
                continue
            mult = (m.group(2) or "").lower()
            if mult == "mil":
                v *= 1000
            elif mult.startswith("milh"):
                v *= 1_000_000
            achados.add(v.normalize())
    return achados


def _publicados(d: Dica) -> list[str]:
    t = [d.titulo, d.frase_story, d.legenda_base]
    for s in d.slides:
        t.append(s.titulo)
        t.extend(s.itens)
    return t


def _textos(d: Dica) -> list[str]:
    return _publicados(d) + list(d.hashtags)


def _motivo_falha(dica: Dica, obter_texto, verificar, verificar_texto, cliente) -> str | None:
    if not 3 <= len(dica.slides) <= 6:
        return f"número de slides fora de 3 a 6 ({len(dica.slides)})"
    if len(dica.titulo) > 60:
        return "título com mais de 60 caracteres"
    if len(dica.frase_story) > 120:
        return "frase do story com mais de 120 caracteres"
    for t in _textos(dica):
        if "3157-6737" in t or TELEFONE.search(t):
            return "texto contém número de telefone"
    if not dica.afirmacoes:
        return "dica sem nenhuma afirmação com citação"
    for a in dica.afirmacoes:
        if a.citacao is None:
            return f"afirmação sem citação: {a.texto}"
    cobertos: set[Decimal] = set()
    for a in dica.afirmacoes:
        c = a.citacao
        v = _valores(a.texto)
        cobertos |= v
        norma = c.norma.strip()
        if v and not (norma.startswith("Decreto") or norma == LC123):
            return f"valor em reais sem decreto citado: {a.texto}"
    for t in _publicados(dica):
        if not _valores(t) <= cobertos:
            return f"valor em reais no texto publicado sem afirmação correspondente: {t}"
    for a in dica.afirmacoes:
        c = a.citacao
        try:
            texto = obter_texto(c.norma, c.artigo, c.url)
        except Exception as e:
            return f"não foi possível obter {c.norma}, {c.artigo}: {e}"
        try:
            r = verificar(a.texto, f"{c.norma}, {c.artigo} {c.dispositivo}".strip(),
                          texto, cliente)
        except Exception as e:
            return f"erro na verificação: {e}"
        if r.sustenta is not True:
            return f"dispositivo não sustenta a afirmação ({a.texto}): {r.motivo}"
    try:
        r = verificar_texto(chr(10).join(_publicados(dica)), [a.texto for a in dica.afirmacoes],
                            cliente)
    except Exception as e:
        return f"erro na verificação de cobertura: {e}"
    if r.sustenta is not True:
        return f"texto publicado com conteúdo não coberto: {r.motivo}"
    return None


def checar_dica(dica: Dica, obter_texto=texto_artigo, verificar=verificar_afirmacao,
                cliente=None, verificar_texto=verificar_cobertura) -> Dica:
    try:
        falha = _motivo_falha(dica, obter_texto, verificar, verificar_texto, cliente)
    except Exception as e:  # fail closed
        falha = f"erro inesperado na checagem: {e}"
    if falha:
        return replace(dica, status="descartada", motivo=falha)
    return replace(dica, status="aprovada", motivo="ok")

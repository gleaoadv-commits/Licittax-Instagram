from __future__ import annotations

import re
from dataclasses import replace

from licittax.ia import verificar_afirmacao
from licittax.leis import texto_artigo
from licittax.dicas.modelo import Dica

TELEFONE = re.compile(r"\(?\d{2}\)?\s?\d{4,5}-\d{4}")


def _textos(d: Dica) -> list[str]:
    t = [d.titulo, d.frase_story, d.legenda_base]
    for s in d.slides:
        t.append(s.titulo)
        t.extend(s.itens)
    return t


def _motivo_falha(dica: Dica, obter_texto, verificar, cliente) -> str | None:
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
    for a in dica.afirmacoes:
        c = a.citacao
        if "R$" in a.texto and not c.norma.strip().startswith("Decreto"):
            return f"valor em reais sem decreto citado: {a.texto}"
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
    return None


def checar_dica(dica: Dica, obter_texto=texto_artigo, verificar=verificar_afirmacao,
                cliente=None) -> Dica:
    try:
        falha = _motivo_falha(dica, obter_texto, verificar, cliente)
    except Exception as e:  # fail closed
        falha = f"erro inesperado na checagem: {e}"
    if falha:
        return replace(dica, status="descartada", motivo=falha)
    return replace(dica, status="aprovada", motivo="ok")

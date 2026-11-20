"""Montagem da legenda do post de feed."""
from licittax.config import Config
from licittax.dicas.modelo import Dica
from licittax.ia import encurtar

LIMITE_CARACTERES = 2200
LIMITE_HASHTAGS = 30


def _hashtags(dica: Dica, cfg: Config) -> str:
    vistas: list[str] = []
    chaves: set[str] = set()
    for h in (*dica.hashtags, *cfg.hashtags):
        h = h.strip()
        if h and h.lower() not in chaves:
            chaves.add(h.lower())
            vistas.append(h)
    return " ".join(vistas[:LIMITE_HASHTAGS])


def _juntar(blocos: list[str]) -> str:
    return "\n\n".join(b for b in blocos if b)


def montar_legenda(dica: Dica, gancho: str, cfg: Config) -> str:
    base_legal = dica.base_legal()
    fixos = [
        "📚 Base legal: " + base_legal if base_legal else "",
        cfg.cta_legenda,
        _hashtags(dica, cfg),
    ]
    gancho = gancho.strip()
    legenda = _juntar([gancho, dica.legenda_base.strip(), *fixos])
    if len(legenda) > LIMITE_CARACTERES:
        reserva = len(_juntar([gancho, "x", *fixos])) - 1  # tudo menos o texto da base
        folga = LIMITE_CARACTERES - reserva
        legenda = _juntar([gancho, encurtar(dica.legenda_base, max(folga, 1)), *fixos])
    return legenda

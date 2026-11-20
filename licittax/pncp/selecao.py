from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from licittax.config import Config
from licittax.datas import dias_uteis_entre
from licittax.pncp.client import ErroPNCP, buscar_contratacoes, tem_item_exclusivo_me_epp
from licittax.pncp.modelo import Edital

log = logging.getLogger(__name__)

MAX_CHECAGENS = 40
MODALIDADE_DISPENSA = 8


class NenhumEditalError(Exception):
    pass


@dataclass(frozen=True)
class Escolha:
    edital: Edital
    exclusivo_me_epp: bool
    prioridade: int


def _valido(e: Edital, hoje: date, ja_publicados: set[str], cfg: Config) -> bool:
    if not (e.objeto and e.uf and e.data_encerramento):
        return False
    if e.modalidade_id not in cfg.modalidades:
        return False
    if e.modalidade_id == MODALIDADE_DISPENSA and e.modo_disputa_id != cfg.modo_disputa_dispensa:
        return False
    if e.numero_controle in ja_publicados:
        return False
    return dias_uteis_entre(hoje, e.data_encerramento.date()) >= cfg.dias_uteis_minimos


def _coletar(data, hoje, ja_publicados, cfg, buscar, ufs) -> list[Edital]:
    """Busca por modalidade x UF; devolve válidos ordenados por valor desc (None por último)."""
    achados: dict[str, Edital] = {}
    falhas = total = 0
    erro: ErroPNCP | None = None
    for uf in ufs:
        for modalidade in cfg.modalidades:
            total += 1
            try:
                lista = buscar(data, modalidade, uf)
            except ErroPNCP as e:
                falhas += 1
                erro = e
                log.warning("PNCP falhou (modalidade %s, UF %s): %s", modalidade, uf, e)
                continue
            for e in lista:
                if _valido(e, hoje, ja_publicados, cfg):
                    achados.setdefault(e.numero_controle, e)
    if total and falhas == total:
        raise erro
    return sorted(
        achados.values(),
        key=lambda e: (e.valor_estimado is None, -(e.valor_estimado or 0)),
    )


def _exclusivo(e: Edital, checar_exclusivo) -> bool:
    try:
        return bool(checar_exclusivo(e))
    except ErroPNCP as ex:
        log.warning("Checagem de exclusividade falhou para %s: %s", e.numero_controle, ex)
        return False


def escolher_edital(
    data_publicacao: date,
    hoje: date,
    ja_publicados: set[str],
    cfg: Config,
    buscar=buscar_contratacoes,
    checar_exclusivo=tem_item_exclusivo_me_epp,
) -> Escolha:
    prioritarios = _coletar(data_publicacao, hoje, ja_publicados, cfg, buscar, cfg.ufs_prioritarias)
    if prioritarios:
        for e in prioritarios[:MAX_CHECAGENS]:
            if _exclusivo(e, checar_exclusivo):
                return Escolha(e, True, 1)
        return Escolha(prioritarios[0], False, 2)

    nacionais = _coletar(data_publicacao, hoje, ja_publicados, cfg, buscar, (None,))
    if nacionais:
        e = nacionais[0]
        return Escolha(e, _exclusivo(e, checar_exclusivo), 3)
    raise NenhumEditalError("Nenhum edital válido encontrado")

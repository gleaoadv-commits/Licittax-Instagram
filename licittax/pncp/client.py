from __future__ import annotations

import time
from datetime import date
from typing import Callable

import requests

from licittax.pncp.modelo import Edital, edital_de_json

URL_LISTA = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
URL_ITENS = "https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens"
TIMEOUT = 30
ESPERAS = (2, 5)  # entre a 1ª/2ª e 2ª/3ª tentativas
TENTATIVAS = 3
MAX_PAGINAS = 20
TAMANHO_PAGINA = 50
TIPO_BENEFICIO_EXCLUSIVO_ME_EPP = 1


class ErroPNCP(Exception):
    pass


def _get(sessao, url, params, espera) -> requests.Response | None:
    """GET com 3 tentativas em 429/5xx/timeout. Devolve None em HTTP 204."""
    ultimo = "sem resposta"
    for tentativa in range(TENTATIVAS):
        try:
            r = sessao.get(url, params=params, timeout=TIMEOUT)
        except (requests.Timeout, requests.ConnectionError) as e:
            ultimo = f"{type(e).__name__}"
        else:
            if r.status_code == 204:
                return None
            if r.status_code == 429 or r.status_code >= 500:
                ultimo = f"HTTP {r.status_code}"
            elif r.status_code >= 400:
                raise ErroPNCP(f"HTTP {r.status_code} em {url}")
            else:
                return r
        if tentativa < TENTATIVAS - 1:
            espera(ESPERAS[tentativa])
    raise ErroPNCP(f"PNCP falhou após {TENTATIVAS} tentativas ({ultimo}): {url}")


def _json(r: requests.Response, url: str):
    try:
        return r.json()
    except ValueError as e:
        raise ErroPNCP(f"Resposta inválida do PNCP em {url}") from e


def buscar_contratacoes(
    data: date,
    modalidade_id: int,
    uf: str | None,
    sessao: requests.Session | None = None,
    espera: Callable[[float], None] = time.sleep,
) -> list[Edital]:
    sessao = sessao or requests.Session()
    dia = data.strftime("%Y%m%d")
    editais: list[Edital] = []
    pagina, total = 1, 1
    while pagina <= total and pagina <= MAX_PAGINAS:
        params = {
            "dataInicial": dia,
            "dataFinal": dia,
            "codigoModalidadeContratacao": modalidade_id,
            "pagina": pagina,
            "tamanhoPagina": TAMANHO_PAGINA,
        }
        if uf:
            params["uf"] = uf
        r = _get(sessao, URL_LISTA, params, espera)
        if r is None:
            break
        corpo = _json(r, URL_LISTA)
        try:
            editais.extend(edital_de_json(d) for d in corpo.get("data") or [])
        except (KeyError, TypeError, ValueError) as e:
            raise ErroPNCP(f"Contratação com formato inesperado: {e!r}") from e
        total = int(corpo.get("totalPaginas") or 1)
        pagina += 1
    return editais


def tem_item_exclusivo_me_epp(
    edital: Edital,
    sessao: requests.Session | None = None,
    espera: Callable[[float], None] = time.sleep,
) -> bool:
    sessao = sessao or requests.Session()
    url = URL_ITENS.format(cnpj=edital.cnpj_orgao, ano=edital.ano, sequencial=edital.sequencial)
    r = _get(sessao, url, None, espera)
    if r is None:
        return False
    itens = _json(r, url)
    if not isinstance(itens, list) or not all(isinstance(i, dict) for i in itens):
        raise ErroPNCP(f"Itens com formato inesperado em {url}")
    return any(i.get("tipoBeneficio") == TIPO_BENEFICIO_EXCLUSIVO_ME_EPP for i in itens)

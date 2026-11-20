import json
from datetime import date
from pathlib import Path

import pytest
import responses

from licittax.pncp.client import ErroPNCP, buscar_contratacoes, tem_item_exclusivo_me_epp
from licittax.pncp.modelo import Edital

FIX = Path(__file__).parent / "fixtures"
URL_LISTA = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
DIA = date(2026, 11, 19)


def _fixture(nome):
    return json.loads((FIX / nome).read_text(encoding="utf-8"))


def _sem_espera(_segundos):
    pass


def _edital():
    return Edital("1-1-1/2026", "07722779000106", 2026, 151, "Orgao", "SP", "Santo Andre",
                  "obj", 6, 3, 10.0, None)


@responses.activate
def test_converte_campos_da_fixture():
    responses.get(URL_LISTA, json=_fixture("pncp_contratacoes.json") | {"totalPaginas": 1})
    editais = buscar_contratacoes(DIA, 6, "SP", espera=_sem_espera)
    e = editais[0]
    assert e.numero_controle
    assert e.uf == "SP"
    assert e.modalidade_id == 6
    assert e.data_encerramento is not None
    assert "uf=SP" in responses.calls[0].request.url


@responses.activate
def test_sem_uf_nao_envia_parametro():
    responses.get(URL_LISTA, json=_fixture("pncp_contratacoes.json") | {"totalPaginas": 1})
    buscar_contratacoes(DIA, 6, None, espera=_sem_espera)
    assert "uf=" not in responses.calls[0].request.url


@responses.activate
def test_valor_zero_vira_none():
    corpo = _fixture("pncp_contratacoes.json")
    corpo["data"][0]["valorTotalEstimado"] = 0
    corpo["totalPaginas"] = 1
    responses.get(URL_LISTA, json=corpo)
    assert buscar_contratacoes(DIA, 6, "SP", espera=_sem_espera)[0].valor_estimado is None


@responses.activate
def test_pagina_ate_total_paginas():
    corpo = _fixture("pncp_contratacoes.json")
    n = len(corpo["data"])
    corpo["totalPaginas"] = 3
    for _ in range(3):
        responses.get(URL_LISTA, json=corpo)
    editais = buscar_contratacoes(DIA, 6, "SP", espera=_sem_espera)
    assert len(responses.calls) == 3
    assert len(editais) == 3 * n


@responses.activate
def test_204_retorna_lista_vazia():
    responses.get(URL_LISTA, status=204)
    assert buscar_contratacoes(DIA, 6, "SP", espera=_sem_espera) == []


@responses.activate
def test_tenta_de_novo_em_429_e_500():
    corpo = _fixture("pncp_contratacoes.json") | {"totalPaginas": 1}
    responses.get(URL_LISTA, status=500)
    responses.get(URL_LISTA, status=429)
    responses.get(URL_LISTA, json=corpo)
    esperas = []
    editais = buscar_contratacoes(DIA, 6, "SP", espera=esperas.append)
    assert len(responses.calls) == 3
    assert editais
    assert esperas == [2, 5]


@responses.activate
def test_falha_apos_3_tentativas():
    for _ in range(3):
        responses.get(URL_LISTA, status=500)
    with pytest.raises(ErroPNCP):
        buscar_contratacoes(DIA, 6, "SP", espera=_sem_espera)
    assert len(responses.calls) == 3


@responses.activate
def test_erro_4xx_nao_repete():
    responses.get(URL_LISTA, status=400)
    with pytest.raises(ErroPNCP):
        buscar_contratacoes(DIA, 6, "SP", espera=_sem_espera)
    assert len(responses.calls) == 1


@responses.activate
def test_limite_de_20_paginas():
    corpo = _fixture("pncp_contratacoes.json") | {"totalPaginas": 99}
    for _ in range(30):
        responses.get(URL_LISTA, json=corpo)
    buscar_contratacoes(DIA, 6, "SP", espera=_sem_espera)
    assert len(responses.calls) == 20


@responses.activate
def test_exclusivo_me_epp():
    itens = _fixture("pncp_itens.json")
    url = "https://pncp.gov.br/api/pncp/v1/orgaos/07722779000106/compras/2026/151/itens"
    responses.get(url, json=itens)
    assert tem_item_exclusivo_me_epp(_edital(), espera=_sem_espera) is True


@responses.activate
def test_sem_exclusividade_me_epp():
    itens = [{"numeroItem": 1, "tipoBeneficio": 4}, {"numeroItem": 2, "tipoBeneficio": 5}]
    responses.get("https://pncp.gov.br/api/pncp/v1/orgaos/07722779000106/compras/2026/151/itens",
                  json=itens)
    assert tem_item_exclusivo_me_epp(_edital(), espera=_sem_espera) is False

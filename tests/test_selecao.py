from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest

from licittax.config import Config
from licittax.datas import BRASILIA
from licittax.pncp.client import ErroPNCP
from licittax.pncp.modelo import Edital
from licittax.pncp.selecao import Escolha, NenhumEditalError, escolher_edital

HOJE = date(2026, 11, 20)  # sexta
PUB = date(2026, 11, 19)
CFG = Config(
    whatsapp="x", cta_story="x", cta_legenda="x",
    ufs_prioritarias=("SP", "MG", "RJ"), modalidades=(6, 4, 8),
    modo_disputa_dispensa=4, dias_uteis_minimos=5,
    inicio_rotacao=date(2026, 1, 1), graph_versao="v21.0", hashtags=(), ensaio=False,
)


def ed(num, uf="SP", valor=1000.0, modalidade=6, modo=None, objeto="Objeto", dias=14, **kw):
    enc = datetime(2026, 11, 20, 10, tzinfo=BRASILIA) + timedelta(days=dias)
    base = Edital(
        numero_controle=num, cnpj_orgao="1", ano=2026, sequencial=1, orgao="O", uf=uf,
        municipio="M", objeto=objeto, modalidade_id=modalidade, modo_disputa_id=modo,
        valor_estimado=valor, data_encerramento=enc,
    )
    return replace(base, **kw)


def fake_buscar(tabela):
    """tabela: {(modalidade, uf): lista | Exception}"""
    chamadas = []

    def buscar(data, modalidade_id, uf):
        chamadas.append((modalidade_id, uf))
        r = tabela.get((modalidade_id, uf), [])
        if isinstance(r, Exception):
            raise r
        return r

    buscar.chamadas = chamadas
    return buscar


def escolher(tabela, exclusivos=(), ja=frozenset()):
    return escolher_edital(
        PUB, HOJE, set(ja), CFG, buscar=fake_buscar(tabela),
        checar_exclusivo=lambda e: e.numero_controle in exclusivos,
    )


def test_prefere_prioritaria_exclusiva_mesmo_com_valor_menor():
    t = {(6, "SP"): [ed("sp", "SP", 1_000_000)], (6, "MG"): [ed("mg", "MG", 100_000)]}
    r = escolher(t, exclusivos={"mg"})
    assert (r.edital.numero_controle, r.prioridade, r.exclusivo_me_epp) == ("mg", 1, True)


def test_sem_exclusivo_pega_maior_valor_prioritario():
    t = {(6, "SP"): [ed("sp", "SP", 1_000_000)], (6, "MG"): [ed("mg", "MG", 100_000)]}
    r = escolher(t)
    assert (r.edital.numero_controle, r.prioridade, r.exclusivo_me_epp) == ("sp", 2, False)


def test_cai_para_nacional_so_sem_prioritarias():
    t = {(6, "SP"): [ed("sp")]}
    b = fake_buscar(t)
    escolher_edital(PUB, HOJE, set(), CFG, buscar=b, checar_exclusivo=lambda e: False)
    assert not any(uf is None for _, uf in b.chamadas)

    t = {(6, None): [ed("pr", "PR", 5), ed("ba", "BA", 50)]}
    r = escolher(t, exclusivos={"ba"})
    assert (r.edital.numero_controle, r.prioridade, r.exclusivo_me_epp) == ("ba", 3, True)


def test_descarta_dispensa_sem_disputa():
    t = {(8, "SP"): [ed("d5", modalidade=8, modo=5), ed("d4", modalidade=8, modo=4, valor=1)]}
    assert escolher(t).edital.numero_controle == "d4"
    with pytest.raises(NenhumEditalError):
        escolher({(8, "SP"): [ed("d5", modalidade=8, modo=5)]})


def test_descarta_prazo_curto():
    # encerra em 4 dias uteis (qui 26/11 -> hoje sex 20: seg,ter,qua,qui = 4)
    t = {(6, "SP"): [ed("curto", dias=6), ed("ok", dias=7, valor=1)]}
    assert escolher(t).edital.numero_controle == "ok"


def test_descarta_ja_publicado_e_sem_objeto():
    t = {(6, "SP"): [ed("a"), ed("b", objeto=None), ed("c", uf=None), ed("d", data_encerramento=None), ed("e", valor=1)]}
    assert escolher(t, ja={"a"}).edital.numero_controle == "e"


def test_valor_none_vai_para_o_fim():
    t = {(6, "SP"): [ed("n", valor=None), ed("v", valor=1.0)]}
    assert escolher(t).edital.numero_controle == "v"
    assert escolher({(6, "SP"): [ed("n", valor=None)]}).edital.numero_controle == "n"


def test_nenhum_valido_levanta_erro():
    with pytest.raises(NenhumEditalError):
        escolher({})


def test_falha_parcial_do_pncp_continua():
    t = {(6, "SP"): ErroPNCP("x"), (6, "MG"): [ed("mg", "MG")]}
    assert escolher(t).edital.numero_controle == "mg"


def test_falha_total_do_pncp_propaga():
    class B:
        def __call__(self, *a):
            raise ErroPNCP("fora")

    with pytest.raises(ErroPNCP):
        escolher_edital(PUB, HOJE, set(), CFG, buscar=B(), checar_exclusivo=lambda e: False)


def test_checa_no_maximo_40():
    editais = [ed(f"e{i}", valor=1000 - i) for i in range(60)]
    n = []

    def chk(e):
        n.append(1)
        return False

    escolher_edital(PUB, HOJE, set(), CFG, buscar=fake_buscar({(6, "SP"): editais}), checar_exclusivo=chk)
    assert len(n) == 40

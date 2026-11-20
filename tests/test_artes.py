from datetime import date, datetime

import pytest
from PIL import Image

from licittax.artes.render import (
    TextoEstourado,
    arte_story_dica,
    arte_story_edital,
    artes_carrossel,
    contexto_story_edital,
    contextos_carrossel,
    formatar_reais,
    html_de,
)
from licittax.config import Config
from licittax.datas import BRASILIA
from licittax.dicas.modelo import Afirmacao, Citacao, Dica, Slide
from licittax.pncp.modelo import Edital
from licittax.pncp.selecao import Escolha

CFG = Config(
    whatsapp="(31) 3157-6737", cta_story="Quer participar? Fale com a Licittax",
    cta_legenda="x", ufs_prioritarias=("SP", "MG", "RJ"), modalidades=(6, 4, 8),
    modo_disputa_dispensa=4, dias_uteis_minimos=5, inicio_rotacao=date(2026, 1, 1),
    graph_versao="v23.0", hashtags=(), ensaio=False,
)


def edital(valor=1234567.89):
    return Edital(
        numero_controle="1-1-1/2026", cnpj_orgao="1", ano=2026, sequencial=1,
        orgao="MUNICÍPIO DE BELO HORIZONTE", uf="MG", municipio="Belo Horizonte",
        objeto="Aquisição de material", modalidade_id=6, modo_disputa_id=None,
        valor_estimado=valor, data_encerramento=datetime(2026, 12, 5, 9, tzinfo=BRASILIA),
    )


def dica(n_slides=3, titulo="Prazos mínimos para propostas"):
    return Dica(
        id="d1", trilha=1, titulo=titulo,
        slides=tuple(Slide(f"Slide {i}", ("Item um", "Item dois")) for i in range(1, n_slides + 1)),
        frase_story="O prazo mínimo para bens é de 8 dias úteis.",
        legenda_base="x",
        afirmacoes=(Afirmacao("a", Citacao("Lei 14.133/2021", "art. 55")),),
        hashtags=(),
    )


def test_story_edital_tem_whatsapp_e_selo():
    html = html_de("story_edital.html.j2",
                   contexto_story_edital(Escolha(edital(), True, 1), "Compra de papel", CFG))
    assert "(31) 3157-6737" in html
    assert "EXCLUSIVO ME/EPP" in html
    assert "Compra de papel" in html
    assert "05/12/2026" in html
    assert "Belo Horizonte/MG" in html


def test_story_edital_sem_selo_quando_nao_exclusivo():
    html = html_de("story_edital.html.j2",
                   contexto_story_edital(Escolha(edital(), False, 2), "Compra", CFG))
    assert "EXCLUSIVO ME/EPP" not in html


def test_story_edital_sem_valor_omite_linha():
    html = html_de("story_edital.html.j2",
                   contexto_story_edital(Escolha(edital(None), False, 2), "Compra", CFG))
    assert "Valor estimado" not in html


def test_formata_valor_em_reais():
    assert formatar_reais(1234567.89) == "R$ 1.234.567,89"
    assert formatar_reais(50) == "R$ 50,00"


def test_carrossel_nunca_tem_whatsapp():
    for template, ctx in contextos_carrossel(dica()):
        assert "3157-6737" not in html_de(template, ctx)


def test_carrossel_tem_capa_slides_e_final(tmp_path):
    caminhos = artes_carrossel(dica(3), tmp_path)
    assert len(caminhos) == 5
    assert all(p.exists() for p in caminhos)
    contextos = contextos_carrossel(dica(3))
    assert "Confira a legenda!" in html_de(*contextos[-1])
    assert "Lei 14.133/2021, art. 55" in html_de(*contextos[-2])  # base legal no último slide
    assert "Lei 14.133/2021, art. 55" not in html_de(*contextos[1])


def test_jpeg_no_tamanho_certo(tmp_path):
    story = arte_story_edital(Escolha(edital(), True, 1), "Compra de papel", CFG, tmp_path)
    story_dica = arte_story_dica(dica(), CFG, tmp_path)
    feed = artes_carrossel(dica(1), tmp_path)[0]
    for caminho, tamanho in ((story, (1080, 1920)), (story_dica, (1080, 1920)),
                             (feed, (1080, 1350))):
        with Image.open(caminho) as img:
            assert img.format == "JPEG"
            assert img.size == tamanho


def test_texto_gigante_estoura(tmp_path):
    with pytest.raises(TextoEstourado):
        artes_carrossel(dica(1, titulo="Muito texto " * 50), tmp_path)

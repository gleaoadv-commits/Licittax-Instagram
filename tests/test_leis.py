from pathlib import Path

import pytest
import responses

from licittax import leis
from licittax.leis import ArtigoNaoEncontrado, extrair_artigo, texto_artigo

FIXTURE = Path(__file__).parent / "fixtures" / "l14133_trecho.html"


@pytest.fixture
def html():
    # Planalto serve windows-1252; o fixture preserva a codificação original.
    return FIXTURE.read_bytes().decode("windows-1252")


def test_extrai_art_55_sem_invadir_56(html):
    texto = extrair_artigo(html, "55")
    assert texto.startswith("Art. 55")
    assert "8 (oito) dias úteis" in texto
    assert "Art. 56" not in texto
    assert "modo de disputa" not in texto


def test_art_54_nao_traz_55(html):
    texto = extrair_artigo(html, "54")
    assert "A publicidade do edital" in texto
    assert "Os prazos mínimos" not in texto


def test_ignora_texto_riscado(html):
    texto = extrair_artigo(html, "87")
    # redação nova (não riscada) presente; redação revogada ausente
    assert "e de contratados" in texto
    assert "na forma disposta em regulamento" not in texto
    assert "Vide Decreto" not in extrair_artigo(html, "1")


def test_ignora_riscado_inline():
    h = "<p>Art. 5º Texto novo <strike>texto revogado</strike> fim.</p><p>Art. 6º Outro.</p>"
    t = extrair_artigo(h, "5")
    assert "revogado" not in t and "Texto novo" in t and "Outro" not in t
    h = "<p>Art. 5º Vale <s>morto</s> isto.</p>"
    assert "morto" not in extrair_artigo(h, "5")


def test_reconhece_ordinal(html):
    texto = extrair_artigo(html, "1")
    assert texto.startswith("Art. 1")
    assert "Esta Lei estabelece normas gerais" in texto
    assert "Art. 2" not in texto


def test_variantes_de_numeracao():
    h = (
        "<p>Art.\xa03\xba-A\xa0Texto A.</p>"
        "<p>Art. 3o Texto ordinal o.</p>"
        "<p>Art. 4. Ponto.</p>"
        "<p>Art. 10 Dez.</p>"
        "<p>Art. 1.048 Mil.</p>"
    )
    assert "Texto A" in extrair_artigo(h, "3-A")
    assert "Texto ordinal" in extrair_artigo(h, "3")
    assert "Texto A" not in extrair_artigo(h, "3")
    assert "Ponto" in extrair_artigo(h, "4")
    assert "Dez" in extrair_artigo(h, "10")
    assert "Mil" in extrair_artigo(h, "1048")


def test_para_em_capitulo():
    h = "<p>Art. 7º Sete.</p><p>CAPÍTULO II</p><p>DA COISA</p><p>Art. 8º Oito.</p>"
    t = extrair_artigo(h, "7")
    assert "Sete" in t and "CAPÍTULO" not in t


def test_referencia_cruzada_nao_corta_artigo():
    h = "<p>Art. 7º Conforme o art. 8º desta Lei.</p><p>§ 1º Mais.</p><p>Art. 8º Oito.</p>"
    t = extrair_artigo(h, "7")
    assert "§ 1º Mais" in t and "Oito" not in t


def test_artigo_inexistente_levanta(html):
    with pytest.raises(ArtigoNaoEncontrado):
        extrair_artigo(html, "999")


@responses.activate
def test_cache_baixa_uma_vez(html):
    leis._CACHE.clear()
    url = leis.FONTES["Lei 14.133/2021"]
    responses.add(responses.GET, url, body=FIXTURE.read_bytes(), content_type="text/html")
    a = texto_artigo("Lei 14.133/2021", "55")
    b = texto_artigo("Lei 14.133/2021", "55")
    assert a == b and "8 (oito) dias úteis" in a
    assert len(responses.calls) == 1


@responses.activate
def test_url_explicita_para_decreto():
    leis._CACHE.clear()
    url = "https://exemplo.gov.br/decreto.htm"
    responses.add(responses.GET, url, body="<p>Art. 1º Do decreto.</p>".encode("utf-8"),
                  content_type="text/html; charset=utf-8")
    assert "Do decreto" in texto_artigo("Decreto 1/2020", "1", url=url)


def test_norma_sem_url_levanta():
    with pytest.raises(ArtigoNaoEncontrado):
        texto_artigo("Decreto 9/2020", "1")


@responses.activate
def test_erro_de_rede_propaga():
    leis._CACHE.clear()
    url = leis.FONTES["LC 123/2006"]
    responses.add(responses.GET, url, status=500)
    with pytest.raises(Exception) as e:
        texto_artigo("LC 123/2006", "3")
    assert not isinstance(e.value, ArtigoNaoEncontrado)

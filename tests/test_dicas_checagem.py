from dataclasses import replace

from licittax.dicas.checagem import checar_dica
from licittax.dicas.modelo import Afirmacao, Citacao, Dica, Slide
from licittax.leis import ArtigoNaoEncontrado
from licittax.ia import Verificacao

CIT = Citacao("Lei 14.133/2021", "art. 55", "§ 1º", "http://x")


def dica(**kw):
    base = dict(
        id="t1-01", trilha=1, titulo="Prazo de propostas",
        slides=(Slide("a", ("1",)), Slide("b", ("2",)), Slide("c", ("3",))),
        frase_story="Fique de olho nos prazos.", legenda_base="Legenda.",
        afirmacoes=(Afirmacao("Prazo mínimo de 8 dias úteis.", CIT),), hashtags=("#licitacao",))
    base.update(kw)
    return Dica(**base)


def texto_ok(norma, artigo, url=None):
    return "texto da lei"


def sim(afirmacao, dispositivo, texto, cliente):
    return Verificacao(True, "ok")


def cob_ok(texto, afirmacoes, cliente):
    return Verificacao(True, "ok")


def cob_nao(texto, afirmacoes, cliente):
    return Verificacao(False, "conteúdo não coberto")


def nao(afirmacao, dispositivo, texto, cliente):
    return Verificacao(False, "não confere")


def test_aprova_dica_valida():
    r = checar_dica(dica(), texto_ok, sim, verificar_texto=cob_ok)
    assert r.status == "aprovada"


def test_descarta_afirmacao_sem_citacao():
    d = dica(afirmacoes=(Afirmacao("x", None),))
    r = checar_dica(d, texto_ok, sim, verificar_texto=cob_ok)
    assert r.status == "descartada" and "citação" in r.motivo


def test_descarta_valor_em_reais_sem_decreto():
    d = dica(afirmacoes=(Afirmacao("Limite de R$ 50 mil.", CIT),))
    assert checar_dica(d, texto_ok, sim, verificar_texto=cob_ok).status == "descartada"
    d = dica(afirmacoes=(Afirmacao("Limite de R$ 50 mil.", Citacao("LC 123/2006", "art. 48")),))
    assert checar_dica(d, texto_ok, sim, verificar_texto=cob_ok).status == "aprovada"


def test_descarta_quando_verificador_nega():
    assert checar_dica(dica(), texto_ok, nao, verificar_texto=cob_ok).status == "descartada"


def test_descarta_quando_artigo_nao_existe():
    def falha(*a, **k):
        raise ArtigoNaoEncontrado("x")
    assert checar_dica(dica(), falha, sim, verificar_texto=cob_ok).status == "descartada"


def test_descarta_erro_de_rede():
    def falha(*a, **k):
        raise ConnectionError("fora")
    r = checar_dica(dica(), falha, sim, verificar_texto=cob_ok)
    assert r.status == "descartada" and r.motivo


def test_descarta_telefone_no_texto():
    for d in (dica(frase_story="Ligue (31) 3157-6737"), dica(legenda_base="Fale 11 98765-4321"),
              dica(slides=(Slide("a", ("tel 3157-6737",)),) * 3)):
        assert checar_dica(d, texto_ok, sim, verificar_texto=cob_ok).status == "descartada"


def test_descarta_slides_fora_de_3_a_6():
    s = Slide("a", ("1",))
    assert checar_dica(dica(slides=(s, s)), texto_ok, sim, verificar_texto=cob_ok).status == "descartada"
    assert checar_dica(dica(slides=(s,) * 7), texto_ok, sim, verificar_texto=cob_ok).status == "descartada"
    assert checar_dica(dica(slides=(s,) * 6), texto_ok, sim, verificar_texto=cob_ok).status == "aprovada"


def test_descarta_titulos_longos():
    assert checar_dica(dica(titulo="x" * 61), texto_ok, sim, verificar_texto=cob_ok).status == "descartada"
    assert checar_dica(dica(frase_story="x" * 121), texto_ok, sim, verificar_texto=cob_ok).status == "descartada"


def test_cliente_repassado():
    vistos = []
    def v(a, d, t, c):
        vistos.append(c)
        return Verificacao(True, "")
    checar_dica(dica(), texto_ok, v, cliente="C", verificar_texto=cob_ok)
    assert vistos == ["C"]


def test_nao_altera_original():
    d = dica()
    checar_dica(d, texto_ok, nao, verificar_texto=cob_ok)
    assert d.status == "pendente"


def test_base_legal_sem_repeticao():
    d = dica(afirmacoes=(
        Afirmacao("a", Citacao("Lei 14.133/2021", "art. 55")),
        Afirmacao("b", Citacao("LC 123/2006", "art. 48")),
        Afirmacao("c", Citacao("Lei 14.133/2021", "art. 55")),
        Afirmacao("d", None)))
    assert d.base_legal() == "Lei 14.133/2021, art. 55; LC 123/2006, art. 48"


def test_base_legal_prefixo_e_dispositivo():
    d = dica(afirmacoes=(
        Afirmacao("a", Citacao("Lei 14.133/2021", "87")),
        Afirmacao("b", Citacao("Lei 14.133/2021", "Art. 75", "inciso II")),
        Afirmacao("c", Citacao("LC 123/2006", "art. 48")),
        Afirmacao("d", Citacao("Lei 14.133/2021", "87"))))
    assert d.base_legal() == ("Lei 14.133/2021, art. 87; Lei 14.133/2021, Art. 75, inciso II; "
                              "LC 123/2006, art. 48")


def test_descarta_quando_cobertura_nega():
    r = checar_dica(dica(), texto_ok, sim, verificar_texto=cob_nao)
    assert r.status == "descartada" and "não coberto" in r.motivo


def test_cobertura_chamada_por_ultimo_e_so_se_demais_passam():
    chamadas = []
    def cob(t, a, c):
        chamadas.append(1)
        return Verificacao(True, "")
    checar_dica(dica(), texto_ok, nao, verificar_texto=cob)
    assert chamadas == []


def test_descarta_afirmacoes_vazias():
    assert checar_dica(dica(afirmacoes=()), texto_ok, sim, verificar_texto=cob_ok).status == "descartada"


def test_descarta_quando_verificar_levanta():
    def boom(*a):
        raise RuntimeError("x")
    assert checar_dica(dica(), texto_ok, boom, verificar_texto=cob_ok).status == "descartada"


def test_descarta_quando_cobertura_levanta():
    def boom(*a):
        raise RuntimeError("x")
    assert checar_dica(dica(), texto_ok, sim, verificar_texto=boom).status == "descartada"


def test_descarta_hashtag_com_telefone():
    d = dica(hashtags=("#31 3157-6737",))
    assert checar_dica(d, texto_ok, sim, verificar_texto=cob_ok).status == "descartada"


DEC = Citacao("Decreto 12.343/2024", "art. 1")


def test_descarta_valor_em_slide_sem_afirmacao():
    d = dica(slides=(Slide("a", ("Limite de R$ 50 mil",)),) * 3)
    assert checar_dica(d, texto_ok, sim, verificar_texto=cob_ok).status == "descartada"
    d = dica(slides=(Slide("a", ("Limite de 50 mil reais",)),) * 3)
    assert checar_dica(d, texto_ok, sim, verificar_texto=cob_ok).status == "descartada"


def test_valor_em_slide_coberto_por_afirmacao_com_lc123():
    d = dica(slides=(Slide("a", ("Limite de R$ 50.000,00",)),) * 3,
             afirmacoes=(Afirmacao("Limite de 50 mil reais.", Citacao("LC 123/2006", "art. 48")),))
    assert checar_dica(d, texto_ok, sim, verificar_texto=cob_ok).status == "aprovada"


def test_valor_com_lei_14133_sem_decreto_descarta():
    d = dica(afirmacoes=(Afirmacao("Limite de R$ 50 mil.", CIT),))
    assert checar_dica(d, texto_ok, sim, verificar_texto=cob_ok).status == "descartada"


def test_valor_com_lc123_passa():
    d = dica(slides=(Slide("a", ("Exclusivo até R$ 80 mil",)),) * 3,
             afirmacoes=(Afirmacao("Exclusividade até R$ 80 mil.", Citacao("LC 123/2006", "art. 48")),))
    assert checar_dica(d, texto_ok, sim, verificar_texto=cob_ok).status == "aprovada"


def test_valor_com_qualquer_decreto_descarta():
    d = dica(afirmacoes=(Afirmacao("Limite de R$ 50 mil.", DEC),))
    r = checar_dica(d, texto_ok, sim, verificar_texto=cob_ok)
    assert r.status == "descartada" and "decreto" in r.motivo

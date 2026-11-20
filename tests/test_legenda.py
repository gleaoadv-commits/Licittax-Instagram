from datetime import date

from licittax.config import Config
from licittax.dicas.modelo import Afirmacao, Citacao, Dica, Slide
from licittax.legenda import montar_legenda

CFG = Config(
    whatsapp="(31) 3157-6737", cta_story="x",
    cta_legenda="Fale no WhatsApp (31) 3157-6737",
    ufs_prioritarias=("SP",), modalidades=(6,), modo_disputa_dispensa=4,
    dias_uteis_minimos=5, inicio_rotacao=date(2026, 1, 1), graph_versao="v23.0",
    hashtags=("#licitacao", "#licittax"), ensaio=False,
)


def dica(base="Texto base.", hashtags=("#me", "#Licitacao")):
    return Dica(
        id="t1-01", trilha=1, titulo="T", slides=(Slide("a", ("b",)),), frase_story="f",
        legenda_base=base,
        afirmacoes=(Afirmacao("x", Citacao("Lei 14.133/2021", "55")),),
        hashtags=tuple(hashtags), status="aprovada",
    )


def test_legenda_termina_com_cta_e_hashtags():
    t = montar_legenda(dica(), "Gancho!", CFG)
    assert "(31) 3157-6737" in t
    assert t.index("(31) 3157-6737") < t.index("#me")
    assert t.startswith("Gancho!\n\nTexto base.\n\n📚 Base legal: Lei 14.133/2021, 55\n\n")
    assert t.endswith("#me #Licitacao #licittax")


def test_legenda_sem_gancho_nao_tem_linha_vazia_extra():
    t = montar_legenda(dica(), "", CFG)
    assert t.startswith("Texto base.")
    assert "\n\n\n" not in t


def test_legenda_respeita_2200_e_30_hashtags():
    muitas = [f"#h{i}" for i in range(50)]
    t = montar_legenda(dica(base="palavra " * 600, hashtags=muitas), "G", CFG)
    assert len(t) <= 2200
    assert len(t.splitlines()[-1].split()) == 30
    assert "(31) 3157-6737" in t

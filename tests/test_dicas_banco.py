from datetime import date, timedelta

import pytest

from licittax.dicas.banco import carregar_banco, dica_do_dia, salvar_banco
from licittax.dicas.modelo import Afirmacao, Citacao, Dica, Slide

INICIO = date(2026, 12, 1)


def d(trilha, n, status="aprovada"):
    return Dica(id=f"t{trilha}-{n:02d}", trilha=trilha, titulo=f"T{trilha}{n}",
                slides=(Slide("a", ("i",)),), frase_story="f", legenda_base="l",
                afirmacoes=(Afirmacao("x", Citacao("Lei 14.133/2021", "art. 1", "", None)),
                            Afirmacao("y", None)),
                hashtags=("#a",), status=status)


def banco(n=2):
    return [d(t, i) for t in range(1, 7) for i in range(1, n + 1)]


def test_ida_e_volta_json(tmp_path):
    b = banco() + [replace_status(d(1, 9), "descartada")]
    p = tmp_path / "sub" / "b.json"
    salvar_banco(b, p)
    assert carregar_banco(p) == b


def replace_status(x, s):
    from dataclasses import replace
    return replace(x, status=s, motivo="m")


def test_from_dict_aceita_formato_do_gerador():
    x = Dica.from_dict({"id": "t1-01", "trilha": 1, "titulo": "t",
                        "slides": [{"titulo": "a", "itens": ["i"]}], "frase_story": "f",
                        "legenda_base": "l", "afirmacoes": [{"texto": "x", "citacao": None}],
                        "hashtags": ["#a"], "status": "pendente"})
    assert x.afirmacoes[0].citacao is None and x.slides[0].itens == ("i",)


def test_dica_do_dia_alterna_trilhas():
    b = banco()
    ts = [dica_do_dia(b, INICIO + timedelta(days=i), INICIO).trilha for i in range(7)]
    assert ts == [1, 2, 3, 4, 5, 6, 1]


def test_dica_do_dia_avanca_dentro_da_trilha():
    b = banco()
    a, c = dica_do_dia(b, INICIO, INICIO), dica_do_dia(b, INICIO + timedelta(days=6), INICIO)
    assert a.trilha == c.trilha == 1 and a.id != c.id


def test_ignora_descartadas_e_pula_trilha_vazia():
    b = [x for x in banco() if x.trilha != 2]
    b.append(replace_status(d(2, 1), "descartada"))
    assert dica_do_dia(b, INICIO + timedelta(days=1), INICIO).trilha == 3
    assert dica_do_dia(b, INICIO + timedelta(days=1), INICIO).status == "aprovada"


def test_mesmo_dia_mesma_dica():
    b = banco()
    assert dica_do_dia(b, INICIO, INICIO) == dica_do_dia(list(reversed(b)), INICIO, INICIO)


def test_dia_anterior_ao_inicio():
    assert dica_do_dia(banco(), INICIO - timedelta(days=1), INICIO).trilha == 6


def test_sem_aprovadas():
    with pytest.raises(ValueError):
        dica_do_dia([replace_status(d(1, 1), "descartada")], INICIO, INICIO)

import json

from licittax.estado import carregar_estado, salvar_estado


def test_estado_ida_e_volta(tmp_path):
    p = tmp_path / "estado.json"
    salvar_estado({"b", "a"}, p)
    assert json.loads(p.read_text())["editais_publicados"] == ["a", "b"]
    assert carregar_estado(p) == {"a", "b"}


def test_estado_inexistente_e_vazio(tmp_path):
    assert carregar_estado(tmp_path / "nao.json") == set()

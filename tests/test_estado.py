import json

from licittax.estado import carregar_estado, salvar_estado


def test_estado_ida_e_volta(tmp_path):
    p = tmp_path / "estado.json"
    salvar_estado({"b", "a"}, p)
    assert json.loads(p.read_text())["editais_publicados"] == ["a", "b"]
    assert carregar_estado(p) == {"a", "b"}


def test_estado_inexistente_e_vazio(tmp_path):
    assert carregar_estado(tmp_path / "nao.json") == set()


def test_marcas_de_publicacao_preservam_editais(tmp_path):
    from licittax.estado import ja_publicado, marcar_publicado
    p = tmp_path / "estado.json"
    salvar_estado({"a"}, p)
    marcar_publicado(p, "2026-11-21-post")
    assert ja_publicado(p, "2026-11-21-post") and not ja_publicado(p, "2026-11-21-edital")
    salvar_estado({"a", "b"}, p)
    assert ja_publicado(p, "2026-11-21-post")
    assert carregar_estado(p) == {"a", "b"}

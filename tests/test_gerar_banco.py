from dataclasses import replace

from licittax.dicas import gerar_banco
from licittax.dicas.banco import carregar_banco, salvar_banco
from licittax.dicas.modelo import Afirmacao, Citacao, Dica, Slide
from licittax.dicas.trilhas import TRILHAS
from licittax.ia import ErroGeracaoDicas


def _dica(id_, trilha, status="aprovada"):
    return Dica(id=id_, trilha=trilha, titulo=id_,
                slides=(Slide("a", ("1",)),) * 3, frase_story="f", legenda_base="l",
                afirmacoes=(Afirmacao("x", Citacao("Lei 14.133/2021", "1")),),
                hashtags=(), status=status, motivo="ok")


def _bruta(n, trilha):
    return {"titulo": f"titulo {trilha}-{n}", "slides": [{"titulo": "a", "itens": ["1"]}] * 3,
            "frase_story": "f", "legenda_base": "l", "afirmacoes": [], "hashtags": []}


def _preparar(monkeypatch, tmp_path, existentes, gerar, aprovar):
    caminho = tmp_path / "banco.json"
    salvar_banco(existentes, caminho)
    monkeypatch.setattr(gerar_banco, "CAMINHO", caminho)
    monkeypatch.setattr(gerar_banco, "criar_cliente", lambda: None)
    monkeypatch.setattr(gerar_banco, "gerar_dicas", gerar)
    monkeypatch.setattr(gerar_banco, "checar_dica", aprovar)
    return caminho


def test_salva_apos_cada_trilha_e_preserva_nao_processadas(monkeypatch, tmp_path):
    existentes = [_dica(f"t{t.numero}-old", t.numero) for t in TRILHAS]
    snapshots = []
    caminho_box = {}

    def gerar(nome, temas, n, cliente):
        # estado do arquivo no inicio de cada trilha (reflete o save da anterior)
        snapshots.append(carregar_banco(caminho_box["c"]))
        trilha = next(t for t in TRILHAS if t.nome == nome).numero
        return [_bruta(i, trilha) for i in range(10)]

    caminho_box["c"] = _preparar(monkeypatch, tmp_path, existentes, gerar,
                                 lambda d, cliente=None: replace(d, status="aprovada", motivo="ok"))
    assert gerar_banco.main() == 0
    # antes da 2a trilha, a 1a ja foi salva e as demais mantem os antigos
    ids = {d.id for d in snapshots[1]}
    assert "t1-01" in ids and "t1-old" in ids  # novas sao anexadas as existentes
    assert all(f"t{t.numero}-old" in ids for t in TRILHAS[1:])
    final = carregar_banco(caminho_box["c"])
    assert all(f"t{t.numero}-old" in {d.id for d in final} for t in TRILHAS)


def test_trilha_com_poucas_aprovadas_mantem_existentes_e_sai_1(monkeypatch, tmp_path):
    existentes = [_dica(f"t{t.numero}-old", t.numero) for t in TRILHAS]

    def aprovar(d, cliente=None):
        if d.trilha == 2:
            return replace(d, status="descartada", motivo="x")
        return replace(d, status="aprovada", motivo="ok")

    caminho = _preparar(monkeypatch, tmp_path, existentes,
                        lambda nome, temas, n, c: [_bruta(i, next(t for t in TRILHAS if t.nome == nome).numero)
                                                   for i in range(10)],
                        aprovar)
    assert gerar_banco.main() == 1
    final = carregar_banco(caminho)
    t2 = [d for d in final if d.trilha == 2]
    assert [d.id for d in t2] == ["t2-old"]


def test_trilha_com_falha_de_geracao_mantem_existentes(monkeypatch, tmp_path):
    existentes = [_dica("t1-old", 1)]

    def gerar(nome, temas, n, c):
        raise ErroGeracaoDicas("x")

    caminho = _preparar(monkeypatch, tmp_path, existentes, gerar, lambda d, cliente=None: d)
    assert gerar_banco.main() == 1
    assert [d.id for d in carregar_banco(caminho)] == ["t1-old"]


# ---- execucao incremental ----

def test_parse_args_padroes_e_valores():
    a = gerar_banco.parse_args([])
    assert a.trilhas == [1, 2, 3, 4, 5, 6]
    assert (a.candidatas, a.max_aprovadas, a.min_aprovadas) == (20, 15, 8)
    a = gerar_banco.parse_args(["--trilhas", "3,1", "--candidatas", "6",
                                "--max-aprovadas", "5", "--min-aprovadas", "1"])
    assert a.trilhas == [1, 3]
    assert (a.candidatas, a.max_aprovadas, a.min_aprovadas) == (6, 5, 1)


def test_parse_args_trilha_invalida():
    import pytest
    with pytest.raises(SystemExit):
        gerar_banco.parse_args(["--trilhas", "9"])


def test_incremental_anexa_continua_ids_e_nao_toca_outras(monkeypatch, tmp_path):
    existentes = [_dica("t1-01", 1), _dica("t1-07", 1), _dica("t2-01", 2)]
    chamadas = []

    def gerar(nome, temas, n, cliente):
        chamadas.append((nome, n))
        # "t1-01" e' titulo ja existente (titulo == id em _dica), com caixa diferente
        return [dict(_bruta(0, 1), titulo="T1-01"), _bruta(1, 1), _bruta(2, 1)]

    caminho = _preparar(monkeypatch, tmp_path, existentes, gerar,
                        lambda d, cliente=None: replace(d, status="aprovada", motivo="ok"))
    assert gerar_banco.main(["--trilhas", "1", "--candidatas", "3", "--min-aprovadas", "1"]) == 0
    assert chamadas == [(TRILHAS[0].nome, 3)]
    final = carregar_banco(caminho)
    assert [d.id for d in final if d.trilha == 1] == ["t1-01", "t1-07", "t1-08", "t1-09"]
    assert [d.id for d in final if d.trilha == 2] == ["t2-01"]
    assert len(final) == 5


def test_incremental_respeita_max_somando_existentes(monkeypatch, tmp_path):
    existentes = [_dica("t1-01", 1)]
    checadas = []

    def aprovar(d, cliente=None):
        checadas.append(d.id)
        return replace(d, status="aprovada", motivo="ok")

    caminho = _preparar(monkeypatch, tmp_path, existentes,
                        lambda *a: [_bruta(i, 1) for i in range(5)], aprovar)
    assert gerar_banco.main(["--trilhas", "1", "--max-aprovadas", "3", "--min-aprovadas", "1"]) == 0
    assert len(checadas) == 2
    assert len(carregar_banco(caminho)) == 3


def test_incremental_abaixo_do_minimo_mantem_e_sai_1(monkeypatch, tmp_path):
    existentes = [_dica("t1-01", 1)]
    caminho = _preparar(monkeypatch, tmp_path, existentes,
                        lambda *a: [_bruta(i, 1) for i in range(3)],
                        lambda d, cliente=None: replace(d, status="descartada", motivo="x"))
    assert gerar_banco.main(["--trilhas", "1", "--min-aprovadas", "1"]) == 1
    assert [d.id for d in carregar_banco(caminho)] == ["t1-01"]

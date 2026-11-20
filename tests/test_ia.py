import json
from types import SimpleNamespace

import pytest

from licittax import ia


class ClienteFalso:
    def __init__(self, texto=None, erro=None, parada="end_turn", respostas=None):
        self.texto, self.erro, self.parada, self.chamadas = texto, erro, parada, []
        self.respostas = list(respostas) if respostas else None
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.chamadas.append(kw)
        if self.erro:
            raise self.erro
        texto = self.respostas.pop(0) if self.respostas else self.texto
        bloco = SimpleNamespace(type="text", text=texto)
        return SimpleNamespace(content=[SimpleNamespace(type="thinking"), bloco], stop_reason=self.parada)


def test_modelos():
    assert ia.MODELO_RAPIDO == "claude-sonnet-5-5"
    assert ia.MODELO_RIGOROSO == "claude-opus-5-5"


def test_encurtar_respeita_limite_e_palavra():
    texto = "Contratação de empresa especializada em serviços de manutenção predial preventiva e corretiva de ar condicionado"
    r = ia.encurtar(texto, 90)
    assert len(r) <= 90 and r.endswith("…")
    assert texto.startswith(r[:-1].rstrip())
    assert texto[len(r[:-1].rstrip())] == " "


def test_encurtar_curto_nao_muda():
    assert ia.encurtar("abc", 90) == "abc"


def test_encurtar_palavra_unica_longa():
    r = ia.encurtar("x" * 200, 10)
    assert len(r) <= 10 and r.endswith("…")


def test_resumo_usa_resposta():
    c = ClienteFalso("Manutenção de ar condicionado")
    assert ia.resumir_objeto("objeto longo", c) == "Manutenção de ar condicionado"
    assert c.chamadas[0]["model"] == ia.MODELO_RAPIDO


def test_resumo_fallback_quando_api_falha():
    obj = "palavra " * 30
    r = ia.resumir_objeto(obj, ClienteFalso(erro=RuntimeError("sem crédito")))
    assert r == ia.encurtar(obj, 90)


def test_resumo_fallback_quando_passa_de_90():
    obj = "Aquisição de material " * 10
    r = ia.resumir_objeto(obj, ClienteFalso("a" * 120))
    assert r == ia.encurtar(obj, 90)


def test_gancho_ok_e_limite():
    assert ia.gancho_legenda("t", "l", ClienteFalso("Você sabia?")) == "Você sabia?"
    assert ia.gancho_legenda("t", "l", ClienteFalso("a" * 151)) == ""


def test_gancho_vazio_quando_api_falha():
    assert ia.gancho_legenda("t", "l", ClienteFalso(erro=RuntimeError("x"))) == ""


def test_verificacao_le_json():
    c = ClienteFalso(json.dumps({"sustenta": True, "motivo": "ok"}))
    v = ia.verificar_afirmacao("a", "inciso I", "texto", c)
    assert v == ia.Verificacao(True, "ok")
    assert c.chamadas[0]["model"] == ia.MODELO_RIGOROSO


def test_verificacao_json_invalido_reprova():
    v = ia.verificar_afirmacao("a", "d", "t", ClienteFalso("não é json"))
    assert v == ia.Verificacao(False, "erro na verificação")


def test_verificacao_erro_api_reprova():
    v = ia.verificar_afirmacao("a", "d", "t", ClienteFalso(erro=RuntimeError("x")))
    assert v.sustenta is False


def test_verificacao_tipo_errado_reprova():
    v = ia.verificar_afirmacao("a", "d", "t", ClienteFalso('{"sustenta": "sim", "motivo": "x"}'))
    assert v.sustenta is False


def test_gerar_dicas_forca_pendente():
    dica = {"id": "t1-01", "trilha": 1, "titulo": "x", "slides": [], "status": "aprovada"}
    c = ClienteFalso(json.dumps({"dicas": [dica]}))
    r = ia.gerar_dicas("Prazos", "temas", 1, c)
    assert r[0]["status"] == "pendente" and r[0]["id"] == "t1-01"
    assert c.chamadas[0]["model"] == ia.MODELO_RIGOROSO


def test_criar_cliente(monkeypatch):
    monkeypatch.setattr(ia.anthropic, "Anthropic", lambda api_key: ("cli", api_key))
    assert ia.criar_cliente({"ANTHROPIC_API_KEY": "k"}) == ("cli", "k")


def _lote(n, trilha=1):
    return json.dumps({"dicas": [{"id": "x", "trilha": trilha, "titulo": f"T{i}", "status": "aprovada"}
                                 for i in range(n)]})


def test_gerar_dicas_em_lotes():
    c = ClienteFalso(respostas=[_lote(5), _lote(5), _lote(5)])
    r = ia.gerar_dicas("Prazos", "temas", 12, c)
    assert len(c.chamadas) == 3 and len(r) == 12
    assert len({d["id"] for d in r}) == 12 and r[0]["id"] == "t1-01"
    assert all(d["status"] == "pendente" for d in r)
    assert "T0" in c.chamadas[1]["messages"][0]["content"]


@pytest.mark.parametrize("parada", ["max_tokens", "refusal"])
def test_gerar_dicas_parada_anormal(parada):
    with pytest.raises(ia.ErroGeracaoDicas):
        ia.gerar_dicas("P", "t", 3, ClienteFalso(_lote(3), parada=parada))


def test_gerar_dicas_sem_chave_dicas():
    with pytest.raises(ia.ErroGeracaoDicas):
        ia.gerar_dicas("P", "t", 3, ClienteFalso('{"outra": []}'))


def test_gerar_dicas_vazio_ou_nao_json():
    for txt in ("", "nada"):
        with pytest.raises(ia.ErroGeracaoDicas):
            ia.gerar_dicas("P", "t", 3, ClienteFalso(txt))


def test_verificacao_max_tokens_reprova():
    c = ClienteFalso(json.dumps({"sustenta": True, "motivo": "ok"}), parada="max_tokens")
    assert ia.verificar_afirmacao("a", "d", "t", c).sustenta is False


def test_cobertura_le_json():
    c = ClienteFalso(json.dumps({"sustenta": True, "motivo": "ok"}))
    assert ia.verificar_cobertura("texto", ["a"], c) == ia.Verificacao(True, "ok")
    assert c.chamadas[0]["model"] == ia.MODELO_RIGOROSO


@pytest.mark.parametrize("c", [
    ClienteFalso("não é json"),
    ClienteFalso(erro=RuntimeError("x")),
    ClienteFalso('{"sustenta": "sim", "motivo": "x"}'),
    ClienteFalso('{"sustenta": true, "motivo": "ok"}', parada="max_tokens"),
    ClienteFalso('{"sustenta": true, "motivo": "ok"}', parada="refusal"),
])
def test_cobertura_falha_fechada(c):
    assert ia.verificar_cobertura("t", ["a"], c).sustenta is False

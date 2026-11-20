import json
import time

import pytest
import responses

from licittax.instagram import ErroInstagram, Instagram

G = "https://graph.facebook.com/v21.0"


def ig():
    return Instagram("123", "SEGREDO", "v21.0", espera=lambda s: None)


def _publicacoes():
    return [c for c in responses.calls if c.request.url.endswith("/media_publish")]


@responses.activate
def test_story_cria_container_e_publica():
    responses.post(f"{G}/123/media", json={"id": "c1"})
    responses.get(f"{G}/c1", json={"status_code": "FINISHED"})
    responses.post(f"{G}/123/media_publish", json={"id": "m1"})
    assert ig().publicar_story("https://x/a.jpg") == "m1"
    corpo = responses.calls[0].request.body
    assert "media_type=STORIES" in corpo and "access_token=SEGREDO" in corpo
    assert "creation_id=c1" in responses.calls[-1].request.body


@responses.activate
def test_carrossel_cria_filhos_pai_e_publica_uma_vez():
    ids = iter(["f1", "f2", "pai"])
    responses.add_callback(responses.POST, f"{G}/123/media",
                           callback=lambda r: (200, {}, json.dumps({"id": next(ids)})))
    for i in ("f1", "f2", "pai"):
        responses.get(f"{G}/{i}", json={"status_code": "FINISHED"})
    responses.post(f"{G}/123/media_publish", json={"id": "m9"})
    assert ig().publicar_carrossel(["u1", "u2"], "legenda") == "m9"
    posts = [c.request.body for c in responses.calls if c.request.url.endswith("/123/media")]
    assert "is_carousel_item=true" in posts[0]
    assert "media_type=CAROUSEL" in posts[2] and "children=f1%2Cf2" in posts[2]
    assert "caption=legenda" in posts[2]
    assert len(_publicacoes()) == 1


@responses.activate
def test_filho_com_erro_nao_publica_nada():
    ids = iter(["f1", "f2"])
    responses.add_callback(responses.POST, f"{G}/123/media",
                           callback=lambda r: (200, {}, json.dumps({"id": next(ids)})))
    responses.get(f"{G}/f1", json={"status_code": "FINISHED"})
    responses.get(f"{G}/f2", json={"status_code": "ERROR"})
    with pytest.raises(ErroInstagram):
        ig().publicar_carrossel(["u1", "u2"], "l")
    assert _publicacoes() == []


@responses.activate
def test_container_nunca_finished_nao_publica():
    responses.post(f"{G}/123/media", json={"id": "c1"})
    responses.get(f"{G}/c1", json={"status_code": "IN_PROGRESS"})
    with pytest.raises(ErroInstagram):
        ig().publicar_story("u")
    assert _publicacoes() == []
    assert len([c for c in responses.calls if c.request.url.startswith(f"{G}/c1")]) == 12


@responses.activate
def test_erro_da_api_traz_mensagem_sem_token():
    responses.post(f"{G}/123/media", status=400, json={"error": {"message": "URL inválida"}})
    with pytest.raises(ErroInstagram) as e:
        ig().publicar_story("u")
    assert "URL inválida" in str(e.value) and "SEGREDO" not in str(e.value)


@responses.activate
def test_token_sem_expiracao_retorna_none():
    responses.get(f"{G}/debug_token", json={"data": {"is_valid": True, "expires_at": 0}})
    assert ig().dias_ate_expirar_token("app", "sec") is None
    assert "access_token=app%7Csec" in responses.calls[0].request.url


@responses.activate
def test_token_com_expiracao_retorna_dias():
    responses.get(f"{G}/debug_token",
                  json={"data": {"is_valid": True, "expires_at": int(time.time()) + 5 * 86400 + 60}})
    assert ig().dias_ate_expirar_token("app", "sec") == 5


@responses.activate
def test_token_invalido_levanta():
    responses.get(f"{G}/debug_token", json={"data": {"is_valid": False, "expires_at": 0}})
    with pytest.raises(ErroInstagram):
        ig().dias_ate_expirar_token("app", "sec")


@responses.activate
@pytest.mark.parametrize("corpo", [[1, 2], "texto", None, 5])
def test_corpo_json_nao_dict_levanta_erro_instagram(corpo):
    responses.post(f"{G}/123/media", json=corpo)
    with pytest.raises(ErroInstagram):
        ig().publicar_story("u")


@responses.activate
def test_erro_nao_dict_levanta_erro_instagram():
    responses.post(f"{G}/123/media", status=500, json={"error": "falhou"})
    with pytest.raises(ErroInstagram):
        ig().publicar_story("u")


@responses.activate
def test_resposta_200_sem_id_levanta():
    responses.post(f"{G}/123/media", json={})
    with pytest.raises(ErroInstagram, match="sem id"):
        ig().publicar_story("u")

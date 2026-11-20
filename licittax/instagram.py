"""Publicacao via Instagram Graph API."""
import time

import requests


class ErroInstagram(Exception):
    pass


class Instagram:
    def __init__(self, ig_user_id, token, versao, sessao=None, espera=time.sleep):
        self.ig = ig_user_id
        self._token = token
        self.base = f"https://graph.facebook.com/{versao}"
        self.sessao = sessao or requests.Session()
        self.espera = espera

    def _resposta(self, r):
        try:
            dados = r.json()
        except ValueError:
            dados = {}
        if r.status_code >= 400 or "error" in dados:
            msg = (dados.get("error") or {}).get("message") or f"HTTP {r.status_code}"
            raise ErroInstagram(str(msg).replace(self._token, "***"))
        return dados

    def _chamar(self, metodo, caminho, **kw):
        try:
            r = getattr(self.sessao, metodo)(f"{self.base}/{caminho}", timeout=60, **kw)
        except requests.RequestException as e:
            raise ErroInstagram(f"falha de rede: {type(e).__name__}") from None
        return self._resposta(r)

    def _post(self, caminho, dados):
        return self._chamar("post", caminho, data={**dados, "access_token": self._token})

    def _get(self, caminho, params):
        return self._chamar("get", caminho, params={**params, "access_token": self._token})

    def _aguardar(self, container):
        for i in range(12):
            status = self._get(container, {"fields": "status_code"}).get("status_code")
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise ErroInstagram(f"container {container} com status {status}")
            if i < 11:
                self.espera(5)
        raise ErroInstagram(f"container {container} nao ficou pronto a tempo")

    def _publicar(self, container):
        return self._post(f"{self.ig}/media_publish", {"creation_id": container})["id"]

    def publicar_story(self, url_imagem):
        c = self._post(f"{self.ig}/media", {"image_url": url_imagem, "media_type": "STORIES"})["id"]
        self._aguardar(c)
        return self._publicar(c)

    def publicar_carrossel(self, urls, legenda):
        filhos = []
        for u in urls:
            f = self._post(f"{self.ig}/media", {"image_url": u, "is_carousel_item": "true"})["id"]
            self._aguardar(f)
            filhos.append(f)
        pai = self._post(f"{self.ig}/media", {"media_type": "CAROUSEL",
                                              "children": ",".join(filhos),
                                              "caption": legenda})["id"]
        self._aguardar(pai)
        return self._publicar(pai)

    def dias_ate_expirar_token(self, app_id, app_secret):
        dados = self._chamar("get", "debug_token",
                             params={"input_token": self._token,
                                     "access_token": f"{app_id}|{app_secret}"})
        data = dados.get("data") or {}
        if not data.get("is_valid"):
            raise ErroInstagram("token invalido")
        exp = data.get("expires_at") or 0
        if exp == 0:
            return None
        return max(0, int((exp - time.time()) // 86400))

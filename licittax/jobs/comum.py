"""Pecas compartilhadas pelos jobs: dependencias injetaveis e execucao com tratamento de erro."""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from licittax import hospedagem, ia, instagram
from licittax.artes import render
from licittax.config import Config, carregar_config
from licittax.dicas.banco import carregar_banco, dica_do_dia
from licittax.pncp import selecao


class FalhaJob(Exception):
    """Falha com mensagem ja em portugues (o que falhou e em que etapa)."""


def _cliente_ia(env):
    try:
        return ia.criar_cliente(env)
    except Exception:
        return None  # sem IA: resumo e gancho usam o fallback


def _instagram(cfg: Config, env) -> instagram.Instagram:
    return instagram.Instagram(env["IG_USER_ID"], env["IG_TOKEN"], cfg.graph_versao)


@dataclass
class Deps:
    env: Mapping[str, str] = field(default_factory=lambda: os.environ)
    raiz: Path = field(default_factory=Path.cwd)
    cfg: Config | None = None
    criar_cliente: Callable = _cliente_ia
    criar_instagram: Callable = _instagram
    hospedar: Callable = hospedagem.hospedar
    commitar: Callable = hospedagem.commitar
    escolher_edital: Callable = selecao.escolher_edital
    resumir_objeto: Callable = ia.resumir_objeto
    gancho_legenda: Callable = ia.gancho_legenda
    arte_story_edital: Callable = render.arte_story_edital
    arte_story_dica: Callable = render.arte_story_dica
    artes_carrossel: Callable = render.artes_carrossel

    def config(self) -> Config:
        return self.cfg or carregar_config(self.raiz / "config.yaml", self.env)

    def saida(self) -> Path:
        pasta = self.raiz / "saida"
        pasta.mkdir(parents=True, exist_ok=True)
        return pasta

    def exigir_segredos(self, *nomes: str) -> None:
        faltam = [n for n in nomes if not self.env.get(n)]
        if faltam:
            raise FalhaJob("variaveis de ambiente ausentes: " + ", ".join(faltam))


def agora(agora_utc: datetime | None) -> datetime:
    return agora_utc or datetime.now(timezone.utc)


def executar(nome: str, corpo: Callable[[], None]) -> int:
    """Roda o job; qualquer excecao vira mensagem em portugues e codigo 1."""
    try:
        corpo()
        return 0
    except FalhaJob as e:
        print(f"[{nome}] ERRO: {e}")
    except Exception as e:  # noqa: BLE001
        print(f"[{nome}] ERRO inesperado: {type(e).__name__}: {e}")
    return 1


def etapa(descricao: str, fn: Callable, *args, **kw):
    try:
        return fn(*args, **kw)
    except FalhaJob:
        raise
    except Exception as e:  # noqa: BLE001
        raise FalhaJob(f"falha em '{descricao}': {type(e).__name__}: {e}") from e


def dica_de_hoje(deps: Deps, cfg: Config, hoje: date):
    banco = etapa("ler banco de dicas", carregar_banco, deps.raiz / "data" / "banco_dicas.json")
    return etapa("escolher dica do dia", dica_do_dia, banco, hoje, cfg.inicio_rotacao)

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Config:
    whatsapp: str
    cta_story: str
    cta_legenda: str
    ufs_prioritarias: tuple[str, ...]
    modalidades: tuple[int, ...]
    modo_disputa_dispensa: int
    dias_uteis_minimos: int
    inicio_rotacao: date
    graph_versao: str
    hashtags: tuple[str, ...]
    ensaio: bool


def carregar_config(caminho: Path = Path("config.yaml"), env: Mapping[str, str] = os.environ) -> Config:
    dados = yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))
    return Config(
        whatsapp=dados["whatsapp"],
        cta_story=dados["cta_story"],
        cta_legenda=dados["cta_legenda"],
        ufs_prioritarias=tuple(dados["ufs_prioritarias"]),
        modalidades=tuple(int(m) for m in dados["modalidades"]),
        modo_disputa_dispensa=int(dados["modo_disputa_dispensa"]),
        dias_uteis_minimos=int(dados["dias_uteis_minimos"]),
        inicio_rotacao=dados["inicio_rotacao"],
        graph_versao=dados["graph_versao"],
        hashtags=tuple(dados["hashtags"]),
        ensaio=env.get("MODO_ENSAIO") == "1",
    )

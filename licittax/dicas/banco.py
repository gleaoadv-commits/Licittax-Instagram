from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from licittax.dicas.modelo import Dica
from licittax.dicas.trilhas import TRILHAS


def carregar_banco(caminho: Path) -> list[Dica]:
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    return [Dica.from_dict(d) for d in dados["dicas"]]


def salvar_banco(dicas: list[Dica], caminho: Path) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = {"dicas": [d.to_dict() for d in dicas]}
    caminho.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _chave_id(d: Dica):
    m = re.search(r"(\d+)$", d.id)
    return (int(m.group(1)) if m else 0, d.id)


def dica_do_dia(banco: list[Dica], dia: date, inicio: date) -> Dica:
    aprovadas = [d for d in banco if d.status == "aprovada"]
    if not aprovadas:
        raise ValueError("banco sem dicas aprovadas")
    idx = (dia - inicio).days
    n = len(TRILHAS)
    for passo in range(n):
        numero = TRILHAS[(idx + passo) % n].numero
        da_trilha = sorted((d for d in aprovadas if d.trilha == numero), key=_chave_id)
        if da_trilha:
            return da_trilha[(idx // n) % len(da_trilha)]
    raise ValueError("nenhuma trilha com dicas aprovadas")

import json
from pathlib import Path

_MAX_PUBLICACOES = 60  # guarda so as ultimas marcas de "ja publicado"


def _ler(caminho: Path) -> dict:
    caminho = Path(caminho)
    if not caminho.exists():
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


def _gravar(dados: dict, caminho: Path) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def carregar_estado(caminho: Path) -> set[str]:
    return set(_ler(caminho).get("editais_publicados", []))


def salvar_estado(publicados: set[str], caminho: Path) -> None:
    dados = _ler(caminho)
    dados["editais_publicados"] = sorted(publicados)
    _gravar(dados, caminho)


def ja_publicado(caminho: Path, marca: str) -> bool:
    """marca = '<data>-<horario>' (ex.: '2026-11-21-post'): evita postar duas vezes no mesmo dia."""
    return marca in _ler(caminho).get("publicacoes", [])


def marcar_publicado(caminho: Path, marca: str) -> None:
    dados = _ler(caminho)
    marcas = [m for m in dados.get("publicacoes", []) if m != marca] + [marca]
    dados["publicacoes"] = sorted(marcas)[-_MAX_PUBLICACOES:]
    dados.setdefault("editais_publicados", [])
    _gravar(dados, caminho)

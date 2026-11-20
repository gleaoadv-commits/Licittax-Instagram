import json
from pathlib import Path


def carregar_estado(caminho: Path) -> set[str]:
    caminho = Path(caminho)
    if not caminho.exists():
        return set()
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return set(dados.get("editais_publicados", []))


def salvar_estado(publicados: set[str], caminho: Path) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = {"editais_publicados": sorted(publicados)}
    caminho.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

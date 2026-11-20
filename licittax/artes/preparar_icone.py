"""Gera assets/brand/icone-transparente.png a partir de icone.png (fundo branco → transparente).

Uso: python -m licittax.artes.preparar_icone
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops

RAIZ = Path(__file__).resolve().parents[2]
ORIGEM = RAIZ / "assets" / "brand" / "icone.png"
DESTINO = RAIZ / "assets" / "brand" / "icone-transparente.png"
LIMIAR = 240


def preparar(origem: Path = ORIGEM, destino: Path = DESTINO) -> Path:
    img = Image.open(origem).convert("RGBA")
    r, g, b, a = img.split()
    # 255 onde o canal passa do limiar; o pixel é "quase branco" se os três passam.
    claro = [c.point(lambda v: 255 if v > LIMIAR else 0) for c in (r, g, b)]
    branco = ImageChops.multiply(ImageChops.multiply(claro[0], claro[1]), claro[2])
    alfa = ImageChops.subtract(a, branco)  # branco → alfa 0; demais mantêm o alfa original
    img.putalpha(alfa)
    caixa = alfa.getbbox()  # recorta a margem vazia para o ícone ocupar o espaço do rodapé
    if caixa:
        img = img.crop(caixa)
    img.save(destino)
    return destino


if __name__ == "__main__":
    print(preparar())

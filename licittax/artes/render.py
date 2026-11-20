"""Artes do Instagram: modelos Jinja (HTML/CSS) renderizados em JPEG pelo Chromium (Playwright)."""
from __future__ import annotations

import io
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from PIL import Image

from licittax.config import Config
from licittax.datas import BRASILIA
from licittax.dicas.modelo import Dica
from licittax.pncp.selecao import Escolha

RAIZ = Path(__file__).resolve().parents[2]
TEMPLATES = Path(__file__).resolve().parent / "templates"
FONTES = RAIZ / "assets" / "fonts"
ICONE = RAIZ / "assets" / "brand" / "icone-transparente.png"

STORY = (1080, 1920)
FEED = (1080, 1350)
QUALIDADE_JPEG = 92

_env = Environment(
    loader=FileSystemLoader(TEMPLATES),
    autoescape=select_autoescape(["html", "j2"]),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)

# Equivale a [...].some(e => e.scrollHeight > e.clientHeight + 1), devolvendo quem estourou.
_JS_ESTOURO = """
[...document.querySelectorAll('.ajustar')]
  .filter(e => e.scrollHeight > e.clientHeight + 1)
  .map(e => `${e.className} (${e.scrollHeight}>${e.clientHeight}): ${e.innerText.slice(0, 60)}`)
"""
# Carrega explicitamente os 4 pesos; falha (False) se algum arquivo de fonte não carregar.
_JS_FONTES = """
Promise.all(['400', '600', '700', '800'].map(p => document.fonts.load(p + ' 40px Poppins')))
  .then(listas => listas.every(l => l.length > 0 && l.every(f => f.status === 'loaded')))
  .catch(() => false)
"""


class TextoEstourado(Exception):
    """Algum bloco de texto não coube no espaço reservado da arte."""


def formatar_reais(valor: float) -> str:
    inteiro, centavos = f"{valor:,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def html_de(template: str, contexto: dict) -> str:
    largura, altura = STORY if template.startswith("story_") else FEED
    base = {
        "fontes": FONTES.as_uri(),
        "icone": ICONE.as_uri(),
        "largura": largura,
        "altura": altura,
    }
    return _env.get_template(template).render({**base, **contexto})


def renderizar(template: str, contexto: dict, saida: Path, largura: int, altura: int) -> Path:
    from playwright.sync_api import sync_playwright

    html = html_de(template, {**contexto, "largura": largura, "altura": altura})
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pagina_html = Path(tmp) / "arte.html"
        pagina_html.write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            navegador = p.chromium.launch(args=["--allow-file-access-from-files"])
            try:
                pagina = navegador.new_page(
                    viewport={"width": largura, "height": altura}, device_scale_factor=1
                )
                pagina.goto(pagina_html.as_uri(), wait_until="load")
                if not pagina.evaluate(_JS_FONTES):
                    raise RuntimeError(f"Fonte Poppins não carregou de {FONTES}")
                pagina.evaluate("document.fonts.ready.then(() => true)")
                estourados = pagina.evaluate(_JS_ESTOURO)
                if estourados:
                    raise TextoEstourado(
                        f"Texto não coube na arte {template}: " + " | ".join(estourados))
                png = pagina.screenshot(type="png", full_page=False)
            finally:
                navegador.close()
    with Image.open(io.BytesIO(png)) as img:
        img.convert("RGB").save(saida, "JPEG", quality=QUALIDADE_JPEG)
    return saida


# ---------- contextos ----------

def _rodape_story(cfg: Config) -> dict:
    return {"cta": cfg.cta_story, "whatsapp": cfg.whatsapp}


def contexto_story_edital(escolha: Escolha, resumo: str, cfg: Config) -> dict:
    e = escolha.edital
    local = "/".join(x for x in (e.municipio, e.uf) if x)
    prazo = None
    if e.data_encerramento is not None:
        prazo = e.data_encerramento.astimezone(BRASILIA).strftime("%d/%m/%Y")
    return {
        "exclusivo": escolha.exclusivo_me_epp,
        "orgao": e.orgao,
        "titulo": resumo,
        "local": local,
        "valor": formatar_reais(e.valor_estimado) if e.valor_estimado else None,
        "prazo": prazo,
        **_rodape_story(cfg),
    }


def contexto_story_dica(dica: Dica, cfg: Config) -> dict:
    return {"frase": dica.frase_story, "base_legal": dica.base_legal(), **_rodape_story(cfg)}


def contextos_carrossel(dica: Dica) -> list[tuple[str, dict]]:
    total = len(dica.slides) + 2
    telas: list[tuple[str, dict]] = [
        ("carrossel_capa.html.j2", {"titulo": dica.titulo, "pagina": 1, "total": total})
    ]
    for i, slide in enumerate(dica.slides):
        ultimo = i == len(dica.slides) - 1
        telas.append(("carrossel_slide.html.j2", {
            "titulo": slide.titulo,
            "itens": list(slide.itens),
            "base_legal": dica.base_legal() if ultimo else "",
            "pagina": i + 2,
            "total": total,
        }))
    telas.append(("carrossel_final.html.j2", {"pagina": total, "total": total}))
    return telas


# ---------- artes ----------

def arte_story_edital(escolha: Escolha, resumo: str, cfg: Config, pasta: Path) -> Path:
    return renderizar("story_edital.html.j2", contexto_story_edital(escolha, resumo, cfg),
                      Path(pasta) / "story_edital.jpg", *STORY)


def arte_story_dica(dica: Dica, cfg: Config, pasta: Path) -> Path:
    return renderizar("story_dica.html.j2", contexto_story_dica(dica, cfg),
                      Path(pasta) / "story_dica.jpg", *STORY)


def artes_carrossel(dica: Dica, pasta: Path) -> list[Path]:
    return [
        renderizar(template, ctx, Path(pasta) / f"carrossel_{n:02d}.jpg", *FEED)
        for n, (template, ctx) in enumerate(contextos_carrossel(dica), start=1)
    ]

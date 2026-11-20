from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Citacao:
    norma: str
    artigo: str
    dispositivo: str = ""
    url: str | None = None


@dataclass(frozen=True)
class Afirmacao:
    texto: str
    citacao: Citacao | None


@dataclass(frozen=True)
class Slide:
    titulo: str
    itens: tuple[str, ...]


@dataclass(frozen=True)
class Dica:
    id: str
    trilha: int
    titulo: str
    slides: tuple[Slide, ...]
    frase_story: str
    legenda_base: str
    afirmacoes: tuple[Afirmacao, ...]
    hashtags: tuple[str, ...]
    status: str = "pendente"
    motivo: str = ""

    def base_legal(self) -> str:
        vistos: list[str] = []
        for a in self.afirmacoes:
            if a.citacao is None:
                continue
            item = f"{a.citacao.norma}, {a.citacao.artigo}"
            if item not in vistos:
                vistos.append(item)
        return "; ".join(vistos)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "trilha": self.trilha, "titulo": self.titulo,
            "slides": [{"titulo": s.titulo, "itens": list(s.itens)} for s in self.slides],
            "frase_story": self.frase_story, "legenda_base": self.legenda_base,
            "afirmacoes": [
                {"texto": a.texto,
                 "citacao": None if a.citacao is None else {
                     "norma": a.citacao.norma, "artigo": a.citacao.artigo,
                     "dispositivo": a.citacao.dispositivo, "url": a.citacao.url}}
                for a in self.afirmacoes],
            "hashtags": list(self.hashtags), "status": self.status, "motivo": self.motivo,
        }

    @staticmethod
    def from_dict(d: dict) -> "Dica":
        def lista(x):
            if not isinstance(x, list):
                raise ValueError("campo deve ser lista")
            return tuple(x)

        def cit(c):
            if not c:
                return None
            return Citacao(c["norma"], c["artigo"], c.get("dispositivo") or "", c.get("url"))
        return Dica(
            id=d["id"], trilha=int(d["trilha"]), titulo=d["titulo"],
            slides=tuple(Slide(s["titulo"], lista(s["itens"])) for s in d["slides"]),
            frase_story=d["frase_story"], legenda_base=d["legenda_base"],
            afirmacoes=tuple(Afirmacao(a["texto"], cit(a.get("citacao")))
                             for a in d["afirmacoes"]),
            hashtags=lista(d["hashtags"]), status=d.get("status", "pendente"),
            motivo=d.get("motivo", ""))

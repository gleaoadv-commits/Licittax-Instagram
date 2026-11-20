"""Job: carrossel diario com a dica do dia."""
import sys
from datetime import datetime

from licittax.datas import eh_dia_de_post, hoje_brasilia
from licittax.jobs.comum import Deps, agora, dica_de_hoje, etapa, executar
from licittax.legenda import montar_legenda


def _rodar(agora_utc: datetime | None, deps: Deps) -> None:
    cfg = deps.config()
    hoje = hoje_brasilia(agora(agora_utc))
    if not eh_dia_de_post(hoje, cfg.inicio_rotacao):
        print("Hoje não é dia de post.")
        return
    if not cfg.ensaio:
        deps.exigir_segredos("IG_USER_ID", "IG_TOKEN", "GITHUB_REPOSITORY")
    dica = dica_de_hoje(deps, cfg, hoje)
    pasta = deps.saida()
    artes = etapa("gerar artes do carrossel", deps.artes_carrossel, dica, pasta)
    cliente = deps.criar_cliente(deps.env)
    gancho = deps.gancho_legenda(dica.titulo, dica.legenda_base, cliente)
    legenda = etapa("montar legenda", montar_legenda, dica, gancho, cfg)

    if cfg.ensaio:
        (pasta / "legenda.txt").write_text(legenda, encoding="utf-8")
        print(f"[post_dica] ensaio: {len(artes)} artes e legenda em {pasta}")
        return

    urls = etapa("hospedar imagens", deps.hospedar, artes, deps.raiz,
                 deps.env["GITHUB_REPOSITORY"], f"{hoje}-post")
    ig = deps.criar_instagram(cfg, deps.env)
    etapa("publicar carrossel", ig.publicar_carrossel, urls, legenda)
    print(f"[post_dica] carrossel publicado: dica {dica.id}")


def main(agora_utc: datetime | None = None, deps: Deps | None = None) -> int:
    deps = deps or Deps()
    return executar("post_dica", lambda: _rodar(agora_utc, deps))


if __name__ == "__main__":
    sys.exit(main())

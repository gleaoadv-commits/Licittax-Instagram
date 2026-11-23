"""Job: carrossel diario com a dica do dia."""
import sys
from datetime import datetime

from licittax.datas import eh_dia_de_post, hoje_brasilia
from licittax.jobs.comum import (JANELA_POST, Deps, agora, dica_de_hoje, etapa, executar, fora_da_janela,
                                  ja_feito_hoje, registrar_publicacao)
from licittax.legenda import montar_legenda


def _rodar(agora_utc: datetime | None, deps: Deps) -> None:
    cfg = deps.config()
    agora_utc = agora(agora_utc)
    if fora_da_janela(deps, cfg, agora_utc, JANELA_POST, "post_dica"):
        return
    hoje = hoje_brasilia(agora_utc)
    if not eh_dia_de_post(hoje, cfg.inicio_rotacao):
        print("Hoje não é dia de post.")
        return
    marca = f"{hoje}-post"
    if not cfg.ensaio:
        if ja_feito_hoje(deps, marca, "post_dica"):
            return
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
    registrar_publicacao(deps, marca)


def main(agora_utc: datetime | None = None, deps: Deps | None = None) -> int:
    deps = deps or Deps()
    return executar("post_dica", lambda: _rodar(agora_utc, deps))


if __name__ == "__main__":
    sys.exit(main())

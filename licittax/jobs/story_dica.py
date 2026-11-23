"""Job das 18h: story da dica (dia de post) ou segundo story de edital (dia sem post)."""
import sys
from datetime import datetime

from licittax.datas import eh_dia_de_post, hoje_brasilia
from licittax.jobs.comum import (JANELA_TARDE, Deps, agora, dica_de_hoje, etapa, executar, fora_da_janela,
                                  ja_feito_hoje, registrar_publicacao)
from licittax.jobs.story_edital import publicar_edital


def _rodar(agora_utc: datetime | None, deps: Deps) -> None:
    cfg = deps.config()
    agora_utc = agora(agora_utc)
    if fora_da_janela(deps, cfg, agora_utc, JANELA_TARDE, "story_dica"):
        return
    hoje = hoje_brasilia(agora_utc)
    if not eh_dia_de_post(hoje, cfg.inicio_rotacao):
        publicar_edital(agora_utc, deps, "-tarde", janela=None)
        return
    marca = f"{hoje}-story-dica"
    if not cfg.ensaio:
        if ja_feito_hoje(deps, marca, "story_dica"):
            return
        deps.exigir_segredos("IG_USER_ID", "IG_TOKEN", "GITHUB_REPOSITORY")
    dica = dica_de_hoje(deps, cfg, hoje)
    arte = etapa("gerar arte do story", deps.arte_story_dica, dica, cfg, deps.saida())

    if cfg.ensaio:
        print(f"[story_dica] ensaio: arte salva em {arte}")
        return

    urls = etapa("hospedar imagem", deps.hospedar, [arte], deps.raiz,
                 deps.env["GITHUB_REPOSITORY"], f"{hoje}-story-dica")
    ig = deps.criar_instagram(cfg, deps.env)
    etapa("publicar story", ig.publicar_story, urls[0])
    print(f"[story_dica] story publicado: dica {dica.id}")
    registrar_publicacao(deps, marca)


def main(agora_utc: datetime | None = None, deps: Deps | None = None) -> int:
    deps = deps or Deps()
    return executar("story_dica", lambda: _rodar(agora_utc, deps))


if __name__ == "__main__":
    sys.exit(main())

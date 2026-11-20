"""Job: story diario com a frase da dica do dia."""
import sys
from datetime import datetime

from licittax.datas import hoje_brasilia
from licittax.jobs.comum import Deps, agora, dica_de_hoje, etapa, executar


def _rodar(agora_utc: datetime | None, deps: Deps) -> None:
    cfg = deps.config()
    if not cfg.ensaio:
        deps.exigir_segredos("IG_USER_ID", "IG_TOKEN", "GITHUB_REPOSITORY")
    hoje = hoje_brasilia(agora(agora_utc))
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


def main(agora_utc: datetime | None = None, deps: Deps | None = None) -> int:
    deps = deps or Deps()
    return executar("story_dica", lambda: _rodar(agora_utc, deps))


if __name__ == "__main__":
    sys.exit(main())

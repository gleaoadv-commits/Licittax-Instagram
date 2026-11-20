"""Job semanal: avisa se o token do Instagram estiver invalido ou perto de vencer."""
import sys
from datetime import datetime

from licittax.jobs.comum import Deps, FalhaJob, etapa, executar

LIMITE_DIAS = 10


def _rodar(deps: Deps) -> None:
    cfg = deps.config()
    deps.exigir_segredos("IG_USER_ID", "IG_TOKEN", "META_APP_ID", "META_APP_SECRET")
    ig = deps.criar_instagram(cfg, deps.env)
    dias = etapa("consultar validade do token", ig.dias_ate_expirar_token,
                 deps.env["META_APP_ID"], deps.env["META_APP_SECRET"])
    if dias is None or dias > LIMITE_DIAS:
        print("[checar_token] token ok" + ("" if dias is None else f" ({dias} dias restantes)"))
        return
    raise FalhaJob(f"ATENCAO: o token do Instagram expira em {dias} dia(s); renove-o")


def main(agora_utc: datetime | None = None, deps: Deps | None = None) -> int:
    deps = deps or Deps()
    return executar("checar_token", lambda: _rodar(deps))


if __name__ == "__main__":
    sys.exit(main())

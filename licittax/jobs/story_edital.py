"""Job: story diario com um edital do PNCP."""
import sys
from datetime import datetime

from licittax.artes.render import TextoEstourado
from licittax.datas import hoje_brasilia, ontem_brasilia
from licittax.estado import carregar_estado, salvar_estado
from licittax.ia import encurtar
from licittax.jobs.comum import Deps, FalhaJob, agora, etapa, executar
from licittax.pncp.selecao import NenhumEditalError


def _rodar(agora_utc: datetime | None, deps: Deps) -> None:
    cfg = deps.config()
    if not cfg.ensaio:
        deps.exigir_segredos("IG_USER_ID", "IG_TOKEN", "GITHUB_REPOSITORY")
    agora_utc = agora(agora_utc)
    hoje, ontem = hoje_brasilia(agora_utc), ontem_brasilia(agora_utc)
    caminho_estado = deps.raiz / "data" / "estado.json"
    estado = etapa("ler estado", carregar_estado, caminho_estado)

    try:
        escolha = deps.escolher_edital(ontem, hoje, estado, cfg)
    except NenhumEditalError:
        raise FalhaJob("nenhum edital valido encontrado para hoje; nada foi publicado") from None
    except Exception as e:
        raise FalhaJob(f"falha em 'buscar edital no PNCP': {type(e).__name__}: {e}") from e

    cliente = deps.criar_cliente(deps.env)
    resumo = deps.resumir_objeto(escolha.edital.objeto, cliente)
    pasta = deps.saida()
    try:
        try:
            arte = deps.arte_story_edital(escolha, resumo, cfg, pasta)
        except TextoEstourado:
            arte = deps.arte_story_edital(escolha, encurtar(resumo, 60), cfg, pasta)
    except TextoEstourado:
        raise FalhaJob("o texto do edital nao coube na arte do story, mesmo encurtado") from None
    except Exception as e:
        raise FalhaJob(f"falha em 'gerar arte do story': {type(e).__name__}: {e}") from e

    if cfg.ensaio:
        print(f"[story_edital] ensaio: arte salva em {arte}")
        return

    urls = etapa("hospedar imagem", deps.hospedar, [arte], deps.raiz,
                 deps.env["GITHUB_REPOSITORY"], f"{hoje}-edital")
    ig = deps.criar_instagram(cfg, deps.env)
    etapa("publicar story", ig.publicar_story, urls[0])
    print(f"[story_edital] story publicado: {escolha.edital.numero_controle}")

    try:
        estado.add(escolha.edital.numero_controle)
        salvar_estado(estado, caminho_estado)
        deps.commitar([caminho_estado], f"chore: estado {hoje}", deps.raiz)
    except Exception as e:
        raise FalhaJob("o story FOI publicado, mas falhou em 'gravar estado': "
                       f"{type(e).__name__}: {e}") from e


def main(agora_utc: datetime | None = None, deps: Deps | None = None) -> int:
    deps = deps or Deps()
    return executar("story_edital", lambda: _rodar(agora_utc, deps))


if __name__ == "__main__":
    sys.exit(main())

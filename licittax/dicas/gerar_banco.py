"""Gera o banco de dicas: python -m licittax.dicas.gerar_banco"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from licittax.ia import ErroGeracaoDicas, criar_cliente, gerar_dicas
from licittax.dicas.banco import carregar_banco, mesclar_banco, salvar_banco
from licittax.dicas.checagem import checar_dica
from licittax.dicas.modelo import Dica
from licittax.dicas.trilhas import TRILHAS

CAMINHO = Path("data/banco_dicas.json")
CANDIDATAS = 20
MAX_APROVADAS = 15
MIN_APROVADAS = 8


def _inteiro_positivo(valor: str) -> int:
    n = int(valor)
    if n < 0:
        raise argparse.ArgumentTypeError("deve ser >= 0")
    return n


def _lista_trilhas(valor: str) -> list[int]:
    try:
        nums = [int(x) for x in valor.split(",") if x.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(f"lista de trilhas invalida: {valor!r}")
    validas = {t.numero for t in TRILHAS}
    ruins = [n for n in nums if n not in validas]
    if ruins or not nums:
        raise argparse.ArgumentTypeError(
            f"trilhas invalidas {ruins or valor!r}; use numeros entre {min(validas)} e {max(validas)}")
    return sorted(set(nums))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="python -m licittax.dicas.gerar_banco")
    ap.add_argument("--trilhas", type=_lista_trilhas, default=[t.numero for t in TRILHAS],
                    help="numeros das trilhas a processar, ex.: 1,3 (padrao: todas)")
    ap.add_argument("--candidatas", type=_inteiro_positivo, default=CANDIDATAS)
    ap.add_argument("--max-aprovadas", type=_inteiro_positivo, default=MAX_APROVADAS)
    ap.add_argument("--min-aprovadas", type=_inteiro_positivo, default=MIN_APROVADAS)
    return ap.parse_args(argv if argv is not None else [])


def _numero_id(d: Dica) -> int:
    m = re.search(r"(\d+)$", d.id)
    return int(m.group(1)) if m else 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    selecionadas = set(args.trilhas)
    cliente = criar_cliente()
    existentes = carregar_banco(CAMINHO) if CAMINHO.exists() else []
    banco: list[Dica] = []
    falhou = False
    # trilhas nao selecionadas, ainda nao processadas ou falhas mantem o que ja existia
    manter: set[int] = {t.numero for t in TRILHAS if t.numero not in selecionadas}
    pendentes = set(selecionadas)
    resumo: list[tuple[int, int, int, int]] = []

    def salvar_parcial() -> None:
        salvar_banco(mesclar_banco(banco, existentes, manter | pendentes), CAMINHO)

    for t in TRILHAS:
        if t.numero not in selecionadas:
            continue
        pendentes.discard(t.numero)
        da_trilha = [d for d in existentes if d.trilha == t.numero]
        aprov_exist = [d for d in da_trilha if d.status == "aprovada"]
        titulos: set[str] = {d.titulo.strip().casefold() for d in da_trilha}
        proximo = max((_numero_id(d) for d in da_trilha), default=0) + 1
        if len(aprov_exist) >= args.max_aprovadas:
            print(f"Trilha {t.numero} ({t.nome}): ja tem {len(aprov_exist)} aprovadas, nada a fazer")
            banco.extend(da_trilha)
            resumo.append((t.numero, 0, 0, len(aprov_exist)))
            salvar_parcial()
            continue
        try:
            brutas = gerar_dicas(t.nome, t.temas, args.candidatas, cliente)
        except ErroGeracaoDicas as e:
            print(f"Trilha {t.numero} ({t.nome}): FALHA na geração: {e}")
            falhou = True
            manter.add(t.numero)
            resumo.append((t.numero, 0, 0, len(aprov_exist)))
            salvar_parcial()
            continue
        candidatas: list[Dica] = []
        for d in brutas:
            titulo = str(d.get("titulo", "")).strip().casefold()
            if titulo in titulos:
                continue
            titulos.add(titulo)
            d = dict(d, trilha=t.numero, id=f"t{t.numero}-{proximo + len(candidatas):02d}")
            try:
                candidatas.append(Dica.from_dict(d))
            except Exception as e:
                print(f"  dica malformada ignorada: {e}")
        novas: list[Dica] = []
        aprovadas = descartadas = checadas = 0
        for dica in candidatas:
            if len(aprov_exist) + aprovadas >= args.max_aprovadas:
                break
            r = checar_dica(dica, cliente=cliente)
            checadas += 1
            if r.status == "aprovada":
                aprovadas += 1
            else:
                descartadas += 1
            novas.append(r)
        print(f"Trilha {t.numero} ({t.nome}): {aprovadas} aprovadas, {descartadas} descartadas")
        if aprovadas < args.min_aprovadas:
            falhou = True
            manter.add(t.numero)  # trilha fraca: mantem as dicas existentes
            resumo.append((t.numero, checadas, 0, len(aprov_exist)))
        else:
            banco.extend(aprov_exist + novas)
            resumo.append((t.numero, checadas, aprovadas, len(aprov_exist) + aprovadas))
        salvar_parcial()
    print("\nResumo por trilha (checadas / aprovadas novas / total aprovadas no banco):")
    for numero, checadas, novas_ok, total in resumo:
        print(f"  Trilha {numero}: {checadas} checadas, {novas_ok} aprovadas novas, {total} aprovadas no banco")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

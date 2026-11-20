"""Gera o banco de dicas: python -m licittax.dicas.gerar_banco"""
from __future__ import annotations

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


def main() -> int:
    cliente = criar_cliente()
    banco: list[Dica] = []
    falhou = False
    trilhas_falhas: set[int] = set()
    for t in TRILHAS:
        try:
            brutas = gerar_dicas(t.nome, t.temas, CANDIDATAS, cliente)
        except ErroGeracaoDicas as e:
            print(f"Trilha {t.numero} ({t.nome}): FALHA na geração: {e}")
            falhou = True
            trilhas_falhas.add(t.numero)
            continue
        titulos: set[str] = set()
        candidatas: list[Dica] = []
        for d in brutas:
            titulo = str(d.get("titulo", "")).strip().casefold()
            if titulo in titulos:
                continue
            titulos.add(titulo)
            d = dict(d, trilha=t.numero, id=f"t{t.numero}-{len(candidatas) + 1:02d}")
            try:
                candidatas.append(Dica.from_dict(d))
            except Exception as e:
                print(f"  dica malformada ignorada: {e}")
        aprovadas = descartadas = 0
        for dica in candidatas:
            if aprovadas >= MAX_APROVADAS:
                break
            r = checar_dica(dica, cliente=cliente)
            if r.status == "aprovada":
                aprovadas += 1
            else:
                descartadas += 1
            banco.append(r)
        print(f"Trilha {t.numero} ({t.nome}): {aprovadas} aprovadas, {descartadas} descartadas")
        if aprovadas < MIN_APROVADAS:
            falhou = True
    existentes = carregar_banco(CAMINHO) if CAMINHO.exists() else []
    salvar_banco(mesclar_banco(banco, existentes, trilhas_falhas), CAMINHO)
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())

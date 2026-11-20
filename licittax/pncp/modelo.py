from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from licittax.datas import BRASILIA


@dataclass(frozen=True)
class Edital:
    numero_controle: str
    cnpj_orgao: str
    ano: int
    sequencial: int
    orgao: str
    uf: str | None
    municipio: str | None
    objeto: str | None
    modalidade_id: int
    modo_disputa_id: int | None
    valor_estimado: float | None
    data_encerramento: datetime | None


def _data(texto: str | None) -> datetime | None:
    if not texto:
        return None
    dt = datetime.fromisoformat(texto)
    # A API devolve horário de Brasília sem fuso.
    return dt if dt.tzinfo else dt.replace(tzinfo=BRASILIA)


def edital_de_json(d: dict) -> Edital:
    orgao = d.get("orgaoEntidade") or {}
    unidade = d.get("unidadeOrgao") or {}
    return Edital(
        numero_controle=d["numeroControlePNCP"],
        cnpj_orgao=orgao["cnpj"],
        ano=int(d["anoCompra"]),
        sequencial=int(d["sequencialCompra"]),
        orgao=orgao.get("razaoSocial", ""),
        uf=unidade.get("ufSigla"),
        municipio=unidade.get("municipioNome"),
        objeto=d.get("objetoCompra"),
        modalidade_id=int(d["modalidadeId"]),
        modo_disputa_id=d.get("modoDisputaId"),
        valor_estimado=d.get("valorTotalEstimado") or None,
        data_encerramento=_data(d.get("dataEncerramentoProposta")),
    )

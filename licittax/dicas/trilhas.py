from dataclasses import dataclass


@dataclass(frozen=True)
class Trilha:
    numero: int
    nome: str
    temas: str


TRILHAS: tuple[Trilha, ...] = (
    Trilha(1, "Primeiros passos",
           "o que é licitação, onde achar editais, benefícios ME/EPP: exclusividade até R$ 80 mil, "
           "empate ficto, prazo extra para regularidade fiscal"),
    Trilha(2, "Cadastro", "SICAF, Compras.gov.br, portais de SP/MG/RJ"),
    Trilha(3, "Documentação", "certidões, onde emitir, validade, erros que inabilitam"),
    Trilha(4, "Disputa", "pregão eletrônico, lances, modos aberto/fechado, negociação"),
    Trilha(5, "Acompanhamento", "prazos, esclarecimento, impugnação, recurso, habilitação"),
    Trilha(6, "Gestão do contrato",
           "empenho, entrega, aditivos, reequilíbrio, recebimento, pagamento"),
)

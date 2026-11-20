from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

BRASILIA = ZoneInfo("America/Sao_Paulo")


def hoje_brasilia(agora_utc: datetime) -> date:
    return agora_utc.astimezone(BRASILIA).date()


def ontem_brasilia(agora_utc: datetime) -> date:
    return hoje_brasilia(agora_utc) - timedelta(days=1)


def dias_uteis_entre(inicio: date, fim: date) -> int:
    """Conta dias de seg a sex no intervalo (inicio, fim]."""
    total = 0
    dia = inicio + timedelta(days=1)
    while dia <= fim:
        if dia.weekday() < 5:
            total += 1
        dia += timedelta(days=1)
    return total


def eh_dia_de_post(hoje: date, inicio: date) -> bool:
    """Dias alternados: o dia de inicio da rotacao e dia de post, depois dia sim/dia nao."""
    return (hoje - inicio).days % 2 == 0

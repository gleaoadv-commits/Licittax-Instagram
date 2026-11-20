from datetime import date, datetime, timezone

from licittax.datas import dias_uteis_entre, hoje_brasilia, ontem_brasilia


def test_ontem_brasilia_vira_dia_as_3h_utc():
    assert ontem_brasilia(datetime(2026, 11, 21, 2, 0, tzinfo=timezone.utc)) == date(2026, 11, 19)
    assert ontem_brasilia(datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)) == date(2026, 11, 20)


def test_hoje_brasilia():
    assert hoje_brasilia(datetime(2026, 11, 21, 2, 0, tzinfo=timezone.utc)) == date(2026, 11, 20)


def test_dias_uteis_pula_fim_de_semana():
    assert dias_uteis_entre(date(2026, 11, 20), date(2026, 11, 27)) == 5   # sex → sex
    assert dias_uteis_entre(date(2026, 11, 21), date(2026, 11, 23)) == 1   # sáb → seg
    assert dias_uteis_entre(date(2026, 11, 23), date(2026, 11, 23)) == 0

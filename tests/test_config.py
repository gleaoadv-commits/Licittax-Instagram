from datetime import date
from pathlib import Path

from licittax.config import carregar_config


def test_carrega_valores_da_spec(tmp_path):
    cfg = carregar_config(Path("config.yaml"), env={})
    assert cfg.whatsapp == "(31) 3157-6737"
    assert cfg.ufs_prioritarias == ("SP", "MG", "RJ")
    assert cfg.modalidades == (6, 4, 8)
    assert cfg.inicio_rotacao == date(2026, 11, 21)
    assert cfg.ensaio is False


def test_modo_ensaio_por_env():
    assert carregar_config(Path("config.yaml"), env={"MODO_ENSAIO": "1"}).ensaio is True

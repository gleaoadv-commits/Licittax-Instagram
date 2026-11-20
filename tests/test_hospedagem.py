import subprocess

import pytest

from licittax.hospedagem import commitar, hospedar


class GitFalso:
    def __init__(self, falhar_em=None):
        self.chamadas = []
        self.falhar_em = falhar_em

    def __call__(self, argv, **kw):
        self.chamadas.append((argv, kw))
        rc = 1 if self.falhar_em and self.falhar_em in argv else 0
        return subprocess.CompletedProcess(argv, rc, stdout="", stderr="boom" if rc else "")


def _arqs(tmp_path):
    origem = tmp_path / "origem"
    origem.mkdir()
    a = origem / "slide1.jpg"
    b = origem / "slide2.jpg"
    a.write_bytes(b"a")
    b.write_bytes(b"b")
    return [a, b]


def test_hospedar_monta_urls_e_faz_push(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git = GitFalso()
    visitadas = []
    urls = hospedar(_arqs(tmp_path), repo, "gleaoadv-commits/licittax-instagram", "2026-11-20-dica",
                    git=git, checar_url=lambda u: visitadas.append(u) or True, espera=lambda s: None)
    base = "https://raw.githubusercontent.com/gleaoadv-commits/licittax-instagram/main/publicadas/2026-11-20-dica/"
    assert urls == [base + "slide1.jpg", base + "slide2.jpg"]
    assert visitadas == urls
    assert (repo / "publicadas" / "2026-11-20-dica" / "slide1.jpg").read_bytes() == b"a"
    comandos = [c[0][1] for c in git.chamadas]
    assert comandos == ["add", "commit", "pull", "push"]
    assert git.chamadas[1][0][-2:] == ["-m", "chore: imagens 2026-11-20-dica"]
    assert all(c[1]["cwd"] == repo for c in git.chamadas)


def test_hospedar_falha_se_url_nao_responde(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(RuntimeError):
        hospedar(_arqs(tmp_path), repo, "o/r", "p", git=GitFalso(),
                 checar_url=lambda u: False, espera=lambda s: None)


def test_commitar_falha_levanta_com_stderr(tmp_path):
    with pytest.raises(RuntimeError, match="boom"):
        commitar([tmp_path / "x"], "msg", tmp_path, git=GitFalso(falhar_em="push"))

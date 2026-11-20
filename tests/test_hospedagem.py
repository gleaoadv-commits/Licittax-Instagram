import subprocess

import pytest

from licittax.hospedagem import commitar, hospedar


class GitFalso:
    def __init__(self, falhar_em=None, rc_diff=1):
        self.chamadas = []
        self.falhar_em = falhar_em
        self.rc_diff = rc_diff  # 1 = ha algo em stage; 0 = nada

    def __call__(self, argv, **kw):
        self.chamadas.append((argv, kw))
        rc = 1 if self.falhar_em and self.falhar_em in argv else 0
        if "diff" in argv:
            rc = self.rc_diff
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
    assert comandos == ["add", "add", "diff", "commit", "pull", "push"]
    assert git.chamadas[3][0][-2:] == ["-m", "chore: imagens 2026-11-20-dica"]
    assert all(c[1]["cwd"] == repo for c in git.chamadas)


def test_hospedar_falha_se_url_nao_responde(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    n = []
    with pytest.raises(RuntimeError):
        hospedar(_arqs(tmp_path), repo, "o/r", "p", git=GitFalso(),
                 checar_url=lambda u: n.append(u) or False, espera=lambda s: None)
    assert len(n) == 12


def test_commitar_falha_levanta_com_stderr(tmp_path):
    git = GitFalso(falhar_em="push")
    with pytest.raises(RuntimeError, match="boom"):
        commitar([tmp_path / "x"], "msg", tmp_path, git=git)
    assert [c[0][1] for c in git.chamadas] == ["add", "diff", "commit", "pull", "push"]


def test_commitar_sem_nada_em_stage_nao_commita_nem_publica(tmp_path):
    git = GitFalso(rc_diff=0)
    commitar([tmp_path / "x"], "msg", tmp_path, git=git)
    assert [c[0][1] for c in git.chamadas] == ["add", "diff"]


def test_commitar_com_stage_roda_na_ordem(tmp_path):
    git = GitFalso(rc_diff=1)
    commitar([tmp_path / "x"], "msg", tmp_path, git=git)
    assert [c[0][1] for c in git.chamadas] == ["add", "diff", "commit", "pull", "push"]


def test_hospedar_remove_pastas_com_mais_de_7_dias(tmp_path):
    repo = tmp_path / "repo"
    pub = repo / "publicadas"
    for nome in ("2026-11-12-edital", "2026-11-13-dica", "2026-11-20-dica", "sem-data"):
        (pub / nome).mkdir(parents=True)
        (pub / nome / "a.jpg").write_bytes(b"x")
    git = GitFalso()
    hospedar(_arqs(tmp_path), repo, "o/r", "2026-11-20-edital", git=git,
             checar_url=lambda u: True, espera=lambda s: None)
    assert not (pub / "2026-11-12-edital").exists()      # 8 dias: removida
    assert (pub / "2026-11-13-dica").exists()            # 7 dias: mantida
    assert (pub / "2026-11-20-dica").exists() and (pub / "sem-data").exists()
    assert (pub / "2026-11-20-edital" / "slide1.jpg").exists()
    argvs = [c[0] for c in git.chamadas]
    add_all = ["git", "add", "-A", "publicadas"]
    assert add_all in argvs
    assert argvs.index(add_all) < argvs.index(["git", "commit", "-m", "chore: imagens 2026-11-20-edital"])


def test_hospedar_prefixo_sem_data_nao_remove_nada(tmp_path):
    repo = tmp_path / "repo"
    (repo / "publicadas" / "2020-01-01-x").mkdir(parents=True)
    hospedar(_arqs(tmp_path), repo, "o/r", "p", git=GitFalso(),
             checar_url=lambda u: True, espera=lambda s: None)
    assert (repo / "publicadas" / "2020-01-01-x").exists()

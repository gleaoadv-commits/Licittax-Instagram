"""Hospedagem das imagens: commit no repositorio publico e URL raw do GitHub."""
import re
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path

import requests


def _rodar(git, argv, repo_dir, aceitar=(0,)):
    r = git(argv, cwd=repo_dir, capture_output=True, text=True)
    if r.returncode not in aceitar:
        raise RuntimeError(f"git {argv[1]} falhou: {(r.stderr or '').strip()}")
    return r.returncode


def commitar(arquivos, mensagem, repo_dir, git=subprocess.run, limpar_publicadas=False):
    repo_dir = Path(repo_dir)
    _rodar(git, ["git", "add", "--", *[str(a) for a in arquivos]], repo_dir)
    if limpar_publicadas:
        _rodar(git, ["git", "add", "-A", "publicadas"], repo_dir)
    if _rodar(git, ["git", "diff", "--cached", "--quiet"], repo_dir, aceitar=(0, 1)) == 0:
        return  # nada em stage: nao ha o que commitar nem publicar
    _rodar(git, ["git", "commit", "-m", mensagem], repo_dir)
    _rodar(git, ["git", "pull", "--rebase"], repo_dir)
    _rodar(git, ["git", "push"], repo_dir)


def _url_responde(url):
    try:
        return requests.get(url, timeout=15).status_code == 200
    except requests.RequestException:
        return False


def _limpar_antigas(repo_dir: Path, prefixo: str, dias: int = 7) -> None:
    """Remove publicadas/<data>-* com mais de `dias` dias em relacao ao prefixo novo."""
    m = re.match(r"\d{4}-\d{2}-\d{2}", prefixo)
    base = repo_dir / "publicadas"
    if not m or not base.is_dir():
        return
    try:
        ref = date.fromisoformat(m.group(0))
    except ValueError:
        return
    for pasta in base.iterdir():
        mp = re.match(r"\d{4}-\d{2}-\d{2}", pasta.name)
        if not pasta.is_dir() or not mp:
            continue
        try:
            if (ref - date.fromisoformat(mp.group(0))).days > dias:
                shutil.rmtree(pasta, ignore_errors=True)
        except ValueError:
            continue


def hospedar(arquivos, repo_dir, repositorio, prefixo, git=subprocess.run,
             checar_url=_url_responde, espera=time.sleep):
    repo_dir = Path(repo_dir)
    destino = repo_dir / "publicadas" / prefixo
    destino.mkdir(parents=True, exist_ok=True)
    copiados = []
    for a in arquivos:
        alvo = destino / Path(a).name
        shutil.copyfile(a, alvo)
        copiados.append(alvo)
    _limpar_antigas(repo_dir, prefixo)
    commitar(copiados, f"chore: imagens {prefixo}", repo_dir, git=git, limpar_publicadas=True)
    base = f"https://raw.githubusercontent.com/{repositorio}/main/publicadas/{prefixo}/"
    urls = [base + c.name for c in copiados]
    for url in urls:
        for tentativa in range(12):
            if checar_url(url):
                break
            espera(5)
        else:
            raise RuntimeError(f"URL nao respondeu 200 em 60 s: {url}")
    return urls

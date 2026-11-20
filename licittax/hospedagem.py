"""Hospedagem das imagens: commit no repositorio publico e URL raw do GitHub."""
import shutil
import subprocess
import time
from pathlib import Path

import requests


def _rodar(git, argv, repo_dir, aceitar=(0,)):
    r = git(argv, cwd=repo_dir, capture_output=True, text=True)
    if r.returncode not in aceitar:
        raise RuntimeError(f"git {argv[1]} falhou: {(r.stderr or '').strip()}")
    return r.returncode


def commitar(arquivos, mensagem, repo_dir, git=subprocess.run):
    repo_dir = Path(repo_dir)
    _rodar(git, ["git", "add", "--", *[str(a) for a in arquivos]], repo_dir)
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
    commitar(copiados, f"chore: imagens {prefixo}", repo_dir, git=git)
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

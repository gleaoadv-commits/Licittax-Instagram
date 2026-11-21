from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from licittax import ia
from licittax.artes.render import TextoEstourado
from licittax.config import Config
from licittax.dicas.banco import salvar_banco
from licittax.estado import carregar_estado
from licittax.instagram import ErroInstagram
from licittax.jobs import checar_token, post_dica, story_dica, story_edital
from licittax.jobs.comum import Deps
from licittax.pncp.modelo import Edital
from licittax.pncp.selecao import Escolha, NenhumEditalError
from tests.test_legenda import dica as _dica

CFG = Config(
    whatsapp="w", cta_story="x", cta_legenda="CTA", ufs_prioritarias=("SP",),
    modalidades=(6,), modo_disputa_dispensa=4, dias_uteis_minimos=5,
    inicio_rotacao=date(2026, 11, 20), graph_versao="v23.0", hashtags=("#a",), ensaio=False,
)
ENV = {"IG_USER_ID": "1", "IG_TOKEN": "t", "GITHUB_REPOSITORY": "o/r",
       "META_APP_ID": "a", "META_APP_SECRET": "s"}
AGORA = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
EDITAL = Edital("NC1", "1", 2026, 1, "O", "SP", "M", "Objeto longo", 6, None, 10.0, None)


class IG:
    def __init__(self, falha=False, dias=30):
        self.stories, self.carrosseis, self.falha, self.dias = [], [], falha, dias

    def publicar_story(self, url):
        if self.falha:
            raise ErroInstagram("boom")
        self.stories.append(url)

    def publicar_carrossel(self, urls, legenda):
        if self.falha:
            raise ErroInstagram("boom")
        self.carrosseis.append((urls, legenda))

    def dias_ate_expirar_token(self, a, s):
        return self.dias


def fazer(tmp_path, ig=None, **kw):
    ig = ig or IG()
    chamadas = {"hospedar": [], "commitar": []}

    def arte(*a, **k):
        p = tmp_path / "saida" / "a.jpg"
        p.parent.mkdir(exist_ok=True)
        p.write_bytes(b"x")
        return p

    def hospedar(arqs, repo, repositorio, prefixo):
        chamadas["hospedar"].append(prefixo)
        return [f"https://x/{prefixo}/{i}.jpg" for i, _ in enumerate(arqs)]

    base = dict(
        env=ENV, raiz=tmp_path, cfg=CFG,
        criar_cliente=lambda env: None,
        criar_instagram=lambda cfg, env: ig,
        hospedar=hospedar,
        commitar=lambda arqs, msg, repo: chamadas["commitar"].append(msg),
        escolher_edital=lambda o, h, est, cfg: Escolha(EDITAL, True, 1),
        resumir_objeto=lambda o, c: "resumo",
        gancho_legenda=lambda t, l, c: "Gancho",
        arte_story_edital=arte, arte_story_dica=arte,
        artes_carrossel=lambda d, p: [arte(), arte()],
    )
    base.update(kw)
    return Deps(**base), ig, chamadas


def test_story_edital_publica_e_grava_estado(tmp_path):
    deps, ig, ch = fazer(tmp_path)
    assert story_edital.main(AGORA, deps) == 0
    assert ig.stories == ["https://x/2026-11-20-edital/0.jpg"]
    assert carregar_estado(tmp_path / "data" / "estado.json") == {"NC1"}
    assert ch["commitar"]


def test_story_edital_ensaio_nao_publica_nem_grava(tmp_path):
    deps, ig, ch = fazer(tmp_path, cfg=replace(CFG, ensaio=True), env={})
    assert story_edital.main(AGORA, deps) == 0
    assert not ig.stories and not ch["hospedar"] and not ch["commitar"]
    assert not (tmp_path / "data" / "estado.json").exists()


def test_story_edital_sem_edital_retorna_1_sem_publicar(tmp_path):
    def nenhum(*a):
        raise NenhumEditalError("x")
    deps, ig, ch = fazer(tmp_path, escolher_edital=nenhum)
    assert story_edital.main(AGORA, deps) == 1
    assert not ig.stories and not ch["hospedar"]


def test_story_edital_ia_fora_ainda_publica(tmp_path):
    # funcoes reais de IA com cliente None: a excecao cai no fallback
    deps, ig, _ = fazer(tmp_path, resumir_objeto=ia.resumir_objeto)
    assert story_edital.main(AGORA, deps) == 0
    assert len(ig.stories) == 1


def test_story_edital_texto_estourado_tenta_encurtado_depois_falha(tmp_path):
    n = []

    def arte(*a):
        n.append(a[1])
        raise TextoEstourado("x")
    deps, ig, _ = fazer(tmp_path, arte_story_edital=arte)
    assert story_edital.main(AGORA, deps) == 1
    assert len(n) == 2 and not ig.stories


def _banco(tmp_path):
    salvar_banco([_dica()], tmp_path / "data" / "banco_dicas.json")


def test_post_e_story_dica_usam_a_mesma_dica_no_dia(tmp_path):
    _banco(tmp_path)
    vistas = []
    deps, ig, ch = fazer(
        tmp_path,
        artes_carrossel=lambda d, p: vistas.append(d.id) or [tmp_path / "a.jpg"],
        arte_story_dica=lambda d, c, p: vistas.append(d.id) or tmp_path / "b.jpg",
    )
    assert post_dica.main(AGORA, deps) == 0
    assert story_dica.main(AGORA, deps) == 0
    assert vistas == ["t1-01", "t1-01"]
    assert "Gancho" in ig.carrosseis[0][1] and "CTA" in ig.carrosseis[0][1]
    assert ch["hospedar"] == ["2026-11-20-post", "2026-11-20-story-dica"]


def test_post_dica_ensaio_escreve_legenda(tmp_path):
    _banco(tmp_path)
    deps, ig, ch = fazer(tmp_path, cfg=replace(CFG, ensaio=True), env={})
    assert post_dica.main(AGORA, deps) == 0
    assert (tmp_path / "saida" / "legenda.txt").read_text(encoding="utf-8").startswith("Gancho")
    assert not ig.carrosseis and not ch["hospedar"]


def test_falha_no_instagram_retorna_1(tmp_path):
    _banco(tmp_path)
    deps, ig, ch = fazer(tmp_path, ig=IG(falha=True))
    assert story_edital.main(AGORA, deps) == 1
    assert post_dica.main(AGORA, deps) == 1
    assert story_dica.main(AGORA, deps) == 1
    assert not (tmp_path / "data" / "estado.json").exists()


def test_segredos_ausentes_retorna_1(tmp_path):
    deps, ig, ch = fazer(tmp_path, env={})
    assert story_edital.main(AGORA, deps) == 1
    assert not ch["hospedar"]


def test_checar_token_avisa_com_10_dias(tmp_path):
    assert checar_token.main(deps=fazer(tmp_path, ig=IG(dias=10))[0]) == 1
    assert checar_token.main(deps=fazer(tmp_path, ig=IG(dias=11))[0]) == 0
    assert checar_token.main(deps=fazer(tmp_path, ig=IG(dias=None))[0]) == 0


def test_checar_token_erro_retorna_1(tmp_path):
    ig = IG()

    def falha(a, s):
        raise ErroInstagram("invalido")
    ig.dias_ate_expirar_token = falha
    assert checar_token.main(deps=fazer(tmp_path, ig=ig)[0]) == 1


def test_story_edital_fim_de_semana_recua_ate_achar(tmp_path):
    datas = []

    def escolher(o, h, est, cfg):
        datas.append(o)
        if o > date(2026, 11, 17):
            raise NenhumEditalError("x")
        return Escolha(EDITAL, True, 1)
    deps, ig, _ = fazer(tmp_path, escolher_edital=escolher)
    assert story_edital.main(AGORA, deps) == 0
    assert datas == [date(2026, 11, 19), date(2026, 11, 18), date(2026, 11, 17)]
    assert ig.stories


def test_story_edital_sem_edital_em_3_dias_falha(tmp_path):
    datas = []

    def nenhum(o, *a):
        datas.append(o)
        raise NenhumEditalError("x")
    deps, ig, _ = fazer(tmp_path, escolher_edital=nenhum)
    assert story_edital.main(AGORA, deps) == 1
    assert len(datas) == 3 and not ig.stories


DIA_POST = AGORA                                   # idx 0 (post)
DIA_SEM_POST = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)  # idx 1


def test_post_dica_em_dia_sem_post_nao_faz_nada(tmp_path, capsys):
    deps, ig, ch = fazer(
        tmp_path,
        artes_carrossel=lambda *a: (_ for _ in ()).throw(AssertionError("render")),
        criar_cliente=lambda env: (_ for _ in ()).throw(AssertionError("ia")),
    )
    assert post_dica.main(DIA_SEM_POST, deps) == 0
    assert "Hoje não é dia de post." in capsys.readouterr().out
    assert not ig.carrosseis and not ch["hospedar"]


def test_story_da_tarde_em_dia_sem_post_publica_segundo_edital(tmp_path):
    deps, ig, ch = fazer(tmp_path)
    assert story_dica.main(DIA_SEM_POST, deps) == 0
    assert ch["hospedar"] == ["2026-11-21-edital-tarde"]
    assert len(ig.stories) == 1 and ch["commitar"]


def test_story_da_tarde_ensaio_edital_usa_outro_nome_de_arquivo(tmp_path):
    deps, ig, ch = fazer(tmp_path, cfg=replace(CFG, ensaio=True), env={},
                         arte_story_edital=lambda e, r, c, p: _escrever(p / "story_edital.jpg"))
    assert story_dica.main(DIA_SEM_POST, deps) == 0
    assert (tmp_path / "saida" / "story_edital_tarde.jpg").exists()
    assert not (tmp_path / "saida" / "story_edital.jpg").exists()


def _escrever(p):
    p.parent.mkdir(exist_ok=True, parents=True)
    p.write_bytes(b"x")
    return p


def test_dicas_avancam_so_nos_dias_de_post(tmp_path):
    from licittax.jobs.comum import dica_de_hoje
    dicas = [replace(_dica(), id=f"t{t}-0{n}", trilha=t) for t in (1, 2, 3) for n in (1, 2)]
    salvar_banco(dicas, tmp_path / "data" / "banco_dicas.json")
    deps, _, _ = fazer(tmp_path)
    ini = CFG.inicio_rotacao
    d = lambda idx: dica_de_hoje(deps, CFG, ini + timedelta(days=idx)).id
    assert d(0) != d(2) != d(4)
    assert d(0) != d(4)
    assert d(0) == d(1)  # dia sem post: idx 1 nao e dia de post (mesma posicao, nao usada)


def test_horario_de_reserva_nao_publica_de_novo(tmp_path):
    _banco(tmp_path)
    deps, ig, _ = fazer(tmp_path)
    for job in (story_edital, post_dica, story_dica):
        assert job.main(AGORA, deps) == 0
        assert job.main(AGORA + timedelta(hours=2), deps) == 0
    assert len(ig.stories) == 2 and len(ig.carrosseis) == 1


def test_falha_no_primeiro_horario_reserva_tenta_de_novo(tmp_path):
    deps, ig, _ = fazer(tmp_path, ig=IG(falha=True))
    assert story_edital.main(AGORA, deps) == 1
    ig.falha = False
    assert story_edital.main(AGORA + timedelta(hours=2), deps) == 0
    assert len(ig.stories) == 1


def test_story_da_tarde_nao_confunde_com_edital_da_manha(tmp_path):
    deps, ig, _ = fazer(tmp_path)
    amanha = AGORA + timedelta(days=1)  # dia sem post: tarde publica 2o edital
    assert story_edital.main(amanha, deps) == 0
    assert story_dica.main(amanha + timedelta(hours=9), deps) == 0
    assert len(ig.stories) == 2

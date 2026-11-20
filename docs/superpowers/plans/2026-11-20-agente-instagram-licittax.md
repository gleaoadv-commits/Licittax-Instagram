# Agente Instagram @licittax — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um programa Python que roda sozinho no GitHub Actions e publica, todo dia, 1 story de edital do PNCP (09h), 1 carrossel de dica (12h) e 1 story de dica (18h) no Instagram @licittax.

**Architecture:** Pacote `licittax/` com módulos pequenos e independentes (PNCP, seleção, leis, IA, banco de dicas, artes, hospedagem, Instagram) costurados por 3 jobs. Artes são modelos HTML/Jinja renderizados em JPEG pelo Playwright. Imagens são commitadas no próprio repositório público e servidas por `raw.githubusercontent.com`; a Graph API do Instagram busca dessa URL. O banco de dicas é gerado e checado uma vez (workflow manual) e a dica do dia é calculada pela data, sem estado.

**Tech Stack:** Python 3.12, requests, jinja2, playwright (chromium), anthropic SDK, pyyaml, beautifulsoup4, pillow, pytest, responses.

**Spec:** `docs/superpowers/specs/2026-11-20-agente-instagram-licittax-design.md`

## Global Constraints

- Idioma de todo texto publicado: português do Brasil.
- WhatsApp: `(31) 3157-6737` — aparece nas artes de **story** e na **legenda** do feed; **nunca** nas artes do feed.
- Stories sem link e sem figurinha (a API só recebe a imagem).
- Story 1080×1920; feed (carrossel) 1080×1350. **Formato JPEG** (a Graph API não aceita PNG).
- Horários Brasília → cron UTC: story edital `0 12 * * *`, post dica `0 15 * * *`, story dica `0 21 * * *`. Todos os dias, inclusive fim de semana.
- UFs prioritárias: `SP`, `MG`, `RJ`.
- Modalidades PNCP aceitas: `6` Pregão eletrônico, `4` Concorrência eletrônica, `8` Dispensa **somente com `modoDisputaId == 4`** (dispensa com disputa). Demais excluídas.
- Edital precisa ter ≥ 5 dias úteis (seg–sex, sem feriados) entre hoje e `dataEncerramentoProposta`.
- Edital: período = dia anterior (data de publicação) no fuso `America/Sao_Paulo`.
- Valor sigiloso/ausente (`valorTotalEstimado` nulo ou 0): a arte omite a linha de valor.
- Visual: estilo do post de referência `assets/referencias/post-2026-11-19-prazos-art55.jpg`. Cores `#041831`, `#142445`, `#084865`, `#1F8A7A`, branco. Fonte Poppins (Regular, SemiBold, Bold, ExtraBold). Ícone oficial `assets/brand/icone.png`.
- Rodapé das artes: ícone + `@licittax` + `Assessoria & Consultoria em Licitações`.
- Última tela do carrossel: `Confira a legenda!`.
- Dicas: 6 trilhas, até 15 aprovadas por trilha; só dicas com status `aprovada` são publicadas.
- Nada é publicado pela metade: qualquer falha antes do `media_publish` aborta o job com código de saída ≠ 0 (o GitHub manda e-mail ao dono).
- Segredos só via variáveis de ambiente (GitHub Secrets): `IG_USER_ID`, `IG_TOKEN`, `META_APP_ID`, `META_APP_SECRET`, `ANTHROPIC_API_KEY`. Nunca no código ou no repositório.
- Modelos Claude: `claude-sonnet-5-5` (resumo e gancho), `claude-opus-5-5` (gerar e verificar dicas). **Ao escrever `licittax/ia.py`, carregue a skill `claude-api` antes.**
- `MODO_ENSAIO=1`: gera as artes e a legenda em `saida/`, não hospeda, não publica, não altera estado.

**Ajuste em relação à spec (§7, token):** em vez de renovar automaticamente um token de 60 dias (o que exigiria o workflow reescrever os próprios secrets), o caminho "sem portfólio" usa o **token de Página derivado de token de longa duração, que não expira**. Nos dois casos, o job semanal `checar-token` avisa por e-mail se o token estiver inválido ou a ≤ 10 dias de vencer.

## Review Focus

- PNCP lento/instável (HTTP 429/5xx, timeout, 204 sem conteúdo, muitas páginas): o job tenta de novo e, sem nenhum edital válido, falha com mensagem clara, sem publicar nada → testes em Task 2 e Task 3.
- Nome de órgão ou objeto muito longos: o texto não pode estourar a arte → resumo limitado a 90 caracteres (Task 5) e detecção de estouro no render (Task 7).
- Instagram devolve container com `status_code` `ERROR` ou nunca `FINISHED`; um slide do carrossel falha → nada é publicado (Task 8).
- API do Claude fora do ar ou sem crédito na hora de publicar: o job publica com fallback (objeto encurtado, legenda sem gancho), não falha (Task 5).
- O número de WhatsApp vazar para uma arte do feed (por exemplo, dentro do texto de uma dica) → teste do HTML renderizado do carrossel (Task 7).

---

## Estrutura de arquivos

```
.gitignore
requirements.txt
pytest.ini
config.yaml
licittax/__init__.py
licittax/config.py            # carrega config.yaml + env
licittax/datas.py             # ontem_brasilia, dias_uteis_entre
licittax/estado.py            # editais já publicados (data/estado.json)
licittax/pncp/modelo.py       # dataclass Edital
licittax/pncp/client.py       # chamadas HTTP ao PNCP
licittax/pncp/selecao.py      # escolha do edital do dia (regras)
licittax/leis.py              # baixa e extrai artigo de lei do Planalto
licittax/ia.py                # todas as chamadas ao Claude
licittax/dicas/trilhas.py     # as 6 trilhas
licittax/dicas/modelo.py      # Dica, Slide, Afirmacao, Citacao (+ JSON)
licittax/dicas/checagem.py    # regras + verificação de citação
licittax/dicas/banco.py       # carregar/salvar banco, dica_do_dia
licittax/dicas/gerar_banco.py # CLI única: gera + checa + grava banco
licittax/artes/render.py      # HTML → JPEG, detecção de estouro
licittax/artes/templates/     # base.css + 5 templates .html.j2
licittax/artes/preparar_icone.py
licittax/legenda.py           # monta legenda do feed
licittax/hospedagem.py        # commit das imagens + URL pública
licittax/instagram.py         # Graph API: story, carrossel, token
licittax/jobs/story_edital.py
licittax/jobs/post_dica.py
licittax/jobs/story_dica.py
licittax/jobs/checar_token.py
data/estado.json
data/banco_dicas.json         # gerado na Task 10
assets/fonts/Poppins-*.ttf
assets/brand/icone-transparente.png
.github/workflows/{testes,story-edital,post-dica,story-dica,checar-token,gerar-banco}.yml
docs/CONFIGURACAO.md          # guia passo a passo para o dono
tests/...
```

---

### Task 1: Base do projeto, configuração e datas

**Files:**
- Create: `.gitignore`, `requirements.txt`, `pytest.ini`, `config.yaml`, `licittax/__init__.py`, `licittax/config.py`, `licittax/datas.py`, `data/estado.json`, `licittax/estado.py`
- Test: `tests/test_config.py`, `tests/test_datas.py`, `tests/test_estado.py`

**Interfaces:**
- Produces:
  - `Config` (dataclass frozen) com campos: `whatsapp: str`, `cta_story: str`, `cta_legenda: str`, `ufs_prioritarias: tuple[str, ...]`, `modalidades: tuple[int, ...]`, `modo_disputa_dispensa: int`, `dias_uteis_minimos: int`, `inicio_rotacao: date`, `graph_versao: str`, `hashtags: tuple[str, ...]`, `ensaio: bool`
  - `carregar_config(caminho: Path = Path("config.yaml"), env: Mapping[str,str] = os.environ) -> Config` (`ensaio` vem de `env.get("MODO_ENSAIO") == "1"`)
  - `ontem_brasilia(agora_utc: datetime) -> date`
  - `hoje_brasilia(agora_utc: datetime) -> date`
  - `dias_uteis_entre(inicio: date, fim: date) -> int` — conta seg–sex no intervalo `(inicio, fim]`; 0 se `fim <= inicio`
  - `carregar_estado(caminho: Path) -> set[str]` e `salvar_estado(publicados: set[str], caminho: Path) -> None` (JSON `{"editais_publicados": [ordenados]}`)

- [ ] **Step 1: Iniciar o repositório**

Run: `git init` e `git checkout -b main` na raiz. `.gitignore`: `__pycache__/`, `.venv/`, `saida/`, `.pytest_cache/`, `.env`.
Expected: `git status` mostra a pasta como repositório.

- [ ] **Step 2: Criar `requirements.txt`, `pytest.ini` e `config.yaml`**

`requirements.txt`: `requests`, `jinja2`, `playwright`, `anthropic`, `pyyaml`, `beautifulsoup4`, `pillow`, `pytest`, `responses` (fixar versões estáveis atuais).
`pytest.ini`: `testpaths = tests`.
`config.yaml` (copiar exatamente):

```yaml
whatsapp: "(31) 3157-6737"
cta_story: "Quer participar? Fale com a Licittax"
cta_legenda: "📲 A Licittax cuida de tudo para sua empresa vender para o governo. Fale no WhatsApp (31) 3157-6737 ou chame no direct."
ufs_prioritarias: [SP, MG, RJ]
modalidades: [6, 4, 8]
modo_disputa_dispensa: 4
dias_uteis_minimos: 5
inicio_rotacao: 2026-11-21
graph_versao: "v23.0"
hashtags: ["#licitacao", "#licitacoes", "#lei14133", "#pregao", "#comprapublica", "#mei", "#epp", "#licittax"]
```

- [ ] **Step 3: Escrever testes que falham**

```python
# tests/test_config.py
def test_carrega_valores_da_spec(tmp_path):
    cfg = carregar_config(Path("config.yaml"), env={})
    assert cfg.whatsapp == "(31) 3157-6737"
    assert cfg.ufs_prioritarias == ("SP", "MG", "RJ")
    assert cfg.modalidades == (6, 4, 8)
    assert cfg.inicio_rotacao == date(2026, 11, 21)
    assert cfg.ensaio is False

def test_modo_ensaio_por_env():
    assert carregar_config(Path("config.yaml"), env={"MODO_ENSAIO": "1"}).ensaio is True

# tests/test_datas.py
def test_ontem_brasilia_vira_dia_as_3h_utc():
    assert ontem_brasilia(datetime(2026, 11, 21, 2, 0, tzinfo=timezone.utc)) == date(2026, 11, 19)
    assert ontem_brasilia(datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)) == date(2026, 11, 20)

def test_dias_uteis_pula_fim_de_semana():
    assert dias_uteis_entre(date(2026, 11, 20), date(2026, 11, 27)) == 5   # sex → sex
    assert dias_uteis_entre(date(2026, 11, 21), date(2026, 11, 23)) == 1   # sáb → seg
    assert dias_uteis_entre(date(2026, 11, 23), date(2026, 11, 23)) == 0

# tests/test_estado.py
def test_estado_ida_e_volta(tmp_path):
    p = tmp_path / "estado.json"
    salvar_estado({"b", "a"}, p)
    assert json.loads(p.read_text())["editais_publicados"] == ["a", "b"]
    assert carregar_estado(p) == {"a", "b"}

def test_estado_inexistente_e_vazio(tmp_path):
    assert carregar_estado(tmp_path / "nao.json") == set()
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `python -m pytest -v`
Expected: FAIL (ImportError).

- [ ] **Step 5: Implementar `config.py`, `datas.py`, `estado.py`** com as assinaturas acima. `datas` usa `zoneinfo.ZoneInfo("America/Sao_Paulo")`. `data/estado.json` inicial: `{"editais_publicados": []}`.

- [ ] **Step 6: Rodar e ver passar**

Run: `python -m pip install -r requirements.txt` e `python -m pytest -v`
Expected: todos PASS.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: base do projeto, configuração, datas e estado"
```

---

### Task 2: Cliente da API do PNCP

**Files:**
- Create: `licittax/pncp/__init__.py`, `licittax/pncp/modelo.py`, `licittax/pncp/client.py`
- Create: `tests/fixtures/pncp_contratacoes.json`, `tests/fixtures/pncp_itens.json` (capturados da API real)
- Test: `tests/test_pncp_client.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True)
  class Edital:
      numero_controle: str            # numeroControlePNCP
      cnpj_orgao: str                 # orgaoEntidade.cnpj
      ano: int                        # anoCompra
      sequencial: int                 # sequencialCompra
      orgao: str                      # orgaoEntidade.razaoSocial
      uf: str | None                  # unidadeOrgao.ufSigla
      municipio: str | None           # unidadeOrgao.municipioNome
      objeto: str | None              # objetoCompra
      modalidade_id: int              # modalidadeId
      modo_disputa_id: int | None     # modoDisputaId
      valor_estimado: float | None    # valorTotalEstimado (0 → None)
      data_encerramento: datetime | None  # dataEncerramentoProposta
  ```
  - `buscar_contratacoes(data: date, modalidade_id: int, uf: str | None, sessao: requests.Session | None = None) -> list[Edital]`
  - `tem_item_exclusivo_me_epp(edital: Edital, sessao: requests.Session | None = None) -> bool`
  - `class ErroPNCP(Exception)`

Endpoints:
- Lista: `GET https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao?dataInicial=AAAAMMDD&dataFinal=AAAAMMDD&codigoModalidadeContratacao={id}&uf={UF}&pagina={n}&tamanhoPagina=50` (sem `uf` quando `None`). Resposta: `{"data": [...], "totalPaginas": N}`; HTTP 204 = lista vazia.
- Itens: `GET https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens`. Exclusivo ME/EPP ⇔ algum item com `tipoBeneficioId == 1`.

- [ ] **Step 1: Capturar fixtures reais**

Run (bash): `curl -s "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao?dataInicial=20261119&dataFinal=20261119&codigoModalidadeContratacao=6&uf=SP&pagina=1&tamanhoPagina=5" -o tests/fixtures/pncp_contratacoes.json`, depois chame o endpoint de itens para o primeiro resultado e salve em `tests/fixtures/pncp_itens.json`.
Expected: JSON válido. **Confira os nomes de campo acima contra a fixture**; se algum diferir, use o nome real e registre no commit.

- [ ] **Step 2: Testes que falham** (usar `responses`)

```python
def test_converte_campos_da_fixture(): ...  # 1º Edital tem numero_controle, uf == "SP", modalidade_id == 6
def test_valor_zero_vira_none(): ...        # valorTotalEstimado 0 → valor_estimado is None
def test_pagina_ate_total_paginas(): ...    # totalPaginas=3 → 3 requisições, itens somados
def test_204_retorna_lista_vazia(): ...
def test_tenta_de_novo_em_429_e_500(): ...  # 500, 429, 200 → sucesso com 3 chamadas (espera injetada/zerada)
def test_falha_apos_3_tentativas(): ...     # 500 x3 → ErroPNCP
def test_exclusivo_me_epp(): ...            # itens com tipoBeneficioId 1 → True; só 4/5 → False
```

- [ ] **Step 3: Rodar e ver falhar** — `python -m pytest tests/test_pncp_client.py -v` → FAIL.

- [ ] **Step 4: Implementar** `modelo.py` e `client.py`. Timeout 30 s; 3 tentativas com espera 2 s/5 s em 429/5xx/timeout (espera injetável para os testes); limite de 20 páginas.

- [ ] **Step 5: Rodar e ver passar** — PASS.

- [ ] **Step 6: Commit** — `git commit -m "feat: cliente da API do PNCP"`

---

### Task 3: Escolha do edital do dia

**Files:**
- Create: `licittax/pncp/selecao.py`
- Test: `tests/test_selecao.py`

**Interfaces:**
- Consumes: `Edital`, `buscar_contratacoes`, `tem_item_exclusivo_me_epp` (Task 2); `Config`, `dias_uteis_entre` (Task 1)
- Produces:
  - `class NenhumEditalError(Exception)`
  - `@dataclass(frozen=True) class Escolha: edital: Edital; exclusivo_me_epp: bool; prioridade: int`
  - `escolher_edital(data_publicacao: date, hoje: date, ja_publicados: set[str], cfg: Config, buscar=buscar_contratacoes, checar_exclusivo=tem_item_exclusivo_me_epp) -> Escolha`

Regras (nesta ordem):
1. Válido = tem `objeto`, `uf`, `data_encerramento`; `modalidade_id in cfg.modalidades`; se `modalidade_id == 8` exige `modo_disputa_id == cfg.modo_disputa_dispensa`; `numero_controle not in ja_publicados`; `dias_uteis_entre(hoje, data_encerramento.date()) >= cfg.dias_uteis_minimos`.
2. Busca primeiro, para cada modalidade, as UFs prioritárias (uma chamada por UF). Ordena os válidos por `valor_estimado` decrescente (`None` por último).
3. Prioridade 1: o primeiro dessa lista com `checar_exclusivo == True` (checa no máximo 40). Prioridade 2: o primeiro da lista.
4. Só se a lista prioritária estiver vazia: busca nacional (`uf=None`) e aplica as mesmas regras de validade/ordenação → prioridade 3 (exclusividade checada só no escolhido, para o selo).
5. Nada válido → `NenhumEditalError`. Uma `ErroPNCP` numa UF/modalidade é registrada e as demais buscas continuam; se **todas** falharem, propaga `ErroPNCP`.

- [ ] **Step 1: Testes que falham** (com `buscar`/`checar_exclusivo` falsos)

```python
def test_prefere_prioritaria_exclusiva_mesmo_com_valor_menor(): ...  # SP 1M não-exclusivo, MG 100k exclusivo → MG, prioridade 1
def test_sem_exclusivo_pega_maior_valor_prioritario(): ...          # prioridade 2
def test_cai_para_nacional_so_sem_prioritarias(): ...                # nacional chamado só nesse caso; prioridade 3
def test_descarta_dispensa_sem_disputa(): ...                        # modalidade 8, modo 5 → ignorado
def test_descarta_prazo_curto(): ...                                 # 4 dias úteis → ignorado
def test_descarta_ja_publicado_e_sem_objeto(): ...
def test_valor_none_vai_para_o_fim(): ...
def test_nenhum_valido_levanta_erro(): ...
def test_falha_parcial_do_pncp_continua(): ...                       # SP levanta ErroPNCP, MG ok → escolhe MG
def test_falha_total_do_pncp_propaga(): ...
```

- [ ] **Step 2: Rodar e ver falhar** → FAIL.
- [ ] **Step 3: Implementar `escolher_edital`** conforme as regras.
- [ ] **Step 4: Rodar e ver passar** → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat: seleção do edital do dia"`

---

### Task 4: Texto oficial das leis (Planalto)

**Files:**
- Create: `licittax/leis.py`
- Create: `tests/fixtures/l14133_trecho.html` (trecho real salvo do Planalto contendo Art. 54, 55, 56, com um `<strike>`)
- Test: `tests/test_leis.py`

**Interfaces:**
- Produces:
  - `FONTES: dict[str, str]` — `"Lei 14.133/2021": "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"`, `"LC 123/2006": "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm"`. Decretos: chave `"Decreto N/AAAA"` → URL informada na própria citação (campo `url` da `Citacao`, Task 6).
  - `extrair_artigo(html: str, artigo: str) -> str` — `artigo` como `"55"`, `"48"`, `"3-A"`; remove `<strike>`/`<s>` (texto revogado); devolve do `Art. 55` até antes do próximo `Art. <n>`.
  - `texto_artigo(norma: str, artigo: str, url: str | None = None, sessao=None) -> str` — baixa (cache por URL em memória; decodifica `windows-1252` quando o cabeçalho não informar), chama `extrair_artigo`.
  - `class ArtigoNaoEncontrado(Exception)`

- [ ] **Step 1: Salvar fixture** com o trecho real (arts. 54–56) da página do Planalto.
- [ ] **Step 2: Testes que falham**

```python
def test_extrai_art_55_sem_invadir_56(): ...       # contém "oito dias úteis"; não contém "Art. 56"
def test_ignora_texto_riscado(): ...
def test_reconhece_ordinal(): ...                   # "Art. 1º" encontrado com artigo="1"
def test_artigo_inexistente_levanta(): ...
def test_cache_baixa_uma_vez(): ...                 # 2 chamadas, 1 requisição (responses)
```

- [ ] **Step 3–4: Ver falhar, implementar com BeautifulSoup, ver passar.**
- [ ] **Step 5: Commit** — `git commit -m "feat: extração de artigos de lei do Planalto"`

---

### Task 5: Chamadas ao Claude (com fallback)

> Carregue a skill `claude-api` antes de escrever este módulo.

**Files:**
- Create: `licittax/ia.py`
- Test: `tests/test_ia.py`

**Interfaces:**
- Produces:
  - `MODELO_RAPIDO = "claude-sonnet-5-5"`, `MODELO_RIGOROSO = "claude-opus-5-5"`
  - `encurtar(texto: str, limite: int) -> str` — corta na última palavra inteira e põe `…`; nunca passa de `limite`
  - `resumir_objeto(objeto: str, cliente) -> str` — ≤ 90 caracteres, linguagem simples, sem inventar; se a API falhar ou passar do limite → `encurtar(objeto, 90)`
  - `gancho_legenda(titulo: str, legenda_base: str, cliente) -> str` — uma frase ≤ 150 caracteres, sem números de lei novos; em falha → `""`
  - `@dataclass(frozen=True) class Verificacao: sustenta: bool; motivo: str`
  - `verificar_afirmacao(afirmacao: str, dispositivo: str, texto_lei: str, cliente) -> Verificacao` — prompt independente ("você é revisor jurídico; responda só se o texto de lei sustenta integralmente a afirmação"); saída JSON estruturada; qualquer erro/JSON inválido → `Verificacao(False, "erro na verificação")`
  - `gerar_dicas(trilha_nome: str, trilha_temas: str, quantidade: int, cliente) -> list[dict]` — JSON no formato de `Dica.from_dict` (Task 6), status `"pendente"`
  - `criar_cliente(env=os.environ)` → `anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"])`

- [ ] **Step 1: Testes que falham** (cliente falso que devolve resposta fixa ou levanta)

```python
def test_encurtar_respeita_limite_e_palavra(): ...   # len <= 90, termina com "…", sem palavra cortada
def test_resumo_fallback_quando_api_falha(): ...
def test_resumo_fallback_quando_passa_de_90(): ...
def test_gancho_vazio_quando_api_falha(): ...
def test_verificacao_le_json(): ...                  # {"sustenta": true, "motivo": "..."} → True
def test_verificacao_json_invalido_reprova(): ...
```

- [ ] **Step 2–4: Ver falhar, implementar, ver passar.**
- [ ] **Step 5: Commit** — `git commit -m "feat: chamadas ao Claude com fallback"`

---

### Task 6: Banco de dicas — modelo, checagem, rotação e geração

**Files:**
- Create: `licittax/dicas/__init__.py`, `trilhas.py`, `modelo.py`, `checagem.py`, `banco.py`, `gerar_banco.py`
- Test: `tests/test_dicas_checagem.py`, `tests/test_dicas_banco.py`

**Interfaces:**
- Consumes: `texto_artigo`, `ArtigoNaoEncontrado` (Task 4); `verificar_afirmacao`, `gerar_dicas`, `criar_cliente` (Task 5)
- Produces:
  - `TRILHAS: tuple[Trilha, ...]` com `Trilha(numero: int, nome: str, temas: str)` — 6 trilhas exatamente como na spec §4 (Primeiros passos; Cadastro; Documentação; Disputa; Acompanhamento; Gestão do contrato), `temas` copiando a lista entre parênteses da spec.
  - ```python
    @dataclass(frozen=True) class Citacao: norma: str; artigo: str; dispositivo: str = ""; url: str | None = None
    @dataclass(frozen=True) class Afirmacao: texto: str; citacao: Citacao | None
    @dataclass(frozen=True) class Slide: titulo: str; itens: tuple[str, ...]
    @dataclass(frozen=True) class Dica:
        id: str; trilha: int; titulo: str; slides: tuple[Slide, ...]; frase_story: str
        legenda_base: str; afirmacoes: tuple[Afirmacao, ...]; hashtags: tuple[str, ...]
        status: str = "pendente"; motivo: str = ""
        def base_legal(self) -> str   # ex.: "Lei 14.133/2021, art. 55; LC 123/2006, art. 48" (sem repetir)
        def to_dict(self) -> dict; @staticmethod def from_dict(d: dict) -> "Dica"
    ```
  - `checar_dica(dica: Dica, obter_texto=texto_artigo, verificar=verificar_afirmacao, cliente=None) -> Dica` — devolve cópia com `status` `"aprovada"` ou `"descartada"` e `motivo`
  - `carregar_banco(caminho: Path) -> list[Dica]`, `salvar_banco(dicas: list[Dica], caminho: Path) -> None`
  - `dica_do_dia(banco: list[Dica], dia: date, inicio: date) -> Dica`
  - `gerar_banco.main()` — `python -m licittax.dicas.gerar_banco`

Regras de `checar_dica` (descarta na primeira que falhar, `motivo` diz qual):
1. 3 ≤ `len(slides)` ≤ 6; `len(titulo)` ≤ 60; `len(frase_story)` ≤ 120.
2. Nenhum texto (título, slides, frase, legenda_base) contém `3157-6737` nem outro telefone (regex `\(?\d{2}\)?\s?\d{4,5}-\d{4}`).
3. Toda `Afirmacao` tem `citacao`.
4. Afirmação com `R$` exige citação cuja `norma` comece com `"Decreto"`.
5. Para cada afirmação: `obter_texto(norma, artigo, url)`; `ArtigoNaoEncontrado`/erro de rede → descarta; `verificar(...)` com `sustenta=False` → descarta.

`dica_do_dia`: só `aprovada`. `idx = (dia - inicio).days`; trilha = `TRILHAS[idx % 6]`; posição = `(idx // 6) % len(aprovadas_da_trilha)`, em ordem de `id`. Trilha sem aprovadas → próxima trilha. Banco sem aprovadas → `ValueError`. Dia anterior a `inicio` usa `idx` negativo com `%` do Python (funciona).

`gerar_banco.main()`: para cada trilha gera 20 candidatas, checa todas, guarda até 15 aprovadas **e** as descartadas (auditoria) em `data/banco_dicas.json`; imprime resumo por trilha; sai com código 1 se alguma trilha tiver < 8 aprovadas.

- [ ] **Step 1: Testes que falham**

```python
# checagem (obter_texto e verificar falsos)
def test_aprova_dica_valida(): ...
def test_descarta_afirmacao_sem_citacao(): ...
def test_descarta_valor_em_reais_sem_decreto(): ...
def test_descarta_quando_verificador_nega(): ...
def test_descarta_quando_artigo_nao_existe(): ...
def test_descarta_telefone_no_texto(): ...
def test_descarta_slides_fora_de_3_a_6(): ...
def test_base_legal_sem_repeticao(): ...
# banco
def test_ida_e_volta_json(tmp_path): ...
def test_dica_do_dia_alterna_trilhas(): ...     # dias consecutivos → trilhas 1,2,3,4,5,6,1
def test_dica_do_dia_avanca_dentro_da_trilha(): ...  # dia 0 e dia 6 → mesma trilha, dicas diferentes
def test_ignora_descartadas_e_pula_trilha_vazia(): ...
def test_mesmo_dia_mesma_dica(): ...
```

- [ ] **Step 2–4: Ver falhar, implementar, ver passar.**
- [ ] **Step 5: Commit** — `git commit -m "feat: banco de dicas com checagem automática e rotação"`

---

### Task 7: Artes (modelos HTML → JPEG)

**Files:**
- Create: `licittax/artes/__init__.py`, `licittax/artes/render.py`, `licittax/artes/preparar_icone.py`
- Create: `licittax/artes/templates/base.css`, `story_edital.html.j2`, `story_dica.html.j2`, `carrossel_capa.html.j2`, `carrossel_slide.html.j2`, `carrossel_final.html.j2`
- Create: `assets/fonts/Poppins-{Regular,SemiBold,Bold,ExtraBold}.ttf` (Google Fonts, licença OFL), `assets/brand/icone-transparente.png`
- Test: `tests/test_artes.py`

**Interfaces:**
- Consumes: `Escolha` (Task 3, contém `Edital` e `exclusivo_me_epp`), `Dica` (Task 6), `Config` (Task 1)
- Produces:
  - `class TextoEstourado(Exception)`
  - `renderizar(template: str, contexto: dict, saida: Path, largura: int, altura: int) -> Path` — JPEG qualidade 92
  - `html_de(template: str, contexto: dict) -> str` (para testes)
  - `arte_story_edital(escolha: Escolha, resumo: str, cfg: Config, pasta: Path) -> Path`
  - `arte_story_dica(dica: Dica, cfg: Config, pasta: Path) -> Path`
  - `artes_carrossel(dica: Dica, pasta: Path) -> list[Path]` — capa + 1 por slide + final

Visual (todas): fundo gradiente `#041831`→`#142445`; arco `#084865` no canto superior direito; tag em pílula `#1F8A7A` texto branco Poppins SemiBold; título Poppins ExtraBold branco alinhado à esquerda; itens numerados com círculo `#084865`; linha "Base legal: …" cinza claro; divisória fina; rodapé com `icone-transparente.png` + `@licittax` + `Assessoria & Consultoria em Licitações`; faixa `#1F8A7A` na base. Margens laterais 80 px. Reproduza o layout da referência `assets/referencias/post-2026-11-19-prazos-art55.jpg`.
- Story edital: tag `EDITAL NOVO`; selo `EXCLUSIVO ME/EPP` (pílula branca, texto `#041831`) só se `exclusivo_me_epp`; órgão; resumo do objeto (título); linhas `📍 Município/UF`, `💰 Valor estimado: R$ X` (omitida se `None`; formato `R$ 1.234.567,89`), `📅 Propostas até: dd/mm/aaaa`; faixa inferior `#1F8A7A` com `cta_story` + `WhatsApp (31) 3157-6737`. Conteúdo entre y=250 e y=1670 (áreas seguras do story).
- Story dica: tag `DICA RÁPIDA`; `frase_story` grande; `base_legal()`; mesma faixa de chamada.
- Carrossel: capa com tag `VOCÊ SABIA?` + título; slides com título + itens numerados (+ base legal no último slide); final `Confira a legenda!`. **Sem WhatsApp.**
- Estouro: todo bloco de texto tem a classe `ajustar`; após carregar, o Playwright avalia `[...document.querySelectorAll('.ajustar')].some(e => e.scrollHeight > e.clientHeight + 1)` → `TextoEstourado`.
- `preparar_icone.py`: torna transparentes os pixels quase brancos (R,G,B > 240) de `assets/brand/icone.png` e grava `icone-transparente.png`. Rodar uma vez e commitar o resultado.

- [ ] **Step 1: Baixar as fontes e gerar o ícone transparente** — `python -m licittax.artes.preparar_icone`; Expected: arquivo criado e cantos com alfa 0.
- [ ] **Step 2: Testes que falham**

```python
def test_story_edital_tem_whatsapp_e_selo(): ...        # html_de contém "(31) 3157-6737" e "EXCLUSIVO ME/EPP"
def test_story_edital_sem_valor_omite_linha(): ...      # valor None → "Valor estimado" ausente
def test_formata_valor_em_reais(): ...                  # 1234567.89 → "R$ 1.234.567,89"
def test_carrossel_nunca_tem_whatsapp(): ...            # nenhum html do carrossel contém "3157-6737"
def test_carrossel_tem_capa_slides_e_final(): ...       # 3 slides → 5 arquivos; último contém "Confira a legenda!"
def test_jpeg_no_tamanho_certo(tmp_path): ...           # story 1080x1920, feed 1080x1350, formato JPEG (Pillow)
def test_texto_gigante_estoura(tmp_path): ...           # título com 600 caracteres → TextoEstourado
```

- [ ] **Step 3: Rodar e ver falhar.** Run: `python -m playwright install chromium` e `python -m pytest tests/test_artes.py -v` → FAIL.
- [ ] **Step 4: Implementar templates e `render.py`.**
- [ ] **Step 5: Rodar e ver passar** → PASS. Abrir 1 JPEG de cada tipo gerado no teste e comparar visualmente com a referência; ajustar até ficar no mesmo estilo.
- [ ] **Step 6: Commit** — `git commit -m "feat: modelos de arte e renderização em JPEG"`

---

### Task 8: Hospedagem das imagens e publicação no Instagram

**Files:**
- Create: `licittax/hospedagem.py`, `licittax/instagram.py`
- Test: `tests/test_instagram.py`, `tests/test_hospedagem.py`

**Interfaces:**
- Produces:
  - `hospedar(arquivos: list[Path], repo_dir: Path, repositorio: str, prefixo: str, git=subprocess.run, checar_url=..., espera=time.sleep) -> list[str]` — copia para `publicadas/<prefixo>/`, `git add` + `git commit -m "chore: imagens <prefixo>"` + `git pull --rebase` + `git push`; devolve `https://raw.githubusercontent.com/<repositorio>/main/publicadas/<prefixo>/<nome>`; aguarda cada URL responder 200 (até 60 s).
  - `commitar(arquivos: list[Path], mensagem: str, repo_dir: Path, git=subprocess.run) -> None` — `git add` dos arquivos, `git commit -m mensagem`, `git pull --rebase`, `git push`; levanta `RuntimeError` se algum comando falhar. Usado por `hospedar` e pelo job `story_edital` (Task 9) para gravar `data/estado.json`.
  - `class ErroInstagram(Exception)`
  - ```python
    class Instagram:
        def __init__(self, ig_user_id: str, token: str, versao: str, sessao=None, espera=time.sleep): ...
        def publicar_story(self, url_imagem: str) -> str            # devolve media id
        def publicar_carrossel(self, urls: list[str], legenda: str) -> str
        def dias_ate_expirar_token(self, app_id: str, app_secret: str) -> int | None  # None = não expira
    ```

Graph API (`https://graph.facebook.com/{versao}`):
- Story: `POST /{ig}/media` `image_url`, `media_type=STORIES` → container; aguarda; `POST /{ig}/media_publish` `creation_id`.
- Carrossel: um `POST /{ig}/media` por imagem com `is_carousel_item=true`; aguarda cada um; `POST /{ig}/media` `media_type=CAROUSEL`, `children=<ids separados por vírgula>`, `caption`; aguarda; `media_publish`.
- Aguardar = `GET /{container}?fields=status_code` a cada 5 s, até 12 vezes; `FINISHED` segue; `ERROR`/`EXPIRED`/tempo esgotado → `ErroInstagram` **antes** de qualquer `media_publish`.
- Token: `GET /debug_token?input_token={token}&access_token={app_id}|{app_secret}` → `data.expires_at` (0 = não expira; `is_valid` falso → `ErroInstagram`).

- [ ] **Step 1: Testes que falham** (`responses`; `espera` zerada; `git` e `checar_url` falsos)

```python
def test_story_cria_container_e_publica(): ...
def test_carrossel_cria_filhos_pai_e_publica_uma_vez(): ...
def test_filho_com_erro_nao_publica_nada(): ...           # nenhuma chamada a media_publish
def test_container_nunca_finished_nao_publica(): ...
def test_token_sem_expiracao_retorna_none(): ...
def test_token_invalido_levanta(): ...
def test_hospedar_monta_urls_e_faz_push(tmp_path): ...    # URLs no formato raw; comandos git na ordem add/commit/pull/push
def test_hospedar_falha_se_url_nao_responde(tmp_path): ...
```

- [ ] **Step 2–4: Ver falhar, implementar, ver passar.**
- [ ] **Step 5: Commit** — `git commit -m "feat: hospedagem de imagens e publicação na Graph API"`

---

### Task 9: Legenda e os jobs de publicação

**Files:**
- Create: `licittax/legenda.py`, `licittax/jobs/__init__.py`, `story_edital.py`, `post_dica.py`, `story_dica.py`, `checar_token.py`
- Test: `tests/test_legenda.py`, `tests/test_jobs.py`

**Interfaces:**
- Consumes: tudo das Tasks 1–8
- Produces:
  - `montar_legenda(dica: Dica, gancho: str, cfg: Config) -> str` = `[gancho]` + `legenda_base` + `"📚 Base legal: " + dica.base_legal()` + `cfg.cta_legenda` + hashtags (de `dica.hashtags` ∪ `cfg.hashtags`, sem repetir, máx. 30), blocos separados por linha em branco; gancho vazio é omitido; ≤ 2200 caracteres (se passar, corta `legenda_base` com `encurtar`).
  - Cada job: `main(agora_utc: datetime | None = None, deps: Deps | None = None) -> int` (0 ok, 1 erro) e `if __name__ == "__main__": sys.exit(main())`. `Deps` agrupa as funções externas (cliente IA, Instagram, hospedar, buscar PNCP) para os testes injetarem falsos.

Fluxos:
- **story_edital:** `escolher_edital(ontem_brasilia, hoje_brasilia, carregar_estado(...))` → `resumir_objeto` → `arte_story_edital` → se ensaio: salvar em `saida/` e sair 0 → `hospedar(prefixo=f"{hoje}-edital")` → `publicar_story` → adicionar `numero_controle` ao estado, `salvar_estado`, commit+push do `data/estado.json`.
- **post_dica:** `dica_do_dia(banco, hoje, cfg.inicio_rotacao)` → `artes_carrossel` → `gancho_legenda` → `montar_legenda` → ensaio? → `hospedar(prefixo=f"{hoje}-post")` → `publicar_carrossel`.
- **story_dica:** mesma `dica_do_dia` → `arte_story_dica` → ensaio? → `hospedar(prefixo=f"{hoje}-story-dica")` → `publicar_story`.
- **checar_token:** `dias_ate_expirar_token`; `None` ou > 10 → 0; ≤ 10 ou erro → imprime aviso e retorna 1.
- Qualquer exceção: imprime a mensagem em português (o que falhou e em que etapa) e retorna 1. Nada é publicado depois de uma falha.

- [ ] **Step 1: Testes que falham**

```python
# legenda
def test_legenda_termina_com_cta_e_hashtags(): ...      # contém "(31) 3157-6737"; hashtags após o CTA
def test_legenda_sem_gancho_nao_tem_linha_vazia_extra(): ...
def test_legenda_respeita_2200_e_30_hashtags(): ...
# jobs (deps falsos)
def test_story_edital_publica_e_grava_estado(tmp_path): ...
def test_story_edital_ensaio_nao_publica_nem_grava(tmp_path): ...
def test_story_edital_sem_edital_retorna_1_sem_publicar(): ...
def test_story_edital_ia_fora_ainda_publica(): ...      # resumir cai no fallback, publica normalmente
def test_post_e_story_dica_usam_a_mesma_dica_no_dia(): ...
def test_falha_no_instagram_retorna_1(): ...
def test_checar_token_avisa_com_10_dias(): ...
```

- [ ] **Step 2–4: Ver falhar, implementar, ver passar.** Run: `python -m pytest -v` → todos PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat: legenda e jobs de publicação"`

---

### Task 10: GitHub Actions, guia de configuração e entrada no ar

**Files:**
- Create: `.github/workflows/testes.yml`, `story-edital.yml`, `post-dica.yml`, `story-dica.yml`, `checar-token.yml`, `gerar-banco.yml`
- Create: `docs/CONFIGURACAO.md`
- Create (gerado): `data/banco_dicas.json`

**Workflows (comum a todos de publicação):** `on: schedule` (cron da Global Constraints) + `workflow_dispatch` com input `ensaio` (boolean, padrão `false`); `permissions: contents: write`; `concurrency: { group: licittax-publicacao, cancel-in-progress: false }`; passos: `actions/checkout@v4`, `actions/setup-python@v5` (3.12, cache pip), `pip install -r requirements.txt`, `python -m playwright install --with-deps chromium`, configurar `git config user.name "licittax-bot"` / `user.email "<id>+github-actions[bot]@users.noreply.github.com"`, rodar `python -m licittax.jobs.<job>` com `env:` dos 5 secrets + `MODO_ENSAIO: ${{ inputs.ensaio && '1' || '0' }}`; em ensaio, `actions/upload-artifact@v4` da pasta `saida/`.
- `testes.yml`: em `push` → `pytest`.
- `checar-token.yml`: cron `0 11 * * 1`, sem Playwright.
- `gerar-banco.yml`: só `workflow_dispatch`; roda `python -m licittax.dicas.gerar_banco`, commita `data/banco_dicas.json`.

**`docs/CONFIGURACAO.md`** — guia para leigo, em português, com prints descritos em texto, nesta ordem:
1. Criar repositório **público** `licittax-instagram` na conta GitHub do dono e enviar o código (comandos exatos).
2. Criar app na Meta (developers.facebook.com), tipo Empresa, produto "Instagram Graph API"; anotar App ID e App Secret.
3. Verificar se existe portfólio empresarial em business.facebook.com e se o dono é administrador dele e da Página da Licittax.
   - **Sim:** criar Usuário do Sistema (admin), atribuir a Página/conta do Instagram e o app, gerar token **sem expiração** com permissões `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `business_management`.
   - **Não:** no Graph API Explorer, gerar token de usuário com as mesmas permissões → trocar por token de longa duração (`/oauth/access_token?grant_type=fb_exchange_token`) → pegar o **token da Página** em `/me/accounts` (token de Página obtido de token longo não expira).
4. ID da conta do Instagram: `17841464593621126` (confirmar em `/{page-id}?fields=instagram_business_account`).
5. Cadastrar em Settings → Secrets and variables → Actions: `IG_USER_ID`, `IG_TOKEN`, `META_APP_ID`, `META_APP_SECRET`, `ANTHROPIC_API_KEY` (criada em console.anthropic.com → API Keys). Nunca colar chaves em conversa ou arquivo.
6. Aviso: os e-mails de falha vão para quem editou por último o agendamento (cron) — deve ser a conta do dono.
7. Parar as publicações manuais pelo Claude Code no navegador quando o agente entrar no ar.

- [ ] **Step 1: Escrever os 6 workflows e o guia.**
- [ ] **Step 2: Verificar localmente** — Run: `python -m pytest -v` → todos PASS; `MODO_ENSAIO=1 python -m licittax.jobs.story_edital` (com `ANTHROPIC_API_KEY` no ambiente local do dono, ou sem ela para testar o fallback) → JPEG em `saida/`; abrir e conferir visualmente.
- [ ] **Step 3: Commit** — `git commit -m "feat: workflows do GitHub Actions e guia de configuração"`
- [ ] **Step 4: Com o dono, seguir `docs/CONFIGURACAO.md` passos 1–5.** Expected: workflow `testes` verde no GitHub.
- [ ] **Step 5: Rodar `gerar-banco` manualmente.** Expected: resumo com ≥ 8 aprovadas por trilha; `data/banco_dicas.json` commitado. Conferir 3 dicas aprovadas e 3 descartadas (motivos fazem sentido).
- [ ] **Step 6: Rodar os 3 jobs com `ensaio = true`.** Expected: artefatos com 1 story de edital, 1 carrossel, 1 story de dica; mostrar ao dono.
- [ ] **Step 7: Rodar `checar-token` manualmente.** Expected: verde.
- [ ] **Step 8: Rodar `story-edital` sem ensaio uma vez.** Expected: story aparece no @licittax; `data/estado.json` com o `numero_controle`. A partir daqui os agendamentos seguem sozinhos.

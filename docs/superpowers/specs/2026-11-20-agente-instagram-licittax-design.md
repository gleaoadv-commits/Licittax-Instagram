# Agente de publicação automática — Instagram @licittax

Data: 2026-11-20 · Status: aprovado pelo dono em 2026-11-20

## 1. Intenção e porquê

A Licittax (Assessoria & Consultoria em Licitações) quer manter o Instagram @licittax ativo todos os dias sem trabalho manual. Hoje as publicações são feitas pelo Claude Code no navegador, que pede permissão a cada passo — por isso o objetivo é um agente **totalmente automático**, sem aprovação humana diária.

O conteúdo serve para atrair empresas — principalmente **ME e EPP** (que têm benefícios legais na LC 123/2006) — que ainda não sabem participar de licitações, e fazê-las procurar a assessoria pelo WhatsApp.

Dores reais do público, segundo o dono: não sabem por onde começar, não sabem se cadastrar, não sabem o que é o SICAF, não sabem tirar certidões, não sabem dar lances, não sabem acompanhar processos e não sabem acompanhar a execução do contrato (a Licittax também faz gestão contratual).

## 2. O que é publicado (dias alternados — atualizado pelo dono em 2026-11-20)

Para economizar dicas e crédito, os dias se alternam. O dia 0 da rotação (`inicio_rotacao`) é dia de post; a partir dele, alterna.

| Dia | 09:00 | 12:00 | 18:00 |
|-----|-------|-------|-------|
| **Dia de post** | Story: edital do PNCP | Post no feed — carrossel (1080×1350) com a dica | Story: dica rápida, mesmo tema do post |
| **Dia sem post** | Story: edital do PNCP | — | Story: **outro** edital (o próximo melhor, nunca repetido) |

Stories 1080×1920. Todos os dias, incluindo fins de semana *(chamada do Claude)*. O segundo edital às 18h é chamada do Claude (dono pediu "horários diferentes"). A dica avança só nos dias de post, então cada dica cobre 2 dias de calendário.

### Contato comercial (decidido pelo dono)
- **Stories:** sem link, sem figurinhas. A arte traz uma chamada comercial e o número **(31) 3157-6737** escrito na imagem.
- **Post do feed:** a arte **não** mostra o número. A **legenda** (gerada pelo agente) termina com chamada + WhatsApp (31) 3157-6737.
- Número e frase de chamada ficam num único arquivo de configuração.

## 3. Story do edital (PNCP)

**Fonte:** API pública de consulta do PNCP (`https://pncp.gov.br/api/consulta`), contratações publicadas no **dia anterior**.

**Seleção (em ordem de prioridade):**
1. UF em **SP, MG ou RJ** e com pelo menos um item com **benefício de participação exclusiva ME/EPP** (informação por item, endpoint de itens da contratação).
2. UF em SP, MG ou RJ, sem exclusividade.
3. Qualquer UF.

**Modalidades aceitas:** pregão eletrônico, concorrência e dispensa com disputa (dispensa eletrônica). Excluídas: inexigibilidade e dispensa sem disputa — o seguidor não teria como participar.

**Concorrência:** só na forma eletrônica *(chamada do Claude)*.

**Valor sigiloso ou ausente:** o edital pode entrar; a arte omite a linha de valor *(chamada do Claude)*.

**Desempate dentro da mesma prioridade:** *(chamada do Claude)* maior valor estimado entre os que ainda têm data de abertura de propostas a pelo menos 5 dias úteis, para dar tempo de o interessado procurar a assessoria.

**Regras de segurança:**
- Texto vem só dos dados oficiais (órgão, objeto, município/UF, valor estimado, data de abertura). O Claude apenas **resume o objeto** em linguagem simples; não inventa nada.
- Se faltar campo essencial (objeto, UF, data de abertura), descarta e passa para o próximo.
- Guarda o histórico de editais publicados; nunca repete.

**Conteúdo da arte:** tag "EDITAL NOVO", selo "EXCLUSIVO ME/EPP" quando aplicável, órgão, objeto resumido, cidade/UF, valor estimado, data de abertura, faixa inferior com chamada + (31) 3157-6737.

## 4. Dicas (post + story de dica)

**Banco de dicas pré-gerado**, não criação livre diária — é o ponto de maior risco jurídico.
- ~90 dicas em **6 trilhas** (~15 cada), seguindo a jornada do cliente:
  1. Primeiros passos (o que é licitação, onde achar editais, benefícios ME/EPP: exclusividade até R$ 80 mil, empate ficto, prazo extra para regularidade fiscal)
  2. Cadastro (SICAF, Compras.gov.br, portais de SP/MG/RJ)
  3. Documentação (certidões, onde emitir, validade, erros que inabilitam)
  4. Disputa (pregão eletrônico, lances, modos aberto/fechado, negociação)
  5. Acompanhamento (prazos, esclarecimento, impugnação, recurso, habilitação)
  6. Gestão do contrato (empenho, entrega, aditivos, reequilíbrio, recebimento, pagamento)
- Cada dica cita a **base legal** (Lei 14.133/2021, LC 123/2006, decretos) quando houver.
- O banco é gerado uma vez com o Claude e salvo como arquivo (JSON/YAML) no repositório.
- **Ninguém revisa o banco manualmente (decisão do dono).** No lugar disso, uma **checagem automática** roda antes de cada dica entrar no banco como "aprovada":
  - Toda afirmação jurídica precisa ter citação (lei, artigo, inciso/parágrafo).
  - O texto oficial do dispositivo citado é baixado de fonte oficial (Planalto para Lei 14.133/2021, LC 123/2006 e decretos federais) e uma segunda chamada ao Claude, independente da que escreveu a dica, confirma se o dispositivo sustenta a afirmação.
  - Dica com citação que não confere, afirmação sem citação, ou valor em reais que muda por decreto anual (ex.: limites de dispensa) sem o decreto vigente citado → **descartada**.
  - Só dicas aprovadas são publicadas. O resultado da checagem fica registrado por dica (aprovada/descartada + motivo).
- **O dono aceita o risco residual** de uma dica errada passar pela checagem automática.
- **Rotação:** troca de trilha a cada dia (1→2→…→6→1) e segue em ordem dentro da trilha. Quando o banco acabar, recomeça (ou gera-se um novo lote — fora do escopo inicial).
- Cada dica no banco contém: título, slides do carrossel (3–6 telas), frase curta para o story, legenda-base, base legal, hashtags.
- **Uso do Claude na hora de publicar:** apenas para variar levemente a legenda (abertura/fechamento), sem alterar o conteúdo técnico. Se a chamada à API falhar, usa a legenda-base do banco.

## 5. Identidade visual

Seguir o **estilo do post de 19/11/2026** (referência salva em `assets/referencias/post-2026-11-19-prazos-art55.jpg`) — *(assumido pelo Claude por ser o mais recente; o dono pode trocar para o estilo antigo azul royal)*:
- Fundo marinho escuro em gradiente (≈ `#041831` → `#142445`), detalhe circular em azul-petróleo (`#084865`) no canto superior direito.
- Tag em pílula verde (`#1F8A7A`) com texto branco ("VOCÊ SABIA?", "EDITAL NOVO", "DICA RÁPIDA").
- Título em **Poppins Bold/ExtraBold** branco, alinhado à esquerda; corpo em Poppins Regular.
- Listas numeradas com marcadores circulares azul-petróleo.
- Linha "Base legal: …" em cinza claro, divisória fina, rodapé "@licittax / Assessoria & Consultoria em Licitações", faixa verde na base.
- Ícone oficial: `assets/brand/icone.png`; logo horizontal: `assets/brand/logo-horizontal.png` (o dono pediu o uso do ícone oficial).
- Carrossel: capa com título + tag; telas internas com o passo a passo; última tela "Confira a legenda!". Sem número de WhatsApp nas artes do feed.
- Stories: mesma linguagem em 1080×1920, com faixa de chamada + número na parte inferior (respeitando as áreas seguras de topo/base do Instagram).
- Artes geradas por **modelos HTML/CSS renderizados para PNG** (ex.: Playwright), sempre idênticos; sem fotos de banco de imagem.

## 6. Abordagens consideradas

| | Abordagem | Prós | Contras |
|---|---|---|---|
| A | Rotina agendada do Claude na nuvem, publicando via Windsor.ai | Parecida com o que o dono já faz | Resultado varia a cada dia; depende do Windsor, que está no plano gratuito (já bloqueou uma função) |
| B | Script Python no GitHub Actions, modelos fixos, API oficial do Instagram | Zero permissões, grátis, determinístico | Sem IA: resumo do objeto do edital ficaria cortado/robótico |
| **C** | **B + chamadas pontuais à API do Claude** | Confiável como B, texto natural no resumo do edital e na legenda | Custo de centavos/mês; exige chave da API do Claude |

**Escolhida pelo dono: C.**

## 7. Arquitetura (decidida)

- **Execução:** GitHub Actions com 3 agendamentos (cron em UTC = horário de Brasília +3h). Um job por publicação, para que a falha de um não impeça os outros.
- **Linguagem:** Python.
- **Repositório:** na conta GitHub **do dono** (ele já tem conta), para que os avisos de falha cheguem ao e-mail dele. *(chamada do Claude)* Repositório **público** — simplifica a hospedagem das imagens e mantém o GitHub Actions gratuito; segredos ficam em *secrets*, e artes e editais já são públicos no Instagram.
- **Publicação:** Instagram Graph API oficial (conta Profissional @licittax, já ligada a Página do Facebook — a conexão via Facebook Login no Windsor indica isso), via app da Meta.
- **Token da Meta:** o dono não sabe se tem portfólio empresarial (Gerenciador de Negócios) nem se é admin. O guia de configuração começa verificando isso com ele, passo a passo:
  - Se existir portfólio e ele for admin → **token de usuário do sistema**, que não expira.
  - Se não → token de longa duração (60 dias) com **renovação automática** por um job semanal e aviso por e-mail se a renovação falhar, com pelo menos 10 dias de antecedência do vencimento.
- **IA:** API do Claude (Anthropic) só para: resumo do objeto do edital e variação da legenda.
- **Hospedagem das imagens:** a Graph API exige URL pública. *(chamada do Claude)* As imagens são publicadas num endereço público do próprio GitHub (ex.: GitHub Pages ou branch pública de assets) antes da publicação.
- **Estado:** histórico de editais publicados e posição na rotação de dicas, salvos no repositório (commit automático pelo próprio workflow).
- **Segredos:** token da Meta, ID da conta do Instagram e chave da API do Claude como *secrets* do GitHub. Nunca no código.
- **Falhas:** se algo falhar (PNCP fora, Instagram recusa, imagem não gera), **não publica nada pela metade** e envia aviso por e-mail ao dono (notificação de falha do GitHub Actions serve como primeira versão).

## 8. Objetivos, não-objetivos, anti-objetivos

**Objetivos:** 3 publicações/dia sem intervenção; visual consistente com a marca; editais relevantes para ME/EPP de SP/MG/RJ; dicas juridicamente corretas.

**Não-objetivos (por ora):** responder comentários/directs; Reels/vídeo; relatórios de desempenho; publicar em outras redes; aprovação prévia pelo dono.

**Anti-objetivos (seria fracasso mesmo funcionando):**
- Dica com informação jurídica errada publicada com o nome da Licittax.
- Edital com dado inventado ou errado (valor, data, órgão).
- Arte fora da identidade visual ou com texto estourando.
- Repetir o mesmo edital ou a mesma dica em sequência.
- Número de WhatsApp aparecendo na arte do feed.

## 9. Restrições

- A API do Instagram não permite link nem figurinha em stories (de acordo com o que o dono quer).
- A API do Claude é cobrada à parte da assinatura do Claude (precisa de conta em console.anthropic.com com crédito).
- Limite da Graph API: 50 publicações por 24h — muito acima do uso.
- O dono não é programador: a configuração inicial (app da Meta, tokens, secrets) precisa de um guia passo a passo.
- A publicação manual atual pelo Claude Code no navegador deve parar quando o agente entrar no ar, para não duplicar.

## 10. Deixado para quem construir

- Estrutura do código, bibliotecas, formato do banco de dicas.
- Detalhes exatos de layout dentro do estilo descrito.
- Estratégia exata de hospedagem pública das imagens.
- Testes e modo "ensaio" (gerar sem publicar) para validação antes de ligar.

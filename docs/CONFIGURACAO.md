# Configuração do agente de Instagram da Licittax

Este guia é uma **referência** do que já foi configurado e de como refazer cada parte (por exemplo, se o token do Instagram precisar ser gerado de novo). Não precisa saber programar. **Nunca cole chaves, tokens ou senhas em conversas, e-mails ou arquivos do repositório** — elas só entram nos "Secrets" do GitHub.

## O que o agente faz sozinho (horário de Brasília)

- 09h: story com um edital do dia anterior (SP, MG ou RJ).
- 12h: post (carrossel) com a dica do dia.
- 18h: story com a mesma dica.
- Segunda-feira, 08h: verificação do token do Instagram (avisa por e-mail se estiver com problema).

## 1. Repositório no GitHub

O repositório é **público** e se chama `licittax-instagram`, na conta `gleaoadv-commits`: https://github.com/gleaoadv-commits/licittax-instagram

Para refazer (pasta do projeto, no terminal):

```
git init
git branch -M main
git remote add origin https://github.com/gleaoadv-commits/licittax-instagram.git
git add .
git commit -m "primeiro envio"
git push -u origin main
```

Depois, em **Settings → Actions → General → Workflow permissions**, marque **Read and write permissions** e salve (o agente precisa gravar arquivos no repositório).

## 2. App na Meta

1. Entre em https://developers.facebook.com e clique em **Meus Apps → Criar app**.
2. Tipo: **Empresa**. Adicione o produto **Instagram Graph API**.
3. Em **Configurações do app → Básico**, anote o **ID do app** e a **Chave Secreta do app** (App Secret).

O ID do app (é público, pode aparecer aqui) é `1183457757344997`. A chave secreta fica só nos Secrets.

## 3. Token do Instagram

Primeiro, em https://business.facebook.com, confira se existe um **portfólio empresarial** e se o dono é **administrador** dele e da Página da Licittax.

### Caminho A — existe portfólio empresarial (o que está em uso)

1. Em **Configurações do negócio → Usuários → Usuários do sistema**, crie um usuário do sistema com função **Administrador**.
2. Em **Atribuir ativos**, dê a ele controle da **Página** da Licittax, da **conta do Instagram** e do **app**.
3. Clique em **Gerar token**, escolha o app e marque **Sem expiração** (nunca expira), com as permissões:
   `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `business_management`.
4. Copie o token e cole direto no Secret `IG_TOKEN` (passo 5). Não guarde em outro lugar.

### Caminho B — não existe portfólio empresarial

1. Abra o **Graph API Explorer** (https://developers.facebook.com/tools/explorer), escolha o app, gere um **token de usuário** com as mesmas cinco permissões acima.
2. Troque por um token de longa duração, abrindo (com o App ID, o App Secret e o token curto no lugar indicado):
   `https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=ID_DO_APP&client_secret=CHAVE_SECRETA&fb_exchange_token=TOKEN_CURTO`
3. Com o token longo no Explorer, consulte `/me/accounts` e copie o **access_token da Página** da Licittax. Token de Página obtido de um token longo **não expira**. Esse é o valor de `IG_TOKEN`.

## 4. ID da conta do Instagram

O ID é `17841464593621126`. Para confirmar: no Graph API Explorer, consulte `/{id-da-pagina}?fields=instagram_business_account` — o número que aparece em `instagram_business_account → id` deve ser esse.

## 5. Secrets do GitHub

No repositório: **Settings → Secrets and variables → Actions → New repository secret**. Os cinco nomes (exatamente assim, em maiúsculas):

| Nome | O que é |
|---|---|
| `IG_USER_ID` | `17841464593621126` |
| `IG_TOKEN` | token do passo 3 |
| `META_APP_ID` | `1183457757344997` |
| `META_APP_SECRET` | chave secreta do app (passo 2) |
| `ANTHROPIC_API_KEY` | chave criada em https://console.anthropic.com → **API Keys** |

Para trocar o token: abra o Secret `IG_TOKEN`, clique em **Update** e cole o novo valor.

## 6. Como rodar manualmente (inclusive em "ensaio")

1. No repositório, aba **Actions**.
2. Escolha o fluxo na lista à esquerda (Story de edital, Post de dica, Story de dica, Checar token, Gerar banco de dicas).
3. Clique em **Run workflow**.
4. Nos fluxos de publicação aparece a caixa **Ensaio**. **Marcada**: gera as imagens e a legenda, mas **não publica nada**; as imagens ficam no fim da página da execução, em **Artifacts** (baixe o .zip). **Desmarcada**: publica de verdade.

## 7. Onde ver falhas

- Aba **Actions**: execuções com um X vermelho falharam. Clique nela e abra o passo em vermelho para ler a mensagem (em português).
- O GitHub também manda **e-mail** em cada falha. Atenção: o e-mail vai para quem editou por último o agendamento (cron) dos fluxos — deve ser a conta do dono. Se não chegar, confira as notificações em github.com/settings/notifications.
- Nada é publicado pela metade: se algo falha antes da publicação, o job para.

## 8. Como mudar horários e WhatsApp

- **WhatsApp, textos de chamada, hashtags, UFs**: edite o arquivo `config.yaml` (no GitHub: abra o arquivo, ícone de lápis, salve com **Commit changes**). Mantenha as aspas e o formato.
- **Horários**: ficam nos arquivos `.github/workflows/*.yml`, na linha `cron`. O horário é em **UTC** (Brasília + 3h): `0 12 * * *` = 09h, `0 15 * * *` = 12h, `0 21 * * *` = 18h. Ao editar, a conta que salvou passa a receber os e-mails de falha.

## 9. Importante: parar as publicações manuais

Quando o agente entrar no ar, **pare de publicar manualmente pelo Claude Code no navegador**, para não haver posts duplicados nem conflito de horários.

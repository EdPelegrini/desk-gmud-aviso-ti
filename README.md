<p align="center"><img src="assets/logo-gmud-aviso-128.png" alt="Aviso de GMUD aprovada" width="96"></p>

# Aviso de GMUD aprovada (Desk Manager + Teams)

Automação em **Maestro** (iPaaS do Desk Manager) que avisa o grupo de TI no **Microsoft Teams** quando uma **GMUD** (Gestão de Mudança) é aprovada por todos os aprovadores, e manda um **lembrete no dia da execução**.

> **Projeto de exemplo.** Todos os nomes, empresas, IDs e URLs deste repositório são fictícios
> (empresa "Empresa Exemplo S.A.", prefixo `exemplo`, pessoas "Ana Souza" e "Bruno Almeida").
> Nenhuma chave, URL de webhook ou dado real está versionado. Adapte à realidade do seu ambiente.

## O que faz

| Recurso | Quando dispara | O que envia |
|---|---|---|
| **Aviso de aprovação** | Webhook do evento *Aprovação/Reprovação de Chamados* | Cartão no Teams: número, título, resumo, solicitante, executor, período, aprovadores e botão "Abrir chamado" |
| **Lembrete do dia** | Cron diário às 07:00 | Um cartão por GMUD que **começa hoje**, em Agendamento ou Andamento |

Conteúdo do cartão (dados fictícios):

```
GMUD aprovada: 0001-000123
TI - Infraestrutura - GMUD - Planejada
Atualização de segurança dos servidores do ambiente corporativo...
Solicitante   Carlos Mendes
Executor      TI - Infraestrutura N2
Período       27/10/2026 22:00 a 27/10/2026 23:00
Aprovadores   Ana Souza, Bruno Almeida
[ Abrir chamado ]
```

## Arquitetura

```
Desk Manager ──(evento 6: aprovação/reprovação)──► Webhook ──► Maestro "GMUD Aprovada - Aviso TI"
Cron 07:00 (Tipo 2) ──── {"acao":"lembrete"} ───────────────────────────────┘
                                                                              │ Python (1 bloco)
                              consulta GMUDs/AutoCategorias na API do Desk ◄──┤
                                                                              ▼
                                                              Workflows do Teams ──► grupo de TI
```

Detalhes em [docs/arquitetura.md](docs/arquitetura.md) e regras em [docs/regras-de-negocio.md](docs/regras-de-negocio.md).

## Estrutura

```
src/parse_aviso.py     bloco Python do Maestro (aviso, lembrete, ler, limpar)
scripts/desk-lib.ps1   helpers de autenticação e chamadas à API
scripts/publicar.ps1   publica o fluxo e as constantes no Maestro
assets/                logo (SVG e PNG)
docs/                  arquitetura e regras de negócio
.env.example           variáveis necessárias (copie para .env)
```

## Como usar

1. **Crie o Maestro** no Desk Manager (nome sugerido: `GMUD Aprovada - Aviso TI`) e anote a chave.
2. **Teams:** no chat ou canal de destino, em *Workflows*, use o modelo **"Enviar alertas de webhook para um chat"** (ou *canal*) e copie a URL do webhook.
3. **Configure o `.env`** a partir do `.env.example` (prefixo, chaves de integração, chave do Maestro, URL do Teams).
4. **Webhook do Desk:** crie um webhook no evento *Aprovação/Reprovação de Chamados* apontando para a Invoke URL POST do Maestro.
5. **Publique** com o envio desligado e teste primeiro:

   ```powershell
   .\scripts\publicar.ps1                          # tudo desligado: só gera prévias
   .\scripts\publicar.ps1 -TeamsAtivo S            # liga o aviso de aprovação
   .\scripts\publicar.ps1 -TeamsAtivo S -LembreteAtivo S   # liga também o lembrete
   ```
6. **Cron do lembrete:** crie um cron **Tipo 2** (chama Maestro) às 07:00, fuso `America/Sao_Paulo`, com corpo `{"acao":"lembrete"}`.
   > Atenção: cron Tipo 2 **executa ao ser salvo**. Salve-o com o lembrete desligado.

### Testes sem enviar nada ao grupo

Faça POST na Invoke URL do Maestro:

| Corpo | Efeito |
|---|---|
| `{"acao":"ler"}` | Devolve decisões, log do lembrete, prévias e total de avisados |
| `{"acao":"limpar"}` | Zera o armazenamento do Maestro |
| `{"acao":"lembrete","data_simulada":"2026-10-27"}` | Simula o lembrete de uma data (nunca envia) |
| evento com `"sem_envio":"S"` | Roda a regra do aviso sem enviar, sem deduplicar e sem gravar log |
| `"agora_simulada":"AAAA-MM-DD HH:MM"` | Simula o relógio (só junto com `sem_envio`) |

## Cuidados

- A **URL do webhook do Teams e as chaves de API são credenciais**. Fique só no `.env`, que está no `.gitignore`.
- Se uma URL já passou por chat, e-mail ou commit, **gere uma nova** no Workflows.
- O Python roda no sandbox do Maestro: sem `getattr`, funções não enxergam variáveis do escopo principal e
  constantes chegam em `memoria["CST_..."]` (não por `{{CST_...}}` dentro de string Python).

# Arquitetura

## Componentes

| Componente | Papel |
|---|---|
| **Webhook do Desk** (evento *Aprovação/Reprovação de Chamados*) | Dispara o Maestro a cada aprovação ou reprovação de chamado |
| **Maestro** `GMUD Aprovada - Aviso TI` | Um único bloco Python com as ações: aviso de aprovação (padrão), `lembrete`, `ler`, `limpar` |
| **Cron Tipo 2** | Chama o Maestro todo dia às 07:00 com `{"acao":"lembrete"}` |
| **Fluxo do Teams (Workflows)** | Recebe o cartão adaptativo e posta no chat/canal do TI |
| **Storage do Maestro** | Deduplicação, log de decisões e prévias |

## Por que um único bloco Python

Cada execução do Maestro tem custo. Um bloco só concentra validação, consultas, deduplicação e envio, em vez de
vários blocos HTTP/IF encadeados. A contrapartida é respeitar o sandbox do Maestro:

- funções não enxergam imports nem variáveis do escopo principal: importe dentro da função e passe tudo por parâmetro;
- sem `getattr`/`hasattr`/`setattr`;
- constantes do Maestro chegam em `memoria["CST_..."]`;
- o id aceito pelo `storage.Storage(...)` é a chave do próprio Maestro (`MAESTRO_PARAMS.codigo`).

## Payload do evento de aprovação

Os dados chegam no campo **`content`** (não em `data`), e ele precisa estar declarado no `response_model` do
`BEGIN_init`, senão chega vazio. Campos usados: `chamado` (código), `chamado_cod` (chave numérica), `assunto_cod`
(auto-categoria), `aprovreprov` (`A`/`R`), `tocorrencia_cod` (tipo de ocorrência), `usuario_aprovador`.

O evento **não traz** título, executor nem período: o Maestro busca no Desk.

## Chamadas à API do Desk

| Chamada | Para quê |
|---|---|
| `POST /GMUDs/lista` com `Pesquisa` = código | status, janela, grupo executor, solicitante |
| `POST /GMUDs/lista` sem `Pesquisa` e com `Limit` | lembrete: todas as GMUDs (sem `Limit` a lista traz só 15) |
| `POST /GMUDs` com `Chave` | `RequerAprovacao` (aprovação completa?) e auto-categoria |
| `POST /AutoCategorias` com `Chave` | aprovadores configurados |

Atenção: `/GMUDs/lista` devolve **nomes de campo diferentes** com e sem `Pesquisa` (`Codigo/St/Agendamento` x
`CodChamado/NomeStatus/DataAgendamento`). A função `norm_gmud` unifica os dois formatos.

## Cron

- **Tipo 2** (chama Maestro); o Tipo 1 não chamou o Maestro neste ambiente.
- O timer só aceita **hora cheia**; o disparo costuma ter alguns minutos de atraso.
- **Executa ao ser salvo.** Salve com o lembrete desligado.

## Publicação do fluxo

O campo `Fluxo` do Maestro é `Base64(escape mínimo(JSON))`: só `%` → `%25` e `+` → `%2B` antes do Base64.
O `tree` é uma lista de caminhos **cumulativos**, um por bloco, terminada em `;`.
Todos os valores de `config` são **strings** (JSON serializado). Veja `scripts/publicar.ps1`.

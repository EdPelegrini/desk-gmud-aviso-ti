# Regras de negócio

Dados de exemplo fictícios. Os códigos (tipo de ocorrência, auto-categoria, status) variam por ambiente.

## Aviso de aprovação

O Desk dispara o evento *Aprovação/Reprovação de Chamados* a cada passo de aprovação de **qualquer** chamado.
O Maestro só envia o aviso quando **todas** as condições abaixo são verdadeiras:

1. É o evento esperado (`trigger = 6`).
2. É **aprovação** (`aprovreprov = "A"`), não reprovação.
3. O chamado é **GMUD** (tipo de ocorrência igual ao código configurado em `S_TIPO_GMUD`).
4. A aprovação está **completa**: no chamado, `RequerAprovacao = "AU"`. Enquanto faltam aprovadores o valor é `S`.
5. A GMUD ainda **não foi avisada** (deduplicação por chave do chamado, últimas 200).
6. A aprovação não chegou **depois da GMUD acontecer**: status Resolvido/Cancelado ou janela de execução já terminada.

Se qualquer condição falhar, o Maestro registra "ignorado" com o motivo e **não** envia nada.

### Por que a regra 6 olha o fim da janela e não o início

GMUDs emergenciais costumam ter início igual ao da abertura, então "o início já passou" silenciaria justamente
as mais importantes. Usar o **fim da janela** (ou o status final) cobre o caso "aprovada só depois de executada"
sem calar as emergenciais aprovadas durante a janela.

### Exemplo

GMUD `0001-000123`, janela de 24/10 20:00 a 25/10 00:00, aprovada por Ana Souza no dia da execução e por
Bruno Almeida em 26/10. A aprovação final de 26/10 é **ignorada**: a janela já terminou, embora o status ainda seja Agendamento.

## Lembrete do dia

Rodado pelo cron das 07:00 (fuso `America/Sao_Paulo`). Para cada GMUD:

- status **Agendamento** ou **Andamento** (Andamento entra porque algumas mudanças começam às 07:00);
- **data de início = hoje** (lembrete só no dia do início, mesmo em janelas longas);
- um **cartão individual** por GMUD;
- **deduplicação** por chamado + data, para o caso de o cron rodar duas vezes no dia.

GMUDs aprovadas **depois** das 07:00 para execução no mesmo dia recebem o aviso de aprovação, mas não o lembrete.

## Chaves de controle

| Constante | Efeito |
|---|---|
| `CST_TEAMS_URL` | URL do webhook do fluxo do Teams (segredo) |
| `CST_TEAMS_ATIVO` | `S` envia o aviso de aprovação; `N` só gera prévia |
| `CST_LEMBRETE_ATIVO` | `S` envia o lembrete (exige `CST_TEAMS_ATIVO = S`) |

## Armazenamento do Maestro (Storage)

Chaves usadas: `decisoes` (últimas 30 decisões de GMUD), `lembretes_log` (últimas 30 execuções do lembrete),
`avisados`, `lembretes`, `previas`, `previas_lembrete`. Aprovações de chamados que **não** são GMUD não entram no log.

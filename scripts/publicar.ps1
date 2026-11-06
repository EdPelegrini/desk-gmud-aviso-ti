# Publica o fluxo do Maestro de aviso de GMUD aprovada no seu ambiente Desk Manager.
# Uso: .\scripts\publicar.ps1 [-TeamsAtivo S|N] [-LembreteAtivo S|N]
#   TeamsAtivo     liga/desliga o envio do aviso de aprovação ao Teams (padrão N)
#   LembreteAtivo  liga/desliga o lembrete diário; só envia se TeamsAtivo = S também (padrão N)
# Pré-requisitos: .env preenchido (veja .env.example) e o Maestro já criado (DESK_MAESTRO_CHAVE).
param(
    [ValidateSet('S','N')][string]$TeamsAtivo = 'N',
    [ValidateSet('S','N')][string]$LembreteAtivo = 'N'
)

. "$PSScriptRoot\desk-lib.ps1"

$py = [IO.File]::ReadAllText("$script:Raiz\src\parse_aviso.py").Replace('SEU-PREFIXO', $script:V.DESK_PREFIXO)
$teamsUrl = $script:V.DESK_TEAMS_WEBHOOK_URL
if ([string]::IsNullOrWhiteSpace($teamsUrl)) { $teamsUrl = 'PREENCHER'; $TeamsAtivo = 'N' }

$rmIni = '{"trigger":"","action":"","acao":"","data":{},"content":"","data_simulada":"","sem_envio":"","agora_simulada":"","MAESTRO_PARAMS":{"token":"","prefixo":"","codigo":""}}'
$rm = '{"saida":{"ok":"","resultado":"","chamado":"","preview":"","teams_ligado":"","lembrete_ligado":"","hoje":"","itens":"","diag":"","decisoes":"","lembretes_log":"","previas":"","avisados_total":"","erro":""}}'
$fluxo = [ordered]@{
    config = @(
        [ordered]@{ name = 'BEGIN_init'; response_model = $rmIni },
        [ordered]@{ name = 'PARSE_Aviso'; jsonata = $py; response_model = $rm })
    # tree: um caminho cumulativo por bloco, terminado em ';'
    tree = 'BEGIN_init;BEGIN_init.PARSE_Aviso;'
    constants = @(
        [ordered]@{ key = 'CST_TEAMS_URL'; value = $teamsUrl },
        [ordered]@{ key = 'CST_TEAMS_ATIVO'; value = $TeamsAtivo },
        [ordered]@{ key = 'CST_LEMBRETE_ATIVO'; value = $LembreteAtivo })
    cron = @('CRON_access_token')   # NOME do cron que gera o token da API (não a chave)
}

# Encoding do campo Fluxo: Base64(escape mínimo(JSON)); o escape de "%" e "+" usa chr(37) de propósito
$fj = $fluxo | ConvertTo-Json -Depth 10 -Compress
$pc = [string][char]37
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($fj.Replace($pc, $pc + '25').Replace('+', $pc + '2B')))

$chave = $script:V.DESK_MAESTRO_CHAVE
$t = Get-DeskToken
$r = Send-Desk $t 'Put' '/Maestro' @{ TMaestro = @{ Chave = $chave; Fluxo = $b64; Panel = 'FluxoMConstrutor' } } 'Menu=FluxoMConstrutor&App=Ticket'
$m = (Send-Desk $t 'Post' '/Maestro' @{ Chave = $chave } 'Origem=Construtor&App=Ticket').TMaestro
"PUT=$r Versao=$($m.Versao) TeamsAtivo=$TeamsAtivo LembreteAtivo=$LembreteAtivo URLconfigurada=$($teamsUrl -ne 'PREENCHER')"

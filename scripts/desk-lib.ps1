# Helpers de acesso ao Desk Manager. Os segredos vêm do arquivo .env (veja .env.example), nunca do código.
$script:Raiz = (Resolve-Path "$PSScriptRoot\..").Path
$script:V = @{}
if (Test-Path "$script:Raiz\.env") {
    Get-Content "$script:Raiz\.env" | ForEach-Object {
        if ($_ -match '^\s*([^#=\s][^=]*)=(.*)$') { $script:V[$Matches[1].Trim()] = $Matches[2].Trim() }
    }
}
$script:Host = "https://$($script:V.DESK_PREFIXO).desk.ms"

function Invoke-Tentativas([scriptblock]$sb) {
    for ($i = 1; $i -le 4; $i++) {
        try { return & $sb } catch { if ($i -eq 4) { throw }; Start-Sleep -Seconds (2 * $i) }
    }
}

# Autentica com a chave de INTEGRAÇÃO do ambiente (não a chave de um operador comum)
function Get-DeskToken {
    $r = Invoke-Tentativas {
        Invoke-RestMethod -Method Post -Uri 'https://api.desk.ms/Login/autenticar' `
            -Headers @{ Authorization = $script:V.DESK_API_KEY } -ContentType 'application/json' `
            -Body (@{ PublicKey = $script:V.DESK_PUBLIC_KEY } | ConvertTo-Json) -TimeoutSec 30
    }
    return "$r"
}

# POST/PUT de formulário "Dados=<json>&<extra>" no host do seu ambiente
function Send-Desk([string]$token, [string]$method, [string]$path, $dados, [string]$extra) {
    $json = if ($dados -is [string]) { $dados } else { $dados | ConvertTo-Json -Depth 20 -Compress }
    $body = 'Dados=' + [uri]::EscapeDataString($json) + '&' + $extra
    Invoke-Tentativas {
        Invoke-RestMethod -Method $method -Uri ($script:Host + $path) -Headers @{ Authorization = $token } `
            -ContentType 'application/x-www-form-urlencoded' -Body $body -TimeoutSec 60
    }
}

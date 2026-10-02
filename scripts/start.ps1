<#
.SYNOPSIS
    Sobe a Planilha Financeira e abre o navegador (SPECS/features/F-15, seção 3.1.3).

.DESCRIPTION
    Decide parte por parte: o que já está no ar não sobe de novo; porta ocupada por
    outro programa interrompe tudo. Prepara o ambiente nesta janela (pode levar
    minutos na primeira vez) e só então abre uma janela para o backend e outra para
    o frontend, espera os dois responderem e abre http://localhost:4200.

    Uso: powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
#>

$URL_HEALTH = 'http://127.0.0.1:8000/api/health'
$URL_APP = 'http://localhost:4200'
$ESPERA_BACKEND_S = 60
$ESPERA_FRONTEND_S = 180

function Falhar([string]$mensagem) {
    Write-Host $mensagem -ForegroundColor Red
    exit 1
}

# Este backend responde o health com o campo `planilha` (SPECS/03, seção 6.3).
function Testar-Backend {
    try {
        $saude = Invoke-RestMethod -Uri $URL_HEALTH -TimeoutSec 2
        return $null -ne $saude -and ($saude.PSObject.Properties.Name -contains 'planilha')
    } catch {
        return $false
    }
}

# Este frontend devolve o index.html com o título do app.
function Testar-Frontend {
    try {
        $pagina = Invoke-WebRequest -Uri $URL_APP -UseBasicParsing -TimeoutSec 2
        return $pagina.Content -match '<title>Planilha Financeira</title>'
    } catch {
        return $false
    }
}

function Testar-PortaOcupada([int]$porta) {
    $ouvintes = Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue
    return $null -ne $ouvintes
}

function Aguardar([scriptblock]$teste, [int]$segundos) {
    $limite = (Get-Date).AddSeconds($segundos)
    while ((Get-Date) -lt $limite) {
        if (& $teste) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Abrir-Janela([string]$script) {
    # Aspas por causa de caminhos com espaço: o Windows PowerShell junta os argumentos sem citá-los.
    Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$script`""
    )
}

$scriptBackend = Join-Path $PSScriptRoot 'start-backend.ps1'
$scriptFrontend = Join-Path $PSScriptRoot 'start-frontend.ps1'

$backendNoAr = Testar-Backend
$frontendNoAr = Testar-Frontend

if ($backendNoAr -and $frontendNoAr) {
    Write-Host 'O aplicativo já está rodando. Abrindo o navegador.'
    Start-Process $URL_APP
    exit 0
}

# Porta de outro programa: não sobe nada, nem a outra parte.
if (-not $backendNoAr -and (Testar-PortaOcupada 8000)) {
    Falhar 'A porta 8000 está em uso por outro programa. Feche-o ou veja o README, seção 5.'
}
if (-not $frontendNoAr -and (Testar-PortaOcupada 4200)) {
    Falhar 'A porta 4200 está em uso por outro programa. Feche-o ou veja o README, seção 5.'
}

# Preparação aqui, antes de contar o tempo de espera (pip/npm install podem levar minutos).
if (-not $backendNoAr) {
    & $scriptBackend -SoPreparar
    if ($LASTEXITCODE -ne 0) {
        exit 1
    }
}
if (-not $frontendNoAr) {
    & $scriptFrontend -SoPreparar
    if ($LASTEXITCODE -ne 0) {
        exit 1
    }
}

if (-not $backendNoAr) {
    Abrir-Janela $scriptBackend
}
if (-not $frontendNoAr) {
    Abrir-Janela $scriptFrontend
}

Write-Host 'Aguardando o backend…'
if (-not (Aguardar ${function:Testar-Backend} $ESPERA_BACKEND_S)) {
    Falhar "O backend não respondeu em $ESPERA_BACKEND_S s. Veja a janela dele para o erro."
}
Write-Host 'Aguardando o frontend…'
if (-not (Aguardar ${function:Testar-Frontend} $ESPERA_FRONTEND_S)) {
    Falhar "O frontend não respondeu em $ESPERA_FRONTEND_S s. Veja a janela dele para o erro."
}

Write-Host "Abrindo $URL_APP"
Start-Process $URL_APP

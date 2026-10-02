<#
.SYNOPSIS
    Sobe o backend da Planilha Financeira em http://127.0.0.1:8000 (SPECS/features/F-15, seção 3.1.1).

.DESCRIPTION
    Confere o Python, prepara backend\.venv na primeira execução (ou se a preparação
    anterior foi interrompida), confere se backend\.env existe e sobe o uvicorn só
    em 127.0.0.1, sem --reload. Não lê o .env nem a credencial: só verifica se o
    .env existe (RNF-05).

.PARAMETER SoPreparar
    Só confere e prepara o ambiente, sem subir o servidor (usado pelo start.ps1).
#>
param([switch]$SoPreparar)

$pastaBackend = Join-Path (Split-Path -Parent $PSScriptRoot) 'backend'
$pastaVenv = Join-Path $pastaBackend '.venv'
$pythonDaVenv = Join-Path $pastaVenv 'Scripts\python.exe'

function Falhar([string]$mensagem) {
    Write-Host $mensagem -ForegroundColor Red
    exit 1
}

function Obter-VersaoDoPython {
    try {
        $saida = & python --version 2>&1 | Out-String
    } catch {
        return $null
    }
    if ($saida -match 'Python (\d+)\.(\d+)') {
        return [version]"$($Matches[1]).$($Matches[2])"
    }
    return $null
}

if (-not $SoPreparar) {
    $Host.UI.RawUI.WindowTitle = 'Planilha Financeira — backend'
}

# 1. Python 3.12+ (SPECS/02, seção 1).
$versao = Obter-VersaoDoPython
if ($null -eq $versao -or $versao -lt [version]'3.12') {
    Falhar 'Python 3.12 ou superior não encontrado. Veja o README, seção 1.'
}

# 2. .venv com as dependências; reinstala se uma preparação anterior parou no meio.
$instalar = $false
if (-not (Test-Path -LiteralPath $pythonDaVenv)) {
    Write-Host 'Preparando o ambiente do backend (primeira execução)…'
    & python -m venv "$pastaVenv"
    if ($LASTEXITCODE -ne 0) {
        Falhar 'Não foi possível criar backend\.venv. Veja o README, seção 3.'
    }
    $instalar = $true
} else {
    & "$pythonDaVenv" -c 'import fastapi, gspread, uvicorn' 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Dependências do backend incompletas. Instalando de novo…'
        $instalar = $true
    }
}
if ($instalar) {
    & "$pythonDaVenv" -m pip install --disable-pip-version-check -r (Join-Path $pastaBackend 'requirements.txt')
    if ($LASTEXITCODE -ne 0) {
        Falhar 'Não foi possível instalar as dependências do backend. Confira a internet e rode de novo.'
    }
}

# 3. Só a existência do .env; o conteúdo é problema do próprio backend.
if (-not (Test-Path -LiteralPath (Join-Path $pastaBackend '.env'))) {
    Falhar 'Falta o arquivo backend/.env. Copie backend/.env.example e preencha SPREADSHEET_ID (README, seção 2.5).'
}

if ($SoPreparar) {
    exit 0
}

# 4. Da pasta backend: o .env e o caminho padrão da credencial são relativos a ela.
Set-Location -LiteralPath $pastaBackend
Write-Host 'Subindo o backend em http://127.0.0.1:8000 (Ctrl+C ou feche esta janela para parar).'
& "$pythonDaVenv" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
exit $LASTEXITCODE

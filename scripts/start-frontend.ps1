<#
.SYNOPSIS
    Sobe o frontend da Planilha Financeira em http://localhost:4200 (SPECS/features/F-15, seção 3.1.2).

.DESCRIPTION
    Confere o Node.js, roda npm install na primeira execução (ou se a anterior foi
    interrompida) e sobe o ng serve, que encaminha /api ao backend (proxy.conf.json).

.PARAMETER SoPreparar
    Só confere e prepara o ambiente, sem subir o servidor (usado pelo start.ps1).
#>
param([switch]$SoPreparar)

$pastaFrontend = Join-Path (Split-Path -Parent $PSScriptRoot) 'frontend'

function Falhar([string]$mensagem) {
    Write-Host $mensagem -ForegroundColor Red
    exit 1
}

function Obter-VersaoDoNode {
    try {
        $saida = & node -v 2>&1 | Out-String
    } catch {
        return $null
    }
    if ($saida -match 'v(\d+)\.(\d+)\.(\d+)') {
        return [version]"$($Matches[1]).$($Matches[2]).$($Matches[3])"
    }
    return $null
}

if (-not $SoPreparar) {
    $Host.UI.RawUI.WindowTitle = 'Planilha Financeira — frontend'
}

# 1. Node.js 24 LTS, ou 22.22.3+ (SPECS/02, seção 1).
$versao = Obter-VersaoDoNode
$aceito = $null -ne $versao -and (
    $versao.Major -eq 24 -or ($versao.Major -eq 22 -and $versao -ge [version]'22.22.3')
)
if (-not $aceito) {
    Falhar 'Node.js 24 LTS (ou 22.22.3+) não encontrado. Veja o README, seção 1.'
}

# 2. Dependências; o ng.cmd falta se nunca instalou ou se a instalação parou no meio.
Set-Location -LiteralPath $pastaFrontend
if (-not (Test-Path -LiteralPath (Join-Path $pastaFrontend 'node_modules\.bin\ng.cmd'))) {
    Write-Host 'Instalando dependências do frontend (primeira execução)…'
    & npm install
    if ($LASTEXITCODE -ne 0) {
        Falhar 'Não foi possível instalar as dependências do frontend. Confira a internet e rode de novo.'
    }
}

if ($SoPreparar) {
    exit 0
}

# 3. ng serve com o proxy de /api para o backend.
Write-Host 'Subindo o frontend em http://localhost:4200 (Ctrl+C ou feche esta janela para parar).'
& npm start
exit $LASTEXITCODE

<#
.SYNOPSIS
    Levanta el stack de ALLOCAT en Docker y escanea la API con OWASP ZAP.

.DESCRIPTION
    Es un wrapper delgado: el trabajo pesado lo hace tools/zap/scan.sh dentro
    del contenedor de ZAP. Esto se hace aca porque la API de ZAP 2.17 solo
    responde en el loopback de su propio namespace de red.

    ZAP se reinicia antes de escanear: la API de 2.17 no tiene forma de borrar
    todas las alertas, asi que sin reinicio el reporte acumularia findings de
    corridas anteriores.

.PARAMETER Full
    Escaneo completo: las 5 categorias de reglas de ZAP. Sin este flag corre en
    modo rapido, con 3 categorias (Information Gathering, Server Security,
    Injection), que es lo que detecta problemas web reales.

.PARAMETER CatTimeout
    Minutos maximos por categoria de reglas. Al agotarse, la categoria se
    detiene y se pasa a la siguiente. Default: 10 en rapido, 25 en completo.

.EXAMPLE
    .\tools\zap\scan.ps1
    .\tools\zap\scan.ps1 -Full -CatTimeout 30
#>
[CmdletBinding()]
param(
    [switch]$Full,
    [int]$CatTimeout = 0
)

$ErrorActionPreference = 'Continue'
# docker compose escribe su progreso en stderr; con 'Stop' eso aborta el script
# aunque el comando termine bien. El exito se valida con $LASTEXITCODE.
Set-Location (Join-Path $PSScriptRoot '..\..')

$Backend = 'http://backend:8000'
$ReportDir = Join-Path (Get-Location) 'zap-reports'

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "`n==> $Name" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "'$Name' fallo con codigo $LASTEXITCODE" }
}

function Test-Backend {
    # Se chequea DENTRO del contenedor a proposito: en el host el puerto 8000
    # puede estar tomado por un uvicorn local y daria un falso positivo.
    param([int]$TimeoutSeconds = 180)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" 2>$null
        if ($LASTEXITCODE -eq 0) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

Invoke-Step 'Levantando MySQL + backend' { docker compose up -d --build db backend }
if (-not (Test-Backend)) { throw "El backend no quedo sano en $Backend" }

Invoke-Step 'Sembrando usuarios, recurso y reserva de prueba' { docker compose --profile tools run --rm seed }

Invoke-Step 'Reiniciando ZAP (sesion limpia, sin alertas previas)' { docker compose --profile zap restart zap }
Write-Host '    (ZAP tarda ~30s en levantar la API; el script de scan espera solo)' -ForegroundColor DarkGray

$quick = if ($Full) { '0' } else { '1' }
$mode = if ($Full) { 'COMPLETO' } else { 'RAPIDO' }
if ($CatTimeout -le 0) { $CatTimeout = if ($Full) { 25 } else { 10 } }
Write-Host "    modo: $mode   tope por categoria: $CatTimeout min" -ForegroundColor DarkGray

Invoke-Step "Escaneando con ZAP (modo $mode)" {
    docker compose --profile zap exec -T `
        -e "SCAN_QUICK=$quick" `
        -e "SCAN_CAT_TIMEOUT=$($CatTimeout * 60)" `
        zap bash /zap/scan/scan.sh
}

Write-Host "`n==> Reportes" -ForegroundColor Green
Get-ChildItem $ReportDir -Filter 'allocat-*' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 4 Name, @{N='KB'; E={[math]::Round($_.Length / 1KB, 1)}}, LastWriteTime |
    Format-Table -AutoSize
Write-Host "  Carpeta: $ReportDir"
$Html = Get-ChildItem $ReportDir -Filter 'allocat-*.html' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($Html) {
    Write-Host "  Abrir el HTML: Start-Process `"$($Html.FullName)`""
} else {
    Write-Host "  (no se genero HTML; el JSON tiene todos los hallazgos)" -ForegroundColor Yellow
}
Write-Host "  Reiniciar todo: docker compose down -v"

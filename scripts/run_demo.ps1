<#
.SYNOPSIS
    BRIF.AI Yerel Demo Başlatıcı Scripti (Windows / PowerShell)
.DESCRIPTION
    Tek bir komutla BRIF.AI yerel konuşma demosunun ön kontrollerini yapar,
    FastAPI sunucusunu ve kullanıcı arayüzünü başlatır, hazır olunca tarayıcıyı açar
    ve Ctrl+C ile süreçleri güvenle temizler.
.EXAMPLE
    .\scripts\run_demo.ps1
.EXAMPLE
    .\scripts\run_demo.ps1 -ApiPort 8005 -UiPort 8090
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [int]$ApiPort = 8000,

    [Parameter(Mandatory=$false)]
    [int]$UiPort = 8080,

    [Parameter(Mandatory=$false)]
    [string]$Model = "qwen3:4b-instruct",

    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://127.0.0.1:11434",

    [Parameter(Mandatory=$false)]
    [switch]$NoBrowser,

    [Parameter(Mandatory=$false)]
    [switch]$NoOllamaCheck
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Get-Item $PSScriptRoot).Parent.FullName
if (-not (Test-Path "$ProjectRoot\pyproject.toml")) {
    $ProjectRoot = Get-Location
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $VenvPython = "python"
}

$LauncherArgs = @(
    "-m", "brif_ai.demo.launcher",
    "--api-port", $ApiPort,
    "--ui-port", $UiPort,
    "--model", $Model,
    "--ollama-url", $OllamaUrl
)

if ($NoBrowser) {
    $LauncherArgs += "--no-browser"
}

if ($NoOllamaCheck) {
    $LauncherArgs += "--no-ollama-check"
}

& $VenvPython $LauncherArgs
exit $LASTEXITCODE

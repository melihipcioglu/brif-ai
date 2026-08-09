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
    [double]$LlmTimeout = 300,

    [Parameter(Mandatory=$false)]
    [switch]$NoBrowser,

    [Parameter(Mandatory=$false)]
    [Alias("NoOllamaCheck")]
    [switch]$SkipOllamaPreflight
)

$ErrorActionPreference = "Stop"

# Resolve Project Root (containing pyproject.toml)
$CandidateRoot = $PSScriptRoot
if (-not (Test-Path "$CandidateRoot\pyproject.toml")) {
    if (Test-Path "$CandidateRoot\..\pyproject.toml") {
        $CandidateRoot = (Get-Item "$CandidateRoot\..").FullName
    } else {
        $CandidateRoot = Get-Location
    }
}
$ProjectRoot = (Get-Item $CandidateRoot).FullName

# Verify .venv Python executable strictly; do NOT fallback to system Python
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Hata: Python sanal ortamı (.venv) bulunamadı. Lütfen sanal ortamın kurulu olduğundan emin olun." -ForegroundColor Red
    exit 1
}

$LauncherArgs = @(
    "-m", "brif_ai.demo.launcher",
    "--api-port", $ApiPort,
    "--ui-port", $UiPort,
    "--model", $Model,
    "--ollama-url", $OllamaUrl,
    "--llm-timeout", $LlmTimeout
)

if ($NoBrowser) {
    $LauncherArgs += "--no-browser"
}

if ($SkipOllamaPreflight) {
    $LauncherArgs += "--skip-ollama-preflight"
}

Push-Location $ProjectRoot
try {
    & $VenvPython $LauncherArgs
} finally {
    Pop-Location
}
exit $LASTEXITCODE

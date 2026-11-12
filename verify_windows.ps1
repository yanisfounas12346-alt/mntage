# Run from the mntage repository root in Windows PowerShell.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Environnement Python absent. Lance d'abord : python -m venv .venv"
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    throw "FFmpeg introuvable. Installe-le avec : winget install --id Gyan.FFmpeg -e"
}
if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    throw "ffprobe introuvable : vérifie ton installation FFmpeg."
}

Write-Host "=== mntage : verification Windows ==="
& $python -m compileall -q app.py job_store.py stock_media.py video_factory.py subtitles.py tests
if ($LASTEXITCODE -ne 0) { throw "Echec de la compilation Python." }

# FFmpeg filter flags vary by build (e.g. ... or TSC); match the filter name.
$filterOutput = & ffmpeg -hide_banner -filters 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw "Impossible de lister les filtres FFmpeg." }
$assFilter = $filterOutput -match '(?m)^\s*\S+\s+ass\s+'
if (-not $assFilter) {
    Write-Host "Filtres de sous-titres disponibles :" -ForegroundColor Yellow
    $filterOutput -split "\r?\n" | Select-String -Pattern '\b(ass|subtitles)\b' | ForEach-Object { Write-Host $_ }
    throw "Filtre ASS absent de cette version FFmpeg. Verifie avec : ffmpeg -filters | findstr ass"
}

& $python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Tests en echec. Consulte les erreurs ci-dessus." }

Write-Host "Tous les tests executes ont reussi." -ForegroundColor Green

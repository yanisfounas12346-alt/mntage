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
& $python -m compileall -q app.py stock_media.py video_factory.py subtitles.py tests
if ($LASTEXITCODE -ne 0) { throw "Echec de la compilation Python." }

& ffmpeg -hide_banner -filters | Select-String -Pattern '^\s*\.\.\.\s+ass\s'
if (-not $?) { throw "Verification du filtre ASS impossible." }

& $python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Tests en echec. Consulte les erreurs ci-dessus." }

Write-Host "Tous les tests executes ont reussi." -ForegroundColor Green

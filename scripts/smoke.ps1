# Local smoke test: boots the webhook against the Firestore emulator and posts a text message.
# Assumes: .venv created, deps installed, Firestore emulator running on $env:FIRESTORE_EMULATOR_HOST.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$env:ENV = "development"
$env:GCP_PROJECT_ID = "reconbob-local"
$env:PYTHONPATH = $root
if (-not $env:FIRESTORE_EMULATOR_HOST) { $env:FIRESTORE_EMULATOR_HOST = "127.0.0.1:8085" }

$body = @{ From = "whatsapp:+15550001111"; To = "whatsapp:+14155238886"; Body = "hi"; NumMedia = "0" }
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:8088" -Method Post -Body $body
Write-Output "--- webhook reply ---"
Write-Output $resp

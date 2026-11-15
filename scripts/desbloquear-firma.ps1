# Desbloquea la clave de firma de LekSO desde PowerShell (usa el Bash de Git para Windows).
# Uso: powershell -File scripts\desbloquear-firma.ps1 [horas | cerrar]
param([string]$Arg = '8')
$git = (Get-Command git -ErrorAction SilentlyContinue).Source
$bash = if ($git) { Join-Path (Split-Path (Split-Path $git)) 'bin\bash.exe' } else { '' }
if (-not (Test-Path $bash)) { $bash = 'C:\Program Files\Git\bin\bash.exe' }
if (-not (Test-Path $bash)) { Write-Host 'No encuentro el Bash de Git para Windows.' -ForegroundColor Red; exit 1 }
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Write-Host ''
Write-Host 'Clave de firma de LekSO' -ForegroundColor Cyan
if ($Arg -ne 'cerrar') {
    Write-Host 'Escribe la contraseña de la clave (no se ve al escribir) y pulsa Intro.' -ForegroundColor Cyan
}
Write-Host ''
Push-Location $raiz
& $bash 'scripts/desbloquear-firma.sh' $Arg
$codigo = $LASTEXITCODE
Pop-Location
Write-Host ''
if ($codigo -eq 0) { Write-Host 'Hecho. Puedes cerrar esta ventana.' -ForegroundColor Green }
else { Write-Host 'No se pudo completar (mira el mensaje de arriba).' -ForegroundColor Red }
exit $codigo

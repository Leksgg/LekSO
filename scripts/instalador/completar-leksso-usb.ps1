# Con permisos de administrador: copia el árbol de LeksSO (ya extraído de la ISO, sin enlaces simbólicos) a la partición 1
# (LEKSSO, sistema EFI) del pendrive multi-sistema. Windows le quita la letra a esa partición, así que se la vuelve a dar.
# Uso: powershell -File completar-leksso-usb.ps1 [-Disco 5] [-Origen D:\temp\leks-tree]
param([int]$Disco = 5, [string]$Origen = 'D:\temp\leks-tree')
$ErrorActionPreference = 'Stop'
Start-Transcript -Path 'D:\temp\completar-usb.log' -Force | Out-Null
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Necesita permisos de administrador.' }
$d = Get-Disk -Number $Disco
if ($d.BusType -ne 'USB' -or $d.IsSystem -or $d.IsBoot) { throw "El disco $Disco no es un USB seguro." }
$p = Get-Partition -DiskNumber $Disco | Where-Object { (Get-Volume -Partition $_ -ErrorAction SilentlyContinue).FileSystemLabel -eq 'LEKSSO' }
if (-not $p) { throw 'No encuentro la partición LEKSSO en ese disco.' }
if (-not $p.DriveLetter) { $p | Add-PartitionAccessPath -AssignDriveLetter; Start-Sleep -Seconds 2; $p = Get-Partition -DiskNumber $Disco -PartitionNumber $p.PartitionNumber }
$l = $p.DriveLetter
if (-not $l) { throw 'Windows no asigna letra a la partición LEKSSO.' }
Write-Host "LEKSSO está en ${l}:"
robocopy $Origen "${l}:\" /E /R:2 /W:2 /NFL /NDL /NP /NJH | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy falló ($LASTEXITCODE)" }
$o = (Get-ChildItem -LiteralPath $Origen -Recurse -File -Force).Count
$t = (Get-ChildItem -LiteralPath "${l}:\" -Recurse -File -Force | Where-Object { $_.FullName -notmatch 'System Volume Information' }).Count
Write-Host ("Archivos: origen {0}, pendrive {1}" -f $o, $t)
foreach ($f in 'EFI\boot\bootx64.efi', 'EFI\boot\grubx64.efi', 'boot\grub\grub.cfg', 'boot\grub\leksso-instalar.cfg', 'boot\grub\theme\2', 'leksso\postinstalar.sh', 'leksso\VERSION_TAG') {
  Write-Host ("  {0,-34} {1}" -f $f, $(if (Test-Path -LiteralPath "${l}:\$f") { 'ok' } else { 'FALTA' }))
}
$nota = "Pendrive multi-sistema`r`nLeksSO: $((Get-Content -LiteralPath "${l}:\leksso\VERSION_TAG" -ErrorAction SilentlyContinue))`r`nWindows 10 x64 en la partición WIN10. Partición LIBRE sin usar.`r`n"
[IO.File]::WriteAllText("${l}:\sistemas.txt", $nota)
if ($o -eq $t) { Write-Host 'Listo.' -ForegroundColor Green } else { Write-Host 'Hay diferencias de recuento: revísalo.' -ForegroundColor Red }
Stop-Transcript | Out-Null
Start-Sleep -Seconds 4

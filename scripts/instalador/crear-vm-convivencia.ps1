# Crea una maquina virtual de Hyper-V para probar que LeksSO y Windows conviven en el mismo equipo
# (menu de arranque, deteccion de Windows, hora de la placa, desbloqueo por TPM).
#
# Uso (PowerShell COMO ADMINISTRADOR):
#   powershell -ExecutionPolicy Bypass -File crear-vm-convivencia.ps1 -IsoWindows "E:\ISO\Win11.iso" [-IsoLeksso "E:\ISO\leksso.iso"] [-Carpeta "E:\VMs\Convivencia-test"]
#
# Deja una VM «Convivencia-test» de generacion 2 con:
#   - arranque seguro (plantilla «Microsoft UEFI Certificate Authority», la que admite Linux) y TPM virtual
#   - DOS discos virtuales: uno para Windows (80 GB) y otro para LeksSO (64 GB), para probar cada sistema en su disco
#   - el DVD con la ISO de Windows puesto (y la de LeksSO si se indica, como segundo DVD)
# No toca ningun disco real ni la VM «LeksSO-test». Pasos despues: instalar Windows en el primer disco; apagar;
# arrancar desde la ISO de LeksSO e instalar en el SEGUNDO disco; comprobar el menu de arranque.
param(
  [Parameter(Mandatory)][string]$IsoWindows,
  [string]$IsoLeksso = "",
  [string]$Carpeta = "E:\VMs\Convivencia-test",
  [string]$Nombre = "Convivencia-test",
  [int]$GBWindows = 80,
  [int]$GBLeksso = 64
)
$ErrorActionPreference = 'Stop'
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw "Ejecuta este script en un PowerShell como administrador."
}
if (-not (Test-Path $IsoWindows)) { throw "No encuentro la ISO de Windows: $IsoWindows" }
if ($IsoLeksso -and -not (Test-Path $IsoLeksso)) { throw "No encuentro la ISO de LeksSO: $IsoLeksso" }
if (Get-VM -Name $Nombre -ErrorAction SilentlyContinue) { throw "Ya existe una VM llamada $Nombre. Borrala o usa -Nombre." }
New-Item -ItemType Directory -Force -Path $Carpeta | Out-Null

$discoW = Join-Path $Carpeta "windows.vhdx"
$discoL = Join-Path $Carpeta "leksso.vhdx"
New-VHD -Path $discoW -SizeBytes ($GBWindows * 1GB) -Dynamic | Out-Null
New-VHD -Path $discoL -SizeBytes ($GBLeksso * 1GB) -Dynamic | Out-Null

$vm = New-VM -Name $Nombre -Generation 2 -MemoryStartupBytes 8GB -Path $Carpeta -NoVHD -SwitchName "Default Switch"
Set-VMProcessor -VMName $Nombre -Count 4
Set-VMMemory -VMName $Nombre -DynamicMemoryEnabled $false
Add-VMHardDiskDrive -VMName $Nombre -Path $discoW
Add-VMHardDiskDrive -VMName $Nombre -Path $discoL
Add-VMDvdDrive -VMName $Nombre -Path $IsoWindows
if ($IsoLeksso) { Add-VMDvdDrive -VMName $Nombre -Path $IsoLeksso }

# Arranque seguro con la plantilla que admite Linux (shim) y Windows, y TPM virtual (Windows 11 lo pide; LeksSO lo usa para el desbloqueo).
Set-VMFirmware -VMName $Nombre -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority
Set-VMKeyProtector -VMName $Nombre -NewLocalKeyProtector
Enable-VMTPM -VMName $Nombre

# Orden de arranque: primero el DVD de Windows.
$dvdW = Get-VMDvdDrive -VMName $Nombre | Select-Object -First 1
Set-VMFirmware -VMName $Nombre -FirstBootDevice $dvdW

Write-Host ""
Write-Host "VM '$Nombre' creada en $Carpeta" -ForegroundColor Green
Write-Host "Discos: Windows ($GBWindows GB) y LeksSO ($GBLeksso GB). Arranque seguro y TPM activados."
Write-Host "Siguiente: enciendela (Start-VM $Nombre), instala Windows en el PRIMER disco, apagala y arranca la ISO de LeksSO."
Write-Host "Para borrarla despues: Stop-VM $Nombre -TurnOff; Remove-VM $Nombre -Force; Remove-Item '$Carpeta' -Recurse"

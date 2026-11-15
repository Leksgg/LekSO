# Mide OBS en Windows grabando la misma escena fija; deja la misma línea CSV que bench-obs.sh.
# Uso: .\bench-obs.ps1 [-Segundos 120] [-Coleccion bench] [-Perfil bench]
param([int]$Segundos = 120, [string]$Coleccion = 'bench', [string]$Perfil = 'bench',
      [string]$Obs = 'C:\Program Files\obs-studio\bin\64bit\obs64.exe')
$logs = Join-Path $env:APPDATA 'obs-studio\logs'
$antes = (Get-ChildItem $logs | Sort-Object LastWriteTime | Select-Object -Last 1).Name
$p = Start-Process $Obs -ArgumentList "--collection `"$Coleccion`" --profile `"$Perfil`" --startrecording --disable-shutdown-check" `
     -WorkingDirectory (Split-Path $Obs) -PassThru
Start-Sleep 15
$n = [int]($Segundos / 2); $cpu = 0; $ram = 0; $gpu = 0; $enc = 0
$nproc = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
$prev = (Get-Process -Id $p.Id).TotalProcessorTime.TotalSeconds
for ($i = 0; $i -lt $n; $i++) {
    Start-Sleep 2
    $proc = Get-Process -Id $p.Id
    $t = $proc.TotalProcessorTime.TotalSeconds
    $cpu += (($t - $prev) / 2) * 100; $prev = $t          # % de un núcleo, igual que ps en Linux
    $ram += $proc.WorkingSet64 / 1MB
    if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
        $g = (nvidia-smi --query-gpu=utilization.gpu,utilization.encoder --format=csv,noheader,nounits | Select-Object -First 1) -split ',\s*'
        $gpu += [double]$g[0]; $enc += [double]$g[1]
    }
}
Stop-Process -Id $p.Id; Start-Sleep 3
$log = Get-ChildItem $logs | Sort-Object LastWriteTime | Select-Object -Last 1
if ($log.Name -eq $antes) { Write-Warning 'No hay registro nuevo de OBS' }
$txt = Get-Content $log.FullName -Raw
function Pct($patron) { if ($txt -match "$patron\D*\d+/\d+ \(([\d.]+)%\)") { "$($Matches[1])%" } else { '0%' } }
'sistema,segundos,cpu_media_pct,ram_media_mb,gpu_media_pct,nvenc_media_pct,saltados,perdidos,retrasados'
'windows,{0},{1:N1},{2:N0},{3:N1},{4:N1},{5},{6},{7}' -f $Segundos, ($cpu / $n), ($ram / $n), ($gpu / $n), ($enc / $n),
    (Pct 'skipped frames due to encoding lag'), (Pct 'missed frames due to rendering lag'), (Pct 'lagged frames due to rendering lag/stalls')

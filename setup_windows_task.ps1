# Script para registrar la tarea programada en Windows (revisión diaria a las 9:00 AM)
$TaskName = "CECATI95_Monitor_Cursos"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ActionPath = "python.exe"
$ActionArg = Join-Path $ScriptDir "monitor_cecati.py --check-now"

Write-Host "Configurando tarea programada diaria: $TaskName ..." -ForegroundColor Cyan

# Definir la acción
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "`"$ScriptDir\monitor_cecati.py`" --check-now" -WorkingDirectory $ScriptDir

# Definir el disparador (diario a las 9:00 AM)
$Trigger = New-ScheduledTaskTrigger -Daily -At "09:00AM"

# Definir la configuración
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Registrar la tarea
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Monitorea la apertura de cursos de sábados en CECATI 95"
    Write-Host "¡Tarea programada registrada exitosamente! Se ejecutará todos los días a las 09:00 AM." -ForegroundColor Green
} catch {
    Write-Host "Error al registrar la tarea: $_" -ForegroundColor Red
}

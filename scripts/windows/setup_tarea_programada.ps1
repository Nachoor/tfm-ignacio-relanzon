# ============================================================
# Configura el Programador de Tareas de Windows para ejecutar
# el scraping semanal de CAIQ cada lunes a las 8:00
#
# Ejecutar UNA VEZ como Administrador desde PowerShell:
#   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\scripts\windows\setup_tarea_programada.ps1
# ============================================================

$TaskName   = "CAIQ_Scraping_Semanal"
$ScriptPath = "C:\Users\Nacho\Documents\TFM\scripts\windows\scraping_semanal.bat"
$LogDir     = "C:\Users\Nacho\Documents\TFM\logs"

# Crear carpeta de logs si no existe
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
    Write-Host "Carpeta de logs creada: $LogDir"
}

# Eliminar tarea anterior si existe
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Tarea anterior eliminada."
}

# Definir accion: ejecutar el .bat
$Action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$ScriptPath`"" `
    -WorkingDirectory "C:\Users\Nacho\Documents\TFM"

# Disparador: cada lunes a las 08:00
$Trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday `
    -At "08:00"

# Configuracion: ejecutar aunque no haya sesion, con maxima prioridad
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Registrar la tarea
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Actualizacion semanal de ofertas de empleo para CAIQ (TFM)" `
    -RunLevel Highest

Write-Host ""
Write-Host "✅ Tarea '$TaskName' registrada correctamente."
Write-Host "   Se ejecutara cada LUNES a las 08:00."
Write-Host ""
Write-Host "Para ejecutar manualmente AHORA:"
Write-Host "   Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Para ver el estado:"
Write-Host "   Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"

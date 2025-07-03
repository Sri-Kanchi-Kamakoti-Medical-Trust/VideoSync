# PowerShell script for Windows Task Scheduler
# This script runs the Python video sync cronjob with virtual environment support

param(
    [string]$ConfigPath = "video_sync_config.json",
    [switch]$Cleanup,
    [switch]$DryRun,
    [string]$VenvPath = "surgical_video_env"
)

# Set script directory as working directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Log file path
$LogFile = Join-Path $ScriptDir "video_sync_scheduler.log"

# Function to write log entries
function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "$Timestamp - $Message"
    Write-Host $LogEntry
    Add-Content -Path $LogFile -Value $LogEntry
}

try {
    Write-Log "Starting video sync cronjob execution"
    
    # Check if virtual environment exists and activate it
    $VenvActivateScript = Join-Path $ScriptDir "$VenvPath\Scripts\Activate.ps1"
    if (Test-Path $VenvActivateScript) {
        Write-Log "Activating virtual environment: $VenvPath"
        try {
            & $VenvActivateScript
            Write-Log "Virtual environment activated successfully"
        } catch {
            Write-Log "Warning: Could not activate virtual environment: $($_.Exception.Message)"
            Write-Log "Continuing with system Python"
        }
    } else {
        Write-Log "Virtual environment not found at: $VenvActivateScript"
        Write-Log "Using system Python installation"
    }
    
    # Check if Python is available
    $PythonExe = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonExe) {
        throw "Python is not installed or not in PATH"
    }
    
    Write-Log "Using Python: $($PythonExe.Source)"
    
    # Build Python command arguments
    $PythonArgs = @("video_sync_cronjob.py", "--config", $ConfigPath)
    
    if ($Cleanup) {
        $PythonArgs += "--cleanup"
    }
    
    if ($DryRun) {
        $PythonArgs += "--dry-run"
    }
    
    Write-Log "Executing: python $($PythonArgs -join ' ')"
    
    # Execute the Python script
    $Process = Start-Process -FilePath "python" -ArgumentList $PythonArgs -Wait -PassThru -NoNewWindow
    
    if ($Process.ExitCode -eq 0) {
        Write-Log "Video sync cronjob completed successfully"
    } else {
        Write-Log "Video sync cronjob failed with exit code: $($Process.ExitCode)"
        exit $Process.ExitCode
    }
    
} catch {
    Write-Log "Error executing video sync cronjob: $($_.Exception.Message)"
    exit 1
} finally {
    # Deactivate virtual environment if it was activated
    if (Get-Command deactivate -ErrorAction SilentlyContinue) {
        deactivate
        Write-Log "Virtual environment deactivated"
    }
}

Write-Log "Video sync cronjob execution finished"

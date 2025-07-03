# Setup script for Surgical Video Sync Cronjob
# This script creates a virtual environment and installs dependencies

param(
    [string]$VenvName = "surgical_video_env",
    [switch]$Force
)

# Set script directory as working directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=== Surgical Video Sync Cronjob Setup ===" -ForegroundColor Green

# Check if Python is installed
try {
    $PythonVersion = python --version 2>&1
    Write-Host "Found Python: $PythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check if virtual environment already exists
$VenvPath = Join-Path $ScriptDir $VenvName
if (Test-Path $VenvPath) {
    if ($Force) {
        Write-Host "Removing existing virtual environment..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $VenvPath
    } else {
        Write-Host "Virtual environment already exists at: $VenvPath" -ForegroundColor Yellow
        Write-Host "Use -Force parameter to recreate it" -ForegroundColor Yellow
        
        # Ask user if they want to continue with existing environment
        $Continue = Read-Host "Continue with existing environment? (y/n)"
        if ($Continue -ne 'y' -and $Continue -ne 'Y') {
            Write-Host "Setup cancelled" -ForegroundColor Yellow
            exit 0
        }
        
        # Skip creation, go to activation
        $SkipCreation = $true
    }
}

# Create virtual environment
if (-not $SkipCreation) {
    Write-Host "Creating virtual environment: $VenvName" -ForegroundColor Cyan
    try {
        python -m venv $VenvName
        Write-Host "Virtual environment created successfully" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
        Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

# Activate virtual environment
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
Write-Host "Activating virtual environment..." -ForegroundColor Cyan

try {
    & $ActivateScript
    Write-Host "Virtual environment activated successfully" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Could not activate virtual environment using PowerShell" -ForegroundColor Yellow
    Write-Host "You may need to run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    
    # Try alternative activation method
    $ActivateBat = Join-Path $VenvPath "Scripts\activate.bat"
    Write-Host "Trying alternative activation method..." -ForegroundColor Cyan
    Write-Host "Please run the following command manually:" -ForegroundColor Yellow
    Write-Host "  $ActivateBat" -ForegroundColor White
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan

$RequirementsFile = Join-Path $ScriptDir "requirements.txt"
if (Test-Path $RequirementsFile) {
    try {
        pip install -r $RequirementsFile
        Write-Host "Dependencies installed successfully from requirements.txt" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Failed to install dependencies from requirements.txt" -ForegroundColor Red
        Write-Host "Trying to install individual packages..." -ForegroundColor Yellow
        
        # Install core dependencies manually
        pip install "azure-storage-blob>=12.14.0"
        pip install "azure-identity>=1.12.0"
    }
} else {
    Write-Host "requirements.txt not found, installing core dependencies..." -ForegroundColor Yellow
    pip install "azure-storage-blob>=12.14.0"
    pip install "azure-identity>=1.12.0"
}

# Verify installation
Write-Host "Verifying installation..." -ForegroundColor Cyan
try {
    python -c "import azure.storage.blob; print('Azure Blob Storage: OK')"
    python -c "import azure.identity; print('Azure Identity: OK')"
    Write-Host "All dependencies verified successfully!" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Some dependencies may not be installed correctly" -ForegroundColor Yellow
}

# Display next steps
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Copy 'video_sync_config_azure_sample.json' to 'video_sync_config.json'" -ForegroundColor White
Write-Host "2. Edit 'video_sync_config.json' with your Azure connection string" -ForegroundColor White
Write-Host "3. Test the configuration with: python video_sync_cronjob.py --dry-run" -ForegroundColor White
Write-Host ""
Write-Host "To activate the virtual environment manually:" -ForegroundColor Cyan
Write-Host "  PowerShell: .\$VenvName\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  Command Prompt: $VenvName\Scripts\activate.bat" -ForegroundColor White
Write-Host ""
Write-Host "To deactivate: deactivate" -ForegroundColor White

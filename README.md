# Surgical Video Sync and Anonymization Cronjob with Azure Blob Storage

This project provides a robust solution for automatically synchronizing and anonymizing surgical videos using hash functions for privacy protection, with integrated Azure Blob Storage upload functionality.

## Features

- **Automatic Video Detection**: Scans source directory for video files in multiple formats
- **Hash-based Anonymization**: Uses SHA256 (configurable) with salt for secure filename anonymization
- **Azure Blob Storage Integration**: Automatically uploads anonymized videos to Azure Blob Storage
- **Duplicate Prevention**: Tracks processed files to avoid reprocessing
- **Upload Verification**: Verifies successful uploads to Azure with size and integrity checks
- **Retry Logic**: Handles failed uploads with configurable retry attempts
- **Comprehensive Logging**: Detailed logs for monitoring and troubleshooting
- **Orphaned File Cleanup**: Removes anonymized files when source files are deleted
- **Windows Task Scheduler Integration**: Ready-to-use scripts for automated execution

## Supported Video Formats

- MP4, AVI, MOV, MKV, WMV, FLV

## Quick Setup (Automated)

For a quick automated setup, you can use the provided setup script:

```powershell
# Navigate to project directory
cd <project_dir>

# Run the setup script
.\setup.ps1

# If you get execution policy error, run this first:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# To recreate virtual environment (if it already exists)
.\setup.ps1 -Force
```

The setup script will:
- Check if Python is installed
- Create virtual environment
- Install all required dependencies
- Verify the installation
- Provide next steps

## Manual Installation (Step by Step)

If you prefer manual setup or the automated script doesn't work:

### Step 1: Prerequisites
1. **Install Python 3.8 or higher**
   - Download from [python.org](https://www.python.org/downloads/)
   - During installation, make sure to check "Add Python to PATH"
   - Verify installation: `python --version`

### Step 2: Create Virtual Environment (Recommended)
Using a virtual environment isolates the project dependencies and prevents conflicts with other Python projects.

#### Option A: Using venv (Built-in, Recommended)
```powershell
# Navigate to your project directory
cd <project_dir>

# Create virtual environment
python -m venv surgical_video_env

# Activate virtual environment
# On Windows PowerShell:
.\surgical_video_env\Scripts\Activate.ps1

# On Windows Command Prompt:
surgical_video_env\Scripts\activate.bat

# Verify activation (you should see (surgical_video_env) in your prompt)
```

#### Option B: Using virtualenv (Alternative)
```powershell
# Install virtualenv if not already installed
pip install virtualenv

# Create virtual environment
virtualenv surgical_video_env

# Activate virtual environment
.\surgical_video_env\Scripts\Activate.ps1
```

#### Option C: Using conda (If you have Anaconda/Miniconda)
```powershell
# Create conda environment
conda create -n surgical_video_env python=3.9

# Activate environment
conda activate surgical_video_env
```

### Step 3: Install Dependencies
**Make sure your virtual environment is activated** (you should see `(surgical_video_env)` in your command prompt)

```powershell
# Install Azure Blob Storage dependencies
pip install azure-storage-blob>=12.14.0 azure-identity>=1.12.0

# Or install from requirements.txt
pip install -r requirements.txt

# Verify installation
pip list
```

### Step 4: Clone or Download Project Files
If you haven't already, download all the project files to your working directory.

### Step 5: Deactivating Virtual Environment
When you're done working on the project:
```powershell
# Deactivate virtual environment
deactivate
```

### Virtual Environment Best Practices
- **Always activate** the virtual environment before running the script
- **Keep requirements.txt updated** when adding new dependencies
- **Don't commit** the virtual environment folder to version control
- **Document** the Python version and dependencies in your project

## Azure Blob Storage Setup

1. **Create Azure Storage Account**:
   - Log into Azure Portal
   - Create a new Storage Account
   - Note the Storage Account name

2. **Get Connection String**:
   - Go to Storage Account > Access Keys
   - Copy the connection string

3. **Configure the Application**:
   - Copy `video_sync_config_azure_sample.json` to `video_sync_config.json`
   - Update the `connection_string` in `azure_blob_settings`
   - Set `container_name` for your videos
   - Adjust other Azure settings as needed

## Configuration

Edit `video_sync_config.json` to customize:

- `source_directory`: Path to source videos
- `destination_directory`: Path for anonymized videos
- `hash_algorithm`: Hashing algorithm (md5, sha1, sha256)
- `salt`: Additional security salt for hashing
- `supported_formats`: Video file extensions to process

## Usage

### Before Running Any Commands
**Always activate your virtual environment first:**
```powershell
# Navigate to project directory
cd <project_dir>

# Activate virtual environment
.\surgical_video_env\Scripts\Activate.ps1

# You should see (surgical_video_env) in your prompt
```

### Manual Execution

```powershell
# Basic sync with Azure upload
python video_sync_cronjob.py

# With custom config
python video_sync_cronjob.py --config my_config.json

# Dry run (preview only)
python video_sync_cronjob.py --dry-run

# Cleanup orphaned files
python video_sync_cronjob.py --cleanup

# Upload only (skip local processing)
python video_sync_cronjob.py --azure-only

# List blobs in Azure container
python video_sync_cronjob.py --list-blobs
```

### Automated Execution (Windows Task Scheduler)

1. **Open Task Scheduler** (`taskschd.msc`)
2. **Create Basic Task**:
   - Name: "Surgical Video Sync"
   - Trigger: Daily/Weekly as needed
   - Action: Start a program
   - Program: `C:\path\to\video_sync_task.bat`

### Alternative PowerShell Execution

```powershell
# Run with PowerShell
.\run_video_sync.ps1

# With cleanup
.\run_video_sync.ps1 -Cleanup

# Dry run
.\run_video_sync.ps1 -DryRun
```

## File Structure

```
project/
├── video_sync_cronjob.py              # Main Python script with Azure integration
├── video_sync_config.json             # Configuration file
├── video_sync_config_azure_sample.json # Sample Azure configuration
├── setup.ps1                          # Automated setup script
├── run_video_sync.ps1                 # PowerShell wrapper with venv support
├── video_sync_task.bat                # Batch file for Task Scheduler
├── requirements.txt                   # Python dependencies
├── surgical_video_env/                # Virtual environment (created by setup)
├── hash_mappings.json                 # Generated mapping file
├── video_sync.log                     # Application log file
└── video_sync_scheduler.log           # Scheduler log file
```

## Azure Blob Storage Features

- **Secure Upload**: Uses Azure connection string authentication
- **Container Management**: Automatically creates containers if they don't exist
- **Blob Organization**: Configurable blob prefix for organized storage
- **Upload Verification**: Verifies file integrity after upload
- **Retry Logic**: Configurable retry attempts with exponential backoff
- **Duplicate Prevention**: Checks for existing blobs before upload
- **Blob Listing**: List all uploaded blobs for verification

## Security Features

- **Salted Hashing**: Uses configurable salt for additional security
- **Mapping Protection**: Original filenames are stored securely
- **No Reversible Encoding**: Hash functions ensure anonymity
- **Configurable Algorithms**: Support for MD5, SHA1, SHA256

## Logging

The application provides comprehensive logging:

- **Application Log**: `video_sync.log` - Python script execution details
- **Scheduler Log**: `video_sync_scheduler.log` - Task scheduler execution
- **Console Output**: Real-time progress information

## Hash Mapping

The system maintains a `hash_mappings.json` file that stores:

- Original filename
- Anonymous filename  
- Processing date
- File size
- Source path
- Azure upload status
- Azure upload date

This allows for reverse lookup if needed while maintaining anonymity and tracking upload status.

## Best Practices

1. **Regular Backups**: Keep backups of `hash_mappings.json`
2. **Test Configuration**: Use `--dry-run` before production
3. **Monitor Logs**: Check logs regularly for issues
4. **Secure Storage**: Store anonymized videos in secure locations
5. **Access Control**: Limit access to mapping files

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure write access to destination directory
2. **Python Not Found**: Add Python to system PATH
3. **Config File Missing**: Verify config file path and format
4. **Large Files**: Monitor disk space for large video files
5. **Azure Authentication**: Verify connection string is correct
6. **Azure Container**: Ensure container exists or enable auto-creation
7. **Network Issues**: Check internet connectivity for Azure uploads
8. **Azure Quotas**: Verify storage account has sufficient space

### Virtual Environment Issues

1. **PowerShell Execution Policy**: If you get an execution policy error:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. **Virtual Environment Not Activating**:
   ```powershell
   # Try using the full path
   <project_dir>\surgical_video_env\Scripts\Activate.ps1
   
   # Or use Command Prompt instead of PowerShell
   surgical_video_env\Scripts\activate.bat
   ```

3. **Module Not Found After Installation**:
   ```powershell
   # Make sure virtual environment is activated
   # Reinstall packages
   pip install --upgrade azure-storage-blob azure-identity
   ```

4. **Wrong Python Version**:
   ```powershell
   # Check Python version in virtual environment
   python --version
   
   # If wrong version, recreate virtual environment
   deactivate
   rmdir /s surgical_video_env
   python -m venv surgical_video_env
   ```

### Azure-Specific Troubleshooting

- **Connection String**: Format should be: `DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net`
- **Container Names**: Must be lowercase, 3-63 characters, alphanumeric and hyphens only
- **Blob Names**: Check for invalid characters in blob names
- **Storage Account**: Ensure it's accessible and not blocked by firewall

### Log Analysis

Check log files for:
- File processing status
- Error messages
- Performance statistics
- System resource usage

## Customization

The script can be extended for:

- Multiple Azure storage accounts
- Azure Key Vault integration for secrets
- Azure Event Grid notifications
- Other cloud storage providers (AWS S3, Google Cloud)
- SFTP/FTP upload functionality
- Email notifications
- Database logging
- Advanced file filtering
- Compression before upload
- Metadata tagging in Azure

## Legal and Compliance

- Ensure compliance with healthcare data protection regulations
- Review anonymization requirements for your jurisdiction
- Implement appropriate access controls
- Consider data retention policies
- Document security measures

## Support

For issues or feature requests:
1. Check the log files for detailed error information
2. Verify configuration settings
3. Test with `--dry-run` mode
4. Review file permissions and paths

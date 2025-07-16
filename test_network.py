import os
import subprocess
import sys
from pathlib import Path
import time

def test_network_connection():
    """Test network connection and file listing"""
    
    # Network configuration
    network_path = r"\\192.168.1.100\surveillance"  # Replace with your actual IP and share
    username = "your_username"  # Replace with your username
    password = "your_password"  # Replace with your password
    
    print(f"Testing network connection to: {network_path}")
    print(f"Username: {username}")
    print("-" * 50)
    
    try:
        # Step 1: Authenticate to network location
        print("Step 1: Authenticating to network location...")
        
        # Extract server from UNC path
        path_parts = network_path.split('\\')
        if len(path_parts) >= 4:
            server = path_parts[2]
            share = path_parts[3]
            
            print(f"Server: {server}")
            print(f"Share: {share}")
            
            # Use net use command to authenticate
            cmd = f'net use {network_path} /user:{username} {password}'
            print(f"Running: net use {network_path} /user:{username} ***")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✓ Authentication successful!")
                print(f"Output: {result.stdout}")
            else:
                print("✗ Authentication failed!")
                print(f"Error: {result.stderr}")
                return False
        else:
            print("✗ Invalid UNC path format")
            return False
            
        # Step 2: Test basic connectivity
        print("\nStep 2: Testing basic connectivity...")
        import socket
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((server, 445))  # SMB port
        sock.close()
        
        if result == 0:
            print("✓ SMB port 445 is accessible")
        else:
            print("✗ Cannot connect to SMB port 445")
            return False
            
        # Step 3: Test directory access
        print("\nStep 3: Testing directory access...")
        network_dir = Path(network_path)
        
        if network_dir.exists():
            print("✓ Network directory exists and is accessible")
        else:
            print("✗ Network directory not accessible")
            return False
            
        # Step 4: List files in directory
        print("\nStep 4: Listing files in network directory...")
        
        try:
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
            file_count = 0
            video_count = 0
            
            print(f"Scanning: {network_path}")
            
            for item in network_dir.iterdir():
                if item.is_file():
                    file_count += 1
                    if item.suffix.lower() in video_extensions:
                        video_count += 1
                        print(f"  📹 {item.name} ({item.stat().st_size / (1024*1024):.1f} MB)")
                    else:
                        print(f"  📄 {item.name}")
                elif item.is_dir():
                    print(f"  📁 {item.name}/")
                    
                # Limit output for testing
                if file_count > 20:
                    print("  ... (showing first 20 items)")
                    break
                    
            print(f"\nSummary:")
            print(f"  Total files: {file_count}")
            print(f"  Video files: {video_count}")
            
        except Exception as e:
            print(f"✗ Error listing files: {e}")
            return False
            
        # Step 5: Test file access
        print("\nStep 5: Testing file access...")
        try:
            # Try to access the first video file found
            for item in network_dir.iterdir():
                if item.is_file() and item.suffix.lower() in video_extensions:
                    print(f"Testing access to: {item.name}")
                    
                    # Get file stats
                    stat = item.stat()
                    print(f"  Size: {stat.st_size / (1024*1024):.1f} MB")
                    print(f"  Modified: {time.ctime(stat.st_mtime)}")
                    
                    # Try to open file (just check if readable)
                    try:
                        with open(item, 'rb') as f:
                            first_bytes = f.read(1024)
                            print(f"  ✓ File is readable ({len(first_bytes)} bytes read)")
                    except Exception as e:
                        print(f"  ✗ File read error: {e}")
                        
                    break
            else:
                print("  No video files found to test")
                
        except Exception as e:
            print(f"✗ Error testing file access: {e}")
            return False
            
        print("\n" + "=" * 50)
        print("✓ All network tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Network test failed: {e}")
        return False
        
    finally:
        # Clean up network connection
        try:
            cleanup_cmd = f'net use {network_path} /delete'
            subprocess.run(cleanup_cmd, shell=True, capture_output=True, text=True)
            print(f"\nCleaned up network connection")
        except:
            pass

def test_with_environment_variables():
    """Test using environment variables for credentials"""
    
    # Set these environment variables before running:
    # set SURVEILLANCE_PATH=\\192.168.1.100\surveillance
    # set SURVEILLANCE_USERNAME=your_username
    # set SURVEILLANCE_PASSWORD=your_password
    
    network_path = os.getenv('SURVEILLANCE_PATH', r'\\192.168.1.100\surveillance')
    username = os.getenv('SURVEILLANCE_USERNAME', 'your_username')
    password = os.getenv('SURVEILLANCE_PASSWORD', 'your_password')
    
    print("Testing with environment variables:")
    print(f"SURVEILLANCE_PATH: {network_path}")
    print(f"SURVEILLANCE_USERNAME: {username}")
    print(f"SURVEILLANCE_PASSWORD: {'*' * len(password)}")
    
    return test_network_connection_with_params(network_path, username, password)

def test_network_connection_with_params(network_path, username, password):
    """Test network connection with provided parameters"""
    
    print(f"Testing network connection to: {network_path}")
    print(f"Username: {username}")
    print("-" * 50)
    
    try:
        # Authenticate
        path_parts = network_path.split('\\')
        if len(path_parts) >= 4:
            server = path_parts[2]
            
            cmd = f'net use {network_path} /user:{username} {password}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✓ Authentication successful!")
                
                # List files
                network_dir = Path(network_path)
                if network_dir.exists():
                    print("✓ Directory accessible")
                    
                    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
                    videos = []
                    
                    for item in network_dir.rglob('*'):
                        if item.is_file() and item.suffix.lower() in video_extensions:
                            videos.append(item)
                            
                    print(f"Found {len(videos)} video files")
                    
                    # Show first few videos
                    for i, video in enumerate(videos[:5]):
                        relative_path = video.relative_to(network_dir)
                        size_mb = video.stat().st_size / (1024*1024)
                        print(f"  {i+1}. {relative_path} ({size_mb:.1f} MB)")
                        
                    if len(videos) > 5:
                        print(f"  ... and {len(videos) - 5} more")
                        
                    return True
                else:
                    print("✗ Directory not accessible")
                    return False
            else:
                print(f"✗ Authentication failed: {result.stderr}")
                return False
        else:
            print("✗ Invalid UNC path")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        # Cleanup
        try:
            subprocess.run(f'net use {network_path} /delete', shell=True, capture_output=True, text=True)
        except:
            pass

if __name__ == "__main__":
    print("Network Path Connection Test")
    print("=" * 50)
    
    # Test 1: Direct credentials
    print("\n1. Testing with direct credentials:")
    test_network_connection()
    
    # Test 2: Environment variables
    print("\n2. Testing with environment variables:")
    test_with_environment_variables()
    
    print("\nTest completed!")
#!/usr/bin/env python3
"""
deploy.py - Deploy TFT Odds data to production EC2 instance via SCP

This script replaces the git-based deployment with direct SCP transfer,
making deployments faster and avoiding git commits for data files.
"""

import argparse
import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

# EC2 connection details (from _commands.md)
EC2_HOST = "ec2-3-14-29-73.us-east-2.compute.amazonaws.com"
EC2_USER = "ubuntu"

# Detect if running in WSL and adjust path accordingly
if os.path.exists("/mnt/c"):
    # Running in WSL - use key from home directory
    # (Windows mounted files have permission issues in WSL)
    EC2_KEY_PATH = os.path.expanduser("~/tft-odds-key.pem")
else:
    # Running on native Windows
    EC2_KEY_PATH = r"C:\Users\mitch\Desktop\tft-odds-key.pem"

REMOTE_PROJECT_PATH = "/home/ubuntu/streamlit-app"

# Files to deploy
DEPLOY_FILES = [
    "live/tour_state.csv",
    "live/probabilities.json",
    "live/tournament_notes.md"  # Optional file
]


def check_ssh_key():
    """Check if SSH key exists and has correct permissions."""
    key_path = Path(EC2_KEY_PATH)
    
    if not key_path.exists():
        print(f"ERROR: SSH key not found at: {EC2_KEY_PATH}")
        print("\nPlease update EC2_KEY_PATH in deploy.py with your key location.")
        return False
    
    # On Unix systems, check permissions
    if not sys.platform.startswith('win'):
        stat_info = os.stat(key_path)
        mode = stat_info.st_mode & 0o777
        if mode != 0o400:
            print(f"WARNING: SSH key permissions are too open ({oct(mode)})")
            print(f"Run: chmod 400 {EC2_KEY_PATH}")
    
    return True


def check_live_files():
    """Check which files exist in the live directory."""
    existing_files = []
    missing_files = []
    
    for file_path in DEPLOY_FILES:
        if os.path.exists(file_path):
            existing_files.append(file_path)
        else:
            # tournament_notes.md is optional
            if "tournament_notes.md" not in file_path:
                missing_files.append(file_path)
    
    if missing_files:
        print("ERROR: Required files missing from live directory:")
        for f in missing_files:
            print(f"  - {f}")
        return None
    
    return existing_files


def get_deployment_info(files):
    """Get information about what will be deployed."""
    info = {
        "file_count": len(files),
        "total_size": 0,
        "probabilities_info": None
    }
    
    for file_path in files:
        info["total_size"] += os.path.getsize(file_path)
        
        # Extract info from probabilities.json if present
        if file_path == "live/probabilities.json":
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                if "simulation_info" in data:
                    info["probabilities_info"] = data["simulation_info"]
            except:
                pass
    
    # Convert size to human readable
    size_mb = info["total_size"] / (1024 * 1024)
    info["size_str"] = f"{size_mb:.2f} MB" if size_mb > 1 else f"{info['total_size'] / 1024:.1f} KB"
    
    return info


def run_scp(local_file, remote_path, description):
    """Run SCP command to transfer a file."""
    scp_cmd = [
        'scp',
        '-i', EC2_KEY_PATH,
        local_file,
        f"{EC2_USER}@{EC2_HOST}:{remote_path}"
    ]
    
    print(f"\n{description}...")
    print(f"  Local: {local_file}")
    print(f"  Remote: {remote_path}")
    
    try:
        result = subprocess.run(scp_cmd, capture_output=True, text=True, check=True)
        print("  ✓ Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed: {e.stderr}")
        return False


def run_ssh_command(command, description):
    """Run a command on the remote server via SSH."""
    ssh_cmd = [
        'ssh',
        '-i', EC2_KEY_PATH,
        f"{EC2_USER}@{EC2_HOST}",
        command
    ]
    
    print(f"\n{description}...")
    
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, check=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e.stderr}")
        return False


def ensure_remote_directories():
    """Ensure the project and live directories exist on the remote server."""
    create_dirs_cmd = f"mkdir -p {REMOTE_PROJECT_PATH}/live {REMOTE_PROJECT_PATH}/backups"
    return run_ssh_command(create_dirs_cmd, "Creating remote directories")


def backup_remote_files():
    """Create a backup of current live files on the remote server."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_cmd = f"""
    cd {REMOTE_PROJECT_PATH} && \
    if [ -d live ] && [ "$(ls -A live)" ]; then \
        cp -r live backups/live_{timestamp} && \
        echo "Backup created: backups/live_{timestamp}"; \
    else \
        echo "No live directory to backup or directory is empty"; \
    fi
    """
    
    return run_ssh_command(backup_cmd, "Creating remote backup")


def restart_streamlit():
    """Restart the Streamlit service on the remote server."""
    restart_cmd = "sudo systemctl restart streamlit.service"
    return run_ssh_command(restart_cmd, "Restarting Streamlit service")


def check_streamlit_status():
    """Check if Streamlit service is running properly."""
    status_cmd = "sudo systemctl is-active streamlit.service"
    return run_ssh_command(status_cmd, "Checking Streamlit status")


def main():
    parser = argparse.ArgumentParser(
        description='Deploy TFT Odds data to production EC2 instance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standard deployment
  python deploy.py
  
  # Deploy without creating backup
  python deploy.py --no-backup
  
  # Deploy without restarting Streamlit
  python deploy.py --no-restart
  
  # Just check what would be deployed (dry run)
  python deploy.py --dry-run
        """
    )
    
    parser.add_argument('--no-backup', action='store_true',
                        help='Skip creating backup on remote server')
    parser.add_argument('--no-restart', action='store_true',
                        help='Skip restarting Streamlit service')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be deployed without doing it')
    parser.add_argument('--force', action='store_true',
                        help='Deploy even if some optional files are missing')
    
    args = parser.parse_args()
    
    print("="*60)
    print("TFT ODDS DEPLOYMENT TO PRODUCTION")
    print("="*60)
    
    # Step 1: Check SSH key
    print("\nChecking SSH configuration...")
    if not check_ssh_key():
        sys.exit(1)
    print("✓ SSH key found")
    
    # Step 2: Check live files
    print("\nChecking live files...")
    files_to_deploy = check_live_files()
    if not files_to_deploy:
        if not args.force:
            print("\nUse --force to deploy with missing optional files.")
            sys.exit(1)
    
    # Step 3: Show deployment info
    deploy_info = get_deployment_info(files_to_deploy)
    print(f"\nFiles to deploy: {deploy_info['file_count']} files ({deploy_info['size_str']})")
    for f in files_to_deploy:
        print(f"  - {f}")
    
    if deploy_info["probabilities_info"]:
        info = deploy_info["probabilities_info"]
        print(f"\nSimulation info:")
        print(f"  - Round: {info.get('current_round', 'N/A')}")
        print(f"  - Active players: {info.get('active_players', 'N/A')}")
        print(f"  - Iterations: {info.get('total_iterations', 'N/A')}")
    
    # Step 4: Confirm deployment
    if args.dry_run:
        print("\n--dry-run specified. No files will be transferred.")
        sys.exit(0)
    
    print(f"\nTarget: {EC2_USER}@{EC2_HOST}:{REMOTE_PROJECT_PATH}/live/")
    
    print("\n" + "="*60)
    print("DEPLOYING...")
    print("="*60)
    
    # Step 5: Ensure remote directories exist
    if not ensure_remote_directories():
        print("\nERROR: Failed to create remote directories.")
        sys.exit(1)
    
    # Step 6: Create backup if requested
    if not args.no_backup:
        if not backup_remote_files():
            print("\nWARNING: Backup failed, but continuing with deployment...")
    
    # Step 7: Deploy files via SCP
    success_count = 0
    for local_file in files_to_deploy:
        # Construct remote path
        relative_path = local_file.replace("\\", "/")  # Handle Windows paths
        remote_file = f"{REMOTE_PROJECT_PATH}/{relative_path}"
        
        if run_scp(local_file, remote_file, f"Deploying {os.path.basename(local_file)}"):
            success_count += 1
        else:
            print(f"\nERROR: Failed to deploy {local_file}")
            if not args.force:
                print("Deployment aborted.")
                sys.exit(1)
    
    print(f"\n✓ Successfully deployed {success_count}/{len(files_to_deploy)} files")
    
    # Step 8: Restart Streamlit if requested
    if not args.no_restart:
        if restart_streamlit():
            print("✓ Streamlit service restarted")
            
            # Check if it's running
            if check_streamlit_status():
                print("✓ Streamlit is running")
            else:
                print("⚠ WARNING: Streamlit may not be running properly")
                print("  Check logs with: ssh to EC2 and run 'sudo journalctl -u streamlit -n 50'")
    
    print("\n" + "="*60)
    print("✅ DEPLOYMENT COMPLETE!")
    print("="*60)
    print(f"\nYour changes are now live at: https://tft-odds.com")
    print("\nTo check server logs:")
    print(f"  ssh -i \"{EC2_KEY_PATH}\" {EC2_USER}@{EC2_HOST}")
    print("  sudo journalctl -u streamlit -f")


if __name__ == "__main__":
    main()
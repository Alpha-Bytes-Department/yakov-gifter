import os
import tarfile
import paramiko
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


# Server configuration
HOST = "82.25.90.134"
USER = "root"
PASSWORD = "Rasel.22@@@@"
REMOTE_PATH = "/app"
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_NAME = "deploy_update.tar.gz"

EXCLUDE_DIRS = {".git", ".venv", ".venv_mac", ".venv_mac_new", "venv", "__pycache__", ".vscode", ".idea"}
EXCLUDE_PREFIXES = (".env",)
EXCLUDE_EXTENSIONS = (".sqlite3", ".pyc", ".pyo", ".tar.gz")

def is_excluded(path, rel_path):
    parts = rel_path.replace("\\", "/").split("/")
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
        if part.startswith(".env"):
            return True
    
    filename = parts[-1]
    if any(filename.startswith(p) for p in EXCLUDE_PREFIXES):
        return True
    if any(filename.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
        return True
    if filename == ARCHIVE_NAME:
        return True
        
    return False

def create_tarball(archive_path):
    print(f"📦 Creating archive: {archive_path}...")
    file_count = 0
    with tarfile.open(archive_path, "w:gz") as tar:
        for root, dirs, files in os.walk(LOCAL_DIR):
            rel_root = os.path.relpath(root, LOCAL_DIR)
            if rel_root == ".":
                rel_root = ""
            
            # Filter out excluded directories in-place to avoid recursing into them
            dirs[:] = [d for d in dirs if not is_excluded(os.path.join(root, d), os.path.join(rel_root, d))]
            
            for file in files:
                rel_file_path = os.path.join(rel_root, file) if rel_root else file
                if not is_excluded(os.path.join(root, file), rel_file_path):
                    abs_file_path = os.path.join(root, file)
                    tar.add(abs_file_path, arcname=rel_file_path)
                    file_count += 1
    print(f"✅ Created tarball with {file_count} files.")

def deploy():
    archive_path = os.path.join(LOCAL_DIR, ARCHIVE_NAME)
    try:
        create_tarball(archive_path)
        
        print(f"🚀 Connecting to {USER}@{HOST}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
        print("✅ Connected to remote server.")
        
        sftp = ssh.open_sftp()
        remote_tar_path = f"/tmp/{ARCHIVE_NAME}"
        print(f"📤 Uploading {ARCHIVE_NAME} to remote {remote_tar_path}...")
        sftp.put(archive_path, remote_tar_path)
        sftp.close()
        print("✅ Archive uploaded successfully.")
        
        print(f"📂 Extracting update into {REMOTE_PATH}...")
        extract_cmd = f"tar -xzf {remote_tar_path} -C {REMOTE_PATH} && rm -f {remote_tar_path}"
        stdin, stdout, stderr = ssh.exec_command(extract_cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        if err and "tar: " in err:
            print(f"⚠️ Extract notice: {err}")
        else:
            print("✅ Extracted updated project files successfully.")

        # Remote commands execution
        remote_commands = [
            f"chmod +x {REMOTE_PATH}/*.sh",
            "docker exec -i app-web-1 python manage.py makemigrations",
            "docker exec -i app-web-1 python manage.py migrate",
            "docker restart app-web-1"
        ]

        print("\n⚙️ Executing post-sync commands on server...")
        for cmd in remote_commands:
            print(f"\n▶ Executing: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            cmd_out = stdout.read().decode().strip()
            cmd_err = stderr.read().decode().strip()
            if cmd_out:
                print(f"[STDOUT]\n{cmd_out}")
            if cmd_err:
                print(f"[STDERR]\n{cmd_err}")
                
        ssh.close()
        print("\n🎉 Deployment completed successfully!")

    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)

if __name__ == "__main__":
    deploy()

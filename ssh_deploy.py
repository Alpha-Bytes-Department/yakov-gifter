import pty, os, sys

def deploy():
    pid, fd = pty.fork()
    if pid == 0:
        # Child
        os.execvp("ssh", ["ssh", "-o", "StrictHostKeyChecking=no", "root@82.25.90.134"])
    else:
        # Parent
        output = b""
        while True:
            try:
                data = os.read(fd, 1024)
                if not data: break
                output += data
                if b"password:" in data.lower():
                    os.write(fd, b"Rasel.22@@@@\n")
                    import time
                    time.sleep(2)
                    # Now send the commands to pull and restart
                    commands = """
                    cd /var/www/Ezlain-backend || cd /root/Ezlain-backend || cd /home/Ezlain-backend || find / -name Ezlain-backend -type d 2>/dev/null | head -n 1 | xargs -I {} cd {}
                    pwd
                    git pull origin main
                    systemctl restart gunicorn || systemctl restart Ezlain-backend || systemctl restart nginx
                    exit
                    """
                    os.write(fd, commands.encode())
            except OSError:
                break
        print(output.decode(errors="ignore"))

deploy()

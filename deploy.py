"""部署脚本：把项目上传到服务器并用 Docker Compose 构建、启动、自检。

仅本地运行（需要 paramiko）。凭据通过环境变量传入，不写死在代码里：

    SM_SSH_HOST      服务器地址，默认 47.109.147.248
    SM_SSH_USER      SSH 用户，默认 root
    SM_SSH_PASSWORD  SSH 密码（必填）
    SM_REMOTE_DIR    远端部署目录，默认 /opt/studymate

用法：
    python deploy.py probe      # 探测服务器环境（系统、Docker、镜像源、端口占用）
    python deploy.py bootstrap  # 一次性：装 Docker、配镜像加速、补 swap、拉基础镜像
    python deploy.py upload     # 上传代码 + 写入 .env
    python deploy.py build      # 构建镜像
    python deploy.py up         # 启动 compose 并等待健康检查
    python deploy.py status     # 查看容器与健康检查状态
    python deploy.py logs       # 查看应用日志
"""

from __future__ import annotations

import os
import posixpath
import sys
import time

import paramiko

HOST = os.environ.get("SM_SSH_HOST", "47.109.147.248")
PORT = int(os.environ.get("SM_SSH_PORT", "22"))
USER = os.environ.get("SM_SSH_USER", "root")
PASSWORD = os.environ.get("SM_SSH_PASSWORD", "")
REMOTE_DIR = os.environ.get("SM_REMOTE_DIR", "/opt/studymate")

# 部分网络（校园网/运营商）会按协议特征封 SSH，换端口也没用。
# 服务器上用 stunnel 把 SSH 包进 TLS（监听 443），这里设置 SM_SSH_TLS=1 即可走该通道。
TLS = os.environ.get("SM_SSH_TLS", "") not in ("", "0", "false", "False")
TLS_PORT = int(os.environ.get("SM_SSH_TLS_PORT", "443"))

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIRS = ["app", "static"]
UPLOAD_FILES = ["requirements.txt", "Dockerfile", ".dockerignore", "docker-compose.yml"]


def _tls_socket():
    """建立到 stunnel 的 TLS 连接（自签证书，不做校验）。"""
    import socket as _socket
    import ssl as _ssl

    raw = _socket.create_connection((HOST, TLS_PORT), timeout=20)
    ctx = _ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = _ssl.CERT_NONE
    return ctx.wrap_socket(raw, server_hostname=HOST)


def _direct_ssh_reachable() -> bool:
    """探测 22 端口是否真的能跑 SSH。

    校园网/运营商常按协议特征拦截 SSH：TCP 能连上，但读不到 banner。
    直接拿 SSH 横幅做判定，避免 paramiko 在后台线程里抛一堆异常。
    """
    import socket as _socket

    try:
        with _socket.create_connection((HOST, PORT), timeout=6) as sock:
            sock.settimeout(5)
            return sock.recv(64).startswith(b"SSH-")
    except OSError:
        return False


def connect() -> paramiko.SSHClient:
    if not PASSWORD:
        sys.exit("缺少环境变量 SM_SSH_PASSWORD")

    base = {
        "username": USER,
        "password": PASSWORD,
        "look_for_keys": False,
        "allow_agent": False,
    }

    def _client() -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

    def _direct() -> paramiko.SSHClient:
        client = _client()
        client.connect(HOST, port=PORT, timeout=15, banner_timeout=15, auth_timeout=15, **base)
        return client

    def _over_tls() -> paramiko.SSHClient:
        client = _client()
        client.connect(
            HOST,
            port=PORT,
            timeout=20,
            banner_timeout=20,
            auth_timeout=20,
            sock=_tls_socket(),
            **base,
        )
        return client

    if TLS:
        print("[ssh] 使用 TLS 443 通道", file=sys.stderr)
        return _over_tls()

    if _direct_ssh_reachable():
        print("[ssh] 22 端口直连", file=sys.stderr)
        return _direct()

    print("[ssh] 22 端口被网络拦截，改走 TLS 443 通道", file=sys.stderr)
    return _over_tls()


def run(ssh: paramiko.SSHClient, command: str, timeout: int = 3600, echo: bool = True) -> tuple[int, str]:
    """执行远端命令并实时打印输出（stderr 合并进 stdout，避免读管道死锁）。"""
    if echo:
        print(f"\n$ {command}", flush=True)
    channel = ssh.get_transport().open_session(timeout=timeout)
    channel.set_combine_stderr(True)
    channel.exec_command(command)
    chunks: list[str] = []
    while True:
        data = channel.recv(4096)
        if not data:
            if channel.exit_status_ready():
                break
            time.sleep(0.05)
            continue
        text = data.decode("utf-8", errors="replace")
        chunks.append(text)
        if echo:
            print(text, end="", flush=True)
    code = channel.recv_exit_status()
    return code, "".join(chunks)


def ensure_remote_dir(sftp: paramiko.SFTPClient, path: str) -> None:
    parts = path.strip("/").split("/")
    current = ""
    for part in parts:
        current += "/" + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def cmd_bootstrap() -> None:
    """安装 Docker、配置国内镜像加速、补充 swap（一次性）。"""
    with connect() as ssh:
        # 1) swap：1.7G 内存构建镜像容易 OOM，先补 2G
        run(
            ssh,
            "if [ ! -f /swapfile ]; then\n"
            "  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile\n"
            "  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab\n"
            "fi\n"
            "free -m | tail -2",
            timeout=300,
        )
        # 2) 安装 Docker + compose 插件
        run(
            ssh,
            "export DEBIAN_FRONTEND=noninteractive; "
            "apt-get update -qq && apt-get install -y -qq docker.io docker-compose-v2 curl ca-certificates",
            timeout=1800,
        )
        run(ssh, "systemctl enable --now docker && docker --version && docker compose version", timeout=300)
        # 3) 镜像加速：Docker Hub 在本机不可达，走公共镜像站
        run(
            ssh,
            "mkdir -p /etc/docker && "
            "cat > /etc/docker/daemon.json <<'EOF'\n"
            "{\n"
            '  "registry-mirrors": ["https://docker.1panel.live", "https://docker.m.daocloud.io", "https://docker.1ms.run"],\n'
            '  "log-driver": "json-file",\n'
            '  "log-opts": {"max-size": "10m", "max-file": "3"}\n'
            "}\n"
            "EOF\n"
            "systemctl restart docker && sleep 3 && docker info | grep -A3 'Registry Mirrors'",
            timeout=300,
        )
        # 4) 拉取基础镜像（真正的可用性门槛）
        run(ssh, "docker pull python:3.11-slim", timeout=1800)
        run(ssh, "docker pull mysql:8.0", timeout=1800)
        run(ssh, "docker images && free -m | tail -2", timeout=120)


def cmd_probe() -> None:
    with connect() as ssh:
        steps = [
            "cat /etc/os-release | head -4",
            "uname -m && nproc && free -m && df -h / | tail -1",
            "docker --version 2>&1 || echo NO_DOCKER",
            "docker compose version 2>&1 || docker-compose --version 2>&1 || echo NO_COMPOSE",
            "ss -lntp 2>/dev/null | grep -E ':(80|3306|8000)\\b' || echo PORTS_FREE",
            "ls -la " + REMOTE_DIR + " 2>&1 || echo DIR_MISSING",
            "curl -sS -m 8 -o /dev/null -w 'dockerhub=%{http_code}\\n' https://registry-1.docker.io/v2/ 2>&1 || echo dockerhub=FAIL",
            "curl -sS -m 8 -o /dev/null -w 'pypi_mirror=%{http_code}\\n' https://mirrors.aliyun.com/pypi/simple/ 2>&1 || echo pypi=FAIL",
            "for m in docker.m.daocloud.io dockerproxy.cn docker.1panel.live hub.rat.dev docker.1ms.run; do "
            "printf '%s ' \"$m\"; curl -sS -m 6 -o /dev/null -w '%{http_code}\\n' https://$m/v2/ 2>&1 || echo FAIL; done",
            "grep -hE '^(deb|URIs)' /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources 2>/dev/null | head -6",
            "apt-cache policy docker.io docker-compose-v2 mysql-server 2>/dev/null | grep -E '^[a-z]|Candidate' | head -12",
            "which python3 mysql mysqld systemctl 2>&1",
            "python3 --version && ls /usr/lib/python3.12/ensurepip 2>/dev/null || echo NO_ENSUREPIP",
        ]
        for step in steps:
            run(ssh, step, timeout=180)


def _iter_local_files():
    for name in UPLOAD_FILES:
        path = os.path.join(LOCAL_DIR, name)
        if os.path.isfile(path):
            yield path, name
    for directory in UPLOAD_DIRS:
        base = os.path.join(LOCAL_DIR, directory)
        for root, _dirs, files in os.walk(base):
            for filename in files:
                local = os.path.join(root, filename)
                if filename.endswith(".pyc") or "__pycache__" in local:
                    continue
                rel = os.path.relpath(local, LOCAL_DIR).replace("\\", "/")
                yield local, rel


def cmd_upload() -> None:
    api_key = os.environ.get("SM_API_KEY", "")
    mysql_password = os.environ.get("SM_MYSQL_PASSWORD", "")
    if not api_key:
        sys.exit("缺少环境变量 SM_API_KEY（硅基流动 API Key）")

    with connect() as ssh:
        sftp = ssh.open_sftp()
        ensure_remote_dir(sftp, REMOTE_DIR)

        # 已部署过的机器上复用原 MySQL 密码：MySQL 只在数据卷初始化时设置 root 密码，
        # 换密码会导致应用连不上。
        remote_env = posixpath.join(REMOTE_DIR, ".env")
        if not mysql_password:
            try:
                with sftp.file(remote_env, "r") as fh:
                    for line in fh.read().decode("utf-8", errors="ignore").splitlines():
                        if line.startswith("MYSQL_PASSWORD="):
                            mysql_password = line.split("=", 1)[1].strip()
            except FileNotFoundError:
                pass
        if not mysql_password:
            import secrets
            import string

            mysql_password = "".join(
                secrets.choice(string.ascii_letters + string.digits) for _ in range(20)
            )
        print(f"MYSQL_PASSWORD={mysql_password}")

        count = 0
        for local, rel in _iter_local_files():
            remote = posixpath.join(REMOTE_DIR, rel)
            ensure_remote_dir(sftp, posixpath.dirname(remote))
            sftp.put(local, remote)
            count += 1
        print(f"已上传 {count} 个文件到 {REMOTE_DIR}")

        env_content = (
            "# 由 deploy.py 生成，勿提交 Git\n"
            f"SILICONFLOW_API_KEY={api_key}\n"
            "SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1\n"
            "LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash\n"
            "EMBEDDING_MODEL=BAAI/bge-m3\n"
            "TOP_K=10\n"
            "MYSQL_HOST=mysql\n"
            "MYSQL_PORT=3306\n"
            "MYSQL_USER=root\n"
            f"MYSQL_PASSWORD={mysql_password}\n"
            "MYSQL_DATABASE=study_mate\n"
            "CHROMA_PERSIST_DIR=/data/chroma\n"
        )
        with sftp.file(remote_env, "w") as fh:
            fh.write(env_content)
        sftp.chmod(remote_env, 0o600)
        sftp.close()
        print(".env 已写入（权限 600）")


def _compose(ssh: paramiko.SSHClient) -> str:
    """返回可用的 compose 命令（新版插件 docker compose / 旧版 docker-compose）。"""
    code, _ = run(ssh, "docker compose version", timeout=60, echo=False)
    return "docker compose" if code == 0 else "docker-compose"


def cmd_build() -> None:
    with connect() as ssh:
        engine = _compose(ssh)
        code, out = run(ssh, f"cd {REMOTE_DIR} && {engine} build --progress=plain", timeout=3600)
        if code != 0:
            print("\n构建失败，是否需要换镜像源重试？可设置环境变量后重跑。")
            sys.exit(code)


def cmd_up() -> None:
    with connect() as ssh:
        engine = _compose(ssh)
        code, out = run(ssh, f"cd {REMOTE_DIR} && {engine} up -d", timeout=1800)
        if code != 0:
            sys.exit(code)
        run(ssh, f"cd {REMOTE_DIR} && {engine} ps", timeout=120)
        for attempt in range(30):
            time.sleep(5)
            code2, out2 = run(
                ssh,
                "curl -sS -m 5 http://127.0.0.1:8000/api/health",
                timeout=60,
                echo=False,
            )
            print(f"[健康检查 {attempt + 1}/30] {out2.strip()[:300]}")
            if '"mysql":"ok"' in out2 and '"chroma":"ok"' in out2:
                run(ssh, "curl -sS -m 5 -o /dev/null -w '首页 HTTP %{http_code}\\n' http://127.0.0.1:8000/", echo=False)
                print("\n服务已就绪：http://" + HOST + ":8000")
                return
        print("\n健康检查未在 150s 内通过，继续查看日志。")
        sys.exit(1)


def cmd_status() -> None:
    with connect() as ssh:
        engine = _compose(ssh)
        run(ssh, f"cd {REMOTE_DIR} && {engine} ps", timeout=120)
        run(ssh, "docker inspect -f '{{.Name}} {{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' study_mate_app study_mate_mysql 2>&1", timeout=120)
        run(ssh, "docker stats --no-stream --format 'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}' 2>&1", timeout=120)
        run(ssh, "free -m | head -2", timeout=60)


def cmd_logs() -> None:
    with connect() as ssh:
        engine = _compose(ssh)
        run(ssh, f"cd {REMOTE_DIR} && {engine} logs --tail=80 app", timeout=120)


def cmd_sh() -> None:
    """在服务器上执行任意命令：python deploy.py sh "docker ps" """
    command = " ".join(sys.argv[2:])
    if not command:
        sys.exit("用法：python deploy.py sh \"<命令>\"")
    with connect() as ssh:
        code, _ = run(ssh, command, timeout=900)
        sys.exit(code)


COMMANDS = {
    "probe": cmd_probe,
    "bootstrap": cmd_bootstrap,
    "upload": cmd_upload,
    "build": cmd_build,
    "up": cmd_up,
    "status": cmd_status,
    "logs": cmd_logs,
    "sh": cmd_sh,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()

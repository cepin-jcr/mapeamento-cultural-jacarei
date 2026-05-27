# -*- coding: utf-8 -*-

import http.server
import json
import sqlite3
import urllib.parse
import os
import sys
import subprocess
import threading
import time
import re
import socket

PORT = 8000
DB_FILE = "mapeamento.db"

# ==========================================
# UTF8
# ==========================================

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace"
        )

        sys.stderr.reconfigure(
            encoding="utf-8",
            errors="replace"
        )

    except:
        pass

# ==========================================
# DATABASE
# ==========================================

def init_db():

    print("\n[SQLITE] INIT")

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        area TEXT,
        bio TEXT,
        contato TEXT,
        foto TEXT
    )
    """)

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM agentes")

    total = cursor.fetchone()[0]

    print(f"[SQLITE] TOTAL = {total}")

    if total == 0:

        print("[SQLITE] INSERT MOCKS")

        mocks = [
            (
                "Ana Silva",
                "Artesanato",
                "Bio",
                "Contato",
                "https://picsum.photos/400"
            ),
            (
                "Carlos Souza",
                "Musica",
                "Bio",
                "Contato",
                "https://picsum.photos/400"
            )
        ]

        cursor.executemany("""
        INSERT INTO agentes
        (nome, area, bio, contato, foto)
        VALUES (?, ?, ?, ?, ?)
        """, mocks)

        conn.commit()

    conn.close()

    print("[SQLITE] OK")

# ==========================================
# HANDLER
# ==========================================

class APIHandler(http.server.BaseHTTPRequestHandler):

    protocol_version = "HTTP/1.1"

    # ======================================

    def log_message(self, format, *args):

        print(
            f"[HTTP] "
            f"{self.client_address} "
            f"{format % args}"
        )

    # ======================================

    def send_cors(self):

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "*"
        )

    # ======================================

    def respond_json(self, data, status=200):

        try:

            text = json.dumps(
                data,
                ensure_ascii=False
            )

            payload = text.encode("utf-8")

            print("\n----------------------")
            print(f"[RESPONSE] STATUS={status}")
            print(f"[RESPONSE] BYTES={len(payload)}")
            print(f"[RESPONSE] DATA={text[:300]}")
            print("----------------------")

            self.send_response(status)

            self.send_cors()

            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(payload))
            )

            self.send_header(
                "Connection",
                "close"
            )

            self.end_headers()

            self.wfile.write(payload)

            self.wfile.flush()

            print("[RESPONSE] SENT")

        except Exception as e:

            print(f"[RESPONSE ERROR] {repr(e)}")

    # ======================================

    def do_OPTIONS(self):

        print("[OPTIONS]")

        self.send_response(200)

        self.send_cors()

        self.end_headers()

    # ======================================

    def do_GET(self):

        print("\n================================")
        print("[GET]")
        print(f"PATH = {self.path}")
        print(f"CLIENT = {self.client_address}")
        print("================================")

        try:

            parsed = urllib.parse.urlparse(self.path)

            path = parsed.path

            # -----------------------------

            if path == "/":

                return self.respond_json({
                    "success": True,
                    "message": "API ONLINE"
                })

            # -----------------------------

            if path == "/api/test":

                return self.respond_json({
                    "success": True,
                    "message": "TEST OK"
                })

            # -----------------------------

            if path == "/api/agentes":

                conn = sqlite3.connect(DB_FILE)

                cursor = conn.cursor()

                cursor.execute("""
                SELECT
                    id,
                    nome,
                    area,
                    bio,
                    contato,
                    foto
                FROM agentes
                """)

                cols = [
                    x[0]
                    for x in cursor.description
                ]

                rows = cursor.fetchall()

                data = [
                    dict(zip(cols, row))
                    for row in rows
                ]

                conn.close()

                print(f"[SQLITE] ROWS={len(data)}")

                return self.respond_json(data)

            # -----------------------------

            return self.respond_json({
                "error": "not found",
                "path": path
            }, 404)

        except Exception as e:

            print(f"[GET ERROR] {repr(e)}")

            return self.respond_json({
                "error": str(e)
            }, 500)

# ==========================================
# HTTP SERVER
# ==========================================

def run_server():

    try:

        print("\n================================")
        print("[SERVER START]")
        print("================================")

        # IMPORTANTISSIMO
        # 0.0.0.0 e nao 127.0.0.1

        bind = ("0.0.0.0", PORT)

        print(f"[BIND] {bind}")

        server = http.server.ThreadingHTTPServer(
            bind,
            APIHandler
        )

        print("[SERVER CREATED]")

        sock = server.socket.getsockname()

        print(f"[SOCKET] {sock}")

        print(f"[ONLINE] http://localhost:{PORT}")

        server.serve_forever()

    except Exception as e:

        print("\n[FATAL SERVER ERROR]")
        print(repr(e))

# ==========================================
# PORT TEST
# ==========================================

def test_port():

    print("\n================================")
    print("[PORT TEST]")
    print("================================")

    s = socket.socket()

    result = s.connect_ex(("127.0.0.1", PORT))

    print(f"[RESULT] {result}")

    if result == 0:
        print("[PORT OPEN]")
    else:
        print("[PORT CLOSED]")

    s.close()

# ==========================================
# CLOUDFLARE
# ==========================================

def get_github_token():
    token_file = "github_token.txt"
    if os.path.exists(token_file):
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                token = f.read().strip()
                if token:
                    return token
        except:
            pass

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    if not sys.stdin.isatty():
        print("[GITHUB] Executando em modo não-interativo. Pulando prompt do token.")
        return None

    print("\n[GITHUB] Token do GitHub não encontrado!")
    print("Para atualizar a URL automaticamente no repositório GitHub Pages, precisamos do seu Token de Acesso Pessoal (PAT).")
    token = input("Insira seu token do GitHub (ou aperte Enter para pular): ").strip()
    if token:
        try:
            with open(token_file, "w", encoding="utf-8") as f:
                f.write(token)
            if os.path.exists(".gitignore"):
                with open(".gitignore", "a+", encoding="utf-8") as f:
                    f.seek(0)
                    content = f.read()
                    if token_file not in content:
                        f.write(f"\n{token_file}\n")
        except Exception as e:
            print("[WARN] Não foi possível salvar o token localmente:", e)
    return token

def update_github_url(url):
    import urllib.request
    import base64
    
    token = get_github_token()
    if not token:
        print("[GITHUB] Atualização automática pulada (sem token).")
        return

    repo = "cepin-jcr/mapeamento-cultural-jacarei"
    path = "local_api_url.txt"
    branch = "main"

    print(f"[GITHUB] Atualizando {path} no repositório {repo}...")
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Python-urllib"
    }

    sha = None
    try:
        req = urllib.request.Request(f"{api_url}?ref={branch}", headers=headers)
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode('utf-8'))
            sha = data.get("sha")
    except Exception as e:
        pass

    body = {
        "message": f"update api url to {url} [skip ci]",
        "content": base64.b64encode(url.encode('utf-8')).decode('utf-8'),
        "branch": branch
    }
    if sha:
        body["sha"] = sha

    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(body).encode('utf-8'),
            headers=headers,
            method="PUT"
        )
        with urllib.request.urlopen(req) as res:
            if res.status in (200, 201):
                print("\n================================")
                print("[GITHUB SUCCESS] URL da API atualizada com sucesso no GitHub Pages!")
                print(f"Nova URL: {url}")
                print("================================\n")
            else:
                print(f"[GITHUB ERROR] Falha ao atualizar. Status: {res.status}")
    except Exception as e:
         print(f"[GITHUB ERROR] Erro na requisição API: {e}")

def start_tunnel():
    print("\n================================")
    print("[INICIANDO TÚNEL DE CONEXÃO]")
    print("================================")

    cmd_cf = [
        "cloudflared",
        "tunnel",
        "--url",
        f"http://127.0.0.1:{PORT}",
        "--protocol",
        "http2",
        "--loglevel",
        "debug"
    ]

    if os.path.exists("cloudflared.exe"):
        cmd_cf[0] = "./cloudflared.exe"

    print(f"[CF] Tentando iniciar Cloudflare Tunnel: {' '.join(cmd_cf)}")

    cf_failed = False
    process_cf = None
    try:
        process_cf = subprocess.Popen(
            cmd_cf,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )
    except FileNotFoundError:
        print("[CF] Executável cloudflared não encontrado. Usando Pinggy como fallback...")
        cf_failed = True

    url = None
    if not cf_failed and process_cf:
        start_time = time.time()
        while time.time() - start_time < 15:
            if process_cf.poll() is not None:
                cf_failed = True
                break

            try:
                line = process_cf.stdout.readline()
                if not line:
                    continue
                line = line.strip()
                print(f"[CF] {line}")

                if "Environment has critical failures" in line or "timeout" in line or "failed to dial" in line:
                    print("[CF] Falha de conexão detectada (provavelmente bloqueio de firewall na porta 7844).")
                    cf_failed = True
                    break

                if "trycloudflare.com" in line:
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                    if match:
                        url = match.group(0)
                        break
            except Exception:
                pass

        if cf_failed or not url:
            print("[CF] Cloudflare falhou ou demorou para conectar. Finalizando processo do Cloudflare...")
            try:
                process_cf.terminate()
                process_cf.wait(timeout=2)
            except:
                pass
            cf_failed = True

    if cf_failed or not url:
        print("\n[PINGGY] Iniciando túnel SSH alternativo sobre HTTPS (Porta 443)...")
        cmd_pinggy = [
            "ssh",
            "-T",
            "-p",
            "443",
            "-o",
            "StrictHostKeyChecking=no",
            "-R",
            f"80:127.0.0.1:{PORT}",
            "a.pinggy.io"
        ]

        print(f"[PINGGY] Executando: {' '.join(cmd_pinggy)}")
        try:
            process_pinggy = subprocess.Popen(
                cmd_pinggy,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )
        except Exception as e:
            print(f"[PINGGY ERROR] Falha ao iniciar SSH cliente: {e}")
            return

        start_time = time.time()
        while time.time() - start_time < 15:
            if process_pinggy.poll() is not None:
                print("[PINGGY EXIT] Processo SSH encerrado.")
                break

            line = process_pinggy.stdout.readline()
            if not line:
                continue
            line = line.strip()
            print(f"[PINGGY] {line}")

            if "pinggy-free.link" in line:
                match = re.search(r'https://[a-zA-Z0-9-]+\.run\.pinggy-free\.link', line)
                if match:
                    url = match.group(0)
                    break

        def keep_reading(proc):
            while proc.poll() is None:
                try:
                    proc.stdout.readline()
                except:
                    break

        threading.Thread(target=keep_reading, args=(process_pinggy,), daemon=True).start()

    if url:
        print("\n================================")
        print("[TÚNEL ESTABELECIDO]")
        print(f"URL PÚBLICA = {url}")
        print("================================")

        # Escreve a URL no arquivo local para que a pasta local esteja conectada
        try:
            with open("local_api_url.txt", "w", encoding="utf-8") as f:
                f.write(url)
            print(f"[LOCAL SUCCESS] URL salva em local_api_url.txt: {url}")
        except Exception as e:
            print(f"[LOCAL ERROR] Falha ao salvar URL localmente: {e}")

        try:
            update_github_url(url)
        except Exception as e:
            print(f"[GITHUB ERROR] Falha ao atualizar URL: {e}")

        while True:
            time.sleep(3600)
    else:
        print("\n[ERRO] Não foi possível estabelecer nenhum túnel de conexão.")

# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    print("\n================================")
    print("DEBUG SERVER")
    print("================================")

    init_db()

    thread = threading.Thread(
        target=run_server,
        daemon=True
    )

    thread.start()

    print("[THREAD STARTED]")

    time.sleep(3)

    test_port()

    try:

        start_tunnel()

    except KeyboardInterrupt:

        print("\n[EXIT]")
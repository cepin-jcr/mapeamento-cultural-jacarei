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

def start_cloudflare():

    print("\n================================")
    print("[CLOUDFLARE]")
    print("================================")

    cmd = [
        "cloudflared",
        "tunnel",
        "--url",
        f"http://localhost:{PORT}",
        "--protocol",
        "http2",
        "--loglevel",
        "debug"
    ]

    print(f"[CMD] {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )

    while True:

        line = process.stdout.readline()

        if not line:

            if process.poll() is not None:

                print("[CLOUDFLARE EXIT]")

                break

            continue

        line = line.strip()

        print(f"[CF] {line}")

        if "trycloudflare.com" in line:

            match = re.search(
                r'https://[a-zA-Z0-9-]+\.trycloudflare\.com',
                line
            )

            if match:

                url = match.group(0)

                print("\n================================")
                print("[TUNNEL ONLINE]")
                print(f"URL = {url}")
                print("================================")

                print("\nTESTE:")
                print(url)
                print(url + "/api/test")
                print(url + "/api/agentes")

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

        start_cloudflare()

    except KeyboardInterrupt:

        print("\n[EXIT]")
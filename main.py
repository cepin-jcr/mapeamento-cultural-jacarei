# -*- coding: utf-8 -*-
"""
Servidor Backend Centralizado - Mapeamento Cultural de Jacarei
Desenvolvido com bibliotecas nativas do Python (Standard Library apenas)
- Banco de Dados SQLite integrado (mapeamento.db)
- Servidor HTTP com suporte total a CORS
- Sincronizacao automatica com Tunel Cloudflare (Sem necessidade de Port-Forwarding!)
"""

import http.server
import socketserver
import json
import sqlite3
import urllib.request
import urllib.parse
import os
import sys
import subprocess
import threading
import time
import re

PORT = 8000
DB_FILE = "mapeamento.db"
CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
CLOUDFLARED_BIN = "cloudflared.exe"
URL_FILE = "local_api_url.txt"

# Configurar stdout para suportar codificacoes legadas sem quebrar por caracteres especiais
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ==========================================
# 1. INICIALIZACAO DO BANCO DE DADOS (SQLITE)
# ==========================================

def init_db():
    print("[SQLITE] Inicializando Banco de Dados SQLite...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Criar tabelas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        area TEXT NOT NULL,
        bio TEXT,
        contato TEXT,
        foto TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS espacos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        tipo TEXT NOT NULL,
        endereco TEXT NOT NULL,
        lat REAL,
        lng REAL,
        descricao TEXT,
        contato TEXT,
        foto TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        data TEXT NOT NULL,
        horario TEXT,
        local TEXT,
        descricao TEXT,
        organizador TEXT,
        foto TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mensagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        texto TEXT NOT NULL,
        data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    
    # Verificar se as tabelas estao vazias para semear dados mockados de Jacarei
    cursor.execute("SELECT COUNT(*) FROM agentes")
    if cursor.fetchone()[0] == 0:
        print("[SQLITE] Semeando dados mockados de Agentes Culturais...")
        agentes_mock = [
            ("Ana Silva", "Artesanato", "Artesa local especializada em croche e ceramica com elementos tradicionais do Vale do Paraiba.", "ana.artes@email.com", "https://picsum.photos/400/400?1"),
            ("Carlos Souza", "Música", "Musico, compositor e violonista classico, com projetos sociais de educacao musical para jovens em Jacarei.", "carlossouza@email.com", "https://picsum.photos/400/400?2"),
            ("Coletivo Jacarei de Teatro", "Teatro", "Grupo independente focado em teatro de rua, intervencoes urbanas e contacao de historias historicas.", "coletivojacarei@email.com", "https://picsum.photos/400/400?3"),
            ("Juliana Mendes", "Artes Visuais", "Artista visual, muralista e pintora que explora as paisagens naturais e o patrimonio historico da regiao.", "juliana.mendes@email.com", "https://picsum.photos/400/400?4"),
            ("Mestre Benedito", "Cultura Popular", "Lider comunitario do grupo de Mocambique de Jacarei, preservando a danca e os cantos de raiz afro-brasileira.", "benedito.popular@email.com", "https://picsum.photos/400/400?5")
        ]
        cursor.executemany("INSERT INTO agentes (nome, area, bio, contato, foto) VALUES (?, ?, ?, ?, ?)", agentes_mock)
        
    cursor.execute("SELECT COUNT(*) FROM espacos")
    if cursor.fetchone()[0] == 0:
        print("[SQLITE] Semeando dados mockados de Espacos Culturais...")
        espacos_mock = [
            ("MAB - Museu de Antropologia do Vale do Paraíba", "Museu", "R. XV de Novembro, 143 - Centro, Jacarei - SP", -23.3053, -45.9658, "Espaco historico que abriga acervos valiosos sobre a cultura, arte popular e a memoria da sociedade do Vale do Paraiba.", "mab@jacarei.sp.gov.br", "https://picsum.photos/600/400?10"),
            ("Sala Mário Lago", "Teatro", "Pca. Raul Chaves, 110 - Centro, Jacarei - SP", -23.3061, -45.9669, "Importante casa de espetaculos municipal, palco de apresentacoes teatrais, danca, exibicoes cinematograficas e concertos musicais gratuitos.", "cultura@jacarei.sp.gov.br", "https://picsum.photos/600/400?11"),
            ("Parque dos Espanhois", "Centro Cultural", "Av. Joaquim Alvarenga, 450 - Jardim Santa Maria, Jacarei - SP", -23.2980, -45.9750, "Espaco verde voltado ao lazer, com anfiteatro ao ar livre, quadras esportivas e encontros de coletivos artisticos nos finais de semana.", "parque.espanhois@email.com", "https://picsum.photos/600/400?12"),
            ("Biblioteca Municipal Macedo Soares", "Biblioteca", "Av. Nove de Julho, 215 - Centro, Jacarei - SP", -23.3035, -45.9610, "Ambiente tranquilo de leitura com acervo de milhares de livros, espaco infantil, computadores para estudo e oficinas literarias.", "biblioteca@jacarei.sp.gov.br", "https://picsum.photos/600/400?13"),
            ("Atelie Vivo de Jacarei", "Atelie Coletivo", "Rua Dr. Lucio Malta, 380 - Centro, Jacarei - SP", -23.3075, -45.9640, "Espaco colaborativo independente de artistas locais, promovendo cursos de pintura, argila, escrita criativa e saraus abertos a comunidade.", "atelievivo@email.com", "https://picsum.photos/600/400?14")
        ]
        cursor.executemany("INSERT INTO espacos (nome, tipo, endereco, lat, lng, descricao, contato, foto) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", espacos_mock)

    cursor.execute("SELECT COUNT(*) FROM eventos")
    if cursor.fetchone()[0] == 0:
        print("[SQLITE] Semeando dados mockados de Eventos Culturais...")
        eventos_mock = [
            ("Feira de Artesanato & Memoria", "2026-06-15", "10:00", "Patio dos Trilhos", "Uma feira vibrante reunindo os melhores artesaos de Jacarei, com oficinas gratuitas de ceramica, musica ao vivo e comidas tipicas regionais.", "Ana Silva", "https://picsum.photos/600/350?20"),
            ("Concerto Especial: Orquestra Sinfonica de Jacarei", "2026-06-20", "20:00", "Sala Mario Lago", "Apresentacao emocionante da Orquestra Sinfonica Municipal interpretando classicos brasileiros e trilhas sonoras famosas do cinema.", "Secretaria de Cultura", "https://picsum.photos/600/350?21"),
            ("Festival de Teatro de Jacarei (FESTE)", "2026-07-05", "18:00", "Praca Raul Chaves", "Grande festival reunindo trupes de teatro locais e convidadas de todo o pais para apresentacoes abertas, intervencoes publicas e oficinas formativas.", "Coletivo Jacarei de Teatro", "https://picsum.photos/600/350?22"),
            ("Exposicao Olhares Jacarei", "2026-06-28", "14:00", "MAB - Museu de Antropologia", "Exposicao fotografica e de murais digitais destacando a arquitetura colonial de Jacarei e a diversidade etnica da populacao valeparaibana.", "Juliana Mendes", "https://picsum.photos/600/350?23"),
            ("Encontro de Mocambique & Capoeira", "2026-07-12", "09:00", "Praca do Rosario", "Celebracao das tradicoes populares afro-brasileiras com roda de capoeira angola, apresentacoes do grupo de Mocambique, cantos rituais e almoco comunitario.", "Mestre Benedito", "https://picsum.photos/600/350?24")
        ]
        cursor.executemany("INSERT INTO eventos (titulo, data, horario, local, descricao, organizador, foto) VALUES (?, ?, ?, ?, ?, ?, ?)", eventos_mock)

    cursor.execute("SELECT COUNT(*) FROM mensagens")
    if cursor.fetchone()[0] == 0:
        print("[SQLITE] Semeando dados mockados de Mensagens da Comunidade...")
        mensagens_mock = [
            ("Sistema", "Ola a todos! Sejam muito bem-vindos ao Mural Cultural da comunidade de Jacarei! Use este espaco para postar recados, fechar parcerias artisticas, convidar para saraus ou compartilhar contatos!"),
            ("Ana Silva", "Estou organizando a proxima Feira de Artesanato no Patio dos Trilhos e procuro musicos locais para apresentacoes acusticas curtas de 30 minutos. Quem tiver interesse, me manda um email!"),
            ("Carlos Souza", "Ola Ana! Tenho total interesse! Podemos apresentar uma selecao de MPB instrumental e violao classico. Vou te mandar um email com alguns videos de apresentacoes anteriores!"),
            ("Coletivo Jacarei de Teatro", "Lembrando que no proximo domingo teremos oficina gratuita de expressao corporal na Praca Raul Chaves a partir das 15h. Tragam roupas confortaveis e garrafas d'agua!"),
            ("Juliana Mendes", "Estou finalizando um novo mural no centro e adoraria a opiniao dos moradores. Postei algumas fotos no meu perfil, confiram la!")
        ]
        cursor.executemany("INSERT INTO mensagens (nome, texto) VALUES (?, ?)", mensagens_mock)
        
    conn.commit()
    conn.close()
    print("[SQLITE] Banco de dados preparado com sucesso!")

# ==========================================
# 2. ROTAS E COMPORTAMENTO DO SERVIDOR HTTP
# ==========================================

class CulturalAPIHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # Desativa logs verbosos no console para nao sujar a saida limpa da tela do usuario
        pass

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def respond_json(self, data, status=200):
        self.send_response(status)
        self.send_cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Permitir ler o arquivo da URL do tunel pela rede local
        if path == "/api/tunnel-url":
            if os.path.exists(URL_FILE):
                with open(URL_FILE, "r") as f:
                    url = f.read().strip()
                return self.respond_json({"url": url})
            else:
                return self.respond_json({"url": ""})

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            if path == '/api/agentes':
                cursor.execute("SELECT id, nome, area, bio, contato, foto FROM agentes ORDER BY nome")
                columns = [col[0] for col in cursor.description]
                data = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return self.respond_json(data)
                
            elif path == '/api/espacos':
                cursor.execute("SELECT id, nome, tipo, endereco, lat, lng, descricao, contato, foto FROM espacos ORDER BY nome")
                columns = [col[0] for col in cursor.description]
                data = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return self.respond_json(data)
                
            elif path == '/api/eventos':
                cursor.execute("SELECT id, titulo, data, horario, local, descricao, organizador, foto FROM eventos ORDER BY data ASC, horario ASC")
                columns = [col[0] for col in cursor.description]
                data = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return self.respond_json(data)
                
            elif path == '/api/mensagens':
                cursor.execute("SELECT id, nome, texto, data_envio FROM mensagens ORDER BY id DESC LIMIT 50")
                columns = [col[0] for col in cursor.description]
                data = [dict(zip(columns, row)) for row in cursor.fetchall()]
                data.reverse()  # Para exibir em ordem cronologica de envio na interface de chat
                return self.respond_json(data)
                
            else:
                self.send_response(404)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(b"Roteamento nao encontrado")
                
        except Exception as e:
            print(f"[GET] Erro de processamento: {str(e)}")
            self.respond_json({"error": str(e)}, 500)
        finally:
            conn.close()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Obter corpo JSON
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return self.respond_json({"error": "Corpo da requisicao vazio"}, 400)
            
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return self.respond_json({"error": "JSON malformatado"}, 400)

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            if path == '/api/agentes':
                nome = payload.get("nome")
                area = payload.get("area")
                bio = payload.get("bio", "")
                contato = payload.get("contato", "")
                foto = payload.get("foto", "https://picsum.photos/400/400?random")
                
                if not nome or not area:
                    return self.respond_json({"error": "Nome e Area sao obrigatorios"}, 400)
                    
                cursor.execute(
                    "INSERT INTO agentes (nome, area, bio, contato, foto) VALUES (?, ?, ?, ?, ?)",
                    (nome, area, bio, contato, foto)
                )
                conn.commit()
                return self.respond_json({"success": True, "id": cursor.lastrowid})
                
            elif path == '/api/espacos':
                nome = payload.get("nome")
                tipo = payload.get("tipo")
                endereco = payload.get("endereco")
                lat = payload.get("lat")
                lng = payload.get("lng")
                descricao = payload.get("descricao", "")
                contato = payload.get("contato", "")
                foto = payload.get("foto", "https://picsum.photos/600/400?random")
                
                if not nome or not tipo or not endereco:
                    return self.respond_json({"error": "Nome, tipo e endereco sao obrigatorios"}, 400)
                
                # Tratar floats de coordenadas
                try:
                    lat_f = float(lat) if lat is not None else -23.3053
                    lng_f = float(lng) if lng is not None else -45.9658
                except ValueError:
                    lat_f, lng_f = -23.3053, -45.9658
                    
                cursor.execute(
                    "INSERT INTO espacos (nome, tipo, endereco, lat, lng, descricao, contato, foto) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (nome, tipo, endereco, lat_f, lng_f, descricao, contato, foto)
                )
                conn.commit()
                return self.respond_json({"success": True, "id": cursor.lastrowid})
                
            elif path == '/api/eventos':
                titulo = payload.get("titulo")
                data = payload.get("data")
                horario = payload.get("horario", "00:00")
                local = payload.get("local", "")
                descricao = payload.get("descricao", "")
                organizador = payload.get("organizador", "")
                foto = payload.get("foto", "https://picsum.photos/600/350?random")
                
                if not titulo or not data:
                    return self.respond_json({"error": "Titulo e data sao obrigatorios"}, 400)
                    
                cursor.execute(
                    "INSERT INTO eventos (titulo, data, horario, local, descricao, organizador, foto) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (titulo, data, horario, local, descricao, organizador, foto)
                )
                conn.commit()
                return self.respond_json({"success": True, "id": cursor.lastrowid})
                
            elif path == '/api/mensagens':
                nome = payload.get("nome")
                texto = payload.get("texto")
                
                if not nome or not texto:
                    return self.respond_json({"error": "Nome e texto sao obrigatorios"}, 400)
                    
                cursor.execute("INSERT INTO mensagens (nome, texto) VALUES (?, ?)", (nome, texto))
                conn.commit()
                return self.respond_json({"success": True, "id": cursor.lastrowid})
                
            else:
                self.send_response(404)
                self.send_cors_headers()
                self.end_headers()
                
        except Exception as e:
            print(f"[POST] Erro de processamento: {str(e)}")
            self.respond_json({"error": str(e)}, 500)
        finally:
            conn.close()

    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Rota de deletar elemento com query params ?id=X
        query = urllib.parse.parse_qs(parsed_url.query)
        target_id = query.get("id", [None])[0]
        
        if not target_id:
            return self.respond_json({"error": "ID nao especificado"}, 400)
            
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            if path == '/api/agentes':
                cursor.execute("DELETE FROM agentes WHERE id = ?", (target_id,))
            elif path == '/api/espacos':
                cursor.execute("DELETE FROM espacos WHERE id = ?", (target_id,))
            elif path == '/api/eventos':
                cursor.execute("DELETE FROM eventos WHERE id = ?", (target_id,))
            else:
                return self.respond_json({"error": "Rota invalida para delecao"}, 404)
                
            conn.commit()
            return self.respond_json({"success": True})
        except Exception as e:
            return self.respond_json({"error": str(e)}, 500)
        finally:
            conn.close()

def run_http_server():
    server_address = ('', PORT)
    with socketserver.TCPServer(server_address, CulturalAPIHandler) as httpd:
        print(f"[HTTP] Servidor ativo na porta local {PORT}")
        httpd.serve_forever()

# ==========================================
# 3. CONTROLE E AUTOMACAO DO CLOUDFLARE TUNNEL
# ==========================================

def get_cloudflared_binary():
    # Verifica se o cloudflared ja esta instalado no sistema (PATH)
    try:
        subprocess.run(["cloudflared", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "cloudflared"
    except FileNotFoundError:
        pass
        
    # Verifica se ja esta na pasta local
    if os.path.exists(CLOUDFLARED_BIN):
        return f"./{CLOUDFLARED_BIN}"
        
    # Se nao encontrar, e for Windows, baixa automaticamente
    if sys.platform.startswith("win"):
        print("[INFO] Utilitario 'cloudflared' nao foi encontrado no sistema.")
        print("[DOWNLOAD] Baixando 'cloudflared.exe' automaticamente da Cloudflare...")
        
        def report_progress(block_num, block_size, total_size):
            read_so_far = block_num * block_size
            if total_size > 0:
                percent = read_so_far * 100 / total_size
                s = f"\r[Progresso do Download]: {percent:.1f}% ({read_so_far / (1024*1024):.1f}MB de {total_size / (1024*1024):.1f}MB)"
                sys.stdout.write(s)
                sys.stdout.flush()
            else:
                sys.stdout.write(f"\rBaixado: {read_so_far / (1024*1024):.1f}MB")
                sys.stdout.flush()

        try:
            urllib.request.urlretrieve(CLOUDFLARED_URL, CLOUDFLARED_BIN, report_progress)
            print("\n[DOWNLOAD] Concluido com sucesso!")
            return f"./{CLOUDFLARED_BIN}"
        except Exception as e:
            print(f"\n[DOWNLOAD] Erro durante o download automatico: {e}")
            print("Por favor, instale o 'cloudflared' manualmente ou execute apenas o servidor local.")
            return None
    else:
        print("[WARNING] Seu sistema operacional nao e Windows.")
        print("Por favor, certifique-se de instalar o utilitario 'cloudflared' no seu sistema operacional.")
        print("Ubuntu/macOS: 'brew install cloudflared' ou 'sudo apt install cloudflared'")
        return None

def start_cloudflare_tunnel(binary):
    if not binary:
        print("[ERROR] Nao foi possivel iniciar o tunel Cloudflare automaticamente.")
        print("Voce pode testar localmente em: http://localhost:8000")
        return
        
    print("[CLOUDFLARE] Iniciando tunel seguro (Quick Tunnel)...")
    cmd = [binary, "tunnel", "--url", f"http://localhost:{PORT}"]
    
    try:
        # Iniciamos o tunel capturando os logs. O cloudflared envia os logs de tunel para o stderr
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            bufsize=1,
            encoding='utf-8',
            errors='ignore'
        )
        
        tunnel_url = None
        # Procura a URL do tunel no log
        for line in iter(process.stdout.readline, ''):
            if "trycloudflare.com" in line:
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if match:
                    tunnel_url = match.group(0)
                    
                    # Salva em um arquivo local para facilitar a auto-descoberta pelo frontend
                    with open(URL_FILE, "w") as f:
                        f.write(tunnel_url)
                        
                    print("\n" + "="*70)
                    print("== SISTEMA DE MAPEAMENTO CULTURAL DE JACAREI - BACKEND ATIVO ==")
                    print("="*70)
                    print(f"   Servidor Local:   http://localhost:{PORT}")
                    print(f"   Tunel Seguro API:  {tunnel_url}")
                    print("="*70)
                    print("   Para conectar este backend ao GitHub Pages:")
                    print("   1. Acesse o site no navegador.")
                    print("   2. Va em 'Ajustar API' na barra superior ou na aba 'Perfil'.")
                    print(f"   3. Insira o seguinte link: {tunnel_url}")
                    print("="*70)
                    print("\n(Pressione Ctrl+C para encerrar o servidor e fechar o tunel)\n")
                    break
        
        # Continua rodando em segundo plano monitorando o processo
        while process.poll() is None:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[INFO] Encerrando tunel Cloudflare e servidor HTTP...")
    except Exception as e:
        print(f"\n[ERROR] Falha ao executar o processo do tunel: {e}")
        print(f"Voce ainda pode usar localmente em http://localhost:{PORT}")

# ==========================================
# 4. EXECUCAO PRINCIPAL
# ==========================================

if __name__ == "__main__":
    init_db()
    
    # Inicia o servidor HTTP em uma thread secundaria (daemon) para rodar junto com o tunel
    server_thread = threading.Thread(target=run_http_server, daemon=True)
    server_thread.start()
    
    # Aguarda o servidor subir
    time.sleep(1)
    
    # Procura e ativa o cloudflared tunnel na thread principal
    cf_binary = get_cloudflared_binary()
    
    try:
        if cf_binary:
            start_cloudflare_tunnel(cf_binary)
        else:
            print("\n[INFO] Rodando apenas em modo local.")
            print(f"Acesse o backend local em: http://localhost:{PORT}")
            print("Pressione Ctrl+C para encerrar.")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Encerrando servidor. Ate logo!")
        sys.exit(0)

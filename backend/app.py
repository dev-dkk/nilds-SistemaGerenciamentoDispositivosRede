import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import mysql.connector
import bcrypt
import subprocess
import platform
import ipaddress
import socket
import nmap
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import traceback
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from logging.handlers import RotatingFileHandler
import json
import jwt

# --- INÍCIO DA CONFIGURAÇÃO CENTRALIZADA DE LOGGING ---

# 1. Obter o logger raiz. Todas as outras bibliotecas (Flask, APScheduler) herdarão essa configuração.
log = logging.getLogger()

def setup_structured_logging():
    """Configura o logging para salvar em arquivos com rotação e formato estruturado."""
    # Formato do log: Data/Hora, Nível, Nome do Módulo, Função, Linha - Mensagem
    log_formatter = logging.Formatter(
        '%(asctime)s %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] - %(message)s'
    )
    
    # Cria um arquivo 'app.log' que rotaciona após 10MB, mantendo 5 backups.
    log_file_handler = RotatingFileHandler('app.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    log_file_handler.setFormatter(log_formatter)
    log_file_handler.setLevel(logging.INFO) # Nível mínimo para o arquivo de log

    # Adiciona um handler para exibir logs no console também (útil para desenvolvimento)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO) # Nível mínimo para o console

    # Define o nível global do logger e limpa handlers existentes para evitar duplicação
    log.setLevel(logging.INFO)
    log.handlers.clear()
    
    # Adiciona os novos handlers
    log.addHandler(log_file_handler)
    log.addHandler(console_handler)

    # Reduz o "ruído" de bibliotecas muito verbosas, se necessário
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('mysql.connector').setLevel(logging.WARNING)
    
    log.info("="*50)
    log.info("Logging Estruturado Configurado com Sucesso")
    log.info("Logs serão salvos em 'app.log'")
    log.info("="*50)

# 2. Chamar a função de configuração uma vez, no início da aplicação.
setup_structured_logging()

# --- FIM DA CONFIGURAÇÃO CENTRALIZADA DE LOGGING ---


def registrar_log_auditoria(id_usuario, nome_usuario, acao, detalhes=None, ip_origem=None):
    """Registra um evento na tabela de LogAuditoria."""
    conn = None
    cursor = None
    log.info(f"AUDIT_DB_LOG: UserID: {id_usuario or 'Sistema'}, User: {nome_usuario or 'Sistema'}, Action: {acao}, IP: {ip_origem}")
    try:
        conn = get_db_connection()
        if not conn:
            log.error("AUDIT_DB_LOG: Falha ao conectar ao DB para registrar log.")
            return

        cursor = conn.cursor()
        query = """
            INSERT INTO LogAuditoria (ID_Usuario_FK, NomeUsuario, Acao, Detalhes, EnderecoIPOrigem)
            VALUES (%s, %s, %s, %s, %s)
        """
        detalhes_str = str(detalhes) if detalhes is not None else None
        cursor.execute(query, (id_usuario, nome_usuario, acao, detalhes_str, ip_origem))
        conn.commit()
    except Exception as e:
        log.exception("Erro ao registrar log de auditoria no banco de dados.")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)
CORS(app) #Habilitando o CORS

# --- INICIALIZAÇÃO DO AGENDADOR ---
scheduler = BackgroundScheduler(daemon=True, timezone='America/Sao_Paulo')
SCAN_JOB_ID = 'scheduled_network_scan_job'
# --- FIM DA INICIALIZAÇÃO DO AGENDADOR --- 
from functools import wraps

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Verifica se o token está no cabeçalho 'Authorization'
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            # O formato esperado é "Bearer <token>"
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            log.warning("AUTH: Token não encontrado na requisição.")
            return jsonify({'message': 'Token é necessário!'}), 401

        try:
            # Tenta decodificar o token usando a mesma chave secreta
            secret_key = os.getenv('SECRET_KEY')
            data = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Para segurança extra, busca o usuário no banco para garantir que ele ainda existe e está ativo
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT ID_Usuario, NomeUsuario, Ativo FROM Usuario WHERE ID_Usuario = %s", (data['id_usuario'],))
            current_user = cursor.fetchone()
            cursor.close()
            conn.close()

            if not current_user or not current_user['Ativo']:
                log.error(f"AUTH: Usuário do token (ID: {data['id_usuario']}) não encontrado ou inativo.")
                return jsonify({'message': 'Usuário do token inválido!'}), 401

        except jwt.ExpiredSignatureError:
            log.warning("AUTH: Token expirado.")
            return jsonify({'message': 'Token expirou!'}), 401
        except Exception as e:
            log.exception("AUTH: Erro ao decodificar o token.")
            return jsonify({'message': 'Token inválido!'}), 401
        
        # Se tudo deu certo, passa o usuário decodificado para a função da rota
        return f(current_user, *args, **kwargs)

    return decorated
# Configuração do Banco de Dados
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        log.debug('Conexão com o MYSQL bem sucedida.')
        return conn
    except mysql.connector.Error as err:
        log.error(f"Erro ao conectar ao MySQL: {err}")
        return None

#Executar ping e guardar IP´s descobertos
def ping_ip(ip_str):
    """Tenta pingar um IP e retorna True se bem-sucedido, False caso contrário."""
    try:
        if platform.system().lower() == 'windows':
            command = ['ping', '-n', '2', '-w', '500', ip_str] 
        else:
            command = ['ping', '-c', '2', '-W', '1', ip_str]

        startupinfo = None
        if platform.system().lower() == 'windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
        stdout, stderr = process.communicate(timeout=3) 

        stdout_decoded = stdout.decode(errors='ignore').strip()
        stderr_decoded = stderr.decode(errors='ignore').strip()
        log.debug(f"Ping para {ip_str}: RC={process.returncode}")
        if stdout_decoded:
            log.debug(f"  STDOUT: {stdout_decoded}")
        if stderr_decoded:
            log.debug(f"  STDERR: {stderr_decoded}")

        return process.returncode == 0
    except subprocess.TimeoutExpired:
        log.warning(f"Timeout GERAL ao executar comando ping para {ip_str}")
        if 'process' in locals() and process: process.kill() 
        return False
    except Exception as e:
        log.error(f"Exceção ao pingar {ip_str}: {e}")
        return False

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro de conexão com o banco de dados"}), 500

        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                a.ID_Alerta,
                a.DescricaoCustomizada,
                a.DataHoraCriacao,
                a.StatusAlerta,
                a.Severidade,
                a.DataHoraResolucao,
                a.DetalhesTecnicos, 
                ta.Nome AS TipoAlertaNome,
                d.NomeHost AS DispositivoNomeHost,
                ipd.EnderecoIP AS IPDescobertoEndereco
            FROM Alerta a
            JOIN TipoAlerta ta ON a.ID_TipoAlerta = ta.ID_TipoAlerta
            LEFT JOIN Dispositivo d ON a.ID_Dispositivo = d.ID_Dispositivo
            LEFT JOIN IPsDescobertos ipd ON a.ID_IPDescoberto_FK = ipd.ID_IPDescoberto
            ORDER BY a.DataHoraCriacao DESC
        """
        cursor.execute(query)
        alerts = cursor.fetchall()
        return jsonify(alerts), 200

    except Exception as e:
        log.exception("Erro ao buscar alertas")
        return jsonify({"message": "Erro interno ao buscar alertas"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

def get_tipo_alerta_id(conn, nome_tipo_alerta):
    cursor_tipo = None
    try:
        cursor_tipo = conn.cursor(dictionary=True)
        cursor_tipo.execute("SELECT ID_TipoAlerta FROM TipoAlerta WHERE Nome = %s", (nome_tipo_alerta,))
        tipo_alerta = cursor_tipo.fetchone()
        return tipo_alerta['ID_TipoAlerta'] if tipo_alerta else None
    finally:
        if cursor_tipo: cursor_tipo.close()


# Sua função get_tipo_alerta_details_by_name 
def get_tipo_alerta_details_by_name(conn, nome_tipo_alerta):
    cursor_ta = None
    try:
        # Garante que temos uma conexão válida
        if not conn or not conn.is_connected():
            log.warning("GET_TIPO_ALERTA: Tentativa de uso com conexão de DB inválida.")
            return None
        cursor_ta = conn.cursor(dictionary=True)
        cursor_ta.execute("SELECT ID_TipoAlerta, SeveridadePadrao FROM TipoAlerta WHERE Nome = %s", (nome_tipo_alerta,))
        tipo_alerta = cursor_ta.fetchone()
        log.debug(f"GET_TIPO_ALERTA: Resultado para '{nome_tipo_alerta}': {tipo_alerta}")
        return tipo_alerta 
    except Exception as e:
        log.error(f"GET_TIPO_ALERTA: Erro ao buscar detalhes do tipo de alerta '{nome_tipo_alerta}': {e}")
        return None
    finally:
        if cursor_ta: cursor_ta.close()

@app.route('/api/alerts/<int:alert_id>/status', methods=['PUT'])
def update_alert_status(alert_id):
    conn = None
    cursor = None
    ip_origem = request.remote_addr
    data = request.get_json()
    
    try:
        # ### AUDITORIA: Obter dados do usuário ###
        id_usuario_logado = data.get('id_usuario')
        nome_usuario_logado = data.get('nome_usuario')
        novo_status = data.get('status')
        
        data = request.get_json()
        novo_status = data.get('status')

        if not novo_status:
            return jsonify({"message": "Novo status não fornecido no corpo da requisição"}), 400

        allowed_statuses = ['Novo', 'Lido', 'Em_Investigacao', 'Resolvido', 'Ignorado']
        if novo_status not in allowed_statuses:
            return jsonify({"message": f"Status '{novo_status}' inválido."}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        
        cursor = conn.cursor()

        if novo_status == 'Resolvido':
            query = "UPDATE Alerta SET StatusAlerta = %s, DataHoraResolucao = %s WHERE ID_Alerta = %s"
            params = (novo_status, datetime.now(), alert_id)
        else:
            query = "UPDATE Alerta SET StatusAlerta = %s WHERE ID_Alerta = %s"
            params = (novo_status, alert_id)
        
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount > 0:
            # ### AUDITORIA: Registrar a mudança de status ###
            detalhes_log = {
                "alerta_id": alert_id,
                "novo_status": novo_status
            }
            registrar_log_auditoria(
                id_usuario=id_usuario_logado,
                nome_usuario=nome_usuario_logado,
                acao='ALERTA_STATUS_ALTERADO',
                detalhes=json.dumps(detalhes_log),
                ip_origem=ip_origem
            )
            
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"message": "Alerta não encontrado ou status não alterado"}), 404
            
        cursor.close()
        conn.close()
        
        return jsonify({"message": f"Status do Alerta ID {alert_id} atualizado para '{novo_status}' com sucesso."}), 200

    except Exception as e:
        if conn: conn.rollback()
        log.exception(f"Erro ao atualizar status para o alerta ID {alert_id}")
        return jsonify({"message": "Erro ao atualizar status do alerta"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

def process_discovered_ip(ip_str):
    conn = None
    cursor = None
    hostname_resolvido = None
    id_ip_descoberto_novo = None 

    log.info(f"PROCESS_IP: Iniciando processamento para IP: {ip_str}")
    try:
        log.debug(f"PROCESS_IP ({ip_str}): Tentando resolver hostname via rDNS...")
        try:
            hostname_resolvido, _, _ = socket.gethostbyaddr(ip_str)
            log.info(f"PROCESS_IP ({ip_str}): Hostname resolvido: {hostname_resolvido}")
        except socket.herror: 
            log.warning(f"PROCESS_IP ({ip_str}): Não foi possível resolver hostname (socket.herror).")
        except Exception as e_dns: 
            log.error(f"PROCESS_IP ({ip_str}): Erro genérico na resolução DNS: {e_dns}")
        
        conn = get_db_connection()
        if not conn:
            log.critical(f"PROCESS_IP ({ip_str}): FALHA - Não foi possível conectar ao DB.")
            return

        cursor = conn.cursor(dictionary=True)
        
        log.debug(f"PROCESS_IP ({ip_str}): Verificando se IP já existe em IPsDescobertos...")
        cursor.execute("SELECT ID_IPDescoberto FROM IPsDescobertos WHERE EnderecoIP = %s", (ip_str,))
        existing_ip_data = cursor.fetchone()

        if existing_ip_data:
            ip_id_existente = existing_ip_data['ID_IPDescoberto']
            log.debug(f"PROCESS_IP ({ip_str}): IP já existe (ID: {ip_id_existente}). Atualizando NomeHostResolvido...")
            update_query = "UPDATE IPsDescobertos SET NomeHostResolvido = %s WHERE ID_IPDescoberto = %s"
            cursor.execute(update_query, (hostname_resolvido, ip_id_existente))
        else:
            log.info(f"PROCESS_IP ({ip_str}): NOVO IP. Inserindo em IPsDescobertos...")
            insert_query = "INSERT INTO IPsDescobertos (EnderecoIP, NomeHostResolvido, StatusResolucao) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (ip_str, hostname_resolvido, 'Novo'))
            id_ip_descoberto_novo = cursor.lastrowid 
            log.info(f"PROCESS_IP ({ip_str}): Inserido em IPsDescobertos com ID: {id_ip_descoberto_novo}")

        conn.commit() 
        log.debug(f"PROCESS_IP ({ip_str}): Commit realizado para IPsDescobertos.")

        if id_ip_descoberto_novo: 
            log.info(f"PROCESS_IP ({ip_str}): Tentando gerar alerta para novo ID_IPDescoberto: {id_ip_descoberto_novo}")
            
            tipo_alerta_info = get_tipo_alerta_details_by_name(conn, 'Novo IP Descoberto')
            log.debug(f"PROCESS_IP ({ip_str}): Detalhes do TipoAlerta 'Novo IP Descoberto': {tipo_alerta_info}")
            
            if tipo_alerta_info and tipo_alerta_info.get('ID_TipoAlerta'):
                id_tipo_alerta = tipo_alerta_info['ID_TipoAlerta']
                severidade_alerta = tipo_alerta_info.get('SeveridadePadrao', 'Media')
                
                descricao_alerta = f"Novo IP detectado na rede: {ip_str}"
                if hostname_resolvido:
                    descricao_alerta += f" (Hostname provável: {hostname_resolvido})"
                
                alert_query_params = (
                    id_tipo_alerta, 
                    id_ip_descoberto_novo, 
                    descricao_alerta, 
                    'Novo',
                    severidade_alerta
                )
                log.debug(f"PROCESS_IP ({ip_str}): Parâmetros para query de Alerta: {alert_query_params}")
                
                alert_query = """
                INSERT INTO Alerta (ID_TipoAlerta, ID_IPDescoberto_FK, DescricaoCustomizada, StatusAlerta, Severidade)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(alert_query, alert_query_params)
                conn.commit() 
                log.info(f"PROCESS_IP ({ip_str}): ALERTA GERADO para novo IP com severidade '{severidade_alerta}'")
            else:
                log.warning(f"PROCESS_IP ({ip_str}): Tipo de Alerta 'Novo IP Descoberto' não encontrado ou inválido. Alerta não gerado.")
        else:
            log.debug(f"PROCESS_IP ({ip_str}): Não é um IP novo, nenhum alerta de 'Novo IP Descoberto' será gerado.")

    except mysql.connector.Error as db_err:
        log.exception(f"PROCESS_IP ({ip_str}): Erro de DB.")
        if conn: conn.rollback()
    except Exception as e:
        log.exception(f"PROCESS_IP ({ip_str}): Erro inesperado.")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        log.info(f"PROCESS_IP: Finalizado processamento para IP: {ip_str}")

def scan_ip_range_segment(ip_list_segment):
    """Recebe uma lista de IPs e pinga cada um, processando os que respondem."""
    active_ips_in_segment = []
    for ip_obj in ip_list_segment:
        ip_str = str(ip_obj)
        if ping_ip(ip_str):
            active_ips_in_segment.append(ip_str)
            process_discovered_ip(ip_str) 
    return active_ips_in_segment

@app.route('/api/discovery/start-scan', methods=['POST'])
def start_discovery_scan():
    ip_ranges_str = os.getenv('DISCOVERY_IP_RANGES', '192.168.1.1-192.168.1.20') 
    all_ips_to_scan = []
    range_segments = ip_ranges_str.split(',')
    
    for segment in range_segments:
        segment = segment.strip()
        if '-' in segment: 
            try:
                start_ip_str, end_part_str = segment.split('-')
                start_ip = ipaddress.ip_address(start_ip_str)
                
                if '.' in end_part_str : 
                    end_ip = ipaddress.ip_address(end_part_str)
                    if start_ip.version != end_ip.version:
                        log.warning(f"Faixa inválida: {segment} - IPs de versões diferentes.")
                        continue
                    if start_ip > end_ip:
                        log.warning(f"Faixa inválida: {segment} - IP inicial maior que IP final.")
                        continue
                    current_ip = start_ip
                    while current_ip <= end_ip:
                        all_ips_to_scan.append(current_ip)
                        current_ip += 1
                else: 
                    end_octet = int(end_part_str)
                    if not (0 <= end_octet <= 255):
                         log.warning(f"Faixa inválida: {segment} - Octeto final inválido.")
                         continue
                    
                    start_ip_addr_bytes = bytearray(start_ip.packed)
                    if start_ip.version == 4 and len(start_ip_addr_bytes) == 4 :
                        if end_octet < start_ip_addr_bytes[3]:
                             log.warning(f"Faixa inválida: {segment} - Octeto final menor que octeto inicial.")
                             continue
                        end_ip_addr_bytes = start_ip_addr_bytes[:]
                        end_ip_addr_bytes[3] = end_octet
                        end_ip = ipaddress.ip_address(bytes(end_ip_addr_bytes))

                        current_ip = start_ip
                        while current_ip <= end_ip:
                            all_ips_to_scan.append(current_ip)
                            if current_ip == end_ip : break 
                            current_ip += 1
                    else:
                        log.warning(f"Formato de faixa X.X.X.X-Z só suportado para IPv4: {segment}")
                        continue
            except ValueError as e:
                log.warning(f"Erro ao processar faixa de IP '{segment}': {e}")
                continue
        elif '/' in segment: 
            try:
                network = ipaddress.ip_network(segment, strict=False)
                for ip_obj in network.hosts(): 
                    all_ips_to_scan.append(ip_obj)
            except ValueError as e:
                log.warning(f"Erro ao processar faixa CIDR '{segment}': {e}")
                continue
        else: 
            try:
                all_ips_to_scan.append(ipaddress.ip_address(segment))
            except ValueError as e:
                log.warning(f"Erro ao processar IP único '{segment}': {e}")
                continue
    
    if not all_ips_to_scan:
        return jsonify({"message": "Nenhuma faixa de IP válida para escanear configurada ou fornecida."}), 400

    log.info(f"Total de IPs a serem escaneados: {len(all_ips_to_scan)}")
    
    active_ips_found = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        chunk_size = 50 
        results_futures = []
        for i in range(0, len(all_ips_to_scan), chunk_size):
            ip_chunk = all_ips_to_scan[i:i + chunk_size]
            future = executor.submit(scan_ip_range_segment, ip_chunk)
            results_futures.append(future)
        
        for future in results_futures:
            active_ips_found.extend(future.result())
    
    return jsonify({
        "message": f"Varredura de descoberta concluída. {len(active_ips_found)} IPs ativos encontrados e processados.",
        "active_ips": active_ips_found 
    }), 200

@app.route('/api/discovery/discovered-ips', methods=['GET'])
def get_discovered_ips():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT ID_IPDescoberto, EnderecoIP, DataPrimeiraDeteccao, DataUltimaDeteccao, 
               StatusResolucao, NomeHostResolvido
        FROM IPsDescobertos ORDER BY DataUltimaDeteccao DESC
        """
        cursor.execute(query)
        discovered_ips = cursor.fetchall()
        return jsonify(discovered_ips), 200
    except Exception as e:
        log.exception("Erro em /api/discovery/discovered-ips")
        return jsonify({"message": "Erro ao buscar IPs descobertos"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    
@app.route('/')
def home():
    return "Bem-vindo ao Backend!"

@app.route('/api/discovery/discovered-ips/<int:id_ip_descoberto>', methods=['GET'])
def get_single_discovered_ip(id_ip_descoberto):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT ID_IPDescoberto, EnderecoIP, DataPrimeiraDeteccao, DataUltimaDeteccao, 
               StatusResolucao, NomeHostResolvido, MAC_Address_Estimado, OS_Estimado, 
               Portas_Abertas, DetalhesVarreduraExtra
        FROM IPsDescobertos WHERE ID_IPDescoberto = %s
        """
        cursor.execute(query, (id_ip_descoberto,))
        discovered_ip = cursor.fetchone()
        if discovered_ip:
            return jsonify(discovered_ip), 200
        else:
            return jsonify({"message": "IP Descoberto não encontrado"}), 404
    except Exception as e:
        log.exception(f"Erro ao buscar IP descoberto específico ID: {id_ip_descoberto}")
        return jsonify({"message": "Erro ao buscar IP descoberto específico"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/login', methods=['POST'])
def login():
    ip_origem = request.remote_addr
    data = request.get_json()
    username_or_email = data.get('username', 'N/A') if data else 'N/A'
    
    try:
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"message": "Dados de login ausentes ou inválidos"}), 400
        
        password_digitada = data['password']
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        
        cursor = conn.cursor(dictionary=True)
        query = "SELECT ID_Usuario, NomeUsuario, SenhaHash, Ativo FROM Usuario WHERE NomeUsuario = %s OR Email = %s"
        cursor.execute(query, (username_or_email, username_or_email))
        user = cursor.fetchone()
        
        if user and user['Ativo']:
            senha_hash_bd = user['SenhaHash'].encode('utf-8')
            password_digitada_bytes = password_digitada.encode('utf-8')
            if bcrypt.checkpw(password_digitada_bytes, senha_hash_bd):
                registrar_log_auditoria(
                    user['ID_Usuario'], 
                    user['NomeUsuario'], 
                    'LOGIN_SUCESSO', 
                    detalhes=f"Usuário '{user['NomeUsuario']}' logado.",
                    ip_origem=ip_origem
                )
                log.info(f"Login bem-sucedido para usuário '{user['NomeUsuario']}' do IP {ip_origem}.")
                # ### ALTERAÇÃO: GERAR O TOKEN JWT ###
                token_payload = {
                    'id_usuario': user['ID_Usuario'],
                    'nome_usuario': user['NomeUsuario'],
                    'exp': datetime.utcnow() + timedelta(hours=8) # Token expira em 8 horas
                }
                secret_key = os.getenv('SECRET_KEY')
                token = jwt.encode(token_payload, secret_key, algorithm='HS256')
                
                cursor.close()
                conn.close()
                return jsonify({
                                    "message": "Login bem-sucedido!",
                                    "token": token, 
                                    "user": {"id": user['ID_Usuario'], "username": user['NomeUsuario']}
                                }), 200
            else:
                registrar_log_auditoria(None, username_or_email, 'LOGIN_FALHA', detalhes=f"Senha incorreta para '{username_or_email}'.", ip_origem=ip_origem)
                log.warning(f"Tentativa de login falhou (senha incorreta) para usuário '{username_or_email}' do IP {ip_origem}.")
                cursor.close()
                conn.close()
                return jsonify({"message": "Usuário ou senha inválidos"}), 401
        else:
            registrar_log_auditoria(None, username_or_email, 'LOGIN_FALHA', detalhes=f"Usuário '{username_or_email}' não encontrado ou inativo.", ip_origem=ip_origem)
            log.warning(f"Tentativa de login falhou (usuário não existe/inativo) para '{username_or_email}' do IP {ip_origem}.")
            cursor.close()
            conn.close()
            return jsonify({"message": "Usuário ou senha inválidos"}), 401
            
    except Exception as e:
        log.exception(f"Erro inesperado no endpoint /login para o usuário '{username_or_email}'")
        return jsonify({"message": "Erro interno no servidor"}), 500
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
    
@app.route('/devices', methods=['GET'])
def get_devices():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        cursor = conn.cursor(dictionary=True)
        search_term = request.args.get('search', None)
        base_query = """
        SELECT d.ID_Dispositivo, d.NomeHost, d.StatusAtual, d.DataUltimaVarredura,
               ip.EnderecoIPValor as IPPrincipal, ifr.EnderecoMAC as MACPrincipal,
               so.Nome as SistemaOperacionalNome, fab.Nome as FabricanteNome,
               td.Nome as TipoDispositivoNome
        FROM Dispositivo d
        LEFT JOIN InterfaceRede ifr ON d.ID_Dispositivo = ifr.ID_Dispositivo 
        LEFT JOIN EnderecoIP ip ON ifr.ID_Interface = ip.ID_Interface AND ip.Principal = TRUE
        LEFT JOIN SistemaOperacional so ON d.ID_SistemaOperacional = so.ID_SistemaOperacional
        LEFT JOIN Fabricante fab ON d.ID_Fabricante = fab.ID_Fabricante
        LEFT JOIN TipoDispositivo td ON d.ID_TipoDispositivo = td.ID_TipoDispositivo
        """
        params = []
        where_clauses = []
        if search_term:
            like_search_term = f"%{search_term}%"
            where_clauses.append("""
            (d.NomeHost LIKE %s OR ip.EnderecoIPValor LIKE %s OR ifr.EnderecoMAC LIKE %s OR
             so.Nome LIKE %s OR fab.Nome LIKE %s OR td.Nome LIKE %s OR
             d.Descricao LIKE %s OR d.Modelo LIKE %s OR d.LocalizacaoFisica LIKE %s)
            """)
            params.extend([like_search_term] * 9)
        
        query = base_query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY d.NomeHost ASC"
        cursor.execute(query, tuple(params))
        devices = cursor.fetchall()
        return jsonify(devices), 200
    except Exception as e:
        log.exception("Erro em /devices (GET com busca)")
        return jsonify({"message": "Erro ao buscar dispositivos"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    
@app.route('/devices', methods=['POST'])
@token_required  # MUDANÇA 1: Proteger a rota com o decorator de token
def add_device(current_user):  # MUDANÇA 2: Receber o 'current_user' do decorator
    conn = None 
    cursor = None
    ip_origem = request.remote_addr
    data = request.get_json()
    
    # MUDANÇA 3: Obter dados do usuário DE FORMA SEGURA a partir do token
    try:
        id_usuario_logado = current_user['ID_Usuario']
        nome_usuario_logado = current_user['NomeUsuario']
    except KeyError:
        # Se o token não tiver as chaves esperadas, é um erro interno/de configuração
        return jsonify({"message": "Erro na configuração do token de autenticação."}), 500

    try:
        # Validação dos dados de entrada
        required_fields = ['NomeHost', 'StatusAtual']
        if not data or not all(field in data for field in required_fields):
            return jsonify({"message": "Dados incompletos (NomeHost e StatusAtual obrigatórios)"}), 400
        
        conn = get_db_connection()
        if not conn: 
            return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        
        cursor = conn.cursor()
        
        # A lógica de inserção no banco de dados permanece a mesma
        device_query = """
        INSERT INTO Dispositivo (NomeHost, Descricao, Modelo, ID_Fabricante, ID_SistemaOperacional, 
                                 ID_TipoDispositivo, StatusAtual, LocalizacaoFisica, Observacoes) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(device_query, (
            data.get('NomeHost'), data.get('Descricao'), data.get('Modelo'), data.get('ID_Fabricante'),
            data.get('ID_SistemaOperacional'), data.get('ID_TipoDispositivo'), data.get('StatusAtual'),
            data.get('LocalizacaoFisica'), data.get('Observacoes')
        ))
        id_dispositivo_novo = cursor.lastrowid
        
        if id_dispositivo_novo and data.get('EnderecoMAC') and data.get('EnderecoIP'):
            interface_query = """
            INSERT INTO InterfaceRede (ID_Dispositivo, EnderecoMAC, ID_Fabricante_MAC, Ativa)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(interface_query, (id_dispositivo_novo, data.get('EnderecoMAC'), data.get('ID_Fabricante_MAC'), True))
            id_interface_nova = cursor.lastrowid
            
            ip_query = """
            INSERT INTO EnderecoIP (ID_Interface, EnderecoIPValor, TipoIP, ID_Rede, Principal, TipoAtribuicao)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(ip_query, (
                id_interface_nova, data.get('EnderecoIP'), data.get('TipoIP', 'IPv4'),
                data.get('ID_Rede'), True, data.get('TipoAtribuicao', 'Descoberto')
            ))
            
        conn.commit()

        # MUDANÇA 4: A chamada de auditoria agora usa os dados seguros do token
        detalhes_log = {
            "dispositivo_id": id_dispositivo_novo,
            "nome_host": data.get('NomeHost'),
            "dados_enviados": data 
        }
        registrar_log_auditoria(
            id_usuario=id_usuario_logado,
            nome_usuario=nome_usuario_logado,
            acao='DISPOSITIVO_ADICIONADO',
            detalhes=json.dumps(detalhes_log),
            ip_origem=ip_origem
        )
        return jsonify({"message": "Dispositivo adicionado com sucesso!", "ID_Dispositivo": id_dispositivo_novo}), 201
        
    except mysql.connector.Error as db_err:
        if conn: conn.rollback()
        # O tratamento de erros de banco de dados continua o mesmo
        logging.error(f"Erro de banco de dados em POST /devices: {db_err}") # Usando logging
        if db_err.errno == 1062: # Erro de entrada duplicada
            # Lógica para tratar duplicidade
            if 'UQ_NomeHost' in db_err.msg or 'NomeHost' in db_err.msg:
                return jsonify({"message": f"Erro: NomeHost '{data.get('NomeHost')}' já existe."}), 409
            elif 'UQ_EnderecoMAC' in db_err.msg or 'EnderecoMAC' in db_err.msg:
                return jsonify({"message": f"Erro: Endereço MAC '{data.get('EnderecoMAC')}' já existe."}), 409
            else:
                return jsonify({"message": f"Erro de duplicidade: {db_err.msg}"}), 409
        return jsonify({"message": f"Erro de banco de dados: {db_err.msg}"}), 500
    
    except Exception as e:
        if conn: conn.rollback()
        logging.exception("Erro inesperado em POST /devices") # Usando logging
        return jsonify({"message": "Erro interno ao adicionar dispositivo"}), 500
    
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/devices/<int:device_id>', methods=['GET'])
def get_device_by_id(device_id): 
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        
        cursor = conn.cursor(dictionary=True)
        main_device_query = """
        SELECT d.ID_Dispositivo, d.NomeHost, d.Descricao, d.Modelo, 
               d.ID_Fabricante, fab.Nome as FabricanteNome,
               d.ID_SistemaOperacional, so.Nome as SistemaOperacionalNome, so.Versao as SistemaOperacionalVersao, so.Familia as SistemaOperacionalFamilia,
               d.ID_TipoDispositivo, td.Nome as TipoDispositivoNome, 
               d.DataDescoberta, d.DataUltimaModificacao, d.DataUltimaVarredura,
               d.StatusAtual, d.LocalizacaoFisica, d.Observacoes,
               u.NomeUsuario as GerenciadoPorNomeUsuario
        FROM Dispositivo d
        LEFT JOIN Fabricante fab ON d.ID_Fabricante = fab.ID_Fabricante
        LEFT JOIN SistemaOperacional so ON d.ID_SistemaOperacional = so.ID_SistemaOperacional
        LEFT JOIN TipoDispositivo td ON d.ID_TipoDispositivo = td.ID_TipoDispositivo
        LEFT JOIN Usuario u ON d.GerenciadoPor = u.ID_Usuario
        WHERE d.ID_Dispositivo = %s
        """
        cursor.execute(main_device_query, (device_id,))
        device = cursor.fetchone()
        
        if device:
            interfaces_query = """
            SELECT ifr.ID_Interface, ifr.NomeInterface, ifr.EnderecoMAC, fab_mac.Nome as FabricanteMAC,
                   ip.EnderecoIPValor, ip.TipoIP, ip.TipoAtribuicao, r.NomeRede, ip.Principal as IPPrincipal
            FROM InterfaceRede ifr
            LEFT JOIN Fabricante fab_mac ON ifr.ID_Fabricante_MAC = fab_mac.ID_Fabricante
            LEFT JOIN EnderecoIP ip ON ifr.ID_Interface = ip.ID_Interface
            LEFT JOIN Rede r ON ip.ID_Rede = r.ID_Rede
            WHERE ifr.ID_Dispositivo = %s
            ORDER BY ifr.ID_Interface ASC, ip.Principal DESC
            """
            cursor.execute(interfaces_query, (device_id,))
            device['interfaces'] = cursor.fetchall()
            log.debug(f"BACKEND /devices/<id> - Enviando dispositivo: {device}")
            return jsonify(device), 200
        else:
            return jsonify({"message": "Dispositivo não encontrado"}), 404
            
    except Exception as e:
        log.exception(f"Erro em /devices/<id> (GET) para device_id: {device_id}")
        return jsonify({"message": "Erro ao buscar detalhes do dispositivo"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/devices/<int:device_id>', methods=['PUT'])
@token_required
def update_device(current_user, device_id):
    conn = None
    cursor = None
    data = request.get_json()
    ip_origem = request.remote_addr
    
    try:
        # ### AUDITORIA: Obter os dados do usuário ###
        id_usuario_logado = current_user['ID_Usuario']
        nome_usuario_logado = current_user['NomeUsuario']
        
        if not data: return jsonify({"message": "Nenhum dado fornecido para atualização"}), 400
        
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Dispositivo WHERE ID_Dispositivo = %s", (device_id,))
        device = cursor.fetchone()
        if not device:
            cursor.close()
            conn.close()
            return jsonify({"message": "Dispositivo não encontrado para atualização"}), 404
            
        allowed_fields = [
            'NomeHost', 'Descricao', 'Modelo', 'ID_Fabricante', 'ID_SistemaOperacional', 
            'ID_TipoDispositivo', 'StatusAtual', 'LocalizacaoFisica', 'Observacoes', 
            'GerenciadoPor', 'DataUltimaVarredura'
        ]
        update_fields = []
        update_values = []
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"`{field}` = %s")
                update_values.append(data[field])
                
        if not update_fields:
            cursor.close()
            conn.close()
            return jsonify({"message": "Nenhum campo válido fornecido para atualização"}), 400
            
        update_values.append(device_id)
        update_query = f"UPDATE Dispositivo SET {', '.join(update_fields)} WHERE ID_Dispositivo = %s"
        
        cursor.close() 
        cursor = conn.cursor()
        cursor.execute(update_query, tuple(update_values))
        conn.commit()
        
        # ### AUDITORIA: Registrar a edição ###
        detalhes_log = {
            "dispositivo_id": device_id,
            "dados_atualizados": {k: v for k, v in data.items() if k not in ['token']} # Não logar o token
        }
        registrar_log_auditoria(
            id_usuario=id_usuario_logado,
            nome_usuario=nome_usuario_logado,
            acao='DISPOSITIVO_EDITADO',
            detalhes=json.dumps(detalhes_log),
            ip_origem=ip_origem
        )
        
        cursor.close()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Dispositivo WHERE ID_Dispositivo = %s", (device_id,))
        updated_device = cursor.fetchone()
        
        return jsonify({"message": "Dispositivo atualizado com sucesso!", "device": updated_device}), 200
        
    except mysql.connector.Error as db_err:
        if conn: conn.rollback()
        log.error(f"Erro de banco de dados em PUT /devices/<id>: {db_err}")
        if db_err.errno == 1062:
            return jsonify({"message": f"Erro: Conflito de dados. O NomeHost '{data.get('NomeHost')}' já pode existir."}), 409
        return jsonify({"message": f"Erro de banco de dados: {db_err.msg}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        log.exception(f"Erro ao atualizar dispositivo ID: {device_id}")
        return jsonify({"message": "Erro ao atualizar dispositivo"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/devices/<int:device_id>', methods=['DELETE'])
@token_required
def delete_device(current_user, device_id):
    """Remove um dispositivo do banco de dados."""
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Erro interno no servidor"}), 500

    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT NomeHost FROM Dispositivo WHERE ID_Dispositivo = %s", (device_id,))
            device_to_delete = cursor.fetchone()

            if not device_to_delete:
                return jsonify({"message": "Dispositivo não encontrado"}), 404
            
            cursor.execute("DELETE FROM Dispositivo WHERE ID_Dispositivo = %s", (device_id,))

            if cursor.rowcount == 0:
                conn.rollback()
                return jsonify({"message": "Dispositivo não pôde ser removido (talvez já tenha sido deletado)."}), 404
            
            # Auditoria
            detalhes_log = {"dispositivo_id": device_id, "nome_host_removido": device_to_delete['NomeHost']}
            registrar_log_auditoria(
                id_usuario=current_user['ID_Usuario'], nome_usuario=current_user['NomeUsuario'],
                acao='DISPOSITIVO_REMOVIDO', detalhes=json.dumps(detalhes_log), ip_origem=request.remote_addr
            )
            conn.commit()
            return jsonify({"message": "Dispositivo removido com sucesso!"}), 200
    
    except Exception as e:
        conn.rollback()
        if e.errno == 1451:
             return jsonify({"message": "Erro: Este dispositivo não pode ser removido pois está em uso em outros registros."}), 400
        else:
             logging.error(f"Erro de integridade do DB: {e}")
             return jsonify({"message": f"Erro de banco de dados: {e}"}), 500
    finally:
        if conn.is_connected(): conn.close()
    
@app.route('/fabricantes', methods=['GET'])
def get_fabricantes():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro de conexão DB"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ID_Fabricante, Nome FROM Fabricante ORDER BY Nome ASC")
        fabricantes = cursor.fetchall()
        return jsonify(fabricantes), 200
    except Exception as e:
        log.exception("Erro em /fabricantes")
        return jsonify({"message": "Erro ao buscar fabricantes"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/sistemasoperacionais', methods=['GET'])
def get_sistemas_operacionais():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro de conexão DB"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ID_SistemaOperacional, Nome, Versao FROM SistemaOperacional ORDER BY Nome ASC, Versao ASC")
        sistemas = cursor.fetchall()
        for so in sistemas:
            so['NomeCompleto'] = f"{so['Nome']} {so['Versao']}" if so['Versao'] else so['Nome']
        return jsonify(sistemas), 200
    except Exception as e:
        log.exception("Erro em /sistemasoperacionais")
        return jsonify({"message": "Erro ao buscar sistemas operacionais"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/tiposdispositivo', methods=['GET'])
def get_tipos_dispositivo():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro de conexão DB"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ID_TipoDispositivo, Nome FROM TipoDispositivo ORDER BY Nome ASC")
        tipos = cursor.fetchall()
        return jsonify(tipos), 200
    except Exception as e:
        log.exception("Erro em /tiposdispositivo")
        return jsonify({"message": "Erro ao buscar tipos de dispositivo"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    
@app.route('/api/discovery/discovered-ips/<int:id_ip_descoberto>/status', methods=['PUT'])
def update_discovered_ip_status(id_ip_descoberto):
    conn = None
    cursor = None
    try:
        data = request.get_json()
        novo_status = data.get('status')
        if not novo_status: return jsonify({"message": "Novo status não fornecido"}), 400
        
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        
        cursor = conn.cursor()
        query = "UPDATE IPsDescobertos SET StatusResolucao = %s WHERE ID_IPDescoberto = %s"
        cursor.execute(query, (novo_status, id_ip_descoberto))
        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"message": "IP Descoberto não encontrado ou status já era o mesmo"}), 404
            
        cursor.close()
        conn.close()
        return jsonify({"message": f"Status do IP Descoberto ID {id_ip_descoberto} atualizado para '{novo_status}'"}), 200
    except Exception as e:
        log.exception(f"Erro em /api/discovery/discovered-ips/<id>/status para id: {id_ip_descoberto}")
        return jsonify({"message": "Erro ao atualizar status do IP descoberto"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    
@app.route('/api/discovery/scan-ip-details', methods=['POST'])
def scan_ip_details():
    data = request.get_json()
    ip_address = data.get('ip_address')
    id_ip_descoberto = data.get('id_ip_descoberto')

    if not ip_address or not id_ip_descoberto:
        return jsonify({"message": "Endereço IP ou ID do IP Descoberto não fornecido"}), 400

    log.info(f"NMAP_SCAN: Iniciando varredura detalhada para o IP: {ip_address} (ID DB: {id_ip_descoberto})")
    nm = None
    try:
        nm = nmap.PortScanner()
        nmap_args = '-sV -T4 -Pn' 
        if os.getenv('NMAP_USE_OS_DETECTION', 'false').lower() == 'true':
            nmap_args += ' -O --version-intensity 5'

        log.info(f"NMAP_SCAN: Executando Nmap com argumentos: '{nmap_args}' no IP: {ip_address}")
        nm.scan(ip_address, arguments=nmap_args)

        hostname_nmap = ip_address 
        mac_address = None
        os_details_str = None 
        open_ports_list = []
        raw_nmap_output = "Nenhum host encontrado por Nmap ou IP não respondeu à varredura detalhada."
        
        scanned_hosts = nm.all_hosts() 
        log.debug(f"NMAP_SCAN: Hosts escaneados por Nmap: {scanned_hosts}")

        if scanned_hosts: 
            host_key = scanned_hosts[0] 
            
            if host_key in nm: 
                host_data = nm[host_key]
                raw_nmap_output = nm.csv() 
                log.debug(f"NMAP_SCAN: Resultado Nmap para {host_key}: {host_data.state()}")

                if host_data.hostnames():
                    for h_entry in host_data.hostnames():
                        if h_entry.get('name') and h_entry.get('type') in ['PTR', 'user']:
                            hostname_nmap = h_entry['name']
                            break
                    if hostname_nmap == ip_address and host_data.hostnames() and host_data.hostnames()[0].get('name'):
                        hostname_nmap = host_data.hostnames()[0]['name']
                
                if 'mac' in host_data.get('addresses', {}): 
                    mac_address = host_data['addresses']['mac'].upper()
                
                if 'osmatch' in host_data and host_data['osmatch']:
                    best_os_match = sorted(host_data['osmatch'], key=lambda x: int(x['accuracy']), reverse=True)[0]
                    os_details_str = best_os_match.get('name', 'N/D')
                
                for proto in host_data.all_protocols():
                    if proto in ['tcp', 'udp']:
                        lport = sorted(list(host_data[proto].keys()), key=int)
                        for port in lport:
                            port_info = host_data[proto][port]
                            if port_info['state'] == 'open':
                                service_name = port_info.get('name', '')
                                product = port_info.get('product', '')
                                version = port_info.get('version', '')
                                service_details = f"{service_name} ({product} {version})".replace("()","").replace("( )","").strip()
                                open_ports_list.append(f"{port}/{proto} - {service_details if service_details else 'Serviço Desconhecido'}")
            else:
                log.warning(f"NMAP_SCAN: Chave do host '{host_key}' (de nm.all_hosts()) não encontrada nos resultados do Nmap.")
        else:
            log.warning(f"NMAP_SCAN: Nenhum host retornado por nm.all_hosts() para o IP {ip_address}.")
        
        conn_db = get_db_connection()
        if not conn_db: 
            log.critical(f"NMAP_SCAN: Erro de conexão DB ao salvar detalhes Nmap para {ip_address}")
            return jsonify({"message": "Erro de conexão DB ao salvar detalhes Nmap"}), 500
        cursor_db = conn_db.cursor()
        
        update_query = """
        UPDATE IPsDescobertos 
        SET NomeHostResolvido = COALESCE(%s, NomeHostResolvido), 
            MAC_Address_Estimado = %s, 
            OS_Estimado = %s, 
            Portas_Abertas = %s,
            DetalhesVarreduraExtra = %s, 
            StatusResolucao = %s,
            DataUltimaDeteccao = CURRENT_TIMESTAMP 
        WHERE ID_IPDescoberto = %s
        """
        ports_str = "\n".join(open_ports_list) if open_ports_list else None
        final_hostname_to_save = hostname_nmap if hostname_nmap and hostname_nmap != ip_address else None

        cursor_db.execute(update_query, (
            final_hostname_to_save,
            mac_address, 
            os_details_str if os_details_str and os_details_str != 'N/D' else None,
            ports_str, 
            raw_nmap_output,
            'Analisado', 
            id_ip_descoberto
        ))
        conn_db.commit()
        cursor_db.close()
        conn_db.close()

        log.info(f"NMAP_SCAN: Varredura detalhada para {ip_address} concluída e salva.")
        return jsonify({
            "message": f"Varredura detalhada para {ip_address} concluída.",
            "data": { 
                "id_ip_descoberto": id_ip_descoberto, "ip_address": ip_address,
                "hostname_nmap": hostname_nmap, "mac_address_estimado": mac_address,
                "os_estimado": os_details_str, "portas_abertas": open_ports_list,
                "status_resolucao": "Analisado"
            }
        }), 200

    except nmap.PortScannerError as e_nmap:
        log.exception(f"Erro do Nmap ao escanear {ip_address}. Verifique a instalação e permissões.")
        return jsonify({"message": f"Erro ao executar Nmap: {str(e_nmap)}. Verifique se Nmap está instalado e no PATH, e se o script tem permissões (para -O)."}), 500
    except Exception as e:
        log.exception(f"Erro ao escanear detalhes do IP {ip_address}")
        return jsonify({"message": "Erro interno ao escanear detalhes do IP."}), 500
    
@app.route('/api/reports/os-summary', methods=['GET'])
def report_os_summary():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro de conexão com o banco de dados"}), 500

        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                COALESCE(so.Nome, 'Não Especificado') as SistemaOperacionalNome, 
                COALESCE(so.Familia, 'Desconhecida') as SistemaOperacionalFamilia,
                COUNT(d.ID_Dispositivo) as TotalDispositivos
            FROM Dispositivo d
            LEFT JOIN SistemaOperacional so ON d.ID_SistemaOperacional = so.ID_SistemaOperacional
            GROUP BY so.Nome, so.Familia
            ORDER BY TotalDispositivos DESC, SistemaOperacionalNome ASC;
        """
        cursor.execute(query)
        os_summary = cursor.fetchall()
        return jsonify(os_summary), 200

    except Exception as e:
        log.exception("Erro ao gerar relatório de sumário por SO")
        return jsonify({"message": "Erro ao gerar relatório de sumário por SO"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


def get_device_list_by_status(status_filter):
    """Função auxiliar para buscar dispositivos por um status específico."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            log.error(f"DB_HELPER: Erro de conexão ao buscar dispositivos com status {status_filter}")
            return None, "Erro de conexão com o banco de dados"
        
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            d.ID_Dispositivo, d.NomeHost, d.StatusAtual, d.DataUltimaVarredura,
            ip.EnderecoIPValor as IPPrincipal, 
            ifr.EnderecoMAC as MACPrincipal,
            so.Nome as SistemaOperacionalNome,
            fab.Nome as FabricanteNome,
            td.Nome as TipoDispositivoNome
        FROM Dispositivo d
        LEFT JOIN InterfaceRede ifr ON d.ID_Dispositivo = ifr.ID_Dispositivo 
        LEFT JOIN EnderecoIP ip ON ifr.ID_Interface = ip.ID_Interface AND ip.Principal = TRUE
        LEFT JOIN SistemaOperacional so ON d.ID_SistemaOperacional = so.ID_SistemaOperacional
        LEFT JOIN Fabricante fab ON d.ID_Fabricante = fab.ID_Fabricante
        LEFT JOIN TipoDispositivo td ON d.ID_TipoDispositivo = td.ID_TipoDispositivo
        WHERE d.StatusAtual = %s
        ORDER BY d.NomeHost ASC
        """
        cursor.execute(query, (status_filter,))
        devices = cursor.fetchall()
        return devices, None
    except Exception as e:
        log.exception(f"Erro ao buscar dispositivos por status '{status_filter}'")
        return None, f"Erro ao gerar relatório de dispositivos {status_filter.lower()}"
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/api/reports/devices-online', methods=['GET'])
def report_devices_online():
    devices, error_message = get_device_list_by_status('Online')
    if error_message:
        return jsonify({"message": error_message}), 500
    return jsonify(devices), 200

@app.route('/api/reports/devices-offline', methods=['GET'])
def report_devices_offline():
    devices, error_message = get_device_list_by_status('Offline')
    if error_message:
        return jsonify({"message": error_message}), 500
    return jsonify(devices), 200

@app.route('/api/dashboard/summary', methods=['GET'])
def dashboard_summary():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro de conexão DB"}), 500
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as total_devices FROM Dispositivo")
        total_devices = cursor.fetchone()['total_devices']

        cursor.execute("SELECT COUNT(*) as online_devices FROM Dispositivo WHERE StatusAtual = 'Online'")
        online_devices = cursor.fetchone()['online_devices']

        cursor.execute("SELECT COUNT(*) as offline_devices FROM Dispositivo WHERE StatusAtual = 'Offline'")
        offline_devices = cursor.fetchone()['offline_devices']

        cursor.execute("SELECT COUNT(*) as new_alerts FROM Alerta WHERE StatusAlerta = 'Novo'")
        new_alerts = cursor.fetchone()['new_alerts']

        summary = {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": offline_devices,
            "new_alerts": new_alerts
        }
        return jsonify(summary), 200
    except Exception as e:
        log.exception("Erro ao buscar sumário do dashboard")
        return jsonify({"message": "Erro ao buscar sumário do dashboard"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/api/dashboard/os-distribution', methods=['GET'])
def dashboard_os_distribution():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro de conexão DB"}), 500
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                COALESCE(so.Nome, 'Não Especificado') as os_name,
                COUNT(d.ID_Dispositivo) as device_count
            FROM Dispositivo d
            LEFT JOIN SistemaOperacional so ON d.ID_SistemaOperacional = so.ID_SistemaOperacional
            GROUP BY so.Nome
            ORDER BY device_count DESC;
        """
        cursor.execute(query)
        os_distribution = cursor.fetchall()
        return jsonify(os_distribution), 200
    except Exception as e:
        log.exception("Erro ao buscar distribuição de SO para dashboard")
        return jsonify({"message": "Erro ao buscar distribuição de SO"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

def get_current_scan_settings():
    """Busca as configurações de varredura atuais do banco de dados."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            log.error("SCHEDULER_SETTINGS: Erro de conexão DB ao buscar configurações.")
            return None 
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT FaixasIP, FrequenciaMinutos, VarreduraAtivada FROM ConfiguracaoVarredura WHERE ID_ConfigVarredura = 1")
        config = cursor.fetchone()
        log.debug(f"SCHEDULER_SETTINGS: Configurações lidas do DB: {config}")
        return config
    except Exception as e:
        log.exception("SCHEDULER_SETTINGS: Erro ao buscar configurações de varredura")
        return None
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


def _execute_actual_network_scan(ip_ranges_list_str, scan_source="Desconhecida"):
    """
    Função principal que realiza a varredura de descoberta de rede.
    """
    log.info(f"SCAN_CORE ({scan_source}): Iniciando varredura para faixas: {ip_ranges_list_str}")
    if not ip_ranges_list_str:
        log.warning(f"SCAN_CORE ({scan_source}): Nenhuma faixa de IP fornecida para a varredura.")
        return []

    all_ips_to_scan_obj_list = []
    range_segments = ip_ranges_list_str.split(',')
    
    for segment in range_segments:
        segment = segment.strip()
        if not segment: continue

        if '-' in segment: 
            try:
                start_ip_str, end_part_str = segment.split('-', 1)
                start_ip = ipaddress.ip_address(start_ip_str.strip())
                end_part_str = end_part_str.strip()
                
                if '.' in end_part_str : 
                    end_ip = ipaddress.ip_address(end_part_str)
                    if start_ip.version != end_ip.version:
                        log.warning(f"SCAN_CORE ({scan_source}): Faixa inválida: {segment} - IPs de versões diferentes.")
                        continue
                    if start_ip > end_ip:
                        log.warning(f"SCAN_CORE ({scan_source}): Faixa inválida: {segment} - IP inicial maior que IP final.")
                        continue
                    current_ip = start_ip
                    while current_ip <= end_ip:
                        all_ips_to_scan_obj_list.append(current_ip)
                        current_ip += 1
                else: 
                    end_octet = int(end_part_str)
                    if not (0 <= end_octet <= 255):
                        log.warning(f"SCAN_CORE ({scan_source}): Faixa inválida: {segment} - Octeto final inválido.")
                        continue
                    
                    start_ip_addr_bytes = bytearray(start_ip.packed)
                    if start_ip.version == 4 and len(start_ip_addr_bytes) == 4 :
                        if start_ip_addr_bytes[3] > end_octet :
                            log.warning(f"SCAN_CORE ({scan_source}): Faixa inválida: {segment} - Octeto final menor que octeto inicial.")
                            continue
                        
                        temp_ip_parts = list(start_ip.packed)
                        temp_ip_parts[3] = end_octet
                        end_ip = ipaddress.ip_address(bytes(temp_ip_parts))

                        current_ip = start_ip
                        while current_ip <= end_ip:
                            all_ips_to_scan_obj_list.append(current_ip)
                            if current_ip == end_ip : break 
                            current_ip += 1
                    else:
                        log.warning(f"SCAN_CORE ({scan_source}): Formato de faixa X.X.X.X-Z só suportado para IPv4: {segment}")
                        continue
            except ValueError as e:
                log.warning(f"SCAN_CORE ({scan_source}): Erro ao processar faixa de IP '{segment}': {e}")
                continue
        elif '/' in segment: 
            try:
                network = ipaddress.ip_network(segment, strict=False)
                for ip_obj in network.hosts(): 
                    all_ips_to_scan_obj_list.append(ip_obj)
            except ValueError as e:
                log.warning(f"SCAN_CORE ({scan_source}): Erro ao processar faixa CIDR '{segment}': {e}")
                continue
        else: # IP único
            try:
                all_ips_to_scan_obj_list.append(ipaddress.ip_address(segment))
            except ValueError as e:
                log.warning(f"SCAN_CORE ({scan_source}): Erro ao processar IP único '{segment}': {e}")
                continue
    
    if not all_ips_to_scan_obj_list:
        log.warning(f"SCAN_CORE ({scan_source}): Nenhuma faixa de IP válida resultou em IPs para escanear.")
        return []

    unique_ips_to_scan_str = sorted(list(set(str(ip) for ip in all_ips_to_scan_obj_list)), key=ipaddress.ip_address)
    final_ips_to_scan_list = [ipaddress.ip_address(ip_str) for ip_str in unique_ips_to_scan_str]

    log.info(f"SCAN_CORE ({scan_source}): Total de IPs únicos a serem escaneados: {len(final_ips_to_scan_list)}")
    
    active_ips_found = []
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 5 or 20) as executor: 
        chunk_size = 50 
        futures = [] 
        for i in range(0, len(final_ips_to_scan_list), chunk_size):
            ip_chunk = final_ips_to_scan_list[i:i + chunk_size]
            future = executor.submit(scan_ip_range_segment, ip_chunk) 
            futures.append(future)
        
        for future in futures:
            try:
                active_ips_found.extend(future.result()) 
            except Exception as e_future:
                log.exception(f"SCAN_CORE ({scan_source}): Erro em uma thread de varredura")

    log.info(f"SCAN_CORE ({scan_source}): Varredura de descoberta concluída. {len(active_ips_found)} IPs ativos encontrados e processados.")
    return active_ips_found

def scheduled_scan_job():
    """A tarefa que o scheduler irá executar."""
    log.info(f"SCHEDULER_JOB: Verificando se a varredura automática deve ser executada...")
    with app.app_context():
        settings = get_current_scan_settings()

        if settings and settings.get('VarreduraAtivada'):
            faixas_ip = settings.get('FaixasIP')
            if faixas_ip:
                log.info(f"SCHEDULER_JOB: Varredura automática ATIVADA. Iniciando varredura para faixas: {faixas_ip}")
                try:
                    _execute_actual_network_scan(faixas_ip, scan_source="Agendada") 
                except Exception as e:
                    log.exception("SCHEDULER_JOB: Erro durante a execução da varredura automática agendada.")
            else:
                log.warning("SCHEDULER_JOB: Varredura automática ATIVADA, mas nenhuma faixa de IP configurada.")
        else:
            log.info("SCHEDULER_JOB: Varredura automática DESATIVADA ou configurações não encontradas.")

def update_scheduled_scan():
    """Remove o job de varredura existente e agenda um novo com base nas configurações atuais do DB."""
    log.info("SCHEDULER_UPDATE: Tentando atualizar tarefa de varredura agendada...")
    
    with app.app_context():
        settings = get_current_scan_settings()

    try:
        if scheduler.get_job(SCAN_JOB_ID):
            scheduler.remove_job(SCAN_JOB_ID)
            log.info(f"SCHEDULER_UPDATE: Job de varredura anterior ('{SCAN_JOB_ID}') removido.")
    except Exception as e:
        log.warning(f"SCHEDULER_UPDATE: Aviso ao tentar remover job anterior (pode não existir ou scheduler não iniciado): {e}")

    if settings and settings.get('VarreduraAtivada') and settings.get('FrequenciaMinutos') is not None:
        try:
            frequencia = int(settings.get('FrequenciaMinutos'))
            if frequencia > 0:
                log.info(f"SCHEDULER_UPDATE: Agendando nova varredura para cada {frequencia} minutos.")
                scheduler.add_job(
                    func=scheduled_scan_job, 
                    trigger='interval', 
                    minutes=frequencia, 
                    id=SCAN_JOB_ID,
                    replace_existing=True,
                    next_run_time=datetime.now() + timedelta(seconds=20) 
                )
            else: 
                log.info(f"SCHEDULER_UPDATE: Frequência é {frequencia}. Nenhuma varredura por intervalo será agendada (considerado manual).")
        except ValueError:
            log.error(f"SCHEDULER_UPDATE: Valor de FrequenciaMinutos ('{settings.get('FrequenciaMinutos')}') não é um inteiro válido.")
        except Exception as e:
            log.exception("SCHEDULER_UPDATE: Erro ao adicionar novo job ao agendador")
    else:
        log.info("SCHEDULER_UPDATE: Varredura automática DESATIVADA ou frequência inválida/não definida. Nenhum job de intervalo agendado.")

@app.route('/api/dashboard/status-distribution', methods=['GET'])
def dashboard_status_distribution():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro de conexão DB"}), 500
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                StatusAtual as status_name,
                COUNT(ID_Dispositivo) as device_count
            FROM Dispositivo
            GROUP BY StatusAtual
            ORDER BY device_count DESC;
        """
        cursor.execute(query)
        status_distribution = cursor.fetchall()
        return jsonify(status_distribution), 200
    except Exception as e:
        log.exception("Erro ao buscar distribuição de status para dashboard")
        return jsonify({"message": "Erro ao buscar distribuição de status"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/api/dashboard/recent-alerts', methods=['GET'])
def dashboard_recent_alerts():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro de conexão DB"}), 500
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                a.ID_Alerta,
                a.DescricaoCustomizada,
                a.DataHoraCriacao,
                a.Severidade,
                ta.Nome AS TipoAlertaNome,
                d.NomeHost AS DispositivoNomeHost,
                ipd.EnderecoIP AS IPDescobertoEndereco
            FROM Alerta a
            JOIN TipoAlerta ta ON a.ID_TipoAlerta = ta.ID_TipoAlerta
            LEFT JOIN Dispositivo d ON a.ID_Dispositivo = d.ID_Dispositivo
            LEFT JOIN IPsDescobertos ipd ON a.ID_IPDescoberto_FK = ipd.ID_IPDescoberto
            WHERE a.StatusAlerta = 'Novo'
            ORDER BY a.DataHoraCriacao DESC
            LIMIT 5 
        """
        cursor.execute(query)
        recent_alerts = cursor.fetchall()
        return jsonify(recent_alerts), 200
    except Exception as e:
        log.exception("Erro ao buscar alertas recentes para dashboard")
        return jsonify({"message": "Erro ao buscar alertas recentes"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/api/settings/scan-config', methods=['GET'])
def get_scan_config_route():
    config = get_current_scan_settings()
    if not config:
        default_config = {
            "ID_ConfigVarredura": 1, "FaixasIP": os.getenv('DISCOVERY_IP_RANGES', '192.168.1.0/24'), 
            "FrequenciaMinutos": 60, "AgendamentoCron": None, 
            "VarreduraAtivada": False
        }
        return jsonify(default_config), 200 
    return jsonify(config), 200

@app.route('/api/settings/scan-config', methods=['PUT'])
def update_scan_config_route():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        if not data: return jsonify({"message": "Dados não fornecidos"}), 400
        
        faixas_ip = data.get('FaixasIP')
        frequencia_minutos_str = data.get('FrequenciaMinutos')
        varredura_ativada = data.get('VarreduraAtivada', False)

        frequencia_minutos = 0
        if frequencia_minutos_str is not None:
            try: 
                frequencia_minutos = int(frequencia_minutos_str)
                if frequencia_minutos < 0:
                    return jsonify({"message": "Frequência em minutos não pode ser negativa."}), 400
            except ValueError:
                return jsonify({"message": "Frequência em minutos deve ser um número."}), 400
        
        if not isinstance(varredura_ativada, bool):
            return jsonify({"message": "VarreduraAtivada deve ser true ou false."}), 400

        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro de conexão DB"}), 500
        cursor = conn.cursor()
        query = """
        UPDATE ConfiguracaoVarredura SET FaixasIP = %s, FrequenciaMinutos = %s, VarreduraAtivada = %s
        WHERE ID_ConfigVarredura = 1 
        """
        cursor.execute(query, (faixas_ip, frequencia_minutos, varredura_ativada))
        conn.commit()
              
        if scheduler.running:
            log.info("API_SETTINGS_SCAN: Configs salvas. Solicitando atualização do agendador...")
            update_scheduled_scan() 
        else:
            log.warning("API_SETTINGS_SCAN: Configs salvas, mas o agendador não está rodando.")
            
        return jsonify({"message": "Configurações de varredura salvas com sucesso!"}), 200
    except Exception as e:
        if conn: conn.rollback()
        log.exception("Erro ao salvar configuração de varredura")
        return jsonify({"message": "Erro ao salvar configuração de varredura"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

try:
    if not scheduler.running:
        log.info("MAIN_APP: Agendador não está rodando. Iniciando...")
        with app.app_context():
            update_scheduled_scan() 
        scheduler.start()
        log.info("MAIN_APP: Agendador iniciado com sucesso.")
        atexit.register(lambda: scheduler.shutdown(wait=False))
    else:
        log.warning("MAIN_APP: Agendador já estava rodando.")
except Exception as e:
    log.critical("MAIN_APP: Erro fatal durante a inicialização do agendador.", exc_info=True)

if __name__ == '__main__':
    is_debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    log.info(f"Iniciando servidor Flask em modo {'DEBUG' if is_debug_mode else 'PRODUÇÃO'}.")
    app.run(debug=is_debug_mode)
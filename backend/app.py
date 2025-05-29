import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import mysql.connector
import bcrypt
import subprocess # Para executar o comando ping
import platform   # Para identificar o sistema operacional para o comando ping
import ipaddress  # Para trabalhar com faixas de IP
import socket
import nmap # Para varredura detalhada
from concurrent.futures import ThreadPoolExecutor # Para executar pings em paralelo (opcional, mas bom para performance)
from datetime import datetime, timedelta # Adicionado para PasswordResetTokens (se não estava antes)

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)
CORS(app) #Habilitando o CORS

# Configuração do Banco de Dados
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        print(f'Conexão com o MYSQL bem sucedida!!!!!!!') # Mantido como no seu original
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao MySQL: {err}")
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
        print(f"Ping para {ip_str}: RC={process.returncode}")
        if stdout_decoded:
            print(f"  STDOUT: {stdout_decoded}")
        if stderr_decoded:
            print(f"  STDERR: {stderr_decoded}")

        return process.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"Timeout GERAL ao executar comando ping para {ip_str}")
        # 'process' pode não estar definido se Popen falhar antes de atribuir
        # Adicionar uma checagem se 'process' existe no escopo local.
        # No entanto, se Popen lança TimeoutExpired, process já foi atribuído.
        if 'process' in locals() and process: process.kill() 
        return False
    except Exception as e:
        print(f"Exceção ao pingar {ip_str}: {e}")
        return False

def process_discovered_ip(ip_str):
    """Processa um IP que respondeu ao ping: tenta resolver o hostname e insere/atualiza na tabela IPsDescobertos."""
    conn = None
    cursor = None
    hostname_resolvido = None

    try:
        print(f"Tentando resolver hostname para IP: {ip_str}...")
        try:
            hostname_resolvido, _, _ = socket.gethostbyaddr(ip_str)
            print(f"  Hostname resolvido para {ip_str}: {hostname_resolvido}")
        except socket.herror: 
            print(f"  Não foi possível resolver o hostname para {ip_str} via rDNS (socket.herror).")
            hostname_resolvido = None
        except Exception as e_dns: 
            print(f"  Erro genérico ao tentar resolver DNS para {ip_str}: {e_dns}")
            hostname_resolvido = None
        
        conn = get_db_connection()
        if not conn:
            print(f"Não foi possível conectar ao DB para processar IP {ip_str}")
            return

        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT ID_IPDescoberto FROM IPsDescobertos WHERE EnderecoIP = %s", (ip_str,))
        existing_ip_data = cursor.fetchone()

        if existing_ip_data:
            print(f"  IP {ip_str} já existe. Atualizando NomeHostResolvido se necessário.")
            update_query = "UPDATE IPsDescobertos SET NomeHostResolvido = %s WHERE ID_IPDescoberto = %s" # DataUltimaDeteccao é atualizado por ON UPDATE
            cursor.execute(update_query, (hostname_resolvido, existing_ip_data['ID_IPDescoberto']))
            conn.commit()
            print(f"  IP {ip_str} (Hostname: {hostname_resolvido or 'N/A'}) atualizado.")
        else:
            print(f"  Novo IP detectado: {ip_str}. Inserindo no banco...")
            insert_query = "INSERT INTO IPsDescobertos (EnderecoIP, NomeHostResolvido, StatusResolucao) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (ip_str, hostname_resolvido, 'Novo'))
            conn.commit()
            print(f"  Novo IP descoberto e salvo: {ip_str} (Hostname: {hostname_resolvido or 'N/A'})")

    except mysql.connector.Error as db_err:
        print(f"Erro de DB ao processar IP {ip_str}: {db_err}")
        if conn: conn.rollback()
    except Exception as e:
        print(f"Erro inesperado ao processar IP {ip_str}: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

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
                        print(f"Faixa inválida: {segment} - IPs de versões diferentes.")
                        continue
                    if start_ip > end_ip:
                        print(f"Faixa inválida: {segment} - IP inicial maior que IP final.")
                        continue
                    current_ip = start_ip
                    while current_ip <= end_ip:
                        all_ips_to_scan.append(current_ip)
                        current_ip += 1
                else: 
                    end_octet = int(end_part_str)
                    if not (0 <= end_octet <= 255):
                         print(f"Faixa inválida: {segment} - Octeto final inválido.")
                         continue
                    
                    start_ip_addr_bytes = bytearray(start_ip.packed)
                    if start_ip.version == 4 and len(start_ip_addr_bytes) == 4 :
                        if end_octet < start_ip_addr_bytes[3]:
                             print(f"Faixa inválida: {segment} - Octeto final menor que octeto inicial.")
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
                        print(f"Formato de faixa X.X.X.X-Z só suportado para IPv4: {segment}")
                        continue
            except ValueError as e:
                print(f"Erro ao processar faixa de IP '{segment}': {e}")
                continue
        elif '/' in segment: 
            try:
                network = ipaddress.ip_network(segment, strict=False)
                for ip_obj in network.hosts(): 
                    all_ips_to_scan.append(ip_obj)
            except ValueError as e:
                print(f"Erro ao processar faixa CIDR '{segment}': {e}")
                continue
        else: 
            try:
                all_ips_to_scan.append(ipaddress.ip_address(segment))
            except ValueError as e:
                print(f"Erro ao processar IP único '{segment}': {e}")
                continue
    
    if not all_ips_to_scan:
        return jsonify({"message": "Nenhuma faixa de IP válida para escanear configurada ou fornecida."}), 400

    print(f"Total de IPs a serem escaneados: {len(all_ips_to_scan)}")
    
    active_ips_found = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        chunk_size = 50 
        results_futures = [] # Renomeado para evitar conflito com 'results' da biblioteca nmap
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
    # ... (seu código como estava, parece OK) ...
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
        cursor.close()
        conn.close()
        return jsonify(discovered_ips), 200
    except Exception as e:
        print(f"Erro em /api/discovery/discovered-ips: {e}")
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": "Erro ao buscar IPs descobertos"}), 500
    
@app.route('/')
def home():
    return "Bem-vindo ao Backend!"

@app.route('/api/discovery/discovered-ips/<int:id_ip_descoberto>', methods=['GET'])
def get_single_discovered_ip(id_ip_descoberto):
    # ... (seu código como estava, parece OK) ...
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
        cursor.close()
        conn.close()
        if discovered_ip:
            return jsonify(discovered_ip), 200
        else:
            return jsonify({"message": "IP Descoberto não encontrado"}), 404
    except Exception as e:
        print(f"Erro em /api/discovery/discovered-ips/<id>: {e}")
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": "Erro ao buscar IP descoberto específico"}), 500

@app.route('/login', methods=['POST'])
def login():
    # ... (seu código como estava, parece OK) ...
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"message": "Dados de login ausentes ou inválidos"}), 400
        username_or_email = data['username']
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
                cursor.close()
                conn.close()
                return jsonify({"message": "Login bem-sucedido!", "user": {"id": user['ID_Usuario'], "username": user['NomeUsuario']}}), 200
            else:
                cursor.close()
                conn.close()
                return jsonify({"message": "Usuário ou senha inválidos"}), 401
        else:
            cursor.close()
            conn.close()
            return jsonify({"message": "Usuário ou senha inválidos"}), 401
    except Exception as e:
        print(f"Erro no endpoint /login: {e}")
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": "Erro interno no servidor"}), 500
    
@app.route('/devices', methods=['GET'])
def get_devices():
    # ... (seu código como estava, parece OK, incluindo a correção do params.extend([like_search_term] * 9)) ...
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
        if where_clauses:
            query = base_query + " WHERE " + " AND ".join(where_clauses)
        else:
            query = base_query
        query += " ORDER BY d.NomeHost ASC"
        cursor.execute(query, tuple(params))
        devices = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(devices), 200
    except Exception as e:
        print(f"Erro em /devices (GET com busca): {e}")
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": "Erro ao buscar dispositivos"}), 500
    
@app.route('/devices', methods=['POST'])
def add_device():
    # ... (seu código como estava, parece OK) ...
    conn = None 
    cursor = None
    try:
        data = request.get_json()
        required_fields = ['NomeHost', 'StatusAtual']
        if not data or not all(field in data for field in required_fields):
            return jsonify({"message": "Dados incompletos (NomeHost e StatusAtual obrigatórios)"}), 400
        nome_host = data.get('NomeHost')
        status_atual = data.get('StatusAtual')
        # ... (pegar outros campos: descricao, modelo, ids, localizacao, observacoes) ...
        descricao = data.get('Descricao')
        modelo = data.get('Modelo')
        id_fabricante = data.get('ID_Fabricante')
        id_so = data.get('ID_SistemaOperacional')
        id_tipo_dispositivo = data.get('ID_TipoDispositivo')
        localizacao = data.get('LocalizacaoFisica')
        observacoes = data.get('Observacoes')
        endereco_mac_principal = data.get('EnderecoMAC')
        endereco_ip_principal = data.get('EnderecoIP')
        tipo_ip_principal = data.get('TipoIP', 'IPv4')
        id_rede_principal = data.get('ID_Rede')
        id_fabricante_mac = data.get('ID_Fabricante_MAC')

        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        cursor = conn.cursor()
        device_query = """
        INSERT INTO Dispositivo (NomeHost, Descricao, Modelo, ID_Fabricante, ID_SistemaOperacional, 
                                 ID_TipoDispositivo, StatusAtual, LocalizacaoFisica, Observacoes) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(device_query, (nome_host, descricao, modelo, id_fabricante, id_so, 
                                     id_tipo_dispositivo, status_atual, localizacao, observacoes))
        id_dispositivo_novo = cursor.lastrowid
        if id_dispositivo_novo and endereco_mac_principal and endereco_ip_principal:
            interface_query = """
            INSERT INTO InterfaceRede (ID_Dispositivo, EnderecoMAC, ID_Fabricante_MAC, Ativa)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(interface_query, (id_dispositivo_novo, endereco_mac_principal, id_fabricante_mac, True))
            id_interface_nova = cursor.lastrowid
            ip_query = """
            INSERT INTO EnderecoIP (ID_Interface, EnderecoIPValor, TipoIP, ID_Rede, Principal, TipoAtribuicao)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(ip_query, (id_interface_nova, endereco_ip_principal, tipo_ip_principal, 
                                     id_rede_principal, True, data.get('TipoAtribuicao', 'Descoberto')))
        conn.commit()
        return jsonify({"message": "Dispositivo adicionado com sucesso!", "ID_Dispositivo": id_dispositivo_novo}), 201
    except mysql.connector.Error as db_err:
        if conn: conn.rollback()
        print(f"Erro de banco de dados em POST /devices: {db_err}")
        # ... (seu tratamento de erro 1062) ...
        if db_err.errno == 1062:
            if 'UQ_NomeHost' in db_err.msg or 'NomeHost' in db_err.msg : # Ajuste
                return jsonify({"message": f"Erro: NomeHost '{data.get('NomeHost')}' já existe."}), 409
            elif 'UQ_EnderecoMAC' in db_err.msg or 'EnderecoMAC' in db_err.msg: # Ajuste
                return jsonify({"message": f"Erro: Endereço MAC '{data.get('EnderecoMAC')}' já existe."}), 409
            else:
                return jsonify({"message": f"Erro de duplicidade: {db_err.msg}"}), 409
        return jsonify({"message": f"Erro de banco de dados: {db_err.msg}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro inesperado em POST /devices: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": "Erro interno ao adicionar dispositivo"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/devices/<int:device_id>', methods=['GET'])
def get_device_by_id(device_id): # Esta função já estava no seu código, mantida.
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
            print(f"BACKEND /devices/<id> - Enviando dispositivo: {device}")
            return jsonify(device), 200
        else:
            return jsonify({"message": "Dispositivo não encontrado"}), 404
    except Exception as e:
        print(f"Erro em /devices/<id> (GET): {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": "Erro ao buscar detalhes do dispositivo"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/devices/<int:device_id>', methods=['PUT'])
def update_device(device_id):
    # ... (seu código como estava, parece OK) ...
    conn = None
    cursor = None
    try:
        data = request.get_json()
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
        allowed_fields = ['NomeHost', 'Descricao', 'Modelo', 'ID_Fabricante', 'ID_SistemaOperacional', 
                          'ID_TipoDispositivo', 'StatusAtual', 'LocalizacaoFisica', 'Observacoes', 
                          'GerenciadoPor', 'DataUltimaVarredura']
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
        # Precisamos de um cursor sem dictionary=True para .rowcount ou .lastrowid em algumas versões/situações
        # Mas para UPDATE, o cursor dictionary=True é ok, e o commit é o principal.
        # Reabrindo cursor não dictionary para o execute de UPDATE para garantir.
        cursor.close() 
        cursor = conn.cursor() # Cursor padrão para execute
        cursor.execute(update_query, tuple(update_values))
        conn.commit()
        
        # Para retornar o dispositivo atualizado, precisamos de dictionary=True novamente
        cursor.close()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Dispositivo WHERE ID_Dispositivo = %s", (device_id,))
        updated_device = cursor.fetchone()
        
        return jsonify({"message": "Dispositivo atualizado com sucesso!", "device": updated_device}), 200
    except mysql.connector.Error as db_err:
        # ... (seu tratamento de erro 1062) ...
        if conn: conn.rollback()
        print(f"Erro de banco de dados em PUT /devices/<id>: {db_err}")
        if db_err.errno == 1062:
            return jsonify({"message": f"Erro: Conflito de dados. O NomeHost '{data.get('NomeHost')}' já pode existir."}), 409
        return jsonify({"message": f"Erro de banco de dados: {db_err.msg}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro em PUT /devices/<id>: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": "Erro ao atualizar dispositivo"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    # ... (seu código como estava, parece OK) ...
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        cursor = conn.cursor()
        cursor.execute("SELECT ID_Dispositivo FROM Dispositivo WHERE ID_Dispositivo = %s", (device_id,))
        device = cursor.fetchone()
        if not device:
            cursor.close()
            conn.close()
            return jsonify({"message": "Dispositivo não encontrado para remoção"}), 404
        cursor.execute("DELETE FROM Dispositivo WHERE ID_Dispositivo = %s", (device_id,))
        conn.commit()
        message = "Dispositivo removido com sucesso!" if cursor.rowcount > 0 else "Dispositivo não encontrado ou não pôde ser removido."
        return jsonify({"message": message}), 200
    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro em DELETE /devices/<id>: {e}")
        return jsonify({"message": "Erro ao remover dispositivo"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    
@app.route('/fabricantes', methods=['GET'])
def get_fabricantes():
    # ... (seu código como estava, parece OK) ...
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro de conexão DB"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ID_Fabricante, Nome FROM Fabricante ORDER BY Nome ASC")
        fabricantes = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(fabricantes), 200
    except Exception as e:
        print(f"Erro em /fabricantes: {e}")
        return jsonify({"message": "Erro ao buscar fabricantes"}), 500

@app.route('/sistemasoperacionais', methods=['GET'])
def get_sistemas_operacionais():
    # ... (seu código como estava, parece OK) ...
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro de conexão DB"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ID_SistemaOperacional, Nome, Versao FROM SistemaOperacional ORDER BY Nome ASC, Versao ASC")
        sistemas = cursor.fetchall()
        for so in sistemas:
            so['NomeCompleto'] = f"{so['Nome']} {so['Versao']}" if so['Versao'] else so['Nome']
        cursor.close()
        conn.close()
        return jsonify(sistemas), 200
    except Exception as e:
        print(f"Erro em /sistemasoperacionais: {e}")
        return jsonify({"message": "Erro ao buscar sistemas operacionais"}), 500

@app.route('/tiposdispositivo', methods=['GET'])
def get_tipos_dispositivo():
    # ... (seu código como estava, parece OK) ...
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro de conexão DB"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ID_TipoDispositivo, Nome FROM TipoDispositivo ORDER BY Nome ASC")
        tipos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(tipos), 200
    except Exception as e:
        print(f"Erro em /tiposdispositivo: {e}")
        return jsonify({"message": "Erro ao buscar tipos de dispositivo"}), 500
    
@app.route('/api/discovery/discovered-ips/<int:id_ip_descoberto>/status', methods=['PUT'])
def update_discovered_ip_status(id_ip_descoberto):
    # ... (seu código como estava, parece OK) ...
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
        print(f"Erro em /api/discovery/discovered-ips/<id>/status: {e}")
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": "Erro ao atualizar status do IP descoberto"}), 500
    
@app.route('/api/discovery/scan-ip-details', methods=['POST'])
def scan_ip_details():
    data = request.get_json()
    ip_address = data.get('ip_address')
    id_ip_descoberto = data.get('id_ip_descoberto')

    if not ip_address or not id_ip_descoberto:
        return jsonify({"message": "Endereço IP ou ID do IP Descoberto não fornecido"}), 400

    print(f"BACKEND: Iniciando varredura Nmap detalhada para o IP: {ip_address} (ID DB: {id_ip_descoberto})")
    nm = None
    try:
        nm = nmap.PortScanner()
        nmap_args = '-sV -T4 -Pn' 
        if os.getenv('NMAP_USE_OS_DETECTION', 'false').lower() == 'true':
            nmap_args += ' -O --version-intensity 5'

        print(f"BACKEND: Executando Nmap com argumentos: '{nmap_args}' no IP: {ip_address}")
        nm.scan(ip_address, arguments=nmap_args)

        hostname_nmap = ip_address 
        mac_address = None
        os_details_str = None 
        open_ports_list = []
        raw_nmap_output = "Nenhum host encontrado por Nmap ou IP não respondeu à varredura detalhada."

        # --- INÍCIO DA CORREÇÃO APLICADA ---
        scanned_hosts = nm.all_hosts() 
        print(f"BACKEND: Hosts escaneados por Nmap: {scanned_hosts}")

        if scanned_hosts: 
            host_key = scanned_hosts[0] 
            
            if host_key in nm: 
                host_data = nm[host_key]
                raw_nmap_output = nm.csv() 
                print(f"BACKEND: Resultado Nmap para {host_key}: {host_data.state()}")

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
                        lport = list(host_data[proto].keys())
                        lport.sort(key=int)
                        for port in lport:
                            port_info = host_data[proto][port]
                            if port_info['state'] == 'open':
                                service_name = port_info.get('name', '')
                                product = port_info.get('product', '')
                                version = port_info.get('version', '')
                                service_details = f"{service_name} ({product} {version})".replace("()","").replace("( )","").strip()
                                open_ports_list.append(f"{port}/{proto} - {service_details if service_details else 'Serviço Desconhecido'}")
            else:
                print(f"BACKEND: Chave do host '{host_key}' (de nm.all_hosts()) não encontrada nos resultados do Nmap.")
        else:
            print(f"BACKEND: Nenhum host retornado por nm.all_hosts() para o IP {ip_address}.")
        # --- FIM DA CORREÇÃO APLICADA ---
        
        conn_db = get_db_connection()
        if not conn_db: return jsonify({"message": "Erro de conexão DB ao salvar detalhes Nmap"}), 500
        cursor_db = conn_db.cursor() # cursor_db estava faltando ser definido aqui no seu código original
        
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
        print(f"Erro do Nmap ao escanear {ip_address}: {str(e_nmap)}")
        return jsonify({"message": f"Erro ao executar Nmap: {str(e_nmap)}. Verifique se Nmap está instalado e no PATH, e se o script tem permissões (para -O)."}), 500
    except Exception as e:
        print(f"Erro ao escanear detalhes do IP {ip_address}: {e}")
        import traceback
        traceback.print_exc() 
        return jsonify({"message": "Erro interno ao escanear detalhes do IP."}), 500
    
if __name__ == '__main__':
    app.run(debug=(os.getenv('FLASK_DEBUG', 'False').lower() == 'true'))
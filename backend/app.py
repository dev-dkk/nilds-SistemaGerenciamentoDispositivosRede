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
from concurrent.futures import ThreadPoolExecutor # Para executar pings em paralelo (opcional, mas bom para performance)
# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)
CORS(app) #Habilitando o CORS

# Configuração do Banco de Dados (exemplo, pode ser melhorada)
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao MySQL: {err}")
        return None
#Executar ping e guardar IP´s descobertos
def ping_ip(ip_str):
    """Tenta pingar um IP e retorna True se bem-sucedido, False caso contrário."""
    try:
        # Determina o parâmetro de contagem e timeout com base no SO
        if platform.system().lower() == 'windows':
            # Para Windows: -n envia X pacotes, -w especifica timeout em milissegundos para cada resposta
            command = ['ping', '-n', '2', '-w', '500', ip_str] # Envia 2 pacotes, espera até 500ms por resposta
        else:
            # Para Linux/macOS: -c envia X pacotes, -W especifica timeout em segundos para esperar por uma resposta
            command = ['ping', '-c', '2', '-W', '1', ip_str] # Envia 2 pacotes, espera até 1s por resposta

        startupinfo = None
        if platform.system().lower() == 'windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        # Aumentando o timeout do communicate para garantir que os pings tenham tempo
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
        stdout, stderr = process.communicate(timeout=3) # Timeout total para o processo Popen de 3 segundos

        # Log detalhado da saída do ping
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
        if process: process.kill() 
        return False
    except Exception as e:
        print(f"Exceção ao pingar {ip_str}: {e}")
        return False

def process_discovered_ip(ip_str):
    """Processa um IP que respondeu ao ping: tenta resolver o hostname e insere/atualiza na tabela IPsDescobertos."""
    conn = None
    cursor = None
    hostname_resolvido = None  # Inicializa como None

    try:
        # 1. Tenta resolver o hostname via Reverse DNS
        print(f"Tentando resolver hostname para IP: {ip_str}...")
        try:
            # O timeout padrão para gethostbyaddr pode ser longo. 
            # Para não bloquear demais, podemos definir um timeout global para a resolução.
            # No entanto, socket.gethostbyaddr não aceita timeout diretamente.
            # Uma resolução DNS lenta pode impactar o tempo total da varredura.
            hostname_resolvido, _, _ = socket.gethostbyaddr(ip_str)
            print(f"  Hostname resolvido para {ip_str}: {hostname_resolvido}")
        except socket.herror: # Erro específico para "host not found", "no recovery", etc.
            print(f"  Não foi possível resolver o hostname para {ip_str} via rDNS (socket.herror).")
            hostname_resolvido = None
        except Exception as e_dns: # Pega outros erros potenciais durante a resolução
            print(f"  Erro genérico ao tentar resolver DNS para {ip_str}: {e_dns}")
            hostname_resolvido = None
        
        # 2. Conecta ao banco para salvar/atualizar
        conn = get_db_connection()
        if not conn:
            print(f"Não foi possível conectar ao DB para processar IP {ip_str}")
            return

        cursor = conn.cursor(dictionary=True)
        
        # 3. Verifica se o IP já existe na tabela IPsDescobertos
        cursor.execute("SELECT ID_IPDescoberto FROM IPsDescobertos WHERE EnderecoIP = %s", (ip_str,))
        existing_ip_data = cursor.fetchone()

        if existing_ip_data:
            # Se existe, atualiza DataUltimaDeteccao (automaticamente pelo DB) 
            # e o NomeHostResolvido se tivermos um novo ou se o anterior era nulo.
            print(f"  IP {ip_str} já existe. Atualizando NomeHostResolvido se necessário.")
            update_query = "UPDATE IPsDescobertos SET NomeHostResolvido = %s WHERE ID_IPDescoberto = %s"
            cursor.execute(update_query, (hostname_resolvido, existing_ip_data['ID_IPDescoberto']))
            conn.commit()
            print(f"  IP {ip_str} (Hostname: {hostname_resolvido or 'N/A'}) atualizado.")
        else:
            # Se não existe, insere como 'Novo'
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
            process_discovered_ip(ip_str) # Processa e salva no DB
    return active_ips_in_segment

@app.route('/api/discovery/start-scan', methods=['POST'])
def start_discovery_scan():
    # Pega as faixas de IP do .env
    ip_ranges_str = os.getenv('DISCOVERY_IP_RANGES', '192.168.1.1-192.168.1.20') # Default se não definido
    
    all_ips_to_scan = []
    range_segments = ip_ranges_str.split(',')
    
    for segment in range_segments:
        segment = segment.strip()
        if '-' in segment: # Formato X.X.X.X-Y.Y.Y.Y ou X.X.X.X-Z (onde Z é o último octeto)
            try:
                start_ip_str, end_part_str = segment.split('-')
                start_ip = ipaddress.ip_address(start_ip_str)
                
                if '.' in end_part_str : # é um IP completo Y.Y.Y.Y
                    end_ip = ipaddress.ip_address(end_part_str)
                    if start_ip.version != end_ip.version:
                        print(f"Faixa inválida: {segment} - IPs de versões diferentes.")
                        continue
                    # Garante que start_ip seja menor ou igual a end_ip
                    if start_ip > end_ip:
                        print(f"Faixa inválida: {segment} - IP inicial maior que IP final.")
                        continue
                    current_ip = start_ip
                    while current_ip <= end_ip:
                        all_ips_to_scan.append(current_ip)
                        current_ip += 1
                else: # é apenas o último octeto Z
                    end_octet = int(end_part_str)
                    if not (0 <= end_octet <= 255):
                         print(f"Faixa inválida: {segment} - Octeto final inválido.")
                         continue
                    
                    # Constrói o IP final baseado no IP inicial
                    # Ex: 192.168.1.1-50 -> start_ip=192.168.1.1, end_ip_addr_bytes[3]=50
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
                            if current_ip == end_ip : break # Evita loop infinito se algo der errado
                            current_ip += 1
                    else:
                        print(f"Formato de faixa X.X.X.X-Z só suportado para IPv4: {segment}")
                        continue

            except ValueError as e:
                print(f"Erro ao processar faixa de IP '{segment}': {e}")
                continue
        elif '/' in segment: # Formato CIDR X.X.X.X/Y
            try:
                network = ipaddress.ip_network(segment, strict=False)
                for ip_obj in network.hosts(): # .hosts() exclui o endereço de rede e broadcast
                    all_ips_to_scan.append(ip_obj)
            except ValueError as e:
                print(f"Erro ao processar faixa CIDR '{segment}': {e}")
                continue
        else: # IP único
            try:
                all_ips_to_scan.append(ipaddress.ip_address(segment))
            except ValueError as e:
                print(f"Erro ao processar IP único '{segment}': {e}")
                continue
    
    if not all_ips_to_scan:
        return jsonify({"message": "Nenhuma faixa de IP válida para escanear configurada ou fornecida."}), 400

    print(f"Total de IPs a serem escaneados: {len(all_ips_to_scan)}")
    
    active_ips_found = []
    # Usando ThreadPoolExecutor para pingar em paralelo (mais rápido para muitos IPs)
    # Ajuste max_workers conforme os recursos do seu sistema
    with ThreadPoolExecutor(max_workers=20) as executor:
        # Divide a lista de IPs em chunks menores para não sobrecarregar o executor de uma vez
        chunk_size = 50 
        results = []
        for i in range(0, len(all_ips_to_scan), chunk_size):
            ip_chunk = all_ips_to_scan[i:i + chunk_size]
            # Mapeia a função ping_ip para cada IP no chunk
            # A função process_discovered_ip é chamada dentro de scan_ip_range_segment
            # que é chamada por ping_and_process_chunk
            future = executor.submit(scan_ip_range_segment, ip_chunk)
            results.append(future)
        
        for future in results:
            active_ips_found.extend(future.result())


    # A varredura é síncrona por enquanto (a requisição espera terminar)
    # Para varreduras longas, o ideal seria uma tarefa assíncrona (Celery, etc.)
    
    return jsonify({
        "message": f"Varredura de descoberta concluída. {len(active_ips_found)} IPs ativos encontrados e processados.",
        "active_ips": active_ips_found # Retorna os IPs que responderam
    }), 200
@app.route('/api/discovery/discovered-ips', methods=['GET'])
def get_discovered_ips():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500

        cursor = conn.cursor(dictionary=True)

        # Ordenar por data de última detecção, os mais recentes primeiro
        query = """
        SELECT 
            ID_IPDescoberto, 
            EnderecoIP, 
            DataPrimeiraDeteccao,
            DataUltimaDeteccao, 
            StatusResolucao,
            NomeHostResolvido
        FROM IPsDescobertos 
        ORDER BY DataUltimaDeteccao DESC
        """
        cursor.execute(query)
        discovered_ips = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(discovered_ips), 200

    except Exception as e:
        print(f"Erro em /api/discovery/discovered-ips: {e}")
        # Mantenha o fechamento da conexão em caso de erro, se aplicável
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": "Erro ao buscar IPs descobertos"}), 500
    
@app.route('/')
def home():
    return "Bem-vindo ao Backend!"

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"message": "Dados de login ausentes ou inválidos"}), 400

        username_or_email = data['username']
        password_digitada = data['password']

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        
        cursor = conn.cursor(dictionary=True) # dictionary=True para retornar linhas como dicionários

        # Tenta encontrar o usuário pelo NomeUsuario ou Email
        query = "SELECT ID_Usuario, NomeUsuario, SenhaHash, Ativo FROM Usuario WHERE NomeUsuario = %s OR Email = %s"
        cursor.execute(query, (username_or_email, username_or_email))
        user = cursor.fetchone()

        if user and user['Ativo']:
            senha_hash_bd = user['SenhaHash'].encode('utf-8') # Senha do BD vem como string, precisa ser bytes
            password_digitada_bytes = password_digitada.encode('utf-8')

            if bcrypt.checkpw(password_digitada_bytes, senha_hash_bd):
                # Login bem-sucedido!
                # Em uma aplicação real, você geraria um token JWT (JSON Web Token) aqui
                # e o retornaria para o cliente para autenticação em requisições futuras.
                cursor.close()
                conn.close()
                return jsonify({
                    "message": "Login bem-sucedido!",
                    "user": {
                        "id": user['ID_Usuario'],
                        "username": user['NomeUsuario']
                    }
                }), 200
            else:
                # Senha incorreta
                cursor.close()
                conn.close()
                return jsonify({"message": "Usuário ou senha inválidos"}), 401
        else:
            # Usuário não encontrado ou inativo
            cursor.close()
            conn.close()
            return jsonify({"message": "Usuário ou senha inválidos"}), 401

    except Exception as e:
        print(f"Erro no endpoint /login: {e}")
        # Tentar fechar a conexão se ela existir e estiver aberta em caso de erro
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor:
                cursor.close()
            conn.close()
        return jsonify({"message": "Erro interno no servidor"}), 500
    
@app.route('/devices', methods=['GET'])
def get_devices():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Pega o termo de busca da query string da URL (ex: /devices?search=meu_pc)
        search_term = request.args.get('search', None) # 'search' é o nome do parâmetro, None se não for fornecido

        base_query = """
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
        """
        
        params = []
        where_clauses = []

        if search_term:
            like_search_term = f"%{search_term}%"
            # Adicione os campos que você quer que sejam pesquisáveis
            # Usamos OR para que o termo possa aparecer em qualquer um dos campos
            where_clauses.append("""
            (d.NomeHost LIKE %s OR 
             ip.EnderecoIPValor LIKE %s OR 
             ifr.EnderecoMAC LIKE %s OR
             so.Nome LIKE %s OR 
             fab.Nome LIKE %s OR
             td.Nome LIKE %s OR
             d.Descricao LIKE %s OR 
             d.Modelo LIKE %s OR
             d.LocalizacaoFisica LIKE %s)
            """)
            # Adiciona o termo de busca para cada placeholder %s na cláusula WHERE
            # O número de repetições do like_search_term deve corresponder ao número de campos no OR
            params.extend([like_search_term] * 9) # Ajuste o número '8' se mudar a quantidade de campos no OR

        if where_clauses:
            query = base_query + " WHERE " + " AND ".join(where_clauses) # Se tiver mais filtros no futuro
        else:
            query = base_query
            
        query += " ORDER BY d.NomeHost ASC" # Mantém a ordenação

        cursor.execute(query, tuple(params))
        devices = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(devices), 200

    except Exception as e:
        print(f"Erro em /devices (GET com busca): {e}")
        # ... (seu tratamento de erro e fechamento de conexão existente) ...
        # Mantenha o fechamento da conexão em caso de erro
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": "Erro ao buscar dispositivos"}), 500
    
@app.route('/devices', methods=['POST'])
def add_device():
    try:
        data = request.get_json()
        
        # Validação básica dos dados recebidos
        required_fields = ['NomeHost', 'StatusAtual'] # Adicione outros campos obrigatórios
        if not data or not all(field in data for field in required_fields):
            return jsonify({"message": "Dados incompletos para adicionar dispositivo"}), 400

        nome_host = data.get('NomeHost')
        status_atual = data.get('StatusAtual')
        descricao = data.get('Descricao')
        modelo = data.get('Modelo')
        id_fabricante = data.get('ID_Fabricante') # Espera-se o ID
        id_so = data.get('ID_SistemaOperacional') # Espera-se o ID
        id_tipo_dispositivo = data.get('ID_TipoDispositivo') # Espera-se o ID
        localizacao = data.get('LocalizacaoFisica')
        observacoes = data.get('Observacoes')
        # DataDescoberta e DataUltimaModificacao têm DEFAULT ou ON UPDATE no banco

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        
        cursor = conn.cursor()
        
        query = """
        INSERT INTO Dispositivo (
            NomeHost, Descricao, Modelo, ID_Fabricante, ID_SistemaOperacional, 
            ID_TipoDispositivo, StatusAtual, LocalizacaoFisica, Observacoes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            nome_host, descricao, modelo, id_fabricante, id_so, 
            id_tipo_dispositivo, status_atual, localizacao, observacoes
        ))
        conn.commit()
        new_device_id = cursor.lastrowid # Pega o ID do dispositivo inserido
        
        cursor.close()
        conn.close()
        
        # Idealmente, aqui você também poderia adicionar dados às tabelas InterfaceRede e EnderecoIP
        # se eles fossem fornecidos na requisição. Por enquanto, vamos simplificar.

        return jsonify({"message": "Dispositivo adicionado com sucesso!", "ID_Dispositivo": new_device_id}), 201

    except mysql.connector.Error as db_err:
        print(f"Erro de banco de dados em /devices (POST): {db_err}")
        # Verificar erro de constraint de unicidade para NomeHost
        if db_err.errno == 1062: # Código de erro para entrada duplicada
             return jsonify({"message": f"Erro: NomeHost '{data.get('NomeHost')}' já existe."}), 409 # 409 Conflict
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": f"Erro de banco de dados: {db_err.msg}"}), 500
    except Exception as e:
        print(f"Erro em /devices (POST): {e}")
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": "Erro ao adicionar dispositivo"}), 500


@app.route('/devices/<int:device_id>', methods=['GET'])
def get_device_by_id(device_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Query para buscar um dispositivo específico com detalhes completos
        # Similar à query de listar todos, mas filtrando pelo ID e buscando mais detalhes se necessário
        query = """
        SELECT 
            d.ID_Dispositivo, d.NomeHost, d.Descricao, d.Modelo, 
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
        cursor.execute(query, (device_id,))
        device = cursor.fetchone()
        
        if device:
            # Aqui você poderia buscar informações adicionais, como todas as interfaces de rede e IPs
            # associados a este dispositivo, e adicioná-los ao dicionário 'device'.
            # Exemplo (simplificado):
            interfaces_query = """
            SELECT ifr.ID_Interface, ifr.NomeInterface, ifr.EnderecoMAC, fab_mac.Nome as FabricanteMAC,
                   ip.EnderecoIPValor, ip.TipoIP, ip.TipoAtribuicao, r.NomeRede
            FROM InterfaceRede ifr
            LEFT JOIN Fabricante fab_mac ON ifr.ID_Fabricante_MAC = fab_mac.ID_Fabricante
            LEFT JOIN EnderecoIP ip ON ifr.ID_Interface = ip.ID_Interface
            LEFT JOIN Rede r ON ip.ID_Rede = r.ID_Rede
            WHERE ifr.ID_Dispositivo = %s
            """
            cursor.execute(interfaces_query, (device_id,))
            device['interfaces'] = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return jsonify(device), 200
        else:
            cursor.close()
            conn.close()
            return jsonify({"message": "Dispositivo não encontrado"}), 404

    except Exception as e:
        print(f"Erro em /devices/<id> (GET): {e}")
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": "Erro ao buscar detalhes do dispositivo"}), 500


@app.route('/devices/<int:device_id>', methods=['PUT'])
def update_device(device_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Nenhum dado fornecido para atualização"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        
        cursor = conn.cursor(dictionary=True)

        # Verificar se o dispositivo existe
        cursor.execute("SELECT * FROM Dispositivo WHERE ID_Dispositivo = %s", (device_id,))
        device = cursor.fetchone()
        if not device:
            cursor.close()
            conn.close()
            return jsonify({"message": "Dispositivo não encontrado para atualização"}), 404

        # Montar a query de atualização dinamicamente com os campos fornecidos
        # Cuidado com SQL Injection se fosse montar a query com f-strings diretamente.
        # Usar placeholders é mais seguro.
        
        # Campos que podem ser atualizados na tabela Dispositivo
        # (excluindo ID_Dispositivo, DataDescoberta, DataUltimaModificacao que são gerenciados de outra forma)
        allowed_fields = [
            'NomeHost', 'Descricao', 'Modelo', 'ID_Fabricante', 
            'ID_SistemaOperacional', 'ID_TipoDispositivo', 'StatusAtual', 
            'LocalizacaoFisica', 'Observacoes', 'GerenciadoPor', 'DataUltimaVarredura'
        ]
        
        update_fields = []
        update_values = []
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"`{field}` = %s") # Usar backticks para nomes de colunas
                update_values.append(data[field])
        
        if not update_fields:
            cursor.close()
            conn.close()
            return jsonify({"message": "Nenhum campo válido fornecido para atualização"}), 400

        # Adiciona o device_id ao final da lista de valores para o WHERE
        update_values.append(device_id)
        
        update_query = f"UPDATE Dispositivo SET {', '.join(update_fields)} WHERE ID_Dispositivo = %s"
        
        cursor.execute(update_query, tuple(update_values))
        conn.commit()
        
        # Buscar o dispositivo atualizado para retornar (opcional)
        cursor.execute("SELECT * FROM Dispositivo WHERE ID_Dispositivo = %s", (device_id,))
        updated_device = cursor.fetchone()

        cursor.close()
        conn.close()
        
        return jsonify({"message": "Dispositivo atualizado com sucesso!", "device": updated_device}), 200

    except mysql.connector.Error as db_err:
        print(f"Erro de banco de dados em /devices/<id> (PUT): {db_err}")
        if db_err.errno == 1062: # Erro de entrada duplicada (ex: NomeHost único)
             return jsonify({"message": f"Erro: Conflito de dados. O NomeHost '{data.get('NomeHost')}' já pode existir."}), 409
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": f"Erro de banco de dados: {db_err.msg}"}), 500
    except Exception as e:
        print(f"Erro em /devices/<id> (PUT): {e}")
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": "Erro ao atualizar dispositivo"}), 500

@app.route('/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Erro interno no servidor (conexão DB)"}), 500
        
        cursor = conn.cursor()

        # Verificar se o dispositivo existe antes de tentar deletar
        cursor.execute("SELECT ID_Dispositivo FROM Dispositivo WHERE ID_Dispositivo = %s", (device_id,))
        device = cursor.fetchone()
        if not device:
            cursor.close()
            conn.close()
            return jsonify({"message": "Dispositivo não encontrado para remoção"}), 404
            
        # As FKs com ON DELETE CASCADE (como em InterfaceRede, LogStatusDispositivo)
        # cuidarão de remover os registros relacionados automaticamente.
        # Para FKs com ON DELETE SET NULL (como em Alerta), o ID será setado para NULL.
        cursor.execute("DELETE FROM Dispositivo WHERE ID_Dispositivo = %s", (device_id,))
        conn.commit()
        
        # rowcount pode verificar se a deleção afetou alguma linha
        if cursor.rowcount > 0:
            message = "Dispositivo removido com sucesso!"
        else:
            # Isso não deveria acontecer se a verificação acima encontrou o dispositivo, mas é uma checagem extra.
            message = "Dispositivo não encontrado ou não pôde ser removido."
            
        cursor.close()
        conn.close()
        
        return jsonify({"message": message}), 200 # Ou 204 No Content se preferir não retornar corpo

    except Exception as e:
        print(f"Erro em /devices/<id> (DELETE): {e}")
        if 'conn' in locals() and conn and conn.is_connected():
            if 'cursor' in locals() and cursor: cursor.close()
            conn.close()
        return jsonify({"message": "Erro ao remover dispositivo"}), 500
    
@app.route('/fabricantes', methods=['GET'])
def get_fabricantes():
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
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"message": "Erro de conexão DB"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ID_SistemaOperacional, Nome, Versao FROM SistemaOperacional ORDER BY Nome ASC, Versao ASC")
        sistemas = cursor.fetchall()
        # Formatar nome com versão para exibição
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

    
if __name__ == '__main__':
    # O debug=True é ótimo para desenvolvimento, mas NÃO use em produção.
    # O Flask irá pegar a configuração de debug do .env se FLASK_DEBUG=True estiver lá.
    app.run(debug=(os.getenv('FLASK_DEBUG', 'False').lower() == 'true'))
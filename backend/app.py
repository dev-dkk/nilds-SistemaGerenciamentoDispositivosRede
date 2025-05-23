import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import mysql.connector
import bcrypt

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
        
        # Query para buscar dispositivos com informações de tabelas relacionadas
        # Ajuste os JOINs e campos conforme sua necessidade e o que quer exibir na lista inicial
        query = """
        SELECT 
            d.ID_Dispositivo, d.NomeHost, d.StatusAtual, d.DataUltimaVarredura,
            ip.EnderecoIPValor as IPPrincipal, 
            ifr.EnderecoMAC as MACPrincipal,
            so.Nome as SistemaOperacionalNome,
            fab.Nome as FabricanteNome,
            td.Nome as TipoDispositivoNome
        FROM Dispositivo d
        LEFT JOIN InterfaceRede ifr ON d.ID_Dispositivo = ifr.ID_Dispositivo -- Assumindo uma interface principal ou a primeira
        LEFT JOIN EnderecoIP ip ON ifr.ID_Interface = ip.ID_Interface AND ip.Principal = TRUE
        LEFT JOIN SistemaOperacional so ON d.ID_SistemaOperacional = so.ID_SistemaOperacional
        LEFT JOIN Fabricante fab ON d.ID_Fabricante = fab.ID_Fabricante
        LEFT JOIN TipoDispositivo td ON d.ID_TipoDispositivo = td.ID_TipoDispositivo
        ORDER BY d.NomeHost ASC
        """
        # Nota: A lógica para "interface principal" e "IP principal" pode precisar de refinamento
        # dependendo de como você modelou isso (ex: uma flag na tabela InterfaceRede/EnderecoIP)
        # Para simplificar, podemos pegar o primeiro IP/MAC encontrado ou um marcado como principal.
        # Se um dispositivo pode ter múltiplas interfaces/IPs, a listagem principal
        # geralmente mostra o "mais representativo".

        cursor.execute(query)
        devices = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(devices), 200

    except Exception as e:
        print(f"Erro em /devices (GET): {e}")
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
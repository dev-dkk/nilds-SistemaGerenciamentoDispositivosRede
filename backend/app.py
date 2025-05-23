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
    return "Bem-vindo ao Backend do Network Asset Manager!"

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

if __name__ == '__main__':
    # O debug=True é ótimo para desenvolvimento, mas NÃO use em produção.
    # O Flask irá pegar a configuração de debug do .env se FLASK_DEBUG=True estiver lá.
    app.run(debug=(os.getenv('FLASK_DEBUG', 'False').lower() == 'true'))
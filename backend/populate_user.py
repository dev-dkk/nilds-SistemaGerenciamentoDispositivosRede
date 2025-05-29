import os
import mysql.connector
import bcrypt
from dotenv import load_dotenv
import getpass # Para ler a senha de forma segura sem mostrá-la no terminal

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

def create_user():
    try:
        # Conexão com o banco de dados
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        cursor = conn.cursor()
        print('Conexão com banco de dados bem sucedida!')
        print("--- Criação de Novo Usuário ---")
        nome_usuario = input("Nome de Usuário (para login): ")
        email = input("Email: ")
        nome_completo = input("Nome Completo (opcional, pressione Enter para pular): ") or None
        
        # Listar perfis disponíveis para facilitar a escolha
        cursor.execute("SELECT ID_Perfil, NomePerfil FROM PerfilUsuario")
        perfis = cursor.fetchall()
        if not perfis:
            print("\nERRO: Nenhum perfil encontrado na tabela PerfilUsuario.")
            print("Por favor, adicione perfis antes de criar usuários (ex: Administrador, Operador).")
            cursor.close()
            conn.close()
            return

        print("\nPerfis Disponíveis:")
        for perfil_id, nome_perfil in perfis:
            print(f"  ID: {perfil_id} - Nome: {nome_perfil}")
        
        while True:
            try:
                id_perfil_str = input("ID do Perfil para este usuário: ")
                id_perfil = int(id_perfil_str)
                if any(p_id == id_perfil for p_id, _ in perfis):
                    break
                else:
                    print("ID de Perfil inválido. Por favor, escolha um da lista.")
            except ValueError:
                print("Entrada inválida. Por favor, digite um número para o ID do Perfil.")

        # Pede a senha em texto plano de forma segura
        senha_plana_str = getpass.getpass("Digite a Senha (não será visível): ")
        senha_plana_bytes = senha_plana_str.encode('utf-8') # Converte para bytes

        # Gera o salt e o hash da senha
        salt = bcrypt.gensalt()
        senha_hash_bytes = bcrypt.hashpw(senha_plana_bytes, salt)
        senha_hash_str = senha_hash_bytes.decode('utf-8') # Converte de volta para string para armazenar

        # Insere o novo usuário
        query = """
        INSERT INTO Usuario (NomeUsuario, SenhaHash, Email, NomeCompleto, ID_Perfil, Ativo)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        # Por padrão, o usuário é criado como Ativo (TRUE = 1)
        cursor.execute(query, (nome_usuario, senha_hash_str, email, nome_completo, id_perfil, True))
        conn.commit()

        print(f"\nUsuário '{nome_usuario}' criado com sucesso!")

    except mysql.connector.Error as err:
        print(f"Erro ao conectar ou operar no MySQL: {err}")
    except Exception as e:
        print(f"Um erro inesperado ocorreu: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            print("Conexão com o banco de dados fechada.")

if __name__ == '__main__':
    create_user()
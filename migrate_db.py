import psycopg2
from psycopg2 import extensions

# Configurações de conexão (baseadas no seu database.py)
DB_CONFIG = {
    "host": "localhost",
    "user": "postgres",
    "password": "1234"
}

def init_db():
    """Cria o banco de dados caso não exista."""
    try:
        # Conecta no banco padrão 'postgres' para criar o novo banco
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database="postgres"
        )
        conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Verifica se o banco existe
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'catalogo_filmes'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute("CREATE DATABASE catalogo_filmes")
            print("Banco de dados 'catalogo_filmes' criado com sucesso!")
        else:
            print("Banco de dados 'catalogo_filmes' já existe.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao inicializar banco de dados: {e}")

def init_table():
    """Cria a tabela 'filmes' caso não exista."""
    try:
        # Conecta no banco 'catalogo_filmes' agora
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database="catalogo_filmes"
        )
        cursor = conn.cursor()

        # Criação da tabela
        sql = """
        CREATE TABLE IF NOT EXISTS filmes (
            id SERIAL PRIMARY KEY,
            titulo VARCHAR(255) NOT NULL,
            genero VARCHAR(100),
            ano DATE,
            url_capa TEXT
        );
        """
        cursor.execute(sql)
        conn.commit()
        print("Tabela 'filmes' verificada/criada com sucesso!")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao inicializar tabela: {e}")


def init_table_usuario():
    """Cria a tabela 'usuario' caso não exista."""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database="catalogo_filmes"
        )
        cursor = conn.cursor()

        sql = """
        CREATE TABLE IF NOT EXISTS usuario (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            senha TEXT NOT NULL
        );
        """
        cursor.execute(sql)

        # Opcional: Criar um usuário inicial se a tabela estiver vazia
        cursor.execute("SELECT COUNT(*) FROM usuario")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO usuario (nome, email, senha) VALUES (%s, %s, %s)",
                ("Riana Aldias", "riana.aldias@gmail.com", "1234")
            )

        conn.commit()
        print("Tabela 'usuario' verificada/criada com sucesso!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao inicializar tabela usuario: {e}")


# No final do arquivo, chame a nova função:
if __name__ == "__main__":
    print("Iniciando migração...")
    init_db()
    init_table()
    init_table_usuario()  # <--- Nova chamada
    print("Migração finalizada.")

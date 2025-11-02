import sqlite3
import os

DB_FILE = os.path.join("data", "pedidos.db")
DB_DIR = "data"

def create_database():
    """
    Cria a estrutura inicial do banco de dados SQLite e insere dados de exemplo.
    """
    
    # Garante que o diretório /data exista
    os.makedirs(DB_DIR, exist_ok=True)
    
    # Conecta ao banco de dados (cria o arquivo se não existir)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print(f"Banco de dados '{DB_FILE}' conectado/criado.")

    # --- Tabela 1: Solicitantes ---
    # Armazena informações das pessoas que fazem os pedidos
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Solicitantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        );
        """)
        print("Tabela 'Solicitantes' criada com sucesso.")
    except sqlite3.Error as e:
        print(f"Erro ao criar tabela 'Solicitantes': {e}")
        conn.close()
        return

    # --- Tabela 2: ControleDePedidos ---
    # O banco de dados local com informações de pedidos
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ControleDePedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_pedido TEXT NOT NULL UNIQUE,
            solicitante_id INTEGER NOT NULL,
            valor REAL NOT NULL,
            centro_de_custos TEXT NOT NULL,
            FOREIGN KEY (solicitante_id) REFERENCES Solicitantes (id)
        );
        """)
        print("Tabela 'ControleDePedidos' criada com sucesso.")
    except sqlite3.Error as e:
        print(f"Erro ao criar tabela 'ControleDePedidos': {e}")
        conn.close()
        return

    # --- Tabela 3: ProcessamentoNF ---
    # Tabela de controle de estado para o agente de IA
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ProcessamentoNF (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_nf TEXT,
            data_nf TEXT,
            fornecedor_nf TEXT,
            valor_nf REAL,
            pedido_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            validation_token TEXT NOT NULL UNIQUE,
            timestamp_envio DATETIME NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES ControleDePedidos (id)
        );
        """)
        print("Tabela 'ProcessamentoNF' criada com sucesso.")
    except sqlite3.Error as e:
        print(f"Erro ao criar tabela 'ProcessamentoNF': {e}")
        conn.close()
        return

    # --- Inserir Dados de Exemplo (para teste) ---
    try:
        # Inserir um solicitante (ignora se o e-mail já existir)
        cursor.execute("""
        INSERT OR IGNORE INTO Solicitantes (nome, email) 
        VALUES ('Usuario Teste', 'solicitante.teste@suaempresa.com');
        """)
        
        # Obter o ID do solicitante que acabamos de inserir
        solicitante_id = cursor.execute("SELECT id FROM Solicitantes WHERE email = 'solicitante.teste@suaempresa.com'").fetchone()[0]

        # Inserir pedidos de exemplo (ignora se o numero_pedido já existir)
        pedidos_exemplo = [
            ('PED-1001-XYZ', solicitante_id, 1500.50, 'TI-INFRA'),
            ('PED-1002-ABC', solicitante_id, 899.90, 'MARKETING')
        ]
        
        cursor.executemany("""
        INSERT OR IGNORE INTO ControleDePedidos (numero_pedido, solicitante_id, valor, centro_de_custos)
        VALUES (?, ?, ?, ?);
        """, pedidos_exemplo)
        
        conn.commit()
        print("Dados de exemplo inseridos com sucesso.")
        
    except sqlite3.Error as e:
        print(f"Erro ao inserir dados de exemplo: {e}")
    finally:
        # Fechar a conexão
        conn.close()
        print(f"Conexão com '{DB_FILE}' fechada.")

if __name__ == "__main__":
    create_database()
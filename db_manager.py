import sqlite3
import os
from datetime import datetime

# Define o caminho para o arquivo do banco de dados dentro da pasta /data
DB_FILE = os.path.join("data", "pedidos.db")

def get_db_connection():
    """
    Cria e retorna uma conexão com o banco de dados SQLite.
    Configura o row_factory para sqlite3.Row para que possamos acessar
    as colunas por nome (como um dicionário).
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_order_details_by_number(numero_pedido):
    """
    Busca detalhes de um pedido e do seu solicitante pelo número do pedido.
    Utiliza um JOIN para combinar dados das tabelas ControleDePedidos e Solicitantes.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query que junta o pedido com os dados do solicitante (nome e email)
    cursor.execute(
        """
        SELECT 
            cp.id as pedido_id, 
            cp.numero_pedido, 
            cp.valor as valor_pedido, 
            cp.centro_de_custos,
            s.nome as solicitante_nome, 
            s.email as solicitante_email
        FROM ControleDePedidos cp
        JOIN Solicitantes s ON cp.solicitante_id = s.id
        WHERE cp.numero_pedido = ?
        """,
        (numero_pedido,)
    )
    
    pedido_data = cursor.fetchone()  # Retorna um objeto sqlite3.Row (dict-like) ou None
    conn.close()
    return pedido_data

def create_processing_entry(nf_data, pedido_id, token):
    """
    Registra uma nova Nota Fiscal em processamento na tabela ProcessamentoNF.
    Define o status inicial como 'PENDING_VALIDATION' e grava o timestamp.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO ProcessamentoNF 
            (numero_nf, data_nf, fornecedor_nf, valor_nf, pedido_id, status, validation_token, timestamp_envio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nf_data.get('numero_nf'),
                nf_data.get('data_nf'),
                nf_data.get('fornecedor_nf'),
                nf_data.get('valor_nf'),
                pedido_id,
                'PENDING_VALIDATION',  # Status inicial
                token,
                datetime.now()         # Timestamp atual
            )
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Erro ao inserir no ProcessamentoNF: {e}")
        conn.rollback()  # Desfaz a transação em caso de erro
    finally:
        conn.close()

def update_processing_status_by_token(token, new_status):
    """
    Atualiza o status de um processamento de NF (para 'APPROVED', 'REJECTED', ou 'TIMEOUT')
    usando o token de validação único.
    
    Só atualiza se o status atual for 'PENDING_VALIDATION' para evitar
    condições de corrida (ex: usuário aprova e timeout ocorre ao mesmo tempo).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            UPDATE ProcessamentoNF
            SET status = ?
            WHERE validation_token = ? AND status = 'PENDING_VALIDATION'
            """,
            (new_status, token)
        )
        conn.commit()
        # Retorna True se uma linha foi de fato atualizada, False caso contrário
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Erro ao atualizar status: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_pending_validations():
    """
    Busca todas as NFs que ainda estão com status 'PENDING_VALIDATION'.
    Usado pelo script de scheduler para verificar timeouts.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT id, validation_token, timestamp_envio, numero_nf 
        FROM ProcessamentoNF
        WHERE status = 'PENDING_VALIDATION'
        """
    )
    
    pending_list = cursor.fetchall()
    conn.close()
    return pending_list

def get_data_for_finance_email(token):
    """
    Coleta todos os dados de NF, Pedido e Solicitante necessários 
    para enviar o e-mail final ao financeiro, usando o token.
    Esta é a consulta mais completa, unindo as 3 tabelas.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT 
            pnf.numero_nf, pnf.data_nf, pnf.fornecedor_nf, pnf.valor_nf, pnf.status,
            cp.numero_pedido, cp.valor as valor_pedido, cp.centro_de_custos,
            s.nome as solicitante_nome
        FROM ProcessamentoNF pnf
        JOIN ControleDePedidos cp ON pnf.pedido_id = cp.id
        JOIN Solicitantes s ON cp.solicitante_id = s.id
        WHERE pnf.validation_token = ?
        """,
        (token,)
    )
    
    data = cursor.fetchone()
    conn.close()
    return data # Retorna um sqlite3.Row (dict-like) com todos os dados
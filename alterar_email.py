import sqlite3
import os

# --- Configuração ---
# Defina o e-mail que você quer mudar e o novo e-mail
EMAIL_ANTIGO = "yonaw27644@lovleo.com"
EMAIL_NOVO = "royadi9000@dwakm.com"
# --------------------

DB_FILE = os.path.join("data", "pedidos.db")

def alterar_email_solicitante():
    """
    Conecta ao banco de dados e atualiza o e-mail de um solicitante.
    """
    if not os.path.exists(DB_FILE):
        print(f"Erro: Banco de dados '{DB_FILE}' não encontrado.")
        print("Execute o script 'setup_db.py' primeiro.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print(f"Tentando alterar e-mail de '{EMAIL_ANTIGO}' para '{EMAIL_NOVO}'...")
    
    try:
        cursor.execute(
            """
            UPDATE Solicitantes
            SET email = ?
            WHERE email = ?
            """,
            (EMAIL_NOVO, EMAIL_ANTIGO)
        )
        
        # Verifica se alguma linha foi realmente alterada
        if cursor.rowcount == 0:
            print(f"Erro: Nenhum solicitante encontrado com o e-mail '{EMAIL_ANTIGO}'.")
            print("Verifique se o e-mail antigo está correto.")
        else:
            conn.commit()
            print("Sucesso!")
            print(f"O e-mail foi alterado de '{EMAIL_ANTIGO}' para '{EMAIL_NOVO}'.")
            
    except sqlite3.IntegrityError as e:
        # Isso acontece se o EMAIL_NOVO já existir (pois a coluna é UNIQUE)
        print(f"Erro de Integridade: {e}")
        print(f"Provavelmente o e-mail '{EMAIL_NOVO}' já está cadastrado para outro usuário.")
        conn.rollback()
    except sqlite3.Error as e:
        print(f"Ocorreu um erro no banco de dados: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    alterar_email_solicitante()
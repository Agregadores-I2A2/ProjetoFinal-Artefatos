import db_manager
import email_manager
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
# Attempt to import python-dotenv; if unavailable, provide a minimal fallback.
try:
    # Use a dynamic import so linters/static analysis won't error if the package isn't installed.
    import importlib
    _dotenv = importlib.import_module("dotenv")
    _load_dotenv = getattr(_dotenv, "load_dotenv", None)
except Exception:
    _load_dotenv = None
def load_dotenv(env_path: str = ".env"):
    """
    Load environment variables from a .env file.
    Prefer python-dotenv if available; otherwise use a simple fallback parser.
    """
    if _load_dotenv:
        return _load_dotenv(env_path)

    import os
    from pathlib import Path

    path = Path(env_path)
    if not path.exists():
        return False

    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('\'"')
                    os.environ.setdefault(key, val)
        return True
    except Exception:
        return False

# Carrega as variáveis de ambiente (.env)
# Isto é crucial porque este script corre num processo separado
# e também precisa de acesso à API_KEY, senhas de e-mail, etc.
load_dotenv()

print("Módulo de Scheduler importado. As variáveis de ambiente foram carregadas.")

def check_timeouts():
    """
    Função principal do job.
    1. Busca NFs com status 'PENDING_VALIDATION'.
    2. Compara o 'timestamp_envio' com o tempo atual.
    3. Se > 48 horas, atualiza o status para 'TIMEOUT' e notifica o financeiro.
    """
    
    agora = datetime.now()
    print(f"\n[{agora.strftime('%Y-%m-%d %H:%M:%S')}] Executando verificação de timeouts...")
    
    try:
        pending_nfs = db_manager.get_pending_validations()
        
        if not pending_nfs:
            print("Nenhuma NF pendente de validação encontrada.")
            return

        print(f"Encontradas {len(pending_nfs)} NFs pendentes. A analisar...")
        
        # Define o limite de tempo
        limite_de_tempo = agora - timedelta(hours=48)
        
        for nf in pending_nfs:
            # O timestamp_envio vem do DB como uma string.
            # Precisamos convertê-lo de volta para um objeto datetime.
            try:
                # Tenta analisar o formato com microsegundos
                timestamp_envio = datetime.strptime(nf['timestamp_envio'], '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                # Se falhar, tenta analisar o formato sem microsegundos
                try:
                    timestamp_envio = datetime.strptime(nf['timestamp_envio'], '%Y-%m-%d %H:%M:%S')
                except ValueError as e:
                    print(f"  -> ERRO: Formato de data inválido '{nf['timestamp_envio']}' para o token {nf['validation_token']}. Ignorando. Erro: {e}")
                    continue # Pula para a próxima NF na lista

            # Compara o timestamp de envio com o limite de 48h atrás
            if timestamp_envio < limite_de_tempo:
                print(f"  -> TIMEOUT: A NF {nf['numero_nf']} (Token: {nf['validation_token']}) expirou.")
                
                # Passo 1: Atualizar o status no DB para 'TIMEOUT'
                # A função update_processing_status_by_token já verifica
                # se o status ainda é 'PENDING_VALIDATION', evitando
                # que um status 'APPROVED' seja sobrescrito.
                updated = db_manager.update_processing_status_by_token(nf['validation_token'], 'TIMEOUT')
                
                if updated:
                    # Passo 2: Notificar o setor financeiro
                    print(f"  -> Status atualizado. A notificar o financeiro...")
                    
                    # Busca todos os dados necessários para o e-mail
                    data_for_email = db_manager.get_data_for_finance_email(nf['validation_token'])
                    
                    if data_for_email:
                        email_manager.send_finance_email(
                            nf_data=data_for_email,
                            pedido_data=data_for_email,
                            status='TIMEOUT'
                        )
                        print(f"  -> E-mail de TIMEOUT para a NF {nf['numero_nf']} enviado.")
                    else:
                        print(f"  -> ERRO CRÍTICO: Não foi possível obter dados para o e-mail (Token: {nf['validation_token']})")
                
                else:
                    # Isto pode acontecer se o utilizador aprovou/rejeitou
                    # exatamente ao mesmo tempo que o scheduler estava a correr.
                    print(f"  -> A NF {nf['numero_nf']} já foi processada (provavelmente aprovada/rejeitada). Nenhuma ação de timeout tomada.")
            
            else:
                # Ainda dentro do prazo
                tempo_restante = (timestamp_envio + timedelta(hours=48)) - agora
                horas_restantes = tempo_restante.total_seconds() / 3600
                print(f"  -> OK: A NF {nf['numero_nf']} ainda está dentro do prazo (restam {horas_restantes:.2f} horas).")

    except Exception as e:
        print(f"ERRO CRÍTICO na execução do 'check_timeouts': {e}")
        # O scheduler continuará a tentar na próxima execução

if __name__ == "__main__":
    # --- Configuração do Scheduler ---
    
    # Usamos BlockingScheduler porque este script não faz
    # mais nada a não ser executar tarefas agendadas.
    scheduler = BlockingScheduler(timezone="America/Sao_Paulo") # Use o seu fuso horário

    # Adiciona a tarefa (job) para executar a função 'check_timeouts'
    # a cada 1 hora. (Pode ajustar para 'minutes=30', etc.)
    scheduler.add_job(check_timeouts, 'interval', hours=1)
    
    print("--- Agente de Scheduler de Timeouts ---")
    print("Este processo verifica o banco de dados por NFs expiradas.")
    print("A executar a primeira verificação imediatamente ao iniciar...")
    
    # Executa uma vez imediatamente ao iniciar o script
    check_timeouts() 
    
    print(f"Primeira verificação concluída. A aguardar o próximo ciclo (a cada 1 hora).")
    print("Mantenha este terminal em execução. Pressione Ctrl+C para sair.")

    try:
        # Inicia o loop de agendamento
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler interrompido pelo utilizador.")
        scheduler.shutdown()

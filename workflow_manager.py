import uuid
import io

# Importa os módulos que criamos
import pdf_processor
import db_manager
import email_manager

def handle_uploaded_invoice(pdf_file: io.BytesIO) -> str:
    """
    Orquestra o fluxo de trabalho completo para um novo upload de NF.

    1. Extrai texto do PDF.
    2. Envia texto para o Gemini para extrair dados.
    3. Valida se o 'numero_pedido' foi encontrado.
    4. Consulta o 'numero_pedido' no banco de dados.
    5. Valida se o pedido existe.
    6. Gera um token de validação.
    7. Salva o estado 'PENDING_VALIDATION' no banco.
    8. Envia o e-mail de validação para o solicitante.

    Retorna uma string de status para a UI do Streamlit.
    """
    
    try:
        print("Iniciando processamento da NF...")
        
        # Passo 1: Extrair texto do PDF
        # O objeto do Streamlit (pdf_file) tem o método .read() que retorna bytes
        pdf_bytes = pdf_file.read()
        print("Extraindo texto do PDF...")
        pdf_text = pdf_processor.extract_text_from_pdf(pdf_bytes)
        
        if not pdf_text:
            return "Erro: O PDF parece estar vazio ou não contém texto legível."

        # Passo 2: Enviar texto para o Gemini (IA)
        print("Enviando texto para a IA (Gemini)...")
        nf_data = pdf_processor.get_invoice_data_with_gemini(pdf_text)
        print(f"IA retornou: {nf_data}")

        # Passo 3: Validar 'numero_pedido' da IA
        numero_pedido_extraido = nf_data.get('numero_pedido')
        if not numero_pedido_extraido:
            return "Erro: O Agente de IA não conseguiu encontrar um 'número do pedido' no campo de descrição da Nota Fiscal."

        # Passo 4: Consultar pedido no banco de dados
        print(f"Consultando Pedido '{numero_pedido_extraido}' no banco de dados...")
        pedido_data = db_manager.get_order_details_by_number(numero_pedido_extraido)

        # Passo 5: Validar se o pedido existe
        if not pedido_data:
            return f"Erro: O Pedido '{numero_pedido_extraido}' foi encontrado na NF, mas não existe em nosso banco de dados 'Controle de Pedidos'."

        # Passo 6: Gerar token de validação único
        token = str(uuid.uuid4())
        print(f"Gerado token de validação: {token}")

        # Passo 7: Salvar o estado 'PENDING_VALIDATION' no banco
        # (pedido_data é um sqlite3.Row, acessamos o 'pedido_id' por chave)
        db_manager.create_processing_entry(nf_data, pedido_data['pedido_id'], token)

        # Passo 8: Enviar e-mail de validação para o solicitante
        print(f"Enviando e-mail de validação para {pedido_data['solicitante_email']}...")
        email_manager.send_validation_email(
            solicitante_email=pedido_data['solicitante_email'],
            solicitante_nome=pedido_data['solicitante_nome'],
            nf_data=nf_data,
            pedido_data=pedido_data,
            validation_token=token
        )
        
        # Sucesso!
        return f"Sucesso! NF {nf_data.get('numero_nf')} processada. Um e-mail de validação foi enviado para {pedido_data['solicitante_nome']}."

    except Exception as e:
        # Captura qualquer erro inesperado (ex: falha na API, falha no DB)
        print(f"ERRO GERAL NO FLUXO: {e}")
        return f"Ocorreu um erro inesperado: {e}"

def handle_validation_response(token: str, action: str) -> str:
    """
    Orquestra o fluxo de resposta de uma validação (clique no e-mail).

    1. Determina o novo status ('APPROVED' ou 'REJECTED').
    2. Tenta atualizar o status no banco de dados (só funciona se estiver 'PENDING').
    3. Se a atualização falhar, informa que o link é inválido/expirado.
    4. Se for bem-sucedido, busca todos os dados da NF e do Pedido.
    5. Envia o e-mail de status final para o setor financeiro.

    Retorna uma string de status para a UI do Streamlit.
    """
    
    try:
        print(f"Processando resposta: token={token}, action={action}")
        
        # Passo 1: Determinar novo status
        if action not in ['approve', 'reject']:
            return "Ação desconhecida."
            
        new_status = 'APPROVED' if action == 'approve' else 'REJECTED'

        # Passo 2: Tentar atualizar o status no banco
        # Esta função (update_processing_status_by_token) só deve atualizar
        # se o status atual for 'PENDING_VALIDATION'.
        print(f"Atualizando status para {new_status} para o token {token}...")
        update_success = db_manager.update_processing_status_by_token(token, new_status)

        # Passo 3: Lidar com token inválido ou já processado
        if not update_success:
            print("Atualização falhou. Token inválido, expirado ou já utilizado.")
            return "Este link de validação é inválido ou já foi processado."

        # Passo 4: Buscar todos os dados para o e-mail do financeiro
        print("Coletando dados para enviar ao financeiro...")
        # Esta função (get_data_for_finance_email) retorna um único
        # objeto sqlite3.Row com todos os dados da NF e do Pedido.
        data_for_email = db_manager.get_data_for_finance_email(token)
        
        if not data_for_email:
             # Isso não deve acontecer se o passo 2 foi bem-sucedido, mas é uma boa checagem.
             print(f"ERRO CRÍTICO: Status atualizado, mas dados não encontrados para o token {token}")
             return "Erro ao buscar dados. Contate o administrador."

        # Passo 5: Enviar e-mail de status final para o financeiro
        print(f"Enviando e-mail para o setor financeiro com status: {new_status}")
        
        # O `email_manager.send_finance_email` espera `nf_data` e `pedido_data`.
        # Como `data_for_email` (um sqlite3.Row) contém todas as chaves
        # de ambos (ex: 'numero_nf', 'numero_pedido', etc.), podemos
        # passar o mesmo objeto para ambos os argumentos.
        email_manager.send_finance_email(
            nf_data=data_for_email, 
            pedido_data=data_for_email, 
            status=new_status
        )
        
        # Sucesso!
        if new_status == 'APPROVED':
            return "Obrigado! O pagamento foi APROVADO e o financeiro foi notificado."
        else:
            return "Confirmação recebida. O pagamento foi REJEITADO e o financeiro foi notificado."

    except Exception as e:
        # Captura qualquer erro inesperado (ex: falha no envio de e-mail)
        print(f"ERRO GERAL NA RESPOSTA: {e}")
        return f"Ocorreu um erro inesperado ao processar sua resposta: {e}"
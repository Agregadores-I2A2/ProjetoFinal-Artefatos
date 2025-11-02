import smtplib
import ssl
import os
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from typing import Any # Para tipar os objetos 'sqlite3.Row' que agem como dicionários

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações de E-mail (puxadas do .env) ---
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT_STR = os.getenv("EMAIL_PORT", "587")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") 
FINANCE_EMAIL = os.getenv("FINANCE_EMAIL")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8501") 

# Validação melhorada
if not all([EMAIL_HOST, EMAIL_PORT_STR, EMAIL_USER, EMAIL_PASSWORD, FINANCE_EMAIL]):
    print("ERRO CRÍTICO: Variáveis de ambiente de e-mail (EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, FINANCE_EMAIL) não estão configuradas no arquivo .env")
else:
    print("Configurações de e-mail carregadas do .env.")
    print(f"HOST: {EMAIL_HOST}, PORT: {EMAIL_PORT_STR}, USER: {EMAIL_USER}")


def _format_currency(value: Any) -> str:
    """Helper para formatar valores numéricos como moeda brasileira."""
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(value)

def _send_email(to_email: str, subject: str, html_content: str, attachments: list = None):
    """
    Função interna para lidar com a conexão SMTP e envio de e-mail.
    (Versão com logging de debug detalhado e suporte a anexos)
    """
    
    # Valida se a porta é um número
    try:
        EMAIL_PORT = int(EMAIL_PORT_STR)
    except ValueError:
        print(f"ERRO: EMAIL_PORT ('{EMAIL_PORT_STR}') no .env não é um número válido.")
        raise
        
    # Cria o objeto de e-mail
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg.set_content("Seu cliente de e-mail não suporta HTML.")
    msg.add_alternative(html_content, subtype="html")
    
    # Adiciona anexos, se houver
    if attachments:
        for attachment_data, attachment_filename, attachment_mimetype in attachments:
            part = MIMEBase(attachment_mimetype.split('/')[0], attachment_mimetype.split('/')[1])
            part.set_payload(attachment_data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{attachment_filename}"')
            msg.attach(part)
    
    # Cria contexto SSL seguro
    context = ssl.create_default_context()
    
    print(f"--- [DEBUG E-MAIL] ---")
    print(f"Tentando enviar e-mail para: {to_email}")
    print(f"Servidor: {EMAIL_HOST}:{EMAIL_PORT}")
    
    try:
        print(f"[DEBUG E-MAIL] Conectando ao servidor SMTP...")
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            print(f"[DEBUG E-MAIL] Conexão estabelecida.")
            
            print(f"[DEBUG E-MAIL] Iniciando STARTTLS...")
            server.starttls(context=context)  # Inicia conexão segura
            print(f"[DEBUG E-MAIL] STARTTLS bem-sucedido.")
            
            print(f"[DEBUG E-MAIL] Fazendo login como {EMAIL_USER}...")
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            print(f"[DEBUG E-MAIL] Login bem-sucedido.")
            
            print(f"[DEBUG E-MAIL] Enviando mensagem...")
            server.send_message(msg)
            
        print(f"[DEBUG E-MAIL] E-mail enviado com sucesso para {to_email}.")
        print(f"----------------------")
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"[DEBUG E-MAIL] FALHA DE AUTENTICAÇÃO: {e}")
        print("[DEBUG E-MAIL] CAUSA PROVÁVEL: Verifique EMAIL_USER e EMAIL_PASSWORD no .env. Lembre-se de usar a 'Senha de App' do Gmail SEM ESPAÇOS.")
        raise ConnectionError(f"Falha de Autenticação (Login/Senha): {e}")
    except smtplib.SMTPException as e:
        print(f"[DEBUG E-MAIL] FALHA DE SMTP: {e}")
        raise ConnectionError(f"Falha de SMTP: {e}")
    except ConnectionRefusedError as e:
        print(f"[DEBUG E-MAIL] FALHA DE CONEXÃO: {e}")
        print("[DEBUG E-MAIL] CAUSA PROVÁVEL: O firewall ou antivírus pode estar bloqueando a porta {EMAIL_PORT}.")
        raise ConnectionError(f"Falha de Conexão: {e}")
    except Exception as e:
        print(f"[DEBUG E-MAIL] FALHA INESPERADA AO ENVIAR E-MAIL para {to_email}: {e}")
        raise ConnectionError(f"Falha ao enviar e-mail: {e}")


def send_validation_email(solicitante_email: str, solicitante_nome: str, nf_data: Any, pedido_data: Any, validation_token: str):
    """
    Envia o e-mail de validação para o solicitante com os links de aprovação/rejeição.
    """
    subject = f"Ação Necessária: Validar NF {nf_data['numero_nf']} (Pedido {pedido_data['numero_pedido']})"
    
    link_approve = f"{APP_BASE_URL}/?action=approve&token={validation_token}"
    link_reject = f"{APP_BASE_URL}/?action=reject&token={validation_token}"

    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .container {{ width: 90%; max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            h2 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f4f4f4; }}
            .actions {{ margin-top: 30px; text-align: center; padding-top: 20px; padding-bottom: 20px; }} /* Espaçamento ajustado aqui */
            .button {{ text-decoration: none; padding: 12px 25px; border-radius: 5px; font-weight: bold; font-size: 16px; }}
            .approve {{ background-color: #28a745; color: white; }}
            .reject {{ background-color: #dc3545; color: white; margin-left: 15px; }}
            .footer {{ margin-top: 40px; font-size: 12px; color: #888; border-top: 1px solid #eee; padding-top: 15px; }} /* Espaçamento ajustado aqui */
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Validação de Nota Fiscal</h2>
            <p>Olá, {solicitante_nome},</p>
            <p>Uma Nota Fiscal foi recebida e associada a um pedido em seu nome. Por favor, revise os dados abaixo e confirme se as informações do pedido estão corretas para que o pagamento seja processado.</p>
            
            <h3>Detalhes da Nota Fiscal (Extraídos pela IA)</h3>
            <table>
                <tr><th>Número NF</th><td>{nf_data['numero_nf']}</td></tr>
                <tr><th>Fornecedor</th><td>{nf_data['fornecedor_nf']}</td></tr>
                <tr><th>Data</th><td>{nf_data['data_nf']}</td></tr>
                <tr><th>Valor NF</th><td>{_format_currency(nf_data['valor_nf'])}</td></tr>
            </table>
            
            <h3>Detalhes do Pedido (do Banco de Dados)</h3>
            <table>
                <tr><th>Número Pedido</th><td>{pedido_data['numero_pedido']}</td></tr>
                <tr><th>Valor do Pedido</th><td>{_format_currency(pedido_data['valor_pedido'])}</td></tr>
                <tr><th>Centro de Custos</th><td>{pedido_data['centro_de_custos']}</td></tr>
            </table>
            
            <div class="actions">
                <p style="font-weight: bold; margin-bottom: 20px;">As informações do pedido acima estão corretas?</p> <!-- Espaço extra aqui --><a href="{link_approve}" class="button approve" style="background-color: #28a745; color: white; text-decoration: none; padding: 12px 25px; border-radius: 5px; font-weight: bold; font-size: 16px;">SIM, APROVAR</a>
                <a href="{link_reject}" class="button reject" style="background-color: #dc3545; color: white; text-decoration: none; padding: 12px 25px; border-radius: 5px; font-weight: bold; font-size: 16px; margin-left: 15px;">NÃO, REJEITAR</a>
            </div>
            
            <div class="footer">
                <p>Se nenhuma ação for tomada em 48 horas, o pagamento será automaticamente retido por segurança.</p>
                <p>Esta é uma mensagem automática. Por favor, não responda diretamente a este e-mail.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    _send_email(solicitante_email, subject, html_body)


def send_finance_email(nf_data: Any, pedido_data: Any, status: str, pdf_attachment_data: bytes = None):
    """
    Envia o e-mail de status final para o setor financeiro.
    Inclui anexo do PDF se o status for 'APPROVED'.
    """
    
    subject_prefix = ""
    action_message = ""
    attachments_list = [] # Lista para armazenar informações de anexos

    if status == 'APPROVED':
        subject_prefix = "[APROVADO]"
        action_message = f"<p style='color: green; font-weight: bold; font-size: 18px;'>Ação: Realizar o pagamento.</p><p>Validado por: {pedido_data['solicitante_nome']}.</p><p>A Nota Fiscal original está anexada para sua referência.</p>"
        
        # Adiciona o anexo apenas se o status for APPROVED
        if pdf_attachment_data:
            filename = f"NF_{nf_data.get('numero_nf', 'SemNumero')}.pdf"
            attachments_list.append((pdf_attachment_data, filename, "application/pdf"))

    elif status == 'REJECTED':
        subject_prefix = "[REJEITADO]"
        action_message = f"<p style='color: red; font-weight: bold; font-size: 18px;'>Ação: NÃO realizar o pagamento.</p><p>Rejeitado por: {pedido_data['solicitante_nome']}. Favor entrar em contato.</p>"
    elif status == 'TIMEOUT':
        subject_prefix = "[TIMEOUT]"
        action_message = f"<p style='color: #E9A11A; font-weight: bold; font-size: 18px;'>Ação: Pagamento suspenso.</p><p>O solicitante ({pedido_data['solicitante_nome']}) não respondeu à validação em 48 horas.</p>"
    else:
        print(f"Status desconhecido '{status}' em send_finance_email. E-mail não enviado.")
        return

    subject = f"{subject_prefix} Pagamento NF {nf_data['numero_nf']} / Pedido {pedido_data['numero_pedido']}"
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>Notificação de Status de Pagamento</h2>
        {action_message}
        <hr style="margin-top: 25px; margin-bottom: 25px;"> <!-- Espaço maior aqui --><h3>Detalhes da Nota Fiscal</h3>
        <ul>
            <li><strong>Número NF:</strong> {nf_data['numero_nf']}</li>
            <li><strong>Fornecedor:</strong> {nf_data['fornecedor_nf']}</li>
            <li><strong>Data:</strong> {nf_data['data_nf']}</li>
            <li><strong>Valor NF:</strong> {_format_currency(nf_data['valor_nf'])}</li>
        </ul>
        
        <h3>Detalhes do Pedido</h3>
        <ul>
            <li><strong>Número Pedido:</strong> {pedido_data['numero_pedido']}</li>
            <li><strong>Solicitante:</strong> {pedido_data['solicitante_nome']}</li>
            <li><strong>Centro de Custos:</strong> {pedido_data['centro_de_custos']}</li>
            <li><strong>Valor do Pedido:</strong> {_format_currency(pedido_data['valor_pedido'])}</li>
        </ul>
        <p style="margin-top: 30px; font-size: 12px; color: #888;">Esta é uma mensagem automática.</p>
    </body>
    </html>
    """
    
    _send_email(FINANCE_EMAIL, subject, html_body, attachments=attachments_list)
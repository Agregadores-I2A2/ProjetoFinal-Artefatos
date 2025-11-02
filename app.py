import streamlit as st
import workflow_manager  # O orquestrador central
import time

# --- Configuração da Página ---
# Deve ser o primeiro comando Streamlit
st.set_page_config(
    page_title="Agente de Análise de NF",
    page_icon="🤖",
    layout="centered"
)

# --- 1. Lógica de Captura de Resposta (Webhook de E-mail) ---
# O Streamlit permite ler parâmetros da URL.
# Verificamos se a URL é uma resposta de um dos e-mails de validação.
query_params = st.query_params

if "token" in query_params and "action" in query_params:
    
    token = query_params.get("token")
    action = query_params.get("action")
    
    # Exibe uma mensagem de processamento enquanto o backend trabalha
    with st.spinner("Processando sua resposta..."):
        try:
            # Chama o orquestrador para lidar com a aprovação/rejeição
            mensagem_resposta = workflow_manager.handle_validation_response(token, action)
            
            # Exibe o resultado para o usuário
            if "APROVADO" in mensagem_resposta or "Obrigado!" in mensagem_resposta:
                st.success(mensagem_resposta)
                st.balloons()
            elif "REJEITADO" in mensagem_resposta:
                st.warning(mensagem_resposta)
            else:
                # Caso o link já tenha sido usado ou expirado
                st.error(mensagem_resposta)
                
            st.info("Pode fechar esta janela.")

        except Exception as e:
            st.error(f"Ocorreu um erro inesperado ao processar a sua resposta: {e}")

    # --- PÁRA A EXECUÇÃO AQUI ---
    # Impede que a UI de upload seja renderizada,
    # mostrando apenas a página de resposta ao usuário.
    st.stop()


# --- 2. Interface Principal de Upload ---
# Este código só é executado se NÃO houver parâmetros "token" e "action" na URL.

st.title("🤖 Agente de Análise de Notas Fiscais")
st.markdown("""
**Bem-vindo(a)!** 

Este agente utiliza IA para automatizar o fluxo de pagamento de Notas Fiscais.

**Instruções:**
1.  Faça o **upload** da Nota Fiscal em PDF.
2.  O agente irá **ler** a NF e encontrar o **número do pedido** na descrição.
3.  Ele irá **consultar** esse pedido no banco de dados local.
4.  Um **e-mail de validação** será enviado ao solicitante do pedido.
""")

# --- Área de Upload ---
uploaded_file = st.file_uploader(
    "Carregue a Nota Fiscal (formato PDF)", 
    type=["pdf"]
)

# --- Botão de Ação ---
# Possibilita iniciar o fluxo de análise e processamento de NF.
if st.button("Executar Análise e Iniciar Fluxo"):
    
    if uploaded_file is not None:
        # Mostra um spinner com mensagens de status
        with st.spinner("O agente está trabalhando..."):
            try:
                # Simula um pouco de trabalho para o spinner ser visível
                time.sleep(1)
                st.write("Lendo o PDF...")
                time.sleep(2)
                st.write("Analisando com IA ...")
                # Chama a função principal do orquestrador
                # Passa o objeto de arquivo (BytesIO) diretamente
                result_message = workflow_manager.handle_uploaded_invoice(uploaded_file)
                # Exibe o resultado final
                if "Sucesso!" in result_message:
                    st.success(result_message)
                else:
                    # Exibe erros de negócio (ex: "Pedido não encontrado")
                    st.error(result_message)
                    
            except Exception as e:
                # Exibe erros inesperados (ex: API offline, E-mail falhou)
                st.exception(f"Ocorreu um erro crítico no sistema: {e}")
                
    else:
        # Se o usuário clicar no botão sem carregar um arquivo
        st.warning("Por favor, carregue um arquivo PDF primeiro.")
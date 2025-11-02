import fitz  # PyMuPDF
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (GEMINI_API_KEY) do arquivo .env
load_dotenv()

# Configura a API do Gemini
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi definida.")
    genai.configure(api_key=api_key)
except ValueError as e:
    print(e)
    # Em um app real, você pode querer lançar uma exceção ou st.error()
    # Aqui, vamos apenas imprimir para fins de depuração.


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extrai todo o texto de um arquivo PDF fornecido como bytes.

    Args:
        pdf_bytes: O conteúdo do arquivo PDF em bytes.

    Returns:
        Uma string contendo todo o texto extraído do PDF.
    """
    full_text = ""
    try:
        # Abre o PDF a partir dos bytes em memória
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            # Itera por todas as páginas do documento
            for page in doc:
                full_text += page.get_text()
        return full_text
    except Exception as e:
        print(f"Erro ao extrair texto do PDF: {e}")
        # Retorna o que foi possível extrair, ou uma string vazia
        return full_text 

def get_invoice_data_with_gemini(pdf_text: str) -> dict:
    """
    Envia o texto extraído do PDF para o Gemini e solicita a extração
    de dados estruturados em formato JSON.

    Args:
        pdf_text: A string de texto completa extraída do PDF.

    Returns:
        Um dicionário Python com os dados extraídos.
    """
    
    # Modelo do Gemini. 'gemini-1.5-flash-latest' é rápido e eficaz para extração.
    model = genai.GenerativeModel('gemini-2.5-pro')

    # --- Engenharia de Prompt Crítica ---
    # Este prompt instrui o modelo a agir como um especialista,
    # define os campos exatos e, o mais importante, restringe
    # a busca do 'numero_pedido' ao campo 'descrição', como no desafio.
    prompt = f"""
    Você é um assistente de contas a pagar especialista em ler notas fiscais brasileiras.
    Analise o texto da nota fiscal a seguir e extraia as seguintes informações no formato JSON.
    O JSON deve ter EXATAMENTE as seguintes chaves:

    1. "numero_nf": O número da Nota Fiscal (ex: "12345").
    2. "data_nf": A data de emissão da nota (ex: "DD/MM/AAAA").
    3. "fornecedor_nf": O nome ou Razão Social do fornecedor/emitente.
    4. "valor_nf": O valor total da nota (ex: 1500.50). Use ponto como separador decimal.
    5. "numero_pedido": O número do pedido. Este número deve ser encontrado *especificamente* dentro do campo "descrição dos serviços", "dados adicionais" ou "informações complementares".
       Pode ter prefixos como 'PED-', 'Pedido n°', 'OC', etc. 
       Se não for encontrado NENHUM número de pedido nesses campos, retorne null para esta chave.

    Texto extraído do PDF:
    ---
    {pdf_text[:8000]} 
    ---

    Responda APENAS com o objeto JSON, sem nenhum texto adicional ou markdown (como ```json ... ```).
    """
    # Nota: {pdf_text[:8000]} limita o tamanho do prompt para evitar limites de token.
    # Ajuste se suas NFs forem muito longas.

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # --- Limpeza da Resposta ---
        # Às vezes, o modelo pode "escapar" e adicionar markdown
        # Este bloco remove o markdown '```json ... ```' se ele existir.
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```"):
             response_text = response_text[3:-3].strip()
            
        # Converte a string JSON em um dicionário Python
        data = json.loads(response_text)
        return data

    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON da resposta do Gemini: {e}")
        print(f"Resposta recebida: {response_text}")
        raise ValueError("O modelo de IA não retornou um JSON válido.")
    except Exception as e:
        print(f"Erro ao chamar a API do Gemini: {e}")
        raise

# --- Bloco de Teste ---
# Isso permite que você teste este arquivo de forma independente
if __name__ == "__main__":
    print("Testando o processador de PDF...")

    # Simule um texto de PDF (substitua por um texto real de NF para um bom teste)
    simulated_pdf_text = """
    NOTA FISCAL DE SERVIÇOS ELETRÔNICA
    Fornecedor: SOLUÇÕES EM TI LTDA
    Data de Emissão: 25/10/2025
    Número da NF: 88765
    
    Descrição dos Serviços:
    - Manutenção de servidores conforme Pedido n° PED-1001-XYZ.
    - Suporte técnico especializado.
    
    VALOR TOTAL DA NOTA: R$ 1.500,50
    """
    
    print("--- Teste do Gemini ---")
    try:
        extracted_data = get_invoice_data_with_gemini(simulated_pdf_text)
        print("Dados extraídos com sucesso:")
        print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
        
        # Teste de verificação
        # Verifica que o número da nota foi extraído corretamente a partir do texto simulado acima
        assert extracted_data.get('numero_nf') == "88765"
        # Verifica que a chave numero_pedido está presente (pode ser None se não encontrada)
        assert 'numero_pedido' in extracted_data
        print("Asserções de teste passaram.")
    except AssertionError as e:
        print("Falha no teste de verificação:", e)
    except Exception as e:
        print("Erro durante o teste:", e)
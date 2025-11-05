import os
from typing import Optional
from openai import OpenAI, APIStatusError, AuthenticationError, RateLimitError
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Variável para armazenar a chave da API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def consultar_chatgpt(prompt: str) -> str:
    """
    Faz uma consulta na API do ChatGPT e retorna a resposta como string.
    
    Args:
        prompt (str): O texto/pergunta a ser enviado para o ChatGPT
        model (str): O modelo a ser usado (padrão: gpt-4o-mini)
        temperature (float): Controla a criatividade (0-2, padrão: 0.2)
        max_tokens (int): Número máximo de tokens na resposta (opcional)
    
    Returns:
        str: A resposta do ChatGPT como string
    
    Raises:
        Exception: Se houver erro na chamada da API
    """

    model = "gpt-4o-mini"
    temperature = 0.2
    max_tokens = None

    prompf_final = f"""
    Os dados a seguir são registros de uma base com informações de grupos de ofertas.
    Classifique os conteúdos em uma das seguintes categorias:

    Eletrodomésticos
    Móveis e Decoração
    Utilidades Domésticas
    Construção e Ferramentas
    Celulares e Smartphones
    Informática
    TV, Áudio e Vídeo
    Games e Consoles
    Moda e Vestuário
    Beleza e Perfumaria
    Relógios e Joias
    Bebês e Maternidade
    Saúde e Cuidados Pessoais
    Pet Shop
    Esporte e Fitness
    Brinquedos e Hobbies
    Viagem e Camping
    Alimentos e Bebidas
    Limpeza e Higiene
    Automotivo

    Analise o seguinte texto: "{prompt}"

    Retorne apenas a categoria correspondente.

    """

    try:
        # Configura a chave da API
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Faz a chamada para a API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompf_final}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Extrai e retorna apenas o texto da resposta
        resposta = response.choices[0].message.content.strip()
        return resposta
        
    except AuthenticationError as e:
        return f"Erro: Chave da API inválida. Detalhes: {str(e)}"
    except RateLimitError as e:
        return f"Erro: Limite de requisições/quota excedida. Verifique seu billing na OpenAI. Detalhes: {str(e)}"
    except APIStatusError as e:
        return f"Erro na API da OpenAI (Status: {e.status_code}): {e.message}"
    except Exception as e:
        return f"Erro inesperado ({type(e).__name__}): {str(e)}"


# Exemplo de uso
if __name__ == "__main__":
    # Campo editável para o prompt
    meu_prompt = "Explique o que é inteligência artificial em poucas palavras"
    
    # Faz a consulta
    resultado = consultar_chatgpt(meu_prompt)
    
    # Exibe o resultado
    print("Resposta do ChatGPT:")
    print(resultado)

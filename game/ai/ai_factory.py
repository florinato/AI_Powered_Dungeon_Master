# ai_factory.py
import os

from game.ai.ai_provider_interface import AIProviderInterface
from dotenv import load_dotenv

# Cargamos las variables del archivo .env al entorno del sistema al iniciar el módulo.
# Solo necesita hacerse una vez.
load_dotenv()

def get_ai_provider() -> AIProviderInterface:
    """
    Fábrica que lee la configuración del entorno y devuelve una instancia
    del proveedor de IA correspondiente.
    """
    # 1. Leemos la variable de entorno usando os.getenv.
    #    Podemos darle un valor por defecto ('gemini') si no está definida.
    provider_name = os.getenv("AI_PROVIDER", "gemini").lower()
    
    print(f"  -> AI Factory: Se ha seleccionado el proveedor '{provider_name}'.")

    # 2. Comparamos el nombre y devolvemos una INSTANCIA de la clase correcta.
    if provider_name == "gemini":
        from game.ai.gemini_provider import GeminiProvider
        return GeminiProvider()  # <-- Creamos y devolvemos la instancia
        
    # elif provider_name == "openai":
    #     # Aquí iría la lógica si en el futuro añades un proveedor de OpenAI
    #     from openai_provider import OpenAIProvider
    #     return OpenAIProvider()
        
    else:
        # Si la configuración es inválida, lanzamos un error claro.
        raise ValueError(f"Proveedor de IA desconocido: '{provider_name}'. Comprueba tu archivo .env.")
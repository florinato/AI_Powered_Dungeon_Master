# gemini_provider.py
import json
import os
import re
import time

import google.generativeai as genai
from dotenv import load_dotenv

from game.ai.ai_provider_interface import AIProviderInterface

load_dotenv()

class GeminiProvider(AIProviderInterface):

    def __init__(self, api_key: str = None, model_name: str = 'gemini-2.0-flash-lite-preview-02-05'):
        """
        Inicializa el proveedor Gemini. Si no se proporciona api_key, intentará usar la de las variables de entorno.
        """
        self.api_key = api_key if api_key else os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is required for GeminiProvider.")
        
        super().__init__(self.api_key, model_name)
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Genera texto usando el modelo Gemini.
        """
        try:
            # Nota: Los parámetros max_tokens y temperature pueden ser más avanzados
            # con el API de Gemini, pero para simplicidad, usamos los defaults o los pasamos.
            # Una implementación más robusta podría manejar los GenerationConfig.
            response = self.model.generate_content(prompt)
            return response.text.strip() if response.text else ""
        except Exception as e:
            print(f"Error during Gemini text generation: {e}")
            return "Error: Could not generate response from Gemini."

    def generate_json(self, prompt: str, max_tokens: int = 4000, temperature: float = 0.5) -> dict:
        """
        Genera texto con Gemini, extrae un objeto JSON, y reintenta con
        autocorrección si el parseo falla.
        """
        for attempt in range(3): # Intentaremos hasta 3 veces
            try:
                print(f"    -> Gemini JSON generation (Attempt {attempt + 1}/3)...")
                response_text = self.generate_text(prompt, max_tokens, temperature)
                
                match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if match:
                    json_str = match.group(1)
                else:
                    start = response_text.find('{')
                    end = response_text.rfind('}')
                    if start != -1 and end != -1 and start < end:
                        json_str = response_text[start:end+1]
                    else:
                        raise ValueError("No JSON object found in the response.")
                
                # Intentamos parsear el JSON. Si falla, saltará al 'except'.
                return json.loads(json_str)

            except (json.JSONDecodeError, ValueError) as e:
                print(f"      -> Attempt {attempt + 1} failed to parse JSON: {e}")
                if attempt < 2: # Si no es el último intento
                    print("      -> Asking AI to self-correct...")
                    # Creamos un nuevo prompt pidiendo a la IA que arregle su propio desastre
                    prompt = (
                        "The following text was supposed to be a valid JSON object, but it failed to parse. "
                        f"The error was: {e}\n\n"
                        "Please correct the formatting and provide ONLY the valid JSON object. Do not add any commentary or explanations. Just the corrected JSON.\n\n"
                        f"Here is the faulty text:\n```\n{response_text}\n```"
                    )
                    time.sleep(2) # Pausa antes de reintentar
                else:
                    print("      -> Max retry attempts reached. Could not get valid JSON.")
                    # Devolvemos el error después del último intento
                    return {"error": f"Failed to parse JSON after multiple attempts: {e}", "raw_response": response_text}
        return {"error": "JSON generation loop failed unexpectedly."} # Fallback por si algo sale muy mal
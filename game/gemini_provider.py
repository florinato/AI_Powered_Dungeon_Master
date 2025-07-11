# gemini_provider.py
import json
import os
import re

import google.generativeai as genai
from ai_provider_interface import AIProviderInterface
from dotenv import load_dotenv

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

    def generate_json(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.5) -> dict:
        """
        Genera texto con Gemini y extrae un objeto JSON de la respuesta.
        """
        try:
            # Es crucial que el prompt indique claramente que se debe devolver JSON,
            # idealmente dentro de bloques ```json...```
            response_text = self.generate_text(prompt, max_tokens, temperature)
            
            # Intenta extraer el JSON de bloques de código
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Si no encuentra bloque de código, intenta buscar el primer { y el último }
                start = response_text.find('{')
                end = response_text.rfind('}')
                if start != -1 and end != -1 and start < end:
                    json_str = response_text[start:end+1]
                else:
                    raise ValueError("No JSON object found in the response.")
            
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing JSON from Gemini response: {e}")
            # Devuelve un diccionario de error para indicar el fallo
            return {"error": f"Failed to parse JSON: {e}", "raw_response": response_text}
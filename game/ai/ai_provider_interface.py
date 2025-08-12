# game/ai/ai_provider_interface.py
"""
AI Provider Interface - Abstract base class for AI language model providers.
"""
from abc import ABC, abstractmethod
from typing import Optional


class AIProviderInterface(ABC):
    """
    Define la interfaz común para cualquier proveedor de modelos de lenguaje (LLM).
    El resto de la aplicación interactuará con los proveedores a través de esta interfaz.
    """

    def __init__(self, api_key: str, model_name: Optional[str] = None):
        """
        Inicializa el proveedor con la clave de API y un nombre de modelo opcional.
        """
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Genera una respuesta de texto a partir de un prompt.
        Esta es la función principal que todos los proveedores deben implementar.
        """

    @abstractmethod
    def generate_json(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.5) -> dict:
        """
        Genera una respuesta y se asegura de que sea un JSON válido.
        Útil para generar game_state, objetos, etc.
        """

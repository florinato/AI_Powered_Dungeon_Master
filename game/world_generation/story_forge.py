# game/story_forge.py

import os
import time

import yaml
from game.ai.ai_factory import get_ai_provider


class StoryForge:
    """
    Un agente interactivo que colabora con el usuario y una IA
    para desarrollar un argumento literario a través de un ciclo de
    creación, crítica y revisión.
    """
    def __init__(self, manifest_path: str):
        print("--- Iniciando la Forja de Historias ---")
        
        # --- 1. Carga de la Visión Inicial ---
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                self.manifest = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"ERROR: No se encontró el archivo de manifiesto en '{manifest_path}'")
            exit()
            
        self.ai_provider = get_ai_provider()
        self.language = self.manifest.get('language', 'Español')
        self.initial_briefing = self.manifest.get('initial_briefing', 'Una historia de fantasía.')
        
        # El historial de la conversación creativa, para mantener el contexto
        self.story_context_history = [f"**Visión Original del Productor:**\n{self.initial_briefing}\n"]

    def _call_creative_agent(self, prompt: str) -> str:
        """Llama a la IA en modo 'Creativo'."""
        system_prompt = "Eres un novelista y guionista creativo. Tu trabajo es escribir contenido narrativo evocador y original."
        full_prompt = f"{system_prompt}\n\n{prompt}"
        
        print("\n>>> [Pidiendo al CREATIVO que escriba]...")
        time.sleep(2) # Pausa para legibilidad
        response = self.ai_provider.generate_text(full_prompt, temperature=0.75)
        self.story_context_history.append(f"**Borrador del Creativo:**\n{response}\n")
        return response

    def _call_critic_agent(self, prompt: str) -> str:
        """Llama a la IA en modo 'Crítico'."""
        system_prompt = "Eres un editor literario y crítico de guiones muy astuto. Tu trabajo es analizar textos, encontrar debilidades y dar feedback claro y accionable."
        full_prompt = f"{system_prompt}\n\n{prompt}"

        print("\n>>> [Pidiendo al CRÍTICO que evalúe]...")
        time.sleep(2)
        response = self.ai_provider.generate_text(full_prompt, temperature=0.6)
        self.story_context_history.append(f"**Análisis del Crítico:**\n{response}\n")
        return response

    def start_session(self):
        """Orquesta el proceso completo de escritura interactiva."""
        
        # --- 2. Generación del Primer Borrador (Ciclo Automático) ---
        print("\n--- Fase 1: Generación del Primer Borrador ---")
        
        # El Crítico da la primera orden al Creativo
        prompt_para_creativo = (
            f"Basado en la siguiente visión del productor, escribe un argumento literario detallado. "
            f"Crea una sinopsis, desarrolla los perfiles de los personajes principales y describe las localizaciones clave. "
            f"El texto debe estar en {self.language}.\n\n"
            f"**Visión del Productor:**\n{self.initial_briefing}"
        )
        borrador_actual = self._call_creative_agent(prompt_para_creativo)

        # El Crítico revisa el trabajo del Creativo
        prompt_para_critico = (
            f"He recibido este primer borrador de un guionista. "
            f"Compara el borrador con la visión original del productor y proporciona 2-3 sugerencias de mejora claras y concisas. "
            f"Céntrate en la coherencia y en si el tono es el correcto. "
            f"El texto debe estar en {self.language}.\n\n"
            f"**Visión Original:**\n{self.initial_briefing}\n\n"
            f"**Borrador a Revisar:**\n{borrador_actual}"
        )
        sugerencias = self._call_critic_agent(prompt_para_critico)
        
        # El Creativo aplica las revisiones
        prompt_revision = (
            f"Tu editor ha revisado tu último borrador y te ha dado las siguientes notas. "
            f"Reescribe el argumento completo aplicando estas mejoras. El texto debe estar en {self.language}.\n\n"
            f"**Notas del Editor:**\n{sugerencias}\n\n"
            f"**Tu Borrador Anterior (para referencia):**\n{borrador_actual}"
        )
        borrador_actual = self._call_creative_agent(prompt_revision)
        
        # --- 3. Ciclo de Revisión con el Usuario ---
        print("\n--- Fase 2: Supervisión del Productor ---")
        
        while True:
            print("\n================ BORRADOR ACTUAL ================")
            print(borrador_actual)
            print("===============================================")
            
            feedback = input(
                "\n¿Qué te parece? Escribe tus notas de revisión. \n"
                "Si estás contento, escribe 'aprobar'. Para salir, escribe 'salir':\n> "
            ).strip()
            
            if feedback.lower() == 'aprobar':
                print("\n¡Argumento aprobado! Guardando la biblia narrativa...")
                with open("narrative_bible.txt", "w", encoding='utf-8') as f:
                    f.write(borrador_actual)
                print(" -> 'narrative_bible.txt' guardado. ¡Fin del programa!")
                break
            
            if feedback.lower() == 'salir':
                print("\nSaliendo sin guardar. ¡Hasta la próxima!")
                break
            
            if not feedback:
                print("Por favor, introduce tus notas o 'aprobar'/'salir'.")
                continue

            # El Crítico (Guardián de tu Criterio) procesa tu feedback
            prompt_para_critico_con_feedback = (
                f"El Productor ha revisado el último borrador y ha dado las siguientes notas de revisión OBLIGATORIAS. "
                f"Tu tarea es tomar estas notas y convertirlas en una orden clara y directa para el guionista. "
                f"El texto debe estar en {self.language}.\n\n"
                f"**Notas del Productor:**\n{feedback}\n\n"
                f"**Último Borrador (para contexto):**\n{borrador_actual}"
            )
            orden_del_productor = self._call_critic_agent(prompt_para_critico_con_feedback)

            # El Creativo aplica la orden final
            prompt_final = (
                f"Tu editor te ha pasado las notas finales del Productor. Es crucial que apliques estos cambios. "
                f"Reescribe el argumento completo siguiendo estas directrices. El texto debe estar en {self.language}.\n\n"
                f"**Directrices del Editor (basadas en las notas del Productor):**\n{orden_del_productor}\n\n"
                f"**Borrador a Revisar:**\n{borrador_actual}"
            )
            borrador_actual = self._call_creative_agent(prompt_final)

if __name__ == '__main__':
    # Asegúrate de que el manifiesto está en la carpeta raíz del proyecto
    script_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(script_dir)
    manifest_file = os.path.join(project_root, "manifest_inspiracion.yaml")
    
    forge = StoryForge(manifest_path=manifest_file)
    forge.start_session()
    
    
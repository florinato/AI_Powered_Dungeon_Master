# game/presenter.py

import game_narrator  # Necesario para generar descripciones de localización
import pyttsx3
from models import PlayerState  # Útil para type hinting en el futuro


class Presenter:
    """
    Gestiona toda la salida del juego al jugador, tanto textual como auditiva.
    Actúa como la "vista" en una arquitectura Modelo-Vista-Controlador.
    """
    def __init__(self, use_voice=True):
        self.use_voice = use_voice
        try:
            self.speech_engine = pyttsx3.init()
            self.speech_engine.setProperty("rate", 180)
        except Exception as e:
            print(f"Warning: Could not initialize text-to-speech engine: {e}")
            self.speech_engine = None
            self.use_voice = False
    
    def speak(self, text: str):
        """Método central para la salida. Imprime en consola y, opcionalmente, habla."""
        print(text)
        if self.use_voice and self.speech_engine:
            self.speech_engine.say(text)
            self.speech_engine.runAndWait()

    def display_location(self, game_state: dict, world_definition: dict, ai_provider):
        loc_id = game_state['player']['location']
        loc_data = game_state['locations'].get(loc_id)
        if not loc_data:
            self.speak(f"ERROR: Location data for '{loc_id}' not found in game state.")
            return
        
        location_name = loc_data.get('name', loc_id.replace('_', ' ').title())

        if "generated_description" not in loc_data:
            print("(Generating atmospheric description, please wait...)")
            loc_description_base = loc_data.get('description', 'A non-descript place.')
            world_theme = world_definition.get('style', 'A generic world theme.')
            language = world_definition.get('language')
            
            loc_data["generated_description"] = game_narrator.generate_location_description(
                provider=ai_provider,
                base_description=loc_description_base,
                location_name=location_name,
                world_theme=world_theme,
                language=language
            )
        
        self.speak(f"\n--- {location_name} ---")
        self.speak(loc_data["generated_description"])

        if loc_data.get('npcs'):
            self.speak("\nNPCs Here:")
            for npc_id, npc_data in loc_data['npcs'].items():
                if npc_data.get('status') != 'defeated':
                    display_name = npc_data.get('name', npc_id).replace('_', ' ').title()
                    self.speak(f"- {display_name}")
        
        if loc_data.get('items'):
            self.speak("\nItems:")
            for item_id, item_data in loc_data['items'].items():
                display_name = item_data.get('name', item_id).replace('_', ' ').title()
                self.speak(f"- {display_name}")

        if loc_data.get('connections'):
            self.speak("\nPaths:")
            for direction, dest_id in loc_data['connections'].items():
                dest_location_data = game_state['locations'].get(dest_id)
                dest_name = dest_location_data.get('name', dest_id) if dest_location_data else f"{dest_id} (Unknown)"
                self.speak(f"- {direction.capitalize()}: {dest_name}")
                
    def display_inventory(self, game_state: dict):
        self.speak("\n--- Inventory ---")
        inventory = game_state['player'].get('inventory', [])
        if not inventory:
            self.speak("Your inventory is empty.")
            return
        for item in inventory:
            self.speak(f"- {item.get('name', 'Unknown Item').replace('_', ' ').title()}: {item.get('description', '')}")
    
    def display_stats(self, game_state: dict):
        p = game_state['player']
        self.speak(f"\n--- Stats ---\nLevel: {p.get('level', 1)}, HP: {p.get('hp', 0)}/{p.get('max_hp', 0)}, Attack: {p.get('attack', 0)}, XP: {p.get('xp', 0)}/{p.get('xp_to_next_level', 0)}")

    def display_quests(self, game_state: dict, world_definition: dict):
        self.speak("\n--- Diario de Misiones ---")
        player_quests = game_state['player'].get('active_quests', {})
        all_quests_def = world_definition.get('quests', {})

        if not player_quests:
            self.speak("No tienes ninguna misión activa.")
            return

        for quest_id, quest_status in player_quests.items():
            quest_def = all_quests_def.get(quest_id)
            if not quest_def:
                self.speak(f"Error: No se encontraron los datos para la misión '{quest_id}'.")
                continue

            status_text = "[Completada]" if quest_status.get('completed') else "[Activa]"
            self.speak(f"\n{status_text} {quest_def.get('title', quest_id)}")
            
            current_step_id = quest_status.get('current_step_id')
            if current_step_id:
                step_def = next((step for step in quest_def.get('steps', []) if step.get('id') == current_step_id), None)
                if step_def:
                    self.speak(f"  └─ Objetivo: {step_def.get('description', 'No hay un objetivo claro...')}")
            
            if quest_status.get('status') == 'ready_to_turn_in':
                self.speak(f"  └─ Tienes que informar de tus progresos para completar la misión.")
                
    def show_help(self):
        self.speak("\n--- Commands ---\nlook, move <dir>, back, get <item>, use <item>, drop <item>, inv, stats, quests, fight, talk, unlock <dir>, image, help, quit")
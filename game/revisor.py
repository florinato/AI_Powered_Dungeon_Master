# game/revisor.py

import json
import os
import random
import re
import time

from ai_factory import get_ai_provider


class WorldRevisor:
    """
    Actúa como un editor de calidad enfocado. Realiza pasadas de revisión
    específicas para problemas de jugabilidad (pacing) y coherencia narrativa,
    aplicando correcciones precisas.
    """

    def __init__(self, input_path: str, output_path: str):
        print("--- World Revisor 3.0 (Focused Editor) Initialized ---")
        self.input_path = input_path
        self.output_path = output_path
        self.ai_provider = get_ai_provider()
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                self.world_data = json.load(f)
            print(f"Successfully loaded world data from '{input_path}'")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"FATAL: Could not load or parse the input file. Error: {e}")
            raise
            
        # Actualizamos los mapas de assets internos
        self._update_asset_maps()

    def revise_and_save(self):
        """Orquesta las pasadas de revisión específicas."""
        print("\n--- Running Revision Passes ---")
        
        # Pasada 1: Corregir problemas de ritmo y colocación de objetos.
        self._revise_gameplay_pacing()
        
        # Pasada 2: Corregir incoherencias entre la descripción y la mecánica.
        self._revise_narrative_consistency()
        
        # Pasada 3: Limpieza técnica final (siempre es buena idea).
        self._final_technical_pass()

        # Guardar el archivo final
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(self.world_data, f, indent=2, ensure_ascii=False)
            print(f"\n--- SUCCESS! Focused revision complete. World saved to '{self.output_path}' ---")
        except Exception as e:
            print(f"FATAL: Could not save revised world file. Error: {e}")
            
    def _update_asset_maps(self):
        """Actualiza los diccionarios internos para un acceso rápido a los datos del mundo."""
        self.locations = {loc['id']: loc for loc in self.world_data.get('locations', [])}
        self.items = {item['id']: item for item in self.world_data.get('item_templates', [])}
        self.npcs = {npc['id']: npc for npc in self.world_data.get('npc_templates', [])}
        self.quests = {q['id']: q for q in self.world_data.get('quests', [])}

    def _get_location_of_asset(self, asset_id: str, asset_type: str) -> str | None:
        """Encuentra en qué localización está un PNJ o un objeto."""
        list_key = 'initial_items' if asset_type == 'item' else 'initial_npcs'
        for loc_id, loc_data in self.locations.items():
            if asset_id in loc_data.get(list_key, []):
                return loc_id
        return None

    def _revise_gameplay_pacing(self):
        """Revisa cada misión en busca de problemas de ritmo (objetivos consecutivos en el mismo lugar)."""
        print("\n[Pass 1] Revising Gameplay Pacing and Asset Placement...")
        for quest_id, quest_data in self.quests.items():
            steps = quest_data.get('steps', [])
            for i in range(len(steps) - 1):
                current_step = steps[i]
                next_step = steps[i+1]
                
                current_obj_loc = self._get_location_of_asset(
                    current_step['objective']['id'], current_step['objective']['type']
                )
                if current_step['objective']['type'] == 'location':
                    current_obj_loc = current_step['objective']['id']

                next_obj_loc = self._get_location_of_asset(
                    next_step['objective']['id'], next_step['objective']['type']
                )
                if next_step['objective']['type'] == 'location':
                    next_obj_loc = next_step['objective']['id']
                
                if current_obj_loc and next_obj_loc and current_obj_loc == next_obj_loc:
                    print(f"  -> Pacing Issue Detected in Quest '{quest_data['title']}':")
                    print(f"     - Step {i+1} and Step {i+2} objectives are both in location '{current_obj_loc}'.")
                    
                    # Mover el activo del SIGUIENTE paso a un lugar mejor
                    asset_to_move_id = next_step['objective']['id']
                    asset_to_move_type = next_step['objective']['type']
                    
                    if asset_to_move_type in ['item', 'npc']:
                        self._move_asset_to_new_location(asset_to_move_id, asset_to_move_type, exclude_loc_id=current_obj_loc)

    def _move_asset_to_new_location(self, asset_id: str, asset_type: str, exclude_loc_id: str | None = None):
        """Mueve un activo de su ubicación actual a una nueva ubicación lógica."""
        # 1. Quitar de la ubicación actual
        current_loc_id = self._get_location_of_asset(asset_id, asset_type)
        if current_loc_id:
            asset_list_key = 'initial_items' if asset_type == 'item' else 'initial_npcs'
            self.locations[current_loc_id][asset_list_key].remove(asset_id)
        
        # 2. Encontrar nueva ubicación
        options = [loc_id for loc_id in self.locations if loc_id != exclude_loc_id]
        if not options: options = list(self.locations.keys()) # Fallback
        
        new_loc_id = random.choice(options)
        
        # 3. Colocar en la nueva ubicación
        asset_list_key = 'initial_items' if asset_type == 'item' else 'initial_npcs'
        self.locations[new_loc_id].setdefault(asset_list_key, []).append(asset_id)
        print(f"     -> CORRECTED: Moved asset '{asset_id}' to a new location '{new_loc_id}'.")

    def _revise_narrative_consistency(self):
        """Revisa cada paso de misión para asegurar que el texto coincida con el objetivo mecánico."""
        print("\n[Pass 2] Revising Narrative Consistency...")
        for quest_id, quest_data in self.quests.items():
            for step in quest_data.get('steps', []):
                description = step.get('description', '')
                objective = step.get('objective', {})
                obj_id = objective.get('id')
                
                if objective.get('type') != 'npc': continue

                # Comprobar si la descripción menciona a un PNJ por su nombre
                mentioned_npcs = [npc_id for npc_id, npc_data in self.npcs.items() if npc_data['name'] in description]
                
                # Si se menciona a algún PNJ y NINGUNO de ellos es el objetivo real...
                if mentioned_npcs and obj_id not in mentioned_npcs:
                    print(f"  -> Narrative Inconsistency Detected in Quest '{quest_data['title']}':")
                    print(f"     - Description mentions NPCs ({[self.npcs[m]['name'] for m in mentioned_npcs]}) but objective is '{self.npcs[obj_id]['name']}'.")
                    
                    self._rewrite_step_description_with_ai(quest_data, step)
    
    def _rewrite_step_description_with_ai(self, quest: dict, step: dict):
        """Usa la IA para reescribir una descripción de paso inconsistente."""
        objective_npc_id = step.get('objective', {}).get('id')
        objective_npc_name = self.npcs.get(objective_npc_id, {}).get('name', 'an unknown entity')
        
        prompt = (
            f"You are a narrative editor. Your task is to rewrite a confusing quest step description to make it clear and consistent with the game's mechanics.\n\n"
            f"**Quest Title:** {quest.get('title')}\n"
            f"**Original (Confusing) Step Description:** \"{step.get('description')}\"\n"
            f"**The Problem:** The description mentions a character that is NOT the actual objective. The TRUE mechanical objective for this step is to interact with or defeat the character named '{objective_npc_name}' (ID: {objective_npc_id}).\n\n"
            f"**Your Task:** Rewrite the step description to be narrativamente engaging AND accurately guide the player towards the correct objective, '{objective_npc_name}'. The new description should seamlessly fit the quest's story.\n\n"
            f"Respond with ONLY a JSON object containing the new description: {{\"new_description\": \"...\"}}"
        )
        
        try:
            # Usamos generate_text y parseamos, a veces es más fiable para respuestas simples
            response_text = self.ai_provider.generate_text(prompt, temperature=0.7)
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                response_json = json.loads(match.group())
                if 'new_description' in response_json:
                    print(f"     -> CORRECTED: Rewriting description.")
                    print(f"        - OLD: \"{step['description']}\"")
                    step['description'] = response_json['new_description']
                    print(f"        - NEW: \"{step['description']}\"")
                    return
        except Exception as e:
            print(f"     -> ERROR: AI failed to rewrite description. {e}")

    def _final_technical_pass(self):
        """Ejecuta correcciones técnicas finales."""
        print("\n[Pass 3] Performing Final Technical Pass...")
        
        for quest_id, quest_data in self.quests.items():
            for i, step in enumerate(quest_data.get('steps', [])):
                # ASEGURAR QUE EL ID DEL PASO SEA UN STRING
                original_id = step.get('id')
                if not isinstance(original_id, str):
                    new_id = f"step_{original_id or i+1}"
                    step['id'] = new_id
                    print(f"    - Technical Fix: Standardized step ID in quest '{quest_data['title']}' from '{original_id}' to '{new_id}'.")

        # ... (la otra lógica de esta función se mantiene)
        # Lógica para corregir IDs de localización narrativos que la IA pudo haber pasado por alto.
        for quest in self.world_data.get('quests', []):
            for step in quest.get('steps', []):
                objective = step.get('objective', {})
                if objective.get('type') == 'location':
                    target_id = objective.get('id')
                    if target_id not in self.locations:
                        print(f"    - Technical Fix: Objective location '{target_id}' is not a physical node.")
                        start_loc = self.world_data['world'].get('starting_location_id')
                        fallback_id = random.choice([lid for lid in self.locations.keys() if lid != start_loc] or list(self.locations.keys()))
                        objective['id'] = fallback_id
                        print(f"      -> Replaced with physical node '{fallback_id}'.")

if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INPUT_FILE = os.path.join(project_root, "world_import_generated.json")
    OUTPUT_FILE = os.path.join(project_root, "world_import_revisado.json")

    if not os.path.exists(INPUT_FILE):
        print(f"Error: El archivo de entrada '{INPUT_FILE}' no existe.")
        print("Asegúrate de ejecutar primero director.py para generarlo.")
    else:
        revisor = WorldRevisor(input_path=INPUT_FILE, output_path=OUTPUT_FILE)
        revisor.revise_and_save()




# game/world_generation/revisor.py

import json
import os
import random

from game.ai.ai_factory import get_ai_provider


class WorldRevisor:
    """
    Actúa como un Game Designer y Editor Jefe. Toma un mundo generado en bruto
    y lo refina en una aventura coherente, lógica y bien hilada, con la autoridad
    para reescribir tramas, renombrar elementos y reubicar activos para
    maximizar la calidad de la experiencia del jugador.
    """

    def __init__(self, input_path: str, output_path: str):
        print("--- World Revisor 4.0 (Lead Game Designer AI) Initialized ---")
        self.input_path = input_path
        self.output_path = output_path
        self.ai_provider = get_ai_provider()
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                self.world_data = json.load(f)
            print(f"Successfully loaded raw world data from '{input_path}'")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"FATAL: Could not load or parse the input file. Error: {e}")
            raise
            
        # Inicializamos los mapas de assets una vez al principio
        self._update_asset_maps()

    def revise_and_save(self):
        """Orquesta el proceso completo de edición de la aventura."""
        print("\n--- Beginning Adventure Design & Coherence Review ---")
        
        all_quests = self.world_data.get('quests', [])
        for i, quest_data in enumerate(all_quests):
            print(f"\n[Editing Quest {i+1}/{len(all_quests)}] '{quest_data.get('title')}'...")
            
            full_quest_context = self._build_full_quest_context(quest_data)
            editorial_plan = self._get_editorial_plan_from_ai(full_quest_context)
            
            if editorial_plan and editorial_plan.get('editorial_plan'):
                print("  -> Applying editorial plan...")
                self._apply_editorial_plan(editorial_plan)
            else:
                print("  -> No editorial plan received or plan was empty. Quest remains as is.")

        self._final_technical_pass()

        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(self.world_data, f, indent=2, ensure_ascii=False)
            print(f"\n--- SUCCESS! Professionally edited world saved to '{self.output_path}' ---")
        except Exception as e:
            print(f"FATAL: Could not save revised world file. Error: {e}")

    def _update_asset_maps(self):
        """Actualiza los diccionarios internos para un acceso rápido y fácil."""
        self.locations = {loc['id']: loc for loc in self.world_data.get('locations', [])}
        self.items = {item['id']: item for item in self.world_data.get('item_templates', [])}
        self.npcs = {npc['id']: npc for npc in self.world_data.get('npc_templates', [])}
        self.quests = {q['id']: q for q in self.world_data.get('quests', [])}
            
    def _build_full_quest_context(self, quest_data: dict) -> dict:
        # ... (esta función está bien, no necesita cambios)
        context = {"quest": quest_data, "involved_assets": {}}
        asset_ids = [quest_data.get('starting_npc_id'), quest_data.get('final_boss_id')]
        for step in quest_data.get('steps', []):
            asset_ids.append(step.get('objective', {}).get('id'))
        
        for asset_id in filter(None, set(asset_ids)):
            if item := self.items.get(asset_id):
                context["involved_assets"][asset_id] = {"type": "item", "data": item}
            elif npc := self.npcs.get(asset_id):
                context["involved_assets"][asset_id] = {"type": "npc", "data": npc}
        return context

    def _get_editorial_plan_from_ai(self, context: dict) -> dict | None:
        """
        La llamada clave a la IA, ahora con directriz de idioma y razón obligatoria.
        """
        world_language = self.world_data.get('world', {}).get('language', 'English')

        prompt = (
            "You are a world-class Lead Game Designer and Narrative Editor. You have received a rough draft for a quest. Your job is to analyze it, identify all flaws (narrative, logical, pacing), and create a detailed, structured plan to transform it into a high-quality, coherent, and fun adventure.\n\n"
            f"**Primary Instruction:** All your rewrites and new text in the plan MUST be written in **{world_language}**.\n\n"
            "**Guiding Principles for Your Edit:**\n"
            "1.  **Semantic Coherence:** Names of items/characters mentioned in quest text MUST match the actual asset names. If they don't, unify them under a single, thematic name.\n"
            "2.  **Logical Player Journey (Breadcrumbs):** The player must always have a clear clue to their next objective. Fix any broken chains in the narrative flow.\n"
            "3.  **Engaging Pacing:** Ensure a sense of journey by placing objectives in distinct, logical locations. Do not place a key item in the same room as the quest giver.\n\n"
            f"**Quest Draft to Review:**\n```json\n{json.dumps(context, indent=2)}\n```\n\n"
            "**Your Task:**\n"
            "Return a JSON object with your complete editorial plan. The JSON must have a key `editorial_plan` which is a list of actions.\n\n"
            "**Valid Actions:** `RENAME_ASSET`, `REWRITE_TEXT`, `RELOCATE_ASSET`.\n"
            "**CRITICAL:** For each action, the `details` object **MUST** include a `reason` key explaining *why* you are making the change.\n\n"
            "**Details Structure:**\n"
            "- For `RENAME_ASSET`: `asset_id`, `new_name`, `reason`.\n"
            # --- CAMBIO CLAVE AQUÍ ---
            "- For `REWRITE_TEXT`: `asset_id`, `text_type` ('description', 'dialogue_prompt', or 'step_description'), `new_text`, `reason`. **If `text_type` is 'step_description', you MUST also include the `step_id` of the step you are rewriting.**\n"
            "- For `RELOCATE_ASSET`: `asset_id`, `asset_type`, `suggested_location_id`, `reason`.\n\n"
            "If the quest is perfect, return an empty `editorial_plan` list. Respond ONLY with the JSON object."
        )
        
        try:
            return self.ai_provider.generate_json(prompt, temperature=0.6, max_tokens=4000)
        except Exception as e:
            print(f"  -> ERROR: AI failed to generate an editorial plan. {e}")
            return None

    def _apply_editorial_plan(self, plan: dict):
        """Ejecuta metódicamente las acciones del plan editorial de la IA, con validación robusta."""
        for action in plan.get('editorial_plan', []):
            action_type = action.get('action')
            details = action.get('details', {})
            reason = details.get('reason', 'No reason provided by AI.')
            
            asset_id = details.get('asset_id')

            if not action_type or not details:
                print(f"    - SKIPPING Action: Malformed action object.")
                continue

            if action_type in ['RENAME_ASSET', 'REWRITE_TEXT', 'RELOCATE_ASSET']:
                if not asset_id or not (self.items.get(asset_id) or self.npcs.get(asset_id) or self.quests.get(asset_id)):
                    print(f"    - SKIPPING Action: {action_type} | Reason: Invalid or missing asset_id '{asset_id}'. AI may have hallucinated.")
                    continue

            asset_id_log = f" for asset '{asset_id}'" if asset_id else ""
            print(f"    - Applying: {action_type}{asset_id_log} | Reason: {reason}")

            try:
                if action_type == 'RENAME_ASSET':
                    new_name = details.get('new_name')
                    if new_name and (asset := self.items.get(asset_id) or self.npcs.get(asset_id)):
                        asset['name'] = new_name

                elif action_type == 'REWRITE_TEXT':
                    text_type = details.get('text_type')
                    new_text = details.get('new_text')
                    
                    if not text_type or not new_text: continue

                    # --- LÓGICA DE REESCRITURA MEJORADA ---
                    if text_type == 'step_description':
                        step_id = details.get('step_id')
                        quest_to_edit = self.quests.get(asset_id)
                        if step_id and quest_to_edit:
                            step_found = False
                            for step in quest_to_edit.get('steps', []):
                                if step.get('id') == step_id:
                                    step['description'] = new_text
                                    step_found = True
                                    break
                            if not step_found:
                                print(f"      -> WARNING: Could not find step with id '{step_id}' in quest '{asset_id}'.")
                    else:
                        # Para descripciones de assets o diálogos de PNJs
                        if asset_to_edit := self.items.get(asset_id) or self.npcs.get(asset_id) or self.quests.get(asset_id):
                            if text_type in asset_to_edit:
                                asset_to_edit[text_type] = new_text
                            else:
                                print(f"      -> WARNING: text_type '{text_type}' not found in asset '{asset_id}'.")

                elif action_type == 'RELOCATE_ASSET':
                    asset_type = details.get('asset_type')
                    suggested_loc = details.get('suggested_location_id')
                    if asset_type:
                        self._move_asset_to_new_location(asset_id, asset_type, preferred_loc_id=suggested_loc)
                        self._update_asset_maps()

            except Exception as e:
                print(f"    -> CRITICAL ERROR while applying action '{action_type}' for asset '{asset_id}'. Error: {e}")
                continue
    def _get_location_of_asset(self, asset_id: str) -> str | None:
        """Encuentra la ubicación actual de un PNJ o un objeto."""
        for loc_id, loc_data in self.locations.items():
            if asset_id in loc_data.get('initial_npcs', []) or asset_id in loc_data.get('initial_items', []):
                return loc_id
        return None
    def _move_asset_to_new_location(self, asset_id: str, asset_type: str, preferred_loc_id: str | None = None, exclude_loc_id: str | None = None):
        """Mueve un activo de su ubicación actual a una nueva ubicación lógica y segura."""
        if not asset_type or not asset_id: return
        
        list_key = 'initial_items' if asset_type == 'item' else 'initial_npcs'
        current_loc_id = self._get_location_of_asset(asset_id)

        if current_loc_id and asset_id in self.locations[current_loc_id].get(list_key, []):
            self.locations[current_loc_id][list_key].remove(asset_id)
        
        if preferred_loc_id and preferred_loc_id in self.locations:
            new_loc_id = preferred_loc_id
        else:
            mission_npcs = {q.get('starting_npc_id') for q in self.quests.values()} | {q.get('final_boss_id') for q in self.quests.values()}
            
            options = []
            for loc_id, loc_data in self.locations.items():
                if loc_id == current_loc_id or loc_id == exclude_loc_id: continue
                
                # Un PNJ no puede ir a una sala con otro PNJ de misión
                if asset_type == 'npc' and any(npc in loc_data.get('initial_npcs', []) for npc in mission_npcs): continue
                
                options.append(loc_id)
            
            if not options:
                options = [loc_id for loc_id in self.locations if loc_id != current_loc_id and loc_id != exclude_loc_id] or list(self.locations.keys())
            
            new_loc_id = random.choice(options)
        
        self.locations[new_loc_id].setdefault(list_key, []).append(asset_id)
        print(f"      -> Moved asset '{asset_id}' to new location '{new_loc_id}'.")

    def _final_technical_pass(self):
        """
        Asegura que todos los IDs sean correctos y jugables después de la edición.
        Esta función ahora también repara estructuras de 'objective' corruptas.
        """
        print("\n[Final Pass] Performing technical validation...")
        
        # Obtenemos una lista de todos los IDs de localizaciones válidas una sola vez
        all_loc_ids = list(self.locations.keys())
        if not all_loc_ids:
            print("  - WARNING: No locations found in world data. Cannot validate location objectives.")
            return

        # Iteramos sobre la lista de misiones
        for quest in self.world_data.get('quests', []):
            if not isinstance(quest, dict) or 'steps' not in quest:
                continue # Omitir misiones mal formadas

            for i, step in enumerate(quest.get('steps', [])):
                if not isinstance(step, dict):
                    continue # Omitir pasos mal formados

                # 1. Estandarizar ID del paso
                step['id'] = f"step_{i+1}"

                # 2. Validar y reparar la estructura del 'objective'
                objective_data = step.get('objective', {})

                # Si 'objective' es un string en lugar de un dict, lo reparamos.
                if isinstance(objective_data, str):
                    print(f"  - WARNING: Corrupted objective structure found in quest '{quest.get('title')}'. Was a string, repairing to dict.")
                    # Asumimos que el string es el ID y el tipo es desconocido, probablemente 'location'
                    objective_data = {'type': 'unknown', 'id': objective_data}
                    step['objective'] = objective_data # Lo reasignamos al paso
                
                # 3. Validar el ID de la localización
                if objective_data.get('type') == 'location':
                    loc_id = objective_data.get('id')
                    if loc_id not in all_loc_ids:
                        new_loc_id = random.choice(all_loc_ids)
                        print(f"  - Technical Fix: Objective location '{loc_id}' in quest '{quest['title']}' is invalid.")
                        print(f"    -> Replaced with random valid location '{new_loc_id}'.")
                        objective_data['id'] = new_loc_id
                        
if __name__ == '__main__':
    # 4. Rutas ajustadas para ser más robustas
    try:
        # Esto asume que 'revisor.py' está en 'game/world_generation/'
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir)) 
        
        INPUT_FILE = os.path.join(project_root, "world_import_generated.json")
        OUTPUT_FILE = os.path.join(project_root, "world_import_revisado.json")

        if not os.path.exists(INPUT_FILE):
            print(f"Error: The input file '{INPUT_FILE}' does not exist.")
            print("Please run director.py first to generate it.")
        else:
            revisor = WorldRevisor(input_path=INPUT_FILE, output_path=OUTPUT_FILE)
            revisor.revise_and_save()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
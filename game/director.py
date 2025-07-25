# game/director.py
import json
import os
import random
import re
import time
from typing import Any, Dict, List

import yaml
from gemini_provider import AIProviderInterface, GeminiProvider
from models import LocationDefinition, WorldDefinition, WorldGraph


class DirectorAgent:
    """
    Actúa como un "Dungeon Master AI" para crear un mundo jugable a partir
    de una estructura de grafo y un manifiesto de alto nivel.
    """
    def __init__(self, provider: AIProviderInterface, manifest_path: str, base_items_path: str):
        print("--- Director Agent Initialized ---")
        self.provider = provider

        # Cargar el manifiesto del usuario
        with open(manifest_path, 'r', encoding='utf-8') as f:
            self.manifest = yaml.safe_load(f)

        # Cargar las plantillas de items base
        with open(base_items_path, 'r', encoding='utf-8') as f:
            self.base_item_templates = json.load(f)

        # --- VALIDACIÓN TEMPRANA DEL IDIOMA ---
        self.world_language = self.manifest.get('language')
        if not self.world_language:
            raise ValueError("FATAL: 'language' key not found or is empty in your manifest .yaml file. Please add it (e.g., 'language: Español').")

        self.world_id = self.manifest.get('world_id', 'default_world')
        self.world_theme = self.manifest.get('world_theme', 'A mysterious world')
        print(f"Loaded manifest for world '{self.manifest.get('world_name', self.world_id)}' in '{self.world_language}'")
        print(f"Theme: '{self.world_theme[:60]}...'")


        # Almacenes de contenido generado
        self.location_definitions: Dict[str, Dict[str, Any]] = {}
        self.npc_templates: Dict[str, Dict[str, Any]] = {}
        self.item_templates: Dict[str, Dict[str, Any]] = {}
        self.quests: List[Dict[str, Any]] = []
        self.world_graph: WorldGraph | None = None
    def _generate_creative_json(self, prompt: str, attempts=3) -> dict | list:
        """
        Envoltura robusta para generar JSON.
        Intenta extraer y limpiar el JSON de la respuesta de la IA.
        Realiza varios intentos si falla.
        """
        print(f"  - Sending prompt to AI: '{prompt[:70]}...'")
        
        for attempt in range(attempts):
            try:
                response_text = self.provider.generate_text(prompt, temperature=0.5)
                print("    -> Pausing for 5 seconds to respect API rate limits...")
                time.sleep(5)
                match = re.search(r'```(?:json)?\s*([\[\{].*?[\]\}])\s*```', response_text, re.DOTALL)
                if match:
                    json_str = match.group(1)
                else:
                    start = -1
                    if 'list of strings' in prompt.lower():
                        start = response_text.find('[')
                        end = response_text.rfind(']')
                    else:
                        start = response_text.find('{')
                        end = response_text.rfind('}')

                    if start != -1 and end != -1 and start < end:
                        json_str = response_text[start:end+1]
                    else:
                        json_str = response_text
                
                json_str = re.sub(r',\s*([\}\]])', r'\1', json_str)
                return json.loads(json_str)

            except (json.JSONDecodeError, Exception) as e:
                print(f"    -> AI generation/parsing failed on attempt {attempt + 1}/{attempts}. Error: {e}")
                if attempt == attempts - 1:
                    return {} if '{' in prompt else []
        
        return {} if '{' in prompt else []

    def orchestrate_world_creation(self, graph: WorldGraph):
        """Orquesta el proceso completo de creación de un mundo sorprendente."""
        print("\n--- Starting World Orchestration ---")
        density_rules = self.manifest.get('density', {})
        self.world_graph = graph
        self._create_themed_locations(graph)
        npc_archetypes = self._design_npc_archetypes(density_rules)
        self._create_specific_npcs(npc_archetypes)
        self._create_themed_items()
        self._design_quests(density_rules)
        self._place_content_in_world()
        
        print("\n--- Orchestration Complete ---")
        
    # --- MÉTODOS DE CREACIÓN DE CONTENIDO (CON PROMPTS MEJORADOS) ---

    def _create_themed_locations(self, graph: WorldGraph):
        print("\n[Master Thought 1/6]: Giving a name and soul to each location...")
        for node_id, node in graph.nodes.items():
            prompt = (
                f"You MUST respond in {self.world_language}. "
                f"The world's theme is: '{self.world_theme}'.\n"
                f"Invent a unique and evocative name and a 2-sentence atmospheric description for a location of type '{node.type}'. "
                f"The name and description MUST be in {self.world_language}. "
                f"Existing names to avoid: {[loc.get('name') for loc in self.location_definitions.values()]}. "
                "Respond ONLY with the JSON object: {\"name\": \"...\", \"description\": \"...\"}"
            )
            content = self._generate_creative_json(prompt)
            
            loc_def = LocationDefinition(
                id=node_id, world_id=self.world_id, name=content.get('name', f"Unnamed {node.type}"),
                description=content.get('description', 'A mysterious place.'), type=node.type, tags=node.tags,
                connections={conn.direction: conn.target_node_id for conn in node.connections},
                initial_npcs=[], initial_items=[]
            )
            self.location_definitions[node_id] = loc_def.model_dump()

    def _design_npc_archetypes(self, density: Dict) -> List[str]:
        print("\n[Master Thought 2/6]: Reading character archetypes directly from manifest...")
        
        # Leemos los arquetipos EXACTOS que has definido en el manifiesto.
        archetypes = self.manifest.get('structure', {}).get('npc_archetypes', [])
        
        if not archetypes:
            # Si el manifiesto no los tiene, generamos unos de fallback.
            print("  -> No archetypes found in manifest. Generating them with AI...")
            density_map = {"low": 3, "medium": 5, "high": 7}
            num_archetypes = density_map.get(density.get('npcs', 'medium'), 5)
            prompt = (
                f"You MUST respond in {self.world_language}. "
                f"For a world with theme '{self.world_theme}', brainstorm {num_archetypes} unique character archetypes. "
                f"Respond ONLY with a JSON list of strings in {self.world_language}."
            )
            archetypes = self._generate_creative_json(prompt)
        else:
            print(f"  -> Found {len(archetypes)} archetypes in manifest.")
            
        return archetypes if isinstance(archetypes, list) else []

    def _create_specific_npcs(self, archetypes: List[str]):
        print("\n[Master Thought 3/6]: Creating unique individuals for these roles...")
        for archetype in archetypes:
            prompt = (
                f"You MUST respond in {self.world_language}. "
                f"Create a specific character for the role '{archetype}' in a world with theme '{self.world_theme}'. "
                f"Provide a unique ID (lowercase_with_underscores, NO accents or special characters), their name, a short description, status (friendly/neutral/hostile), and a personality/dialogue prompt. "
                f"The name, description, and dialogue_prompt MUST be in {self.world_language}. "
                "Respond ONLY with the JSON object: {\"id\": \"...\", \"name\": \"...\", \"description\": \"...\", \"status\": \"...\", \"dialogue_prompt\": \"...\"}"
            )
            npc_data = self._generate_creative_json(prompt)
            
            if not npc_data or not all(k in npc_data for k in ['id', 'name', 'description']):
                print(f"    -> WARNING: AI failed to provide basic info for archetype '{archetype}'. Skipping.")
                continue

            stats_prompt = f"Based on this character: '{npc_data['description']}', provide balanced game stats (HP between 10-100, Attack between 1-20, XP between 5-50). Respond ONLY with the JSON object: {{\"hp\": ..., \"attack\": ..., \"xp\": ...}}"
            stats = self._generate_creative_json(stats_prompt)

            if not stats or not all(k in stats for k in ['hp', 'attack', 'xp']):
                print(f"    -> WARNING: AI failed to provide valid stats for NPC '{npc_data['name']}'. Skipping.")
                continue

            npc_data.update(stats)
            npc_data['role'] = archetype 
            self.npc_templates[npc_data['id']] = npc_data
    
    def _create_themed_items(self):
        print("\n[Master Thought 4/6]: Theming base items for treasures and tools...")
        for template_id, base_data in self.base_item_templates.items():
            prompt = (
                f"You MUST respond in {self.world_language}. "
                f"Give a unique, thematic name and description for a '{base_data['type']}' item (template: {template_id}) that fits the world theme '{self.world_theme}'. "
                f"The name and description MUST be in {self.world_language}. "
                "Respond ONLY with the JSON object: {\"name\": \"...\", \"description\": \"...\"}"
            )
            themed_data = self._generate_creative_json(prompt)
            
            final_item = base_data.copy()
            final_item.update(themed_data)
            # Crear ID a partir del nombre en inglés o un fallback
            safe_name = themed_data.get('name', f'item_{template_id}').encode('ascii', 'ignore').decode('ascii').lower().replace(' ', '_')
            final_item['id'] = f"{safe_name}_{random.randint(100,999)}"
            final_item['template_id'] = template_id
            self.item_templates[final_item['id']] = final_item


    def _design_quests(self, density: Dict):
        print("\n--- [DEBUG] Master Thought 5/6: Entering _design_quests ---")
        self.quests = []

        quest_seeds = self.manifest.get('quest_seeds', [])
        if not quest_seeds:
            print("  -> [DEBUG] CRITICAL: No 'quest_seeds' found in manifest. Aborting.")
            return

        density_map = {"low": 1, "medium": 2, "high": 3}
        quest_density_setting = density.get('quests', 'medium')
        num_quests_to_generate = min(density_map.get(quest_density_setting, 2), len(quest_seeds))
        print(f"  -> [DEBUG] Quest density is '{quest_density_setting}'. Will generate {num_quests_to_generate} quest(s).")
        selected_seeds = random.sample(quest_seeds, num_quests_to_generate)
        
        for i, seed in enumerate(selected_seeds):
            print(f"  -> [DEBUG] Developing seed '{seed.get('title', 'NO TITLE')}'")
            
            # --- PROMPT A PRUEBA DE TODO ---
            # Le pedimos solo texto, separado por un token especial que podamos parsear.
            prompt = (
                f"You are a quest designer writing in {self.world_language}. "
                f"Based on this quest idea: '{seed.get('description', '')}', write a full quest. "
                f"First, write a detailed, engaging 'full_description' for the player. "
                f"Then, on new lines, write exactly 3 short, one-sentence descriptions for the quest steps, each starting with 'STEP:'. "
                f"Do NOT use JSON format. Respond ONLY with plain text."
                f"\n\nEXAMPLE:\n"
                f"Esta es la descripción completa y detallada de la misión...\n"
                f"STEP: Este es el objetivo del primer paso.\n"
                f"STEP: Este es el objetivo del segundo paso.\n"
                f"STEP: Este es el objetivo del tercer paso."
            )
            
            # Usamos generate_text, no _generate_creative_json
            full_text_response = self.provider.generate_text(prompt)
            print(f"  -> [DEBUG] AI returned raw text:\n{full_text_response}")
            
            # --- PARSEO MANUAL Y ENSAMBLAJE ---
            try:
                parts = full_text_response.split("STEP:")
                if len(parts) >= 4: # Debe haber una descripción y al menos 3 pasos
                    full_description = parts[0].strip()
                    step_descriptions = [step.strip() for step in parts[1:]]

                    print("    -> [DEBUG] Manual parsing SUCCESSFUL.")
                    
                    safe_title = seed.get('title', f'QUEST_{i}').encode('ascii', 'ignore').decode('ascii').upper().replace(' ', '_')
                    quest_id = f"QUEST_{safe_title}"

                    steps = []
                    for j, step_desc in enumerate(step_descriptions):
                        steps.append({
                            "id": f"paso_{j+1}",
                            "description": step_desc,
                            "objective": {"type": "narrative", "id": "unknown"}
                        })

                    final_quest = {
                        "id": quest_id, "title": seed.get('title'),
                        "description": full_description, "steps": steps,
                        "quest_giver_archetype": seed.get('quest_giver_archetype'),
                        "boss_archetype": seed.get('boss_archetype')
                    }
                    
                    self.quests.append(final_quest)
                    print(f"    -> [DEBUG] SUCCESS! Quest '{final_quest['title']}' added to self.quests.")
                else:
                    raise ValueError("Response did not contain enough 'STEP:' separators.")

            except Exception as e:
                print(f"    -> [DEBUG] CRITICAL FAILURE: Could not parse AI's text response. Error: {e}. Skipping.")
        
        print(f"--- [DEBUG] Exiting _design_quests. Total quests generated: {len(self.quests)} ---")

    def _place_content_in_world(self):
        print("\n--- [Master Thought 6/6] Placing content intelligently using the zoned map ---")
        
        if not self.world_graph or not self.location_definitions:
            print("  -> CRITICAL: World graph or location definitions are missing. Aborting placement.")
            return

        # --- 1. CLASIFICAR LAS LOCALIZACIONES BASÁNDONOS EN LOS TAGS DEL MAPA ---
        locations_by_tag = {"all": list(self.world_graph.nodes.keys())}
        for node_id, node_data in self.world_graph.nodes.items():
            for tag in node_data.tags:
                if tag not in locations_by_tag:
                    locations_by_tag[tag] = []
                locations_by_tag[tag].append(node_id)
        
        print(f"  -> Classified locations by tags: {list(locations_by_tag.keys())}")

        # --- 2. CLASIFICAR EL CONTENIDO GENERADO ---
        placed_npc_ids = set()
        placed_item_ids = set()

        # --- 3. PRIORIDAD 1: COLOCACIÓN DE TRAMA (MISIONES) ---
        if self.quests:
            for quest in self.quests:
                print(f"  -> Placing content for Quest: '{quest.get('title')}'")
                
                # 3.1. Colocar al Quest Giver
                giver_archetype = quest.get('quest_giver_archetype')
                quest_giver_npc = next((npc for npc in self.npc_templates.values() if npc.get('role') == giver_archetype), None)
                
                # Buscamos un nodo con tag 'quest_start'. Si no hay, usamos un 'hub'.
                possible_giver_locs = locations_by_tag.get('quest_start', locations_by_tag.get('hub', locations_by_tag['all']))
                
                if quest_giver_npc and possible_giver_locs:
                    target_loc = random.choice(possible_giver_locs)
                    self.location_definitions[target_loc]['initial_npcs'].append(quest_giver_npc['id'])
                    quest['starting_npc_id'] = quest_giver_npc['id']
                    placed_npc_ids.add(quest_giver_npc['id'])
                    print(f"    -> Placed Quest Giver '{quest_giver_npc['name']}' in tagged location '{target_loc}'.")

                # 3.2. Colocar al Jefe Final
                boss_archetype = quest.get('boss_archetype')
                boss_npc = next((npc for npc in self.npc_templates.values() if npc.get('role') == boss_archetype), None)
                
                # Buscamos un nodo con tag 'quest_end'. Si no, uno 'dangerous'.
                possible_boss_locs = locations_by_tag.get('quest_end', locations_by_tag.get('dangerous', locations_by_tag['all']))

                if boss_npc and possible_boss_locs:
                    lair_id = random.choice(possible_boss_locs)
                    self.location_definitions[lair_id]['initial_npcs'].append(boss_npc['id'])
                    placed_npc_ids.add(boss_npc['id'])
                    print(f"    -> Placed Boss '{boss_npc['name']}' in tagged location '{lair_id}'.")
                
                # 3.3. Colocar Objetos de Misión
                for step in quest.get('steps', []):
                    objective = step.get('objective', {})
                    if objective.get('type') == 'item':
                        item_id = objective.get('id')
                        if item_id in self.item_templates:
                            # Lo colocamos en una localización peligrosa para que sea un desafío
                            placement_loc_id = random.choice(locations_by_tag.get('dangerous', locations_by_tag['all']))
                            self.location_definitions[placement_loc_id]['initial_items'].append(item_id)
                            placed_item_ids.add(item_id)
                            print(f"    -> Placed Quest Item '{self.item_templates[item_id]['name']}' in '{placement_loc_id}'.")

        # --- 4. PRIORIDAD 2: DISTRIBUCIÓN DEL RESTO DEL CONTENIDO ---
        remaining_npcs = [npc for npc in self.npc_templates.values() if npc['id'] not in placed_npc_ids]
        for npc in remaining_npcs:
            # Usamos afinidades: hostiles en lugares peligrosos, neutrales en cualquier sitio, amistosos en hubs.
            if npc.get('status') == 'hostile' and 'dangerous' in locations_by_tag:
                target_loc = random.choice(locations_by_tag['dangerous'])
            elif npc.get('status') == 'friendly' and 'safe' in locations_by_tag:
                target_loc = random.choice(locations_by_tag['safe'])
            else:
                target_loc = random.choice(locations_by_tag['all'])
            self.location_definitions[target_loc]['initial_npcs'].append(npc['id'])
            
        remaining_items = [item for item in self.item_templates.values() if item['id'] not in placed_item_ids and item['type'] != 'quest']
        for item in remaining_items:
            # Colocamos items de forma aleatoria por todo el mapa
            target_loc = random.choice(locations_by_tag['all'])
            self.location_definitions[target_loc]['initial_items'].append(item['id'])

        print("\n--- Content Placement Complete ---")
        total_npcs = sum(len(loc['initial_npcs']) for loc in self.location_definitions.values())
        total_items = sum(len(loc['initial_items']) for loc in self.location_definitions.values())
        print(f" -> Total NPCs placed: {total_npcs}")
        print(f" -> Total Items placed: {total_items}")

    def assemble_and_save(self, graph: WorldGraph, output_path: str):
        """Assembles the final world data and saves it to a file."""
        print("\n--- Assembling Final World File ---")
        starting_node_id = list(graph.nodes.keys())[0] if graph.nodes else "node_0_0"
        
        try:
            world_def = WorldDefinition(
                id=self.world_id,
                name=self.manifest.get('world_name', 'A New World'),
                style=self.world_theme,
                lore=self.manifest.get('world_description', ''),
                language=self.world_language,
                starting_location_id=starting_node_id,
                main_quests={q['id']: q for q in self.quests}
            ).model_dump()
        except Exception as e:
            print(f"Error creating WorldDefinition Pydantic model: {e}")
            raise

        final_data = {
            "world": world_def,
            "locations": list(self.location_definitions.values()),
            "item_templates": list(self.item_templates.values()),
            "npc_templates": list(self.npc_templates.values()),
            "quests": self.quests,
        }
        
        # Guardar con encoding utf-8 para preservar caracteres especiales
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        print(f"SUCCESS! World import file '{output_path}' has been generated.")


if __name__ == "__main__":
    # --- CONFIGURACIÓN ---
    try:
        # Esto hace las rutas relativas al script, más robusto
        script_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(script_dir) # Sube un nivel desde 'game'

        GRAPH_FILE = os.path.join(project_root, "grid_map_5x5_p50_zoned_structure.json")
        MANIFEST_FILE = os.path.join(project_root, "manifest_Roma.yaml")
        BASE_ITEMS_FILE = os.path.join(project_root, "base_item_templates.json")
        OUTPUT_FILE = os.path.join(project_root, "world_import_generated.json")

        # 1. Cargar el grafo estructural
        with open(GRAPH_FILE, 'r', encoding='utf-8') as f:
            world_graph = WorldGraph(**json.load(f))

        # 2. Inicializar el Director y el proveedor de IA
        ai_provider = GeminiProvider()
        director = DirectorAgent(provider=ai_provider, manifest_path=MANIFEST_FILE, base_items_path=BASE_ITEMS_FILE)

        # 3. Orquestar la creación del mundo
        director.orchestrate_world_creation(world_graph)

        # 4. Guardar el resultado final
        director.assemble_and_save(world_graph, OUTPUT_FILE)

    except FileNotFoundError as e:
        print(f"\nERROR: Could not find a required file: {e}.")
        print("Please ensure your graph, manifest, and base items files exist at the project root.")
    except Exception as e:
        print(f"\nAN UNEXPECTED ERROR OCCURRED: {e}")
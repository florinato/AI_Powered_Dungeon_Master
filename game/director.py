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
        print("\n[Master Thought 2/6]: Designing character roles for this world...")
        density_map = {"low": 3, "medium": 5, "high": 7}
        num_archetypes = density_map.get(density.get('npcs', 'medium'), 5)
        
        prompt = (
            f"You MUST respond in {self.world_language}. "
            f"For a world with theme '{self.world_theme}', brainstorm {num_archetypes} unique character archetypes. "
            f"Examples for a noir theme in Spanish: 'Detective hastiado', 'Viuda misteriosa', 'Policía corrupto'. "
            f"Respond ONLY with a JSON list of strings in {self.world_language}: [\"arquetipo1\", \"arquetipo2\", ...]"
        )
        archetypes = self._generate_creative_json(prompt)
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
        print("\n[Master Thought 5/6]: Designing the main story and quests...")
        density_map = {"low": 1, "medium": 3, "high": 5}
        num_quests = density_map.get(density.get('quests', 'medium'), 3)

        prompt = (
            f"You MUST respond in {self.world_language}. "
            f"Design one compelling main quest for a world with theme '{self.world_theme}'. "
            f"Provide a unique quest ID (e.g., 'CASO_001_ONICE'), a title, a description, and 3-4 major steps. "
            f"The title, description, and steps MUST be in {self.world_language}. "
            f"Also, suggest which NPC archetypes (in {self.world_language}) would be the quest giver and the final boss. "
            "Respond ONLY with the JSON object: {\"id\": \"...\", \"title\": \"...\", \"description\": \"...\", \"steps\": [{\"id\":\"paso1\", \"description\":\"...\"}, ...], \"quest_giver_archetype\": \"...\", \"boss_archetype\": \"...\"}"
        )
        quest_data = self._generate_creative_json(prompt)
        if quest_data and 'id' in quest_data:
            self.quests.append(quest_data)

    def _place_content_in_world(self):
        """
        Coloca todo el contenido generado en el mundo de forma inteligente y robusta.
        """
        print("\n[Master Thought 6/6]: Setting the stage, placing things with purpose...")
        if not self.location_definitions or (not self.npc_templates and not self.item_templates):
            print("  - No content to place. Aborting placement.")
            return

        placement_rules = self.manifest.get('placement_rules', {})
        min_npcs_per_loc = placement_rules.get('min_npcs_per_location', 0)
        
        placed_npc_ids = set()
        
        hub_locations = [loc_id for loc_id, loc in self.location_definitions.items() if loc.get('type') in ['capital_city', 'town', 'safe_zone']]
        if not hub_locations:
            hub_locations = [list(self.location_definitions.keys())[0]]
        
        wild_locations = [loc_id for loc_id in self.location_definitions if loc_id not in hub_locations]

        if self.quests:
            main_quest = self.quests[0]
            quest_giver_archetype = main_quest.get('quest_giver_archetype')
            boss_archetype = main_quest.get('boss_archetype')

            quest_giver_npc = next((npc for npc in self.npc_templates.values() if npc.get('role') == quest_giver_archetype), None)
            if quest_giver_npc:
                quest_giver_id = quest_giver_npc['id']
                self.location_definitions[hub_locations[0]]['initial_npcs'].append(quest_giver_id)
                placed_npc_ids.add(quest_giver_id)
                main_quest['starting_npc_id'] = quest_giver_id
                print(f"  - Placed Quest Giver '{quest_giver_npc['name']}' in hub '{hub_locations[0]}'.")

            boss_npc = next((npc for npc in self.npc_templates.values() if npc.get('role') == boss_archetype), None)
            if boss_npc and wild_locations:
                boss_id = boss_npc['id']
                lair_id = random.choice(wild_locations[len(wild_locations)//2:]) if len(wild_locations) > 1 else wild_locations[0]
                self.location_definitions[lair_id]['initial_npcs'].append(boss_id)
                placed_npc_ids.add(boss_id)
                main_quest['final_boss_id'] = boss_id
                print(f"  - Placed Boss '{boss_npc['name']}' in lair '{lair_id}'.")

                quest_item = next((item for item in self.item_templates.values() if item.get('type') == 'quest'), None)
                if quest_item:
                    self.location_definitions[lair_id]['initial_items'].append(quest_item['id'])
                    print(f"    -> Guarding quest item '{quest_item['name']}'.")

        generic_npcs = [npc for npc_id, npc in self.npc_templates.items() if npc_id not in placed_npc_ids]
        if generic_npcs:
            friendly_generics = [npc for npc in generic_npcs if npc.get('status') != 'hostile']
            hostile_generics = [npc for npc in generic_npcs if npc.get('status') == 'hostile']

            for npc in friendly_generics:
                self.location_definitions[random.choice(hub_locations)]['initial_npcs'].append(npc['id'])
            print(f"  - Distributed {len(friendly_generics)} friendly NPCs in hub locations.")

            for loc_id in wild_locations:
                if 'lair_id' in locals() and loc_id == lair_id: continue
                if random.random() < 0.6 and hostile_generics:
                    self.location_definitions[loc_id]['initial_npcs'].append(random.choice(hostile_generics)['id'])
            print(f"  - Distributed hostile creatures across the wilds.")

        if min_npcs_per_loc > 0:
            print(f"  - Applying rule: Ensure at least {min_npcs_per_loc} NPC(s) per location.")
            filler_npcs = list(self.npc_templates.values())
            if not filler_npcs:
                print("    -> WARNING: No NPCs available to enforce minimum rule.")
            else:
                for loc_id, loc_data in self.location_definitions.items():
                    while len(loc_data.get('initial_npcs', [])) < min_npcs_per_loc:
                        npc_to_add = random.choice(filler_npcs)
                        loc_data['initial_npcs'].append(npc_to_add['id'])
                        print(f"    -> Added filler NPC '{npc_to_add['name']}' to '{loc_data['name']}' to meet minimum.")
                        
        print("  - Finished placing all content.")

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

        GRAPH_FILE = os.path.join(project_root, "grid_map_5x5_p30_structure.json")
        MANIFEST_FILE = os.path.join(project_root, "manifest_cine_negro.yaml")
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
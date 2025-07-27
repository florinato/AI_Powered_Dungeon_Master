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
    def __init__(self, provider: AIProviderInterface, manifest_path: str, base_items_path: str):
        print("--- Director Agent Initialized ---")
        self.provider = provider
        with open(manifest_path, 'r', encoding='utf-8') as f:
            self.manifest = yaml.safe_load(f)
        with open(base_items_path, 'r', encoding='utf-8') as f:
            self.base_item_templates = json.load(f)

        self.world_language = self.manifest.get('language')
        if not self.world_language:
            raise ValueError("FATAL: 'language' key not found in manifest.")

        self.world_id = self.manifest.get('world_id', 'default_world')
        self.world_theme = self.manifest.get('world_theme', 'A mysterious world')
        self.creative_examples = self.manifest.get('creative_examples', {})

        # --- NUEVO: Diccionario de Esquemas de Validación ---
        self.validation_schemas = {
            "location": ["name", "description"],
            "trap": ["name", "description", "damage", "disarm_difficulty"],
            "generic_item": ["name", "description"],
            "quest": ["title", "description", "steps", "key_quest_item", "quest_giver_role", "boss_role"],
            "npc": ["id", "name", "description", "status", "dialogue_prompt"],
            "stats": ["hp", "attack", "xp"]
        }
        
        # Almacenes de contenido
        self.location_definitions: Dict[str, Dict[str, Any]] = {}
        self.item_templates: Dict[str, Dict[str, Any]] = {}
        self.npc_templates: Dict[str, Dict[str, Any]] = {}
        self.quests: List[Dict[str, Any]] = []
        self.traps: Dict[str, Dict[str, Any]] = {}

    def _generate_and_validate_json(self, prompt: str, schema_key: str, max_attempts: int = 3) -> dict | list:
        """
        Genera JSON, lo valida contra un esquema y pide correcciones a la IA si falla.
        """
        required_keys = self.validation_schemas.get(schema_key, [])
        original_prompt = prompt

        for attempt in range(max_attempts):
            print(f"  -> Sending prompt to AI (Attempt {attempt + 1}/{max_attempts}): '{prompt[:80]}...'")
            try:
                response_text = self.provider.generate_text(prompt, temperature=0.7)
                time.sleep(5)
                match = re.search(r'```(?:json)?\s*([\[\{].*?[\]\}])\s*```', response_text, re.DOTALL)
                if match:
                    json_str = match.group(1)
                else:
                    json_match = re.search(r'[\[\{].*?[\]\}]', response_text, re.DOTALL)
                    json_str = json_match.group(0) if json_match else response_text
                json_str = re.sub(r',\s*([\}\]])', r'\1', json_str)
                generated_json = json.loads(json_str)
            except Exception as e:
                print(f"    -> AI generation/parsing failed: {e}")
                prompt = (
                    f"{original_prompt}\n\n"
                    f"PREVIOUS ATTEMPT FAILED. The response was not valid JSON. "
                    f"Please correct the formatting and provide ONLY the valid JSON object. "
                    f"Your invalid response was:\n{response_text}"
                )
                continue

            missing_keys = [key for key in required_keys if key not in generated_json]
            if not missing_keys:
                print("    -> Validation PASSED.")
                return generated_json
            print(f"    -> Validation FAILED. Missing keys: {missing_keys}")
            prompt = (
                f"{original_prompt}\n\n"
                f"PREVIOUS ATTEMPT FAILED. The JSON you provided was missing these required keys: {', '.join(missing_keys)}. "
                f"Please correct your response and include ALL the required keys. "
                f"Your invalid JSON was:\n{json.dumps(generated_json, indent=2)}"
            )
        print(f"  -> CRITICAL: Failed to generate valid JSON for schema '{schema_key}' after {max_attempts} attempts.")
        return {} if isinstance(required_keys, list) and required_keys else []

    def _get_creative_context(self) -> str:
        """Construye una cadena de texto con el contexto creativo del manifiesto."""
        context_parts = [
            f"You are a creative Dungeon Master designing a role-playing game in {self.world_language}.",
            f"The world's theme is: '{self.world_theme}'.",
            f"The historical context is: '{self.manifest.get('historical_context', 'not specified')}'.",
            "Your creations must be coherent, logical, and fit the established theme."
        ]
        if 'location_types' in self.creative_examples:
            context_parts.append(f"Examples of locations include: {', '.join(self.creative_examples['location_types'])}.")
        if 'npc_archetypes_examples' in self.creative_examples:
            context_parts.append(f"Examples of character archetypes include: {', '.join(self.creative_examples['npc_archetypes_examples'])}.")
        return "\n".join(context_parts)

    def orchestrate_world_creation(self, graph: WorldGraph):
        """Orquesta el proceso completo basándose en el blueprint del Arquitecto."""
        print("\n--- Starting World Orchestration (Blueprint-Driven) ---")
        
        # --- ¡CORREGIDO! Accedemos a los atributos con . en lugar de .get() ---
        total_npcs_needed = sum(node.npc_count for node in graph.nodes.values())
        total_items_needed = sum(node.item_count for node in graph.nodes.values())
        total_quests_needed = sum(1 for node in graph.nodes.values() if node.has_quest_start)
        total_traps_needed = sum(1 for node in graph.nodes.values() if node.has_trap)
        
        print(f"  -> Blueprint requires: {total_quests_needed} Quests, {total_npcs_needed} NPCs, {total_items_needed} Items, {total_traps_needed} Traps.")
        
        # El resto de la cadena de montaje
        self._create_themed_locations(graph)
        self._create_themed_traps(total_traps_needed)
        self._create_generic_items(total_items_needed)
        self._design_quests_and_key_assets(total_quests_needed)
        self._create_generic_npcs(total_npcs_needed)
        self._place_content_in_world(graph)
        
        print("\n--- Orchestration Complete ---")

    def _create_themed_locations(self, graph: WorldGraph):
        print("\n[Stage 1.1] Creating themed locations...")
        creative_context = self._get_creative_context()
        for node_id, node in graph.nodes.items():
            prompt = (
                f"{creative_context}\n\n"
                f"**Task:** Invent a unique and evocative name and a 2-sentence atmospheric description for a location with these properties: type='{node.type}', tags={node.tags}.\n"
                f"Respond ONLY with the JSON object: {{\"name\": \"...\", \"description\": \"...\"}}"
            )
            content = self._generate_and_validate_json(prompt, schema_key="location")
            loc_def = LocationDefinition(
                id=node_id,
                world_id=self.world_id,
                name=content.get('name', f"Unnamed Location"),
                description=content.get('description', 'A mysterious place.'),
                type=node.type,
                tags=node.tags,
                connections={conn['direction']: conn['target_node_id'] for conn in node.connections},
                initial_npcs=[],
                initial_items=[],
                traps={}
            )
            self.location_definitions[node_id] = loc_def.model_dump()

    def _create_themed_traps(self, num_traps_needed: int):
        print(f"\n[Stage 1.2] Creatively designing {num_traps_needed} themed traps...")
        if num_traps_needed == 0: return
        creative_context = self._get_creative_context()
        for i in range(num_traps_needed):
            prompt = (
                f"{creative_context}\n\n"
                f"**Task:** Invent a creative, thematic trap. Provide a `name`, a detailed `description`, a `damage` value (10-50), and a `disarm_difficulty` ('simple', 'challenging', 'very_challenging').\n"
                f"Respond ONLY with the JSON object."
            )
            trap_data = self._generate_and_validate_json(prompt, schema_key="trap")
            if trap_data and 'name' in trap_data and 'damage' in trap_data:
                trap_id = f"trap_{trap_data['name'].encode('ascii', 'ignore').decode('ascii').lower().replace(' ', '_')}_{random.randint(100,999)}"
                self.traps[trap_id] = {**trap_data, "id": trap_id, "triggered": False}

    def _create_generic_items(self, num_items_needed: int):
        print(f"\n[Stage 1.3] Creating {num_items_needed} generic themed items...")
        if num_items_needed == 0: return
        creative_context = self._get_creative_context()
        templates = [t for t in self.base_item_templates.values() if t.get('type') != 'quest']
        for _ in range(num_items_needed):
            base_data = random.choice(templates)
            prompt = (
                f"{creative_context}\n\n"
                f"**Task:** Give a unique, thematic name and description for a '{base_data['type']}' item.\n"
                "Respond ONLY with the JSON object: {\"name\": \"...\", \"description\": \"...\"}"
            )
            themed_data = self._generate_and_validate_json(prompt, schema_key="generic_item")
            final_item = {**base_data, **themed_data}
            safe_name = themed_data.get('name', f'item_{base_data["type"]}').encode('ascii', 'ignore').decode('ascii').lower().replace(' ', '_')
            final_item['id'] = f"{safe_name}_{random.randint(100,999)}"
            self.item_templates[final_item['id']] = final_item

    def _design_quests_and_key_assets(self, num_quests_needed: int):
        print(f"\n[Stage 2.1] Creatively designing {num_quests_needed} quests from scratch...")
        if num_quests_needed == 0: return
        creative_context = self._get_creative_context()
        for i in range(num_quests_needed):
            print(f"  -> Inventing Quest {i+1}/{num_quests_needed}...")
            prompt = (
                f"{creative_context}\n\n"
                f"**Your Task:** Invent a NEW, original quest that fits the world.\n"
                f"**Instructions for the JSON response:**\n"
                f"- `title`: A compelling title for the quest.\n"
                f"- `description`: A detailed plot description.\n"
                f"- `steps`: A list of 3 logical steps, each with a `description` and a structured `objective` (e.g., {{\"type\": \"item\", \"id\": \"daga_secreta\"}}).\n"
                f"- `key_quest_item`: An object for a crucial item for this quest, with its own `id`, `name`, and `description`.\n"
                f"- `quest_giver_role`: **Invent** a short, descriptive role for the character who gives the quest (e.g., 'a cynical spymaster who needs a deniable agent').\n"
                f"- `boss_role`: **Invent** a short, descriptive role for the main antagonist (e.g., 'a charismatic cult leader manipulating senators').\n"
                f"Respond ONLY with the complete JSON object for this single quest."
            )
            quest_data = self._generate_and_validate_json(prompt, schema_key="quest")
            if not (quest_data and 'title' in quest_data and 'steps' in quest_data and 'quest_giver_role' in quest_data):
                print(f"    -> FAILED to generate a valid quest structure. Skipping.")
                continue
            quest_data['id'] = f"QUEST_{quest_data['title'].encode('ascii', 'ignore').decode('ascii').upper().replace(' ', '_')}_{random.randint(100,999)}"
            key_item_info = quest_data.pop('key_quest_item', {})
            if 'id' in key_item_info:
                item_id = key_item_info['id']
                self.item_templates[item_id] = {**self.base_item_templates["QUEST_ITEM_MACGUFFIN"], **key_item_info, "template_id": "QUEST_ITEM_MACGUFFIN"}
            quest_giver_role = quest_data.get('quest_giver_role')
            if quest_giver_role:
                giver_npc = self._create_npc_for_role(quest_giver_role, 'quest_giver', quest_data['title'])
                if giver_npc:
                    quest_data['starting_npc_id'] = giver_npc['id']
                    self.npc_templates[giver_npc['id']] = giver_npc
                    print(f"    -> Invented Quest Giver: '{giver_npc['name']}' (Role: {quest_giver_role})")
            boss_role = quest_data.get('boss_role')
            if boss_role:
                boss_npc = self._create_npc_for_role(boss_role, 'boss', quest_data['title'])
                if boss_npc:
                    quest_data['final_boss_id'] = boss_npc['id']
                    self.npc_templates[boss_npc['id']] = boss_npc
                    print(f"    -> Invented Boss: '{boss_npc['name']}' (Role: {boss_role})")
            self.quests.append(quest_data)

    def _create_npc_for_role(self, narrative_role: str, function_in_story: str, quest_context: str) -> Dict | None:
        print(f"  -> Inventing a specific NPC for the story function '{function_in_story}' described as: '{narrative_role}'...")
        creative_context = self._get_creative_context()
        prompt = (
            f"{creative_context}\n\n"
            f"**Your Task:** Create a specific, unique character who fits this **narrative role**: '{narrative_role}'.\n"
            f"This character will serve as the '{function_in_story}' in a story about '{quest_context}'.\n"
            f"Give them a fitting `name`, `description`, `status` (friendly/neutral/hostile), and a `dialogue_prompt` that captures their personality. Also provide a unique `id`.\n"
            f"Respond ONLY with the JSON object."
        )
        npc_data = self._generate_and_validate_json(prompt, schema_key="npc")
        if npc_data and 'id' in npc_data:
            stats_prompt = f"Based on '{npc_data.get('description', '')}', provide balanced stats (hp, attack, xp). JSON ONLY."
            stats = self._generate_and_validate_json(stats_prompt, schema_key="stats")
            npc_data.update(stats or {})
            npc_data['assigned_role'] = function_in_story
            npc_data['narrative_role'] = narrative_role
            return npc_data
        return None

    def _create_generic_npcs(self, num_npcs_needed: int):
        num_extras_to_create = num_npcs_needed - len(self.npc_templates)
        if num_extras_to_create <= 0: return
        
        print(f"\n[Stage 3.1] Creatively designing {num_extras_to_create} generic world inhabitants (extras)...")
        creative_context = self._get_creative_context()

        for i in range(num_extras_to_create):
            # Le pedimos a la IA que se invente un rol para un extra
            prompt_role = (
                f"{creative_context}\n\n"
                f"**Your Task:** Invent a simple, one-sentence role for a generic background character in this world.\n"
                f"Example roles might be: 'a gossiping street vendor', 'a weary legionary on leave', 'a nervous patrician's body-slave'.\n"
                f"Respond with a single JSON object: {{\"role\": \"...\"}}"
            )
            role_data = self._generate_and_validate_json(prompt_role, schema_key="npc")
            narrative_role = role_data.get('role', 'a generic citizen')

            print(f"  -> Inventing extra NPC {i+1}/{num_extras_to_create} with role: '{narrative_role}'...")
            generic_npc = self._create_npc_for_role(narrative_role, "extra", "the daily life of the world")
            if generic_npc and generic_npc['id'] not in self.npc_templates:
                self.npc_templates[generic_npc['id']] = generic_npc

    def _place_content_in_world(self, graph: WorldGraph):
        print("\n[Stage 4.1] Placing all content according to the blueprint...")
        if not self.location_definitions: return

        # Preparamos listas de nuestro contenido para poder distribuirlo
        all_quests = self.quests[:]
        all_traps = list(self.traps.values())
        quest_givers = [npc for npc in self.npc_templates.values() if npc.get('assigned_role') == 'quest_giver']
        bosses = [npc for npc in self.npc_templates.values() if npc.get('assigned_role') == 'boss']
        extras = [npc for npc in self.npc_templates.values() if npc.get('assigned_role') == 'extra']
        quest_items = [item for item in self.item_templates.values() if item.get('type') == 'quest']
        generic_items = [item for item in self.item_templates.values() if item.get('type') != 'quest']

        # Iteramos sobre CADA NODO del plano y cumplimos sus requisitos
        for node_id, node_blueprint in graph.nodes.items():
            location = self.location_definitions[node_id]
            
            # --- ¡CORREGIDO! Usamos . en lugar de .get() para acceder a los atributos del blueprint ---
            
            # 1. Colocar Misión (si el plano lo pide)
            if node_blueprint.has_quest_start and all_quests:
                quest_to_place = all_quests.pop(0)
                giver_id = quest_to_place.get('starting_npc_id')
                giver_npc = next((g for g in quest_givers if g['id'] == giver_id), None)
                if giver_npc:
                    location['initial_npcs'].append(giver_npc['id'])
                    quest_givers.remove(giver_npc)

            # 2. Colocar NPCs (el número exacto que pide el plano)
            num_npcs_to_place = node_blueprint.npc_count
            while len(location['initial_npcs']) < num_npcs_to_place:
                npc_pool = bosses or extras
                if not npc_pool: break
                npc_to_place = npc_pool.pop(0)
                location['initial_npcs'].append(npc_to_place['id'])
            
            # 3. Colocar Items (el número exacto que pide el plano)
            num_items_to_place = node_blueprint.item_count
            while len(location['initial_items']) < num_items_to_place:
                item_pool = quest_items or generic_items
                if not item_pool: break
                item_to_place = item_pool.pop(0)
                location['initial_items'].append(item_to_place['id'])

            # 4. Colocar Trampa (si el plano lo pide)
            if node_blueprint.has_trap and all_traps:
                trap_to_place = all_traps.pop(0)
                location.setdefault('traps', {})[trap_to_place['id']] = trap_to_place
        
        print("--- Blueprint-driven placement complete ---")

    def assemble_and_save(self, graph: WorldGraph, output_path: str):
        print("\n--- Assembling Final World File ---")
        starting_node_id = list(graph.nodes.keys())[0] if graph.nodes else "node_0_0"
        main_quests_dict = {q['id']: q for q in self.quests}
        try:
            world_def_data = {
                "id": self.world_id, "name": self.manifest.get('world_name', 'A New World'),
                "style": self.world_theme, "lore": self.manifest.get('world_description', ''),
                "language": self.world_language, "inhabitant_description": self.manifest.get('inhabitant_description'),
                "starting_location_id": starting_node_id, "main_quests": main_quests_dict
            }
            world_def = WorldDefinition(**world_def_data).model_dump()
        except Exception as e:
            print(f"--- CRITICAL FAILURE: Error creating WorldDefinition Pydantic model. ---")
            print(f"  -> Error: {e}")
            raise
        final_data = {
            "world": world_def, "locations": list(self.location_definitions.values()),
            "item_templates": list(self.item_templates.values()),
            "npc_templates": list(self.npc_templates.values()), "quests": self.quests,
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        print(f"\n--- SUCCESS! World import file '{output_path}' has been generated. ---")
        print(f" -> Contained {len(self.quests)} quests.")
        print(f" -> Contained {len(self.npc_templates)} NPC templates.")
        print(f" -> Contained {len(self.item_templates)} item templates.")
        print("-----------------------------------------------------------------")

if __name__ == "__main__":
    try:
        script_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(script_dir)
        GRAPH_FILE = os.path.join(project_root, "grid_map_3x3_p60_blueprint.json")
        MANIFEST_FILE = os.path.join(project_root, "manifest_Roma.yaml")
        BASE_ITEMS_FILE = os.path.join(project_root, "base_item_templates.json")
        OUTPUT_FILE = os.path.join(project_root, "world_import_generated.json")
        with open(GRAPH_FILE, 'r', encoding='utf-8') as f:
            world_graph = WorldGraph(**json.load(f))
        ai_provider = GeminiProvider()
        director = DirectorAgent(provider=ai_provider, manifest_path=MANIFEST_FILE, base_items_path=BASE_ITEMS_FILE)
        director.orchestrate_world_creation(world_graph)
        director.assemble_and_save(world_graph, OUTPUT_FILE)
    except FileNotFoundError as e:
        print(f"\nERROR: Could not find a required file: {e}.")
    except Exception as e:
        print(f"\nAN UNEXPECTED ERROR OCCURRED: {e}")

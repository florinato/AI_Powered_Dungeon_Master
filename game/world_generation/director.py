# game/director.py
import json
import os
import random
import re
import time
from typing import Any, Dict, List

import yaml

from game.ai.ai_factory import get_ai_provider
from game.ai.ai_provider_interface import AIProviderInterface
from game.core.models import LocationDefinition, WorldDefinition, WorldGraph


class DirectorAgent:
    # __init__ no cambia
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

        self.validation_schemas = {
            "location": ["name", "description"],
            "trap": ["name", "description", "damage", "disarm_difficulty"],
            "generic_item": ["name", "description"],
            "quest": ["title", "description", "steps", "key_quest_item", "quest_giver_role", "boss_role"],
            "npc": ["id", "name", "description", "status", "dialogue_prompt"],
            "stats": ["hp", "attack", "xp"]
        }
        
        self.location_definitions: Dict[str, Dict[str, Any]] = {}
        self.item_templates: Dict[str, Dict[str, Any]] = {}
        self.npc_templates: Dict[str, Dict[str, Any]] = {}
        self.quests: List[Dict[str, Any]] = []
        self.traps: Dict[str, Dict[str, Any]] = {}
        self.narrative_node_map: Dict[str, str] = {}
        
    # _generate_and_validate_json no cambia
    def _generate_and_validate_json(self, prompt: str, schema_key: str, max_attempts: int = 3) -> dict | list:
        required_keys = self.validation_schemas.get(schema_key, [])
        original_prompt = prompt

        for attempt in range(max_attempts):
            print(f"  -> Sending prompt to AI (Attempt {attempt + 1}/{max_attempts}): '{prompt[:80]}...'")
            try:
                response_text = self.provider.generate_text(prompt, temperature=0.7)
                time.sleep(2) 
                
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
                prompt = (f"{original_prompt}\n\nPREVIOUS ATTEMPT FAILED. The response was not valid JSON. Please correct the formatting and provide ONLY the valid JSON object. Your invalid response was:\n{response_text}")
                continue

            check_target = generated_json[0] if isinstance(generated_json, list) and generated_json else generated_json
            if not isinstance(check_target, dict):
                prompt = (f"{original_prompt}\n\nPREVIOUS ATTEMPT FAILED. The response was not a JSON object. Please provide ONLY the valid JSON object. Your invalid response was:\n{json.dumps(generated_json, indent=2)}")
                continue

            missing_keys = [key for key in required_keys if key not in check_target]

            if not missing_keys:
                print("    -> Validation PASSED.")
                return generated_json
            print(f"    -> Validation FAILED. Missing keys: {missing_keys}")
            prompt = (f"{original_prompt}\n\nPREVIOUS ATTEMPT FAILED. The JSON you provided was missing these required keys: {', '.join(missing_keys)}. Please correct your response and include ALL the required keys. Your invalid JSON was:\n{json.dumps(generated_json, indent=2)}")
        
        print(f"  -> CRITICAL: Failed to generate valid JSON for schema '{schema_key}' after {max_attempts} attempts.")
        return {} if schema_key in ["location", "trap", "generic_item", "quest", "npc", "stats"] else []


    # --- PROMPT REVISADO (POSITIVO) ---
    def _get_creative_context(self) -> str:
        """Construye una cadena de texto con el contexto creativo del manifiesto, enfocado en directrices positivas."""
        context_parts = [
            f"You are a world-building AI. Your SOLE source of truth is the following manifest. You MUST adhere strictly to its theme, tone, and language to create a coherent and playable game world.",
            f"**World Theme:** '{self.world_theme}'. All your creations must feel like they belong in this specific universe.",
            f"**Context:** '{self.manifest.get('historical_context', 'not specified')}'. This defines the available technology, architectural styles, and societal norms.",
            f"**Language:** You must respond in '{self.world_language}'.",
        ]
        
        if 'location_types' in self.creative_examples:
            context_parts.append(f"**Inspirational Location Examples:** {', '.join(self.creative_examples['location_types'])}. Use these as a style guide for your own original ideas.")
        if 'npc_archetypes_examples' in self.creative_examples:
            context_parts.append(f"**Inspirational Inhabitant Examples:** {', '.join(self.creative_examples['npc_archetypes_examples'])}. Inhabitants should align with this style and the description: '{self.manifest.get('inhabitant_description', '')}'.")
        
        context_parts.append("Your goal is to generate content that is logical, thematically consistent, and enhances the gameplay experience.")
        return "\n".join(context_parts)

    def orchestrate_world_creation(self, graph: WorldGraph):
        # (Esta función no cambia)
        print("\n--- Starting World Orchestration (Blueprint-Driven) ---")
        
        total_npcs_needed = sum(node.npc_count for node in graph.nodes.values())
        total_items_needed = sum(node.item_count for node in graph.nodes.values())
        total_quests_needed = sum(1 for node in graph.nodes.values() if node.has_quest_start)
        total_traps_needed = sum(1 for node in graph.nodes.values() if node.has_trap)
        
        print(f"  -> Blueprint requires: {total_quests_needed} Quests, {total_npcs_needed} NPCs, {total_items_needed} Items, {total_traps_needed} Traps.")
        
        self._create_themed_locations(graph)
        self._create_themed_traps(total_traps_needed)
        self._design_quests_and_key_assets(total_quests_needed) 
        self._link_narrative_to_spatial_map(graph)
        self._create_generic_items(total_items_needed)
        self._create_generic_npcs(total_npcs_needed)
        self._place_content_in_world(graph)
        
        print("\n--- Orchestration Complete ---")

    # --- PROMPT REVISADO (POSITIVO) ---
    def _create_themed_locations(self, graph: WorldGraph):
        print("\n[Stage 1.1] Creatively designing themed locations for the world map...")
        creative_context = self._get_creative_context()
        generated_names = []

        for node_id, node in graph.nodes.items():
            prompt = (
                f"{creative_context}\n\n"
                f"**Your Task:** Describe a single location for this world. Invent a unique, evocative name and a 2-sentence atmospheric description that are PERFECTLY ALIGNED with the world's theme and context.\n"
                f"**Location Properties:** This location should be suitable for a node with type='{node.type}' and tags={node.tags}.\n"
                f"**Guideline:** The name and description must be specific and sound authentic to the established world. For example, for a sci-fi theme, a name like 'Sector Gamma-7 Observation Deck' is highly thematic.\n"
                f"**Previously generated names (do not repeat):** {', '.join(generated_names) if generated_names else 'None'}.\n"
                f"Respond ONLY with the JSON object: {{\"name\": \"...\", \"description\": \"...\"}}"
            )
            content = self._generate_and_validate_json(prompt, schema_key="location")
            if content.get("name"): generated_names.append(content["name"])
            
            loc_def = LocationDefinition(
                id=node_id, world_id=self.world_id,
                name=content.get('name', f"Unnamed Location {node_id}"),
                description=content.get('description', 'A mysterious place.'),
                type=node.type, tags=node.tags,
                connections={conn['direction']: conn['target_node_id'] for conn in node.connections},
            )
            self.location_definitions[node_id] = loc_def.model_dump()

    # --- PROMPT REVISADO (POSITIVO) ---
    def _create_themed_traps(self, num_traps_needed: int):
        print(f"\n[Stage 1.2] Creatively designing {num_traps_needed} themed traps...")
        if num_traps_needed == 0: return
        creative_context = self._get_creative_context()
        for i in range(num_traps_needed):
            prompt = (
                f"{creative_context}\n\n"
                f"**Task:** Invent a creative trap that is technologically and thematically appropriate for this specific world.\n"
                f"**Guideline:** The trap's mechanism should be plausible within the world's context. For a sci-fi theme, a 'Malfunctioning Stasis Field' is a good concept.\n"
                f"**JSON Output:** Provide a `name`, a detailed `description`, a `damage` value (10-50), and a `disarm_difficulty` ('simple', 'challenging', 'very_challenging').\n"
                f"Respond ONLY with the JSON object."
            )
            trap_data = self._generate_and_validate_json(prompt, schema_key="trap")
            if trap_data and 'name' in trap_data:
                trap_id = f"trap_{trap_data['name'].encode('ascii', 'ignore').decode('ascii').lower().replace(' ', '_')}_{random.randint(100,999)}"
                self.traps[trap_id] = {**trap_data, "id": trap_id, "triggered": False}

    # --- PROMPT REVISADO (POSITIVO) ---
    def _design_quests_and_key_assets(self, num_quests_needed: int):
        print(f"\n[Stage 2.1] Creatively designing {num_quests_needed} quests and their key assets...")
        if num_quests_needed == 0: return
        
        creative_context = self._get_creative_context()
        
        for i in range(num_quests_needed):
            print(f"  -> Inventing Quest {i+1}/{num_quests_needed}...")
            prompt = (
                f"{creative_context}\n\n"
                f"**Your Task:** Invent a NEW, original quest storyline that is PERFECTLY ALIGNED with the world's theme, context, and language.\n"
                f"**Instructions for the JSON response:**\n"
                f"- `title`: A compelling, thematic title.\n"
                f"- `description`: A plot summary that feels native to this world.\n"
                f"- `steps`: A list of 2-3 logical steps. Each must have an `id`, `description`, and a structured `objective`.\n"
                f"  - Objective `type` must be 'item', 'npc', or 'location'.\n"
                f"  - Objective `id` must be a CREATIVE, THEMATIC name (e.g., 'sentient_data_crystal', 'rogue_security_droid', 'main_reactor_chamber'). These should be thematically consistent.\n"
                f"- `key_quest_item`: An object for ONE crucial plot device. Its `id`, `name`, and `description` must fit the theme.\n"
                f"- `quest_giver_role`: Invent a descriptive function for the individual/entity who gives the quest, fitting the world's inhabitants (e.g., 'a cynical corporate liaison', 'an isolated AI consciousness').\n"
                f"- `boss_role`: Invent a descriptive function for the main antagonist (e.g., 'a bio-enhanced mercenary captain', 'a swarm of self-replicating nanites').\n"
                f"Respond ONLY with the complete JSON object for this single quest."
            )
            
            quest_data = self._generate_and_validate_json(prompt, schema_key="quest")
            # ... resto de la función sin cambios
            if not (quest_data and 'title' in quest_data and 'steps' in quest_data and 'quest_giver_role' in quest_data):
                print(f"    -> FAILED to generate a valid quest structure. Skipping.")
                continue
            
            quest_id = f"QUEST_{quest_data['title'].encode('ascii', 'ignore').decode('ascii').upper().replace(' ', '_')}_{random.randint(100,999)}"
            quest_data['id'] = quest_id
            
            giver_npc = self._create_npc_for_role(quest_data['quest_giver_role'], 'quest_giver', quest_data['title'])
            if giver_npc:
                quest_data['starting_npc_id'] = giver_npc['id']
                self.npc_templates[giver_npc['id']] = giver_npc
                print(f"    -> Created Quest Giver: '{giver_npc['name']}' (ID: {giver_npc['id']})")

            boss_npc = self._create_npc_for_role(quest_data['boss_role'], 'boss', quest_data['title'])
            if boss_npc:
                quest_data['final_boss_id'] = boss_npc['id']
                self.npc_templates[boss_npc['id']] = boss_npc
                print(f"    -> Created Boss: '{boss_npc['name']}' (ID: {boss_npc['id']})")
                for step in quest_data.get('steps', []):
                    if step.get('objective', {}).get('type') == 'npc':
                         step['objective']['id'] = boss_npc['id']
                         print(f"    -> Linked Boss to quest step objective.")

            key_item_info = quest_data.pop('key_quest_item', {})
            if 'name' in key_item_info:
                item_id = f"qitem_{key_item_info['name'].encode('ascii', 'ignore').decode('ascii').lower().replace(' ', '_')}_{random.randint(100,999)}"
                key_item_info['id'] = item_id
                self.item_templates[item_id] = {**self.base_item_templates["QUEST_ITEM_MACGUFFIN"], **key_item_info}
                print(f"    -> Created Key Quest Item: '{key_item_info['name']}' (ID: {item_id})")
                for step in quest_data.get('steps', []):
                    if step.get('objective', {}).get('type') == 'item':
                         step['objective']['id'] = item_id
                         print(f"    -> Linked Key Item to quest step objective.")

            self.quests.append(quest_data)

    def _link_narrative_to_spatial_map(self, graph: WorldGraph):
        # (Esta función no cambia, su lógica es correcta)
        print("\n[Stage 2.2] Linking narrative objectives to the spatial map...")
        available_nodes = list(graph.nodes.keys())
        
        quest_start_nodes = [node.id for node in graph.nodes.values() if node.has_quest_start]
        random.shuffle(quest_start_nodes)
        
        for quest in self.quests:
            if quest_start_nodes and 'starting_npc_id' in quest:
                node_id = quest_start_nodes.pop(0)
                self.narrative_node_map[quest['starting_npc_id']] = node_id
                if node_id in available_nodes: available_nodes.remove(node_id)
                print(f"  -> Mapping Quest Giver '{quest['starting_npc_id']}' to start node '{node_id}'.")

            if available_nodes and 'final_boss_id' in quest:
                node_id = available_nodes.pop(-1)
                self.narrative_node_map[quest['final_boss_id']] = node_id
                print(f"  -> Mapping Boss '{quest['final_boss_id']}' to end node '{node_id}'.")

        for quest in self.quests:
            for step in quest.get('steps', []):
                objective = step.get('objective', {})
                if objective.get('type') == 'location':
                    narrative_loc_id = objective['id']
                    if narrative_loc_id in self.narrative_node_map:
                        objective['id'] = self.narrative_node_map[narrative_loc_id]
                        continue

                    if available_nodes:
                        chosen_node_id = random.choice(available_nodes)
                        available_nodes.remove(chosen_node_id)
                        self.narrative_node_map[narrative_loc_id] = chosen_node_id
                        original_id = objective['id']
                        objective['id'] = chosen_node_id
                        print(f"  -> Mapped narrative location '{original_id}' to physical node '{chosen_node_id}'.")
                    else:
                        fallback_node_id = random.choice(list(graph.nodes.keys()))
                        objective['id'] = fallback_node_id
                        print(f"  -> WARNING: No more available nodes. Mapped '{narrative_loc_id}' to fallback node '{fallback_node_id}'.")

    # --- PROMPT REVISADO (POSITIVO) ---
    def _create_npc_for_role(self, narrative_role: str, function_in_story: str, quest_context: str) -> Dict | None:
        print(f"  -> Inventing a specific NPC for the function '{function_in_story}' described as: '{narrative_role}'...")
        creative_context = self._get_creative_context()
        
        prompt = (
            f"{creative_context}\n\n"
            f"**Your Task:** Create a specific, unique individual/entity who fits this **narrative function**: '{narrative_role}'.\n"
            f"This entity serves the function of '{function_in_story}' in a story about '{quest_context}'.\n"
            f"**Guideline:** Their appearance, name, and personality MUST be deeply rooted in the world's specific theme and context.\n"
            f"**JSON Output:** Give them a fitting `name`, `description`, `status` (friendly/neutral/hostile), a `dialogue_prompt` capturing their personality, and a simple one-word `id`.\n"
            f"Respond ONLY with the JSON object."
        )
        npc_data = self._generate_and_validate_json(prompt, schema_key="npc")
        
        # ... resto de la función sin cambios
        if npc_data and 'name' in npc_data and 'id' in npc_data:
            npc_data['id'] = f"{npc_data['id'].upper()}_{random.randint(100,999)}"
            
            stats_prompt = (
                f"Based on this description for a '{function_in_story}': '{npc_data.get('description', '')}', provide balanced stats (hp, attack, xp). "
                f"The stats should be reasonable for the world's theme. Respond ONLY with the JSON object: {{\"hp\": ..., \"attack\": ..., \"xp\": ...}}"
            )
            stats = self._generate_and_validate_json(stats_prompt, schema_key="stats")
            npc_data.update(stats or {})
            
            npc_data['assigned_role'] = function_in_story
            npc_data['narrative_role'] = narrative_role
            return npc_data
        return None

    # --- PROMPT REVISADO (POSITIVO) ---
    def _create_generic_items(self, num_items_needed: int):
        created_item_count = len(self.item_templates)
        num_extras_to_create = num_items_needed - created_item_count
        if num_extras_to_create <= 0: return

        print(f"\n[Stage 3.1] Creating {num_extras_to_create} generic themed items (filler)...")
        creative_context = self._get_creative_context()
        templates = [t for t in self.base_item_templates.values() if t.get('type') != 'quest']
        for _ in range(num_extras_to_create):
            base_data = random.choice(templates)
            prompt = (
                f"{creative_context}\n\n"
                f"**Task:** Give a unique, thematic name and description for a '{base_data['type']}' item. It MUST fit the world's theme.\n"
                f"**Guideline:** A healing item in a sci-fi world could be a 'Bio-foam Canister'. A weapon could be a 'Plasma Cutter'. The name should reflect the world's technology and style.\n"
                "Respond ONLY with the JSON object: {\"name\": \"...\", \"description\": \"...\"}"
            )
            themed_data = self._generate_and_validate_json(prompt, schema_key="generic_item")
            if themed_data and 'name' in themed_data:
                final_item = {**base_data, **themed_data}
                safe_name = themed_data['name'].encode('ascii', 'ignore').decode('ascii').lower().replace(' ', '_')
                final_item['id'] = f"{safe_name}_{random.randint(100,999)}"
                if final_item['id'] not in self.item_templates:
                    self.item_templates[final_item['id']] = final_item

    # --- PROMPT REVISADO (POSITIVO) ---
    def _create_generic_npcs(self, num_npcs_needed: int):
        created_npc_count = len(self.npc_templates)
        num_extras_to_create = num_npcs_needed - created_npc_count
        if num_extras_to_create <= 0: return
        
        print(f"\n[Stage 3.2] Creatively designing {num_extras_to_create} generic world inhabitants (extras)...")
        creative_context = self._get_creative_context()

        for i in range(num_extras_to_create):
            prompt_role = (
                f"{creative_context}\n\n"
                f"**Your Task:** Invent a simple, one-sentence function for a generic background inhabitant that would plausibly exist in this world.\n"
                f"**Guideline:** The function must be consistent with the world's theme and context. For a sci-fi world, 'a navigator charting star maps' or 'a synthetic being servicing droids' are good examples.\n"
                f"Respond with a single JSON object: {{\"role\": \"...\"}}"
            )
            role_data = self._generate_and_validate_json(prompt_role, schema_key="generic_item") 
            narrative_role = role_data.get('role', 'a generic citizen')

            print(f"  -> Inventing extra NPC {i+1}/{num_extras_to_create} with function: '{narrative_role}'...")
            generic_npc = self._create_npc_for_role(narrative_role, "extra", "the daily life of the world")
            if generic_npc and generic_npc['id'] not in self.npc_templates:
                self.npc_templates[generic_npc['id']] = generic_npc

    # El resto de las funciones (_place_content_in_world, assemble_and_save, __main__) no necesitan cambios
    def _place_content_in_world(self, graph: WorldGraph):
        print("\n[Stage 4.1] Placing all content according to the narrative and blueprint...")
        if not self.location_definitions: return

        for npc_id, node_id in self.narrative_node_map.items():
            if node_id in self.location_definitions and npc_id in self.npc_templates:
                location = self.location_definitions[node_id]
                location.setdefault('initial_npcs', []).append(npc_id)

        for quest in self.quests:
            for step in quest.get('steps', []):
                objective = step.get('objective', {})
                if objective.get('type') == 'item':
                    item_id = objective.get('id')
                    quest_giver_node = self.narrative_node_map.get(quest.get('starting_npc_id'))
                    
                    possible_nodes = [nid for nid in graph.nodes.keys() if nid != quest_giver_node]
                    if not possible_nodes: possible_nodes = list(graph.nodes.keys())
                    
                    if item_id in self.item_templates:
                        node_id_for_item = random.choice(possible_nodes)
                        self.location_definitions[node_id_for_item].setdefault('initial_items', []).append(item_id)
                        print(f"  -> Placing Quest Item '{item_id}' at node '{node_id_for_item}'.")
        
        extras = [npc for npc in self.npc_templates.values() if npc.get('assigned_role') == 'extra']
        generic_items = [item for item in self.item_templates.values() if item.get('type') != 'quest']
        all_traps = list(self.traps.values())

        for node_id, node_blueprint in graph.nodes.items():
            location = self.location_definitions[node_id]
            
            needed_npcs = node_blueprint.npc_count
            current_npcs = len(location.get('initial_npcs', []))
            while current_npcs < needed_npcs and extras:
                location['initial_npcs'].append(extras.pop(0)['id'])
                current_npcs += 1

            needed_items = node_blueprint.item_count
            current_items = len(location.get('initial_items', []))
            while current_items < needed_items and generic_items:
                location['initial_items'].append(generic_items.pop(0)['id'])
                current_items += 1
                
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
    # (El main no necesita cambios, solo asegúrate de que los nombres de archivo son correctos)
    try:
        script_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(script_dir) if script_dir else os.getcwd()
        
        GRAPH_FILE = os.path.join(project_root, "../grid_map_3x3_p100_blueprint.json")
        MANIFEST_FILE = os.path.join(project_root, "../manifest_silicoides.yaml")
        BASE_ITEMS_FILE = os.path.join(project_root, "../base_item_templates.json")
        OUTPUT_FILE = os.path.join(project_root, "../world_import_generated.json")
        
        with open(GRAPH_FILE, 'r', encoding='utf-8') as f:
            world_graph_data = json.load(f)
        
        world_graph = WorldGraph(**world_graph_data)
        
        ai_provider: AIProviderInterface = get_ai_provider()
        director = DirectorAgent(provider=ai_provider, manifest_path=MANIFEST_FILE, base_items_path=BASE_ITEMS_FILE)
        
        director.orchestrate_world_creation(world_graph)
        director.assemble_and_save(world_graph, OUTPUT_FILE)

    except FileNotFoundError as e:
        print(f"\nERROR: Could not find a required file: {e}.")
        print(f"Current working directory: {os.getcwd()}")
    except Exception as e:
        import traceback
        print(f"\nAN UNEXPECTED ERROR OCCURRED: {e}")
        traceback.print_exc()

# El bloque __main__ no necesita cambios
if __name__ == "__main__":
    try:
        script_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(script_dir) if script_dir else os.getcwd()
        
        # Asegúrate de que los nombres de archivo sean correctos y apunten a la raíz del proyecto
        GRAPH_FILE = os.path.join(project_root, "grid_map_3x3_p100_blueprint.json")
        MANIFEST_FILE = os.path.join(project_root, "manifest_silicoides.yaml")
        BASE_ITEMS_FILE = os.path.join(project_root, "base_item_templates.json")
        OUTPUT_FILE = os.path.join(project_root, "world_import_generated.json")
        
        # ¡CORRECCIÓN CLAVE!
        # Cargamos el JSON y lo pasamos directamente a Pydantic.
        # Pydantic ahora manejará la validación sin necesidad de parches manuales.
        with open(GRAPH_FILE, 'r', encoding='utf-8') as f:
            world_graph_data = json.load(f)
        
        world_graph = WorldGraph(**world_graph_data)
        
        ai_provider: AIProviderInterface = get_ai_provider()
        director = DirectorAgent(provider=ai_provider, manifest_path=MANIFEST_FILE, base_items_path=BASE_ITEMS_FILE)
        
        # En la orquestación, accedemos a los atributos del blueprint con .
        # Ejemplo dentro de orchestrate_world_creation: node.npc_count
        director.orchestrate_world_creation(world_graph)
        director.assemble_and_save(world_graph, OUTPUT_FILE)

    except FileNotFoundError as e:
        print(f"\nERROR: Could not find a required file: {e}.")
        print(f"Current working directory: {os.getcwd()}")
    except Exception as e:
        import traceback
        print(f"\nAN UNEXPECTED ERROR OCCURRED: {e}")
        traceback.print_exc()
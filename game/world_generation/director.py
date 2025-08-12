# game/world_generation/director.py
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
    """
    The Director Agent - A Manifesto-Driven Creative Engine.
    
    Interprets a detailed narrative manifest to generate all creative content,
    translating character profiles and plot hooks into a faithful, expanded, playable world.
    """
    
    def __init__(self, provider: AIProviderInterface, manifest_path: str, base_items_path: str):
        print("--- Director Agent Initialized (Manifesto-Driven Mode) ---")
        self.provider = provider
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                self.manifest = yaml.safe_load(f)
            print(f"  -> Successfully loaded manifest: '{manifest_path}'")
        except FileNotFoundError:
            print(f"FATAL ERROR: Manifest file not found at '{manifest_path}'")
            raise
            
        with open(base_items_path, 'r', encoding='utf-8') as f:
            self.base_item_templates = json.load(f)

        # --- EXTRACCIÓN ESTRUCTURADA DEL MANIFIESTO ---
        self.world_id = self.manifest.get('world_id', 'unnamed_world')
        self.world_name = self.manifest.get('world_name', 'A New World')
        self.language = self.manifest.get('language', 'English')
        
        inspiration = self.manifest.get('high_level_inspiration', {})
        self.core_concept = inspiration.get('core_concept', 'A mysterious world.')
        
        self.narrative_bible = self.manifest.get('narrative_bible', {})
        self.creative_examples = self.manifest.get('creative_examples', {})

        # --- ESTRUCTURAS DE DATOS INTERNAS ---
        self.location_definitions: Dict[str, Dict[str, Any]] = {}
        self.item_templates: Dict[str, Dict[str, Any]] = {}
        self.npc_templates: Dict[str, Dict[str, Any]] = {}
        self.quests: List[Dict[str, Any]] = []

        self.validation_schemas = {
            "location_details": ["name", "description"],
            "full_npc": ["id", "name", "description", "status", "dialogue_prompt", "hp", "attack", "xp"],
            "expanded_quest": ["title", "description", "steps", "starting_npc_id", "final_boss_role", "key_quest_item"],
        }

    def _generate_and_validate_json(self, prompt: str, schema_key: str, max_attempts: int = 3) -> dict | None:
        """Generates and validates JSON from the AI, returning a dictionary or None."""
        required_keys = self.validation_schemas.get(schema_key, [])
        for attempt in range(max_attempts):
            print(f"  -> AI Call (Schema: {schema_key}, Attempt {attempt + 1}/{max_attempts})")
            try:
                response_text = self.provider.generate_text(prompt, temperature=0.75, max_tokens=2500)
                time.sleep(2)
                
                match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if match:
                    json_str = match.group(1)
                else:
                    json_str = re.search(r'\{.*?\}', response_text, re.DOTALL).group(0)

                json_str = re.sub(r',\s*([\}\]])', r'\1', json_str)
                generated_json = json.loads(json_str)

                if not isinstance(generated_json, dict) or any(key not in generated_json for key in required_keys):
                    raise ValueError(f"Validation failed. Missing keys: {required_keys}")
                
                print("    -> AI Response Validated.")
                return generated_json
            except Exception as e:
                print(f"    -> AI generation/parsing/validation failed: {e}")
                if attempt == max_attempts - 1:
                    print(f"  -> CRITICAL: Failed to get valid JSON for schema '{schema_key}' after {max_attempts} attempts.")
                    return None

    def _get_creative_context(self) -> str:
        """Builds a rich creative context based on the full manifest."""
        context_parts = [
            "You are a world-building AI. Your primary source of truth is the following Narrative Bible. Adhere strictly to its theme, tone, characters, and locations.",
            f"**Language:** You must respond ONLY in '{self.language}'.",
            "--- NARRATIVE BIBLE CONTEXT ---",
            f"**Synopsis:** {self.narrative_bible.get('synopsis', 'Not specified.')}",
        ]
        if main_chars := self.narrative_bible.get('main_characters'):
            context_parts.append("\n**Main Characters:**")
            for char in main_chars:
                context_parts.append(f"- {char.get('name', 'N/A')} ({char.get('aspect', 'N/A')})")
        
        if key_locs := self.narrative_bible.get('key_locations'):
            context_parts.append("\n**Key Locations:**")
            for loc in key_locs:
                context_parts.append(f"- {loc.get('name', 'N/A')}")
            
        context_parts.append("\n--- END OF BIBLE CONTEXT ---")
        return "\n".join(context_parts)

    def orchestrate_world_creation(self, graph: WorldGraph):
        """Orchestrates the world creation process guided by the detailed manifest."""
        print("\n--- Starting World Orchestration (Manifesto-Driven) ---")
        
        num_quests_to_generate = sum(1 for node in graph.nodes.values() if node.has_quest_start)

        self._create_themed_locations(graph)
        self._create_main_cast_npcs()
        self._design_quests_from_hooks(num_quests_to_generate)
        self._place_content_in_world(graph)
        
        print("\n--- Orchestration Complete ---")

    def _create_themed_locations(self, graph: WorldGraph):
        """Generates thematic names and descriptions for the physical nodes of the map."""
        print("\n[Stage 1] Generating Thematic Regions...")
        
        location_suggestions = self.creative_examples.get('location_suggestions', [])
        location_examples_str = ""
        if location_suggestions and isinstance(location_suggestions[0], dict):
            location_examples_str = ', '.join([f"'{loc.get('name', '')}'" for loc in location_suggestions])
        elif location_suggestions:
            location_examples_str = ', '.join(location_suggestions)

        context = (
            f"You are a world builder creating locations for a game in {self.language}.\n"
            f"**Core Concept:** {self.core_concept}\n"
            f"**Inspirational Location Examples:** {location_examples_str}"
        )

        for node_id, node_data in graph.nodes.items():
            prompt = (
                f"{context}\n\n"
                "**Task:** Invent a unique, evocative name and a 2-sentence atmospheric description for a game region. The tone must match the core concept and examples.\n"
                f"Respond ONLY with a JSON object: {{\"name\": \"...\", \"description\": \"...\"}}"
            )
            content = self._generate_and_validate_json(prompt, "location_details")
            content = content or {}
            
            loc_def = LocationDefinition(
                id=node_id, world_id=self.world_id,
                name=content.get('name', f"Unnamed Region {node_id}"),
                description=content.get('description', 'A mysterious place.'),
                type=node_data.type, tags=node_data.tags,
                connections={conn['direction']: conn['target_node_id'] for conn in node_data.connections},
            )
            self.location_definitions[node_id] = loc_def.model_dump()

    def _create_main_cast_npcs(self):
        """Creates NPC templates for the main characters defined in the narrative bible."""
        print("\n[Stage 2] Generating Main Cast NPCs from Narrative Bible...")
        creative_context = self._get_creative_context()
        main_characters = self.narrative_bible.get('main_characters', [])
        
        for char_data in main_characters:
            print(f"  -> Generating NPC for: {char_data.get('name', 'Unknown')}")
            prompt = (
                f"{creative_context}\n\n"
                "**Task:** Create a playable NPC template based on the following character profile.\n\n"
                f"**Character Profile:**\n{yaml.dump(char_data, allow_unicode=True)}\n"
                "**JSON Output:** Generate a JSON object with `id` (e.g., 'EVA_ROSTOVA'), `name`, `description`, `status`, `dialogue_prompt`, `hp`, `attack`, `xp`.\n"
                "Respond ONLY with the JSON object."
            )
            npc_json = self._generate_and_validate_json(prompt, "full_npc")
            if npc_json and npc_json.get('id') not in self.npc_templates:
                self.npc_templates[npc_json['id']] = npc_json
            else:
                print(f"    -> FAILED or duplicate NPC for {char_data.get('name', 'Unknown')}.")
    
    def _design_quests_from_hooks(self, num_quests_to_generate: int):
        """Expands 'plot_hooks' from the manifest into playable quests."""
        print(f"\n[Stage 3] Expanding {num_quests_to_generate} Plot Hooks into Quests...")
        if num_quests_to_generate == 0: return
        
        creative_context = self._get_creative_context()
        plot_hooks = self.narrative_bible.get('plot_hooks', [])
        if not plot_hooks:
            print("  -> WARNING: No plot_hooks in manifest. Cannot generate quests.")
            return

        random.shuffle(plot_hooks)
        main_cast_ids = list(self.npc_templates.keys())
        
        for hook in plot_hooks[:num_quests_to_generate]:
            print(f"  -> Expanding hook: '{hook.get('title', 'Untitled')}'")
            prompt = (
                f"{creative_context}\n\n"
                "**Your Task:** Expand the plot hook below into a complete, logical, 3-step quest.\n\n"
                f"**Plot Hook:**\n{yaml.dump(hook, allow_unicode=True)}\n"
                f"**Available Main Characters (for quest giver):** {main_cast_ids}\n\n"
                "**JSON Output Requirements:**\n"
                "- `title`: Title from the plot hook.\n- `description`: Journal description.\n"
                "- `starting_npc_id`: Choose the MOST LOGICAL character ID from the available list.\n"
                "- `final_boss_role`: Invent a thematic antagonist ROLE for this quest.\n"
                "- `key_quest_item`: An object for ONE crucial plot device with `name` and `description`.\n"
                "- `steps`: **This MUST be a list of DICTIONARIES.** Each dictionary in the list **MUST** have the following keys:\n"
                "  - `id`: A string identifier like 'step_1'.\n"
                "  - `description`: A string describing the step.\n"
                "  - `objective`: A dictionary with 'type' and 'id' keys.\n\n"
                "Respond ONLY with the complete JSON object."
            )
            
            quest_data = self._generate_and_validate_json(prompt, "expanded_quest")
            if quest_data:
                self._process_and_store_quest(quest_data)

    def _process_and_store_quest(self, quest_data: dict):
        """Takes a generated quest, creates its assets (boss, item), and stores it."""
        title = quest_data.get('title', 'UNTITLED')
        quest_id = f"QUEST_{title.encode('ascii', 'ignore').decode('ascii').upper().replace(' ', '_')}_{random.randint(100,999)}"
        quest_data['id'] = quest_id
        
        steps = quest_data.get('steps', [])
        if not all(isinstance(step, dict) for step in steps):
            print(f"    -> CRITICAL WARNING: AI generated 'steps' for quest '{title}' as a list of strings, not dictionaries. Skipping asset linking for this quest.")
            self.quests.append(quest_data)
            return

        boss_role = quest_data.pop('final_boss_role', 'a generic villain')
        boss_npc = self._create_npc_for_role(boss_role, 'boss')
        if boss_npc:
            quest_data['final_boss_id'] = boss_npc['id']
            self.npc_templates[boss_npc['id']] = boss_npc
            for step in steps:
                if step.get('objective', {}).get('type') == 'npc':
                    step['objective']['id'] = boss_npc['id']

        key_item_info = quest_data.pop('key_quest_item', {})
        if 'name' in key_item_info:
            item_id = f"qitem_{key_item_info['name'].encode('ascii', 'ignore').decode('ascii').lower().replace(' ', '_')}_{random.randint(100,999)}"
            key_item_info['id'] = item_id
            self.item_templates[item_id] = {**self.base_item_templates.get("QUEST_ITEM_MACGUFFIN", {}), **key_item_info}
            for step in steps:
                if step.get('objective', {}).get('type') == 'item':
                    step['objective']['id'] = item_id
        
        self.quests.append(quest_data)

    def _create_npc_for_role(self, narrative_role: str, function: str) -> Dict | None:
        """Helper to create a single NPC, usually a boss."""
        print(f"  -> Generating a '{function}' NPC with role: '{narrative_role}'")
        creative_context = self._get_creative_context()
        prompt = (
            f"{creative_context}\n\n"
            f"**Task:** Create a single NPC template for a '{function}' described as '{narrative_role}'.\n"
            "**JSON Output:** `id`, `name`, `description`, `status`, `dialogue_prompt`, `hp`, `attack`, `xp`.\n"
            "Respond ONLY with the JSON object."
        )
        npc_json = self._generate_and_validate_json(prompt, "full_npc")
        if npc_json:
            npc_json['assigned_role'] = function
            return npc_json
        return None

    def _place_content_in_world(self, graph: WorldGraph):
        """Places the generated content into the location definitions using manifest-driven logic."""
        print("\n[Stage 4] Placing all content into the world map...")

        # 1. IDENTIFICAR ASSETS Y NODOS DISPONIBLES
        quest_givers = {q['starting_npc_id'] for q in self.quests if 'starting_npc_id' in q}
        all_mission_npcs = quest_givers.copy()
        for quest in self.quests:
            if final_boss_id := quest.get('final_boss_id'):
                all_mission_npcs.add(final_boss_id)

        main_cast_to_place = {
            npc_id for npc_id in self.npc_templates
            if npc_id not in all_mission_npcs
        }

        quest_start_nodes = [nid for nid, node in graph.nodes.items() if node.has_quest_start]
        random.shuffle(quest_start_nodes)

        # 2. COLOCACIÓN DIRIGIDA (PNJs de Misión)
        for giver_id in quest_givers:
            if quest_start_nodes:
                node_id = quest_start_nodes.pop(0)
                self.location_definitions[node_id].setdefault('initial_npcs', []).append(giver_id)
                print(f"  -> Placed Quest Giver '{giver_id}' at designated start node '{node_id}'.")
        
        available_nodes_for_cast = [nid for nid in self.location_definitions if not self.location_definitions[nid].get('initial_npcs')]
        random.shuffle(available_nodes_for_cast)

        for npc_id in main_cast_to_place:
            if available_nodes_for_cast:
                node_id = available_nodes_for_cast.pop(0)
                self.location_definitions[node_id].setdefault('initial_npcs', []).append(npc_id)
                print(f"  -> Placed Main Cast member '{npc_id}' at '{node_id}'.")
        
        # 3. COLOCACIÓN DE "RELLENO" (Objetos)
        all_item_ids = list(self.item_templates.keys())
        random.shuffle(all_item_ids)
        all_node_ids = list(self.location_definitions.keys())

        for item_id in all_item_ids:
            node_id = random.choice(all_node_ids)
            self.location_definitions[node_id].setdefault('initial_items', []).append(item_id)

    def assemble_and_save(self, output_path: str):
        """Assembles the final world data and saves it to a JSON file."""
        print("\n--- Assembling Final World File ---")
        
        final_data = {
            "world": {
                "id": self.world_id, "name": self.world_name,
                "style": self.core_concept, "lore": self.narrative_bible.get('synopsis', ''),
                "language": self.language, 
                "inhabitant_description": self.manifest.get('inhabitant_description'),
                "starting_location_id": list(self.location_definitions.keys())[0]
            },
            "locations": list(self.location_definitions.values()),
            "item_templates": list(self.item_templates.values()),
            "npc_templates": list(self.npc_templates.values()),
            "quests": self.quests,
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        print(f"\n--- SUCCESS! World import file '{output_path}' has been generated. ---")


if __name__ == '__main__':
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        
        GRAPH_FILE = os.path.join(project_root, "grid_map_3x3_p100_blueprint.json")
        MANIFEST_FILE = os.path.join(project_root, "manifest_world.yaml")
        BASE_ITEMS_FILE = os.path.join(project_root, "base_item_templates.json")
        OUTPUT_FILE = os.path.join(project_root, "world_import_generated.json")
        
        with open(GRAPH_FILE, 'r', encoding='utf-8') as f:
            world_graph = WorldGraph(**json.load(f))
        
        ai_provider = get_ai_provider()
        
        director = DirectorAgent(provider=ai_provider, manifest_path=MANIFEST_FILE, base_items_path=BASE_ITEMS_FILE)
        director.orchestrate_world_creation(world_graph)
        director.assemble_and_save(output_path=OUTPUT_FILE)

    except Exception as e:
        import traceback
        print(f"\nAN UNEXPECTED ERROR OCCURRED: {e}")
        traceback.print_exc()
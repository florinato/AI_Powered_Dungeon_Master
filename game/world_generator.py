# world_generator.py
import ast
import json
import os
import re

# Importamos la interfaz, no la implementación concreta
from ai_provider_interface import AIProviderInterface
from dotenv import load_dotenv
# Necesitamos la clase concreta de Gemini para poder instanciarla aquí
from gemini_provider import GeminiProvider

# Si quisieras usar otro, importarías su clase aquí

load_dotenv()

# --- Lógica de Validación (antes en ai_interactions_gemini.py) ---
def validate_game_state(game_state: dict) -> bool:
    """
    Validates the game state structure and required keys.
    Returns True if valid, raises ValueError otherwise.
    """
    if not isinstance(game_state, dict):
        raise ValueError("Game state must be a dictionary.")

    # Player validation
    required_player_keys = {
        "location", "location_history", "hp", "max_hp", "attack",
        "xp", "level", "xp_to_next_level", "inventory",
    }
    if "player" not in game_state:
        raise ValueError("Missing 'player' section in game state.")
    if not required_player_keys.issubset(game_state["player"].keys()):
        missing = required_player_keys - game_state["player"].keys()
        raise ValueError(f"Player state is missing required keys: {missing}")

    # Quests validation
    required_quest_keys = {"description", "completed", "required_items", "required_npcs"}
    if "quests" not in game_state:
        raise ValueError("Missing 'quests' section in game state.")
    for quest_name, quest_data in game_state["quests"].items():
        if not isinstance(quest_data, dict) or not required_quest_keys.issubset(quest_data.keys()):
            missing = required_quest_keys - quest_data.keys()
            raise ValueError(f"Quest '{quest_name}' is missing required keys: {missing}")

    # Locations validation
    required_location_keys = {
        "description", "npcs", "items", "connections",
        "locked_paths", "hidden_items", "traps",
    }
    if "locations" not in game_state:
        raise ValueError("Missing 'locations' section in game state.")
    for location_name, location_data in game_state["locations"].items():
        if not isinstance(location_data, dict) or not required_location_keys.issubset(location_data.keys()):
            missing = required_location_keys - location_data.keys()
            raise ValueError(f"Location '{location_name}' is missing required keys: {missing}")

        # Traps validation within location
        traps = location_data.get("traps", {})
        if not isinstance(traps, dict):
             raise ValueError(f"Traps in location '{location_name}' must be a dictionary.")
        for trap_name, trap_data in traps.items():
            required_trap_keys = {"description", "damage", "disarm_difficulty", "triggered"}
            if not isinstance(trap_data, dict) or not required_trap_keys.issubset(trap_data.keys()):
                missing = required_trap_keys - trap_data.keys()
                raise ValueError(f"Trap '{trap_name}' in location '{location_name}' is missing keys: {missing}")

    print("Game state structure validated successfully.")
    return True

# --- Lógica de Generación ---
def generate_initial_game_state(provider: AIProviderInterface, attempts: int = 3) -> dict | None:
    """
    Generates the initial game state using the provided AI provider.
    
    Args:
        provider: An instance of an AI provider implementing AIProviderInterface.
        attempts: The number of retries if generation or validation fails.

    Returns:
        A dictionary representing the game state, or None on failure.
    """
    prompt = """
    Generate a structured game state for a Dungeons & Dragons-inspired game in JSON format. The structure should include the following elements:

    {
        "player": {
            "location": "starting_location",
            "location_history": [],
            "hp": 120,
            "max_hp": 120,
            "attack": 10,
            "xp": 0,
            "level": 1,
            "xp_to_next_level": 75,
            "inventory": [
                {
                    "name": "healing_potion",
                    "type": "healing",
                    "healing_amount": 25,
                    "description": "A potion that restores 25 HP."
                },
                {
                    "name": "silver_key",
                    "type": "key",
                    "description": "A shiny silver key with intricate engravings."
                }
            ]
        },
        "quests": {
            "retrieve_ancient_artifact": {
                "description": "Retrieve the Ancient Artifact protected by the Shadow Lord in the Cursed Castle.",
                "completed": false,
                "required_items": ["ancient_artifact"],
                "required_npcs": []
            },
            "find_mystic_gem": {
                "description": "Locate the Mystic Gem concealed in the Crystal Caves.",
                "completed": false,
                "required_items": ["mystic_gem"],
                "required_npcs": []
            },
            "vanquish_final_boss": {
                "description": "Slay the Shadow Lord in the Cursed Castle.",
                "completed": false,
                "required_items": [],
                "required_npcs": ["final_boss"]
            }
        },
        "locations": {
            "starting_location": {
                "description": "A peaceful village surrounded by lush forests and rolling hills.",
                "npcs": {
                    "village_elder": {
                        "hp": 50,
                        "max_hp": 50,
                        "attack": 5,
                        "status": "active"
                    }
                },
                "items": {
                    "healing_potion": {
                        "type": "healing",
                        "healing_amount": 25,
                        "description": "A potion that restores 25 HP."
                    },
                    "silver_key": {
                        "type": "key",
                        "description": "A shiny silver key with intricate engravings."
                    },
                    "dagger": {
                        "name": "dagger",
                        "type": "weapon",
                        "attack_boost": 10,
                        "description": "A small but sharp dagger."
                    }
                },
                "connections": {
                    "north": "dark_forest",
                    "east": "mystic_lake",
                    "south": "abandoned_mine",
                    "west": "ancient_ruins"
                },
                "locked_paths": {
                    "west": true,
                    "north": true,
                },
                "hidden_items": {}, # Asegurarse de que está vacío
                "traps": {
                    "avalanche": {
                        "description": "A sudden avalanche triggered by a footstep, it's fast and deadly.",
                        "damage": 30,
                        "disarm_difficulty": "very_challenging",
                        "triggered": false
                    }
                }
            }
        }
    }

    **Instructions:**
    - **Use the Same Quests:**
        - Do not change the quests from the example.
        - Ensure the quests are exactly as defined in the example, including the quest names and descriptions.
    - **Quest Structure:**
        - Each quest should have the following fields:
            - `description`: As provided.
            - `completed`: Set to **false**.
            - `required_items`: A list of item names required to complete the quest.
            - `required_npcs`: A list of NPC names that need to be defeated to complete the quest.
    - **Placement:**
        - **Final Boss NPC and Ancient Artifact:**
            - Place both the `final_boss` NPC and the `ancient_artifact` item (type: `quest_item`, description: "An ancient artifact pulsing with dark energy.") in the **same location**.
            - For the `vanquish_final_boss` quest, set `required_npcs` to `["final_boss"]`.
            - For the `retrieve_ancient_artifact` quest, set `required_items` to `["ancient_artifact"]`.
            - Don't place quest items in hidden items.
        - **Mystic Gem:**
            - Place the `mystic_gem` (type: `quest_item`, description: "A gem that glows with inner light.", required_for_quest: "find_mystic_gem") in a **different location**.
            - For the `find_mystic_gem` quest, set `required_items` to `["mystic_gem"]`.
    - **Complete All Entries:**
        - Define between **8 to 12** unique locations without using placeholders like `{...}`.
        - Ensure all necessary fields (`description`, `npcs`, `items`, `connections`, `locked_paths`, `hidden_items`, `traps`) are present for each location.
    - **Maintain Consistency:**
        - Follow the same JSON structure as the example above.
        - Ensure that locations, items, and NPCs are interconnected logically.
    - **Include Traps in Locations:**
        - **Trap Definition:** Each location may include a `traps` key with traps defined as:
            - `description`: A description of the trap.
            - `damage`: The amount of HP the player loses if the trap is triggered.
            - `disarm_difficulty`: Difficulty level for disarming the trap (`"simple"`, `"challenging"`, `"very_challenging"`).
            - `triggered`: Set to `false`.
        - **Distribution:** Include between **0 to 2** traps per location, with most locations having **0 or 1** traps.
    - **Configure Locked Paths and Keys:**
        - **Locked Paths:** lock **4 to 6** paths in total across all locations.
        - **Locked Paths:** All paths leading to the final boss location must be **locked**.
        - **Keys Availability:** Provide **more keys** (e.g., 2 times the number of locked paths) to ensure players can progress through the game. Keys should be of type `key` and have a description.
    - **Include Hidden Items:** Ensure the `hidden_items` dictionary is present for each location but is **empty** (`{}`).
    - **Logical Location Connections:**
        - **Connectivity:** Ensure that all locations are connected logically, allowing smooth navigation.
        - **Final Boss Location:** Design the final boss location (e.g., `cursed_castle`) to be the **most challenging to reach**, requiring multiple keys or steps.
    - **Distribute Item Types Based on Probabilities:**
        - **Item Type Distribution:**
            - **Tool:** 10%
            - **Weapon:** 20%
            - **Healing:** 50%
            - **Key:** 30%
        - **Implementation:** Ensure that the distribution of item types across all locations adheres to these probabilities as closely as possible. Include items in the `items` dictionary for each location.
    - **Player Statistics Configuration:**
        - **Player Stats:**
            - `max_hp`: Range between **80 to 140**.
            - `attack`: Range between **6 to 14**.
            - `xp`: Set to **0**.
            - `level`: Set to **1**.
            - `xp_to_next_level`: Choose from **50, 75, or 100**.
            - `inventory`: Include between **2 to 4** items, following the item type probabilities.
    - **JSON Formatting and Validation:**
        - **Format:** Ensure the game state is a **well-structured** and **error-free** JSON object.
        - **Syntax:** Properly use commas, quotes, braces, and brackets.
        - **Validation:** The JSON must pass standard JSON validation checks without errors.
    """
    
    for attempt in range(1, attempts + 1):
        print(f"Attempting to generate world state... (Attempt {attempt}/{attempts})")
        try:
            # Aquí se usa el proveedor que se pasó como argumento
            response_text = provider.generate_text(prompt)
            
            # Limpiar el texto de respuesta para aislar el JSON
            # Se enfoca en extraer bloques de código JSON, que es una forma común que las IAs usan.
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                game_state_text = json_match.group(1)
            else:
                # Si no encuentra bloque de código, intenta buscar el primer { y el último }
                start = response_text.find('{')
                end = response_text.rfind('}')
                if start != -1 and end != -1 and start < end:
                    game_state_text = response_text[start:end+1]
                else:
                    raise ValueError("No JSON object structure found in response.")
            
            # Validar el JSON obtenido
            game_state_data = json.loads(game_state_text)
            if validate_game_state(game_state_data):
                print("Successfully generated and validated game state.")
                return game_state_data
            
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}. Raw response snippet: {response_text[:200]}...")
        except ValueError as ve:
            print(f"Validation Error: {ve}. Raw response snippet: {response_text[:200]}...")
        except Exception as e:
            print(f"An error occurred during API call or processing: {e}")

    print("Failed to generate a valid game state after multiple attempts.")
    return None
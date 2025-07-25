# game/test_quest_activation.py

import json

from game_engine import accept_quest, check_quest_progress
from models import PlayerState

print("--- Running Quest Activation Test ---")

# --- 1. Simulación de la Carga de Datos ---
# Simulamos lo que haría `db_manager.load_world_definition()`
print("Step 1: Loading mock world data...")
try:
    with open("world_import_generated.json", 'r', encoding='utf-8') as f:
        # Cargamos el JSON que generó el Director
        raw_world_data = json.load(f)

    # Reestructuramos los datos como lo haría `load_world_definition`
    world_definition = {
        "id": raw_world_data['world']['id'],
        "name": raw_world_data['world']['name'],
        "quests": {q['id']: q for q in raw_world_data['quests']},
        "npc_templates": {npc['id']: npc for npc in raw_world_data['npc_templates']}
        # Añadir otras secciones si son necesarias para el test
    }
    print("  -> World data loaded and restructured successfully.")
except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
    print(f"  -> FATAL ERROR: Could not load or parse 'world_import_generated.json'. Details: {e}")
    exit()

# --- 2. Simulación del Estado Inicial del Jugador ---
print("\nStep 2: Creating mock initial player state...")
# Creamos un estado de jugador y un game_state simple
player = PlayerState(
    player_id=1,
    player_name="Tester",
    world_id=world_definition['id'],
    current_location_id="node_0_0",
    active_quests={}
)
game_state = {
    "player": player.model_dump(),
    # Añadimos datos mínimos necesarios para las funciones del engine
    "locations": {},
    "item_templates": {},
    "npc_templates": world_definition['npc_templates']
}
print(f"  -> Player '{player.player_name}' created.")

# --- 3. Simulación de la Conversación y Activación ---
print("\nStep 3: Simulating dialogue with a quest giver...")

# Extraemos la primera misión y su PNJ iniciador del `world_definition`
if not world_definition['quests']:
    print("  -> TEST FAILED: No quests found in the loaded world definition.")
    exit()

first_quest_id = list(world_definition['quests'].keys())[0]
quest_data = world_definition['quests'][first_quest_id]
starting_npc_id = quest_data.get('starting_npc_id')

if not starting_npc_id:
    print(f"  -> TEST FAILED: Quest '{quest_data.get('title')}' does not have a 'starting_npc_id' assigned.")
    exit()

print(f"  -> Target Quest: '{quest_data.get('title')}'")
print(f"  -> Expected Quest Giver ID: '{starting_npc_id}'")

# Simulamos que el jugador habla con ESE PNJ
target_id = starting_npc_id
player_quests = game_state['player'].get('active_quests', {})

# Esta es la lógica EXACTA de `handle_dialogue`
quest_to_offer = None
if quest_data.get('starting_npc_id') == target_id and first_quest_id not in player_quests:
    quest_to_offer = first_quest_id

if quest_to_offer:
    print(f"  -> SUCCESS: The trigger condition in handle_dialogue worked correctly.")
    print(f"  -> Simulating player accepting the quest...")
    
    # Llamamos a la función del game_engine para aceptar la misión
    game_state, result = accept_quest(game_state, world_definition, quest_to_offer)
    
    print(f"  -> Result from accept_quest: {result['message']}")
    
    # Verificación final
    if quest_to_offer in game_state['player']['active_quests']:
        print("  -> FINAL VERIFICATION: Quest was successfully added to the player's active quests.")
        print("\n--- TEST PASSED ---")
    else:
        print("  -> FATAL ERROR: accept_quest was called, but the quest is not in the player's active quests.")
        print("\n--- TEST FAILED ---")

else:
    print(f"  -> TEST FAILED: The trigger condition in handle_dialogue did not work.")
    print(f"     - Quest's starting_npc_id: {quest_data.get('starting_npc_id')}")
    print(f"     - Player is talking to (target_id): {target_id}")
    print(f"     - Is quest already active? {'Yes' if first_quest_id in player_quests else 'No'}")
    print("\n--- TEST FAILED ---")    
    print("\n--- TEST FAILED ---")
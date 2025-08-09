# refact/game_setup.py
import copy
import json
from typing import Optional

from game.data.db_manager import (get_db_connection, load_world_definition,
                        save_player_state)
from game.core.models import PlayerQuestState, PlayerState


def create_new_character(world_id: str, player_name: str) -> Optional[PlayerState]:
    """
    Crea un nuevo estado de jugador para una nueva partida en un mundo específico.
    """
    print(f"Creating new character '{player_name}' in world '{world_id}'...")
    
    # 1. Load world definition to get the starting location
    world_def = load_world_definition(world_id)
    if not world_def:
        return None

    # 2. Create initial PlayerState object
    # Note: player_id is None because the DB will assign it automatically.
    
    starting_location = world_def.get('starting_location_id')
    if not starting_location:
        print(f"Error: World '{world_id}' has no starting_location_id defined.")
        return None
    
    initial_state = PlayerState(
        player_name=player_name,
        world_id=world_id,
        current_location_id=starting_location
        # Other values use Pydantic defaults
    )

    # 3. Save this initial state to DB to get an ID
    # We modify save_player_state to return the ID
    new_player_id = save_new_player(initial_state)
    if new_player_id is None:
        print("Error: Could not save new character to database.")
        return None
        
    initial_state.player_id = new_player_id
    
    print(f"New character created with ID: {new_player_id}")
    return initial_state

# Necesitamos una versión de 'save' que devuelva el ID del nuevo jugador
def save_new_player(player_state: PlayerState) -> Optional[int]:
    """Guarda un NUEVO jugador y devuelve su ID auto-generado."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    player_data = player_state.model_dump(exclude={'player_id'}) # Excluimos el ID porque es autoincremental
    for key in ['location_history', 'inventory', 'active_quests', 'world_state_delta']:
        player_data[key] = json.dumps(player_data[key])
        
    try:
        cursor.execute("""
            INSERT INTO players (player_name, world_id, level, hp, max_hp, attack, xp, xp_to_next_level, current_location_id, location_history, inventory, active_quests, world_state_delta)
            VALUES (:player_name, :world_id, :level, :hp, :max_hp, :attack, :xp, :xp_to_next_level, :current_location_id, :location_history, :inventory, :active_quests, :world_state_delta)
        """, player_data)
        
        new_id = cursor.lastrowid
        conn.commit()
        return new_id
    except Exception as e:
        print(f"Database error while saving new player: {e}")
        return None
    finally:
        conn.close()

def create_game_world_instance(world_definition: dict, player_state) -> dict:
    """
    Crea una instancia jugable del mundo para la sesión actual.
    Esta versión es más robusta y explícita.
    """
    print("Creating game world instance for the current session...")
    
    # 1. Obtenemos las plantillas que necesitaremos
    location_templates = world_definition.get('locations', {})
    npc_templates = world_definition.get('npc_templates', {})
    item_templates = world_definition.get('item_templates', {})

    if not location_templates:
        print("  -> [DEBUG] CRITICAL ERROR in create_game_world_instance: No location templates found in world_definition!")
        return {"locations": {}}

    # 2. Creamos el diccionario vacío donde construiremos las localizaciones "vivas"
    instanced_locations = {}

    # 3. Iteramos sobre las PLANTILLAS de localización
    for loc_id, loc_template in location_templates.items():
        # Creamos una copia profunda de la plantilla para no modificar la original
        new_loc_instance = copy.deepcopy(loc_template)

        # --- Instanciamos los PNJs para esta localización ---
        npc_ids_in_loc = new_loc_instance.get('initial_npcs', [])
        instanced_npcs = {}
        for npc_id in npc_ids_in_loc:
            if npc_id in npc_templates:
                # Creamos una copia del PNJ de su plantilla
                instanced_npcs[npc_id] = copy.deepcopy(npc_templates[npc_id])
        # Reemplazamos la lista de IDs por un diccionario de objetos PNJ completos
        new_loc_instance['npcs'] = instanced_npcs
        
        # --- Instanciamos los Items para esta localización ---
        item_ids_in_loc = new_loc_instance.get('initial_items', [])
        instanced_items = {}
        for item_id in item_ids_in_loc:
            if item_id in item_templates:
                # Creamos una copia del ítem de su plantilla
                instanced_items[item_id] = copy.deepcopy(item_templates[item_id])
        # Reemplazamos la lista de IDs por un diccionario de objetos Item completos
        new_loc_instance['items'] = instanced_items
        
        # Guardamos la localización "viva" y completamente poblada en nuestro diccionario final
        instanced_locations[loc_id] = new_loc_instance

    print(f"  -> [DEBUG] Instanced {len(instanced_locations)} locations.")
    print("World instance created successfully.")
    
    # El resultado final es un diccionario que contiene la clave "locations"
    return {"locations": instanced_locations}
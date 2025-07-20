# refact/game_setup.py
import copy
import json
from typing import Optional

from db_manager import (get_db_connection, load_world_definition,
                        save_player_state)
from models import PlayerQuestState, PlayerState


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

def create_game_world_instance(world_definition: dict, player_state: PlayerState) -> dict:
    """
    Crea una instancia jugable del mundo.
    Empieza con una copia profunda de la definición y luego aplica los deltas del jugador.
    """
    print("Creating game world instance for the current session...")
    
    # 1. Copia profunda de las partes mutables de la definición del mundo.
    # ¡Esto es crucial para no modificar la definición original en memoria!
    world_instance = {
        'locations': copy.deepcopy(world_definition.get('locations', {})),
        'item_templates': world_definition.get('item_templates', {}), # Suelen ser inmutables
        'npc_templates': world_definition.get('npc_templates', {}),   # Suelen ser inmutables
        'quests': copy.deepcopy(world_definition.get('quests', {})),
    }

    # 2. "Poblar" las localizaciones con instancias de NPCs e Items.
    # La definición solo nos da los IDs, aquí creamos los objetos completos.
    for loc_id, loc_data in world_instance['locations'].items():
        # Poblar NPCs
        npc_instances = {}
        for npc_id in loc_data.get('initial_npcs', []):
            if npc_id in world_instance['npc_templates']:
                # Creamos una copia para que cada NPC sea único
                npc_instances[npc_id] = copy.deepcopy(world_instance['npc_templates'][npc_id])
        loc_data['npcs'] = npc_instances
        
        # Poblar Items
        item_instances = {}
        for item_id in loc_data.get('initial_items', []):
            if item_id in world_instance['item_templates']:
                item_instances[item_id] = copy.deepcopy(world_instance['item_templates'][item_id])
        loc_data['items'] = item_instances

    # 3. Aplicar los deltas guardados en el estado del jugador (esto es para cargar partida)
    # Por ahora lo dejamos simple, pero aquí iría la lógica para aplicar `player_state.world_state_delta`
    # Ejemplo de cómo podría ser:
    # for path, value in player_state.world_state_delta.items():
    #     keys = path.split('.')
    #     current_level = world_instance
    #     for key in keys[:-1]:
    #         current_level = current_level[key]
    #     if value is None:
    #         del current_level[keys[-1]]
    #     else:
    #         current_level[keys[-1]] = value
            
    print("World instance created successfully.")
    return world_instance
# refact/game_setup.py
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
    
    # 1. Cargar la definición del mundo para obtener la ubicación inicial
    world_def = load_world_definition(world_id)
    if not world_def:
        return None

    # 2. Crear el objeto PlayerState inicial
    # Nota: player_id es None porque la BD lo asignará automáticamente.
    initial_state = PlayerState(
        player_name=player_name,
        world_id=world_id,
        current_location_id=world_def['starting_location_id']
        # El resto de los valores se toman de los defaults de Pydantic
    )

    # 3. Guardar este estado inicial en la BD para obtener un ID
    # Modificamos save_player_state para que devuelva el ID
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
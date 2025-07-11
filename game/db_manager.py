# refact/db_manager.py

import json
import os
import sqlite3
from typing import List, Optional

from models import PlayerState

DB_FILE = "game_database.db"

def get_db_connection():
    """Crea y devuelve una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def create_schema(conn: sqlite3.Connection):
    """Crea el esquema completo y normalizado de la base de datos."""
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS worlds (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        style TEXT,
        lore TEXT,
        starting_location_id TEXT NOT NULL,
        main_quests TEXT -- Almacenado como JSON
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        id TEXT NOT NULL,
        world_id TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        connections TEXT,
        initial_npcs TEXT,
        initial_items TEXT,
        PRIMARY KEY (id, world_id),
        FOREIGN KEY (world_id) REFERENCES worlds (id)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS item_templates (
        id TEXT NOT NULL,
        world_id TEXT NOT NULL,
        template_id TEXT,
        name TEXT NOT NULL,
        description TEXT,
        type TEXT,
        damage_base INTEGER,
        healing_amount INTEGER,
        properties TEXT,
        PRIMARY KEY (id, world_id),
        FOREIGN KEY (world_id) REFERENCES worlds (id)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS npc_templates (
        id TEXT NOT NULL,
        world_id TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        hp INTEGER,
        attack INTEGER,
        status TEXT,
        xp INTEGER,
        dialogue_prompt TEXT,
        PRIMARY KEY (id, world_id),
        FOREIGN KEY (world_id) REFERENCES worlds (id)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quests (
        id TEXT NOT NULL,
        world_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        starting_npc_id TEXT,
        steps TEXT,
        PRIMARY KEY (id, world_id),
        FOREIGN KEY (world_id) REFERENCES worlds (id)
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name TEXT NOT NULL,
        world_id TEXT NOT NULL,
        level INTEGER DEFAULT 1,
        hp INTEGER,
        max_hp INTEGER,
        attack INTEGER,
        xp INTEGER,
        xp_to_next_level INTEGER,
        current_location_id TEXT NOT NULL,
        location_history TEXT,
        inventory TEXT,
        active_quests TEXT,
        world_state_delta TEXT,
        FOREIGN KEY (world_id) REFERENCES worlds (id)
    )""")
    
    conn.commit()
    print("Database schema checked and created/updated if necessary.")

def import_world_from_json(conn: sqlite3.Connection, world_json_path: str):
    """Importa la definición de un mundo desde un archivo JSON normalizado."""
    print(f"--- Attempting to import world from '{world_json_path}' ---")

    try:
        with open(world_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing world JSON file: {e}")
        return

    cursor = conn.cursor()
    world_id = data['world']['id']

    cursor.execute("SELECT id FROM worlds WHERE id = ?", (world_id,))
    if cursor.fetchone():
        print(f"World '{world_id}' already exists. Skipping import.")
        return

    # 1. Import World Definition
    world_data = data['world']
    world_data['main_quests'] = json.dumps(world_data.get('main_quests', {}))
    cursor.execute("""
        INSERT INTO worlds (id, name, style, lore, starting_location_id, main_quests)
        VALUES (:id, :name, :style, :lore, :starting_location_id, :main_quests)
    """, world_data)
    print(f"Imported world: {world_id}")

    # 2. Import Locations
    locations_to_insert = [
        {**loc, "world_id": world_id, 
         "connections": json.dumps(loc.get('connections', {})),
         "initial_npcs": json.dumps(loc.get('initial_npcs', [])),
         "initial_items": json.dumps(loc.get('initial_items', []))}
        for loc in data['locations']
    ]
    cursor.executemany("""
        INSERT INTO locations (id, world_id, name, description, connections, initial_npcs, initial_items)
        VALUES (:id, :world_id, :name, :description, :connections, :initial_npcs, :initial_items)
    """, locations_to_insert)
    print(f"Imported {len(locations_to_insert)} locations.")

    # 3. Import Item Templates
    items_to_insert = [
        {**item, "world_id": world_id,
         "damage_base": item.get('damage_base'),
         "healing_amount": item.get('healing_amount'),
         "properties": json.dumps(item.get('properties', []))}
        for item in data['item_templates']
    ]
    cursor.executemany("""
        INSERT INTO item_templates (id, world_id, template_id, name, description, type, damage_base, healing_amount, properties)
        VALUES (:id, :world_id, :template_id, :name, :description, :type, :damage_base, :healing_amount, :properties)
    """, items_to_insert)
    print(f"Imported {len(items_to_insert)} item templates.")

    # 4. Import NPC Templates
    npcs_to_insert = [{**npc, "world_id": world_id} for npc in data['npc_templates']]
    cursor.executemany("""
        INSERT INTO npc_templates (id, world_id, name, description, hp, attack, status, xp, dialogue_prompt)
        VALUES (:id, :world_id, :name, :description, :hp, :attack, :status, :xp, :dialogue_prompt)
    """, npcs_to_insert)
    print(f"Imported {len(npcs_to_insert)} NPC templates.")

    # 5. Import Quests
    quests_to_insert = [
        {**quest, "world_id": world_id,
         "starting_npc_id": quest.get('starting_npc'),
         "steps": json.dumps(quest.get('steps', []))}
        for quest in data.get('quests', [])
    ]
    cursor.executemany("""
        INSERT INTO quests (id, world_id, title, description, starting_npc_id, steps)
        VALUES (:id, :world_id, :title, :description, :starting_npc_id, :steps)
    """, quests_to_insert)
    print(f"Imported {len(quests_to_insert)} quests.")

    conn.commit()
    print("--- World import completed successfully. ---")


def save_player_state(player_state: PlayerState):
    """Guarda o actualiza el estado de un jugador en la BD."""
    conn = get_db_connection()
    cursor = conn.cursor()
    player_data = player_state.model_dump()
    player_data['id'] = player_data.pop('player_id')
    for key in ['location_history', 'inventory', 'active_quests', 'world_state_delta']:
        player_data[key] = json.dumps(player_data[key])
    cursor.execute("""
        INSERT OR REPLACE INTO players (id, player_name, world_id, level, hp, max_hp, attack, xp, xp_to_next_level, current_location_id, location_history, inventory, active_quests, world_state_delta)
        VALUES (:id, :player_name, :world_id, :level, :hp, :max_hp, :attack, :xp, :xp_to_next_level, :current_location_id, :location_history, :inventory, :active_quests, :world_state_delta)
    """, player_data)
    conn.commit()
    conn.close()
    print(f"Player state for '{player_state.player_name}' (ID: {player_data['id']}) saved.")

def get_player_state(player_id: int) -> Optional[PlayerState]:
    """Carga el estado de un jugador desde la BD y lo devuelve como un modelo Pydantic."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
    player_row = cursor.fetchone()
    conn.close()
    if player_row:
        player_data = dict(player_row)
        if 'id' in player_data:
            player_data['player_id'] = player_data.pop('id')
        for key in ['location_history', 'inventory', 'active_quests', 'world_state_delta']:
            if key in player_data and player_data[key]:
                player_data[key] = json.loads(player_data[key])
        return PlayerState(**player_data)
    return None

def load_world_definition(world_id: str) -> Optional[dict]:
    """
    Carga todas las definiciones de un mundo (locations, items, npcs, quests)
    desde la base de datos y las devuelve en un solo diccionario.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Cargar metainformación del mundo
    cursor.execute("SELECT * FROM worlds WHERE id = ?", (world_id,))
    world_row = cursor.fetchone()
    if not world_row:
        print(f"World with id '{world_id}' not found in database.")
        conn.close()
        return None
    
    world_def = dict(world_row)
    world_def['main_quests'] = json.loads(world_def['main_quests']) # Decodificar JSON

    # Cargar todas las demás definiciones
    tables_to_load = ['locations', 'item_templates', 'npc_templates', 'quests']
    for table_name in tables_to_load:
        cursor.execute(f"SELECT * FROM {table_name} WHERE world_id = ?", (world_id,))
        rows = cursor.fetchall()
        # Usamos el ID de la entidad como clave para un acceso rápido
        world_def[table_name] = {row['id']: dict(row) for row in rows}

        # Decodificar campos JSON dentro de cada entidad si es necesario
        for entity_id, entity_data in world_def[table_name].items():
            for key, value in entity_data.items():
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    try:
                        entity_data[key] = json.loads(value)
                    except json.JSONDecodeError:
                        pass # No era un JSON, lo dejamos como está

    conn.close()
    print(f"Successfully loaded complete definition for world '{world_id}'.")
    return world_def

def get_available_saves(world_id: str) -> List[dict]:
    """Devuelve una lista de las partidas guardadas para un mundo específico."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, player_name, level FROM players WHERE world_id = ?", (world_id,))
    saves = [{"id": row["id"], "player_name": row["player_name"], "level": row["level"]} for row in cursor.fetchall()]
    conn.close()
    return saves

if __name__ == "__main__":
    print("--- Running DB Manager Initializer and Importer ---")
    
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Removed old database file '{DB_FILE}'.")

    conn = get_db_connection()
    create_schema(conn)
    import_world_from_json(conn, "refact/eldoria_world_import.json")
    conn.close()
        
    print("\n--- DB Manager script finished ---")
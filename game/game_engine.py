# game/game_engine.py

import random

import rag_manager

# --- Lógica de Habilidades y Eventos ---

def perform_skill_check(difficulty: str) -> tuple[bool, int]:
    roll = random.randint(1, 10)
    thresholds = {"simple": 3, "challenging": 6, "very_challenging": 8}
    return roll >= thresholds.get(difficulty, 3), roll

def trigger_trap(game_state: dict, trap_info: tuple) -> tuple[dict, dict]:
    trap_name, trap_data = trap_info
    damage = trap_data.get('damage', 10)
    game_state['player']['hp'] = max(0, game_state['player']['hp'] - damage)
    game_state['locations'][game_state['player']['location']]['traps'][trap_name]['triggered'] = True
    message = f"Oh no! You triggered a trap: {trap_name.replace('_', ' ').title()}! You take {damage} damage."
    result = {"message": message, "type": "trap_triggered", "game_over": game_state['player']['hp'] <= 0}
    return game_state, result


# --- Lógica de Movimiento ---

def move_player(game_state: dict, world_definition: dict, direction: str) -> tuple[dict, dict]:
    loc_id = game_state['player']['location']
    loc_data = game_state['locations'][loc_id]
    connections = loc_data.get('connections', {})
    if direction not in connections:
        return game_state, {"message": "You can't go that way.", "type": "error"}
    new_loc_id = connections[direction]
    if loc_data.get('locked_paths', {}).get(direction, False):
        return game_state, {"message": f"The path to the {direction} is locked.", "type": "info"}
    game_state['player']['location_history'].append(loc_id)
    game_state['player']['location'] = new_loc_id
    dest_name = game_state['locations'].get(new_loc_id, {}).get('name', new_loc_id)
    result = {"message": f"You move {direction} to {dest_name}.", "type": "move"}
    new_loc_data = game_state['locations'][new_loc_id]
    active_trap = next(((n, d) for n, d in new_loc_data.get('traps', {}).items() if not d.get('triggered')), None)
    if active_trap:
        result['event'] = 'trap_encountered'
        result['trap_info'] = active_trap
    return game_state, result

def move_back(game_state: dict, world_definition: dict) -> tuple[dict, dict]:
    if not game_state['player']['location_history']:
        return game_state, {"message": "You can't go back any further.", "type": "info"}
    prev_loc_id = game_state['player']['location_history'].pop()
    game_state['player']['location'] = prev_loc_id
    prev_loc_name = game_state['locations'].get(prev_loc_id, {}).get('name', prev_loc_id)
    return game_state, {"message": f"You move back to {prev_loc_name}.", "type": "move"}

def unlock_path(game_state: dict, world_definition: dict, direction: str) -> tuple[dict, dict]:
    key = next((item for item in game_state['player']['inventory'] if item.get('type') == 'key'), None)
    if not key:
        return game_state, {"message": "You don't have a key.", "type": "error"}
    success, _ = perform_skill_check("challenging")
    if success:
        game_state['player']['inventory'].remove(key)
        game_state['locations'][game_state['player']['location']]['locked_paths'][direction] = False
        message = f"Success! You unlocked the path to the {direction}."
    else:
        message = "The lock resists your attempt."
    return game_state, {"message": message, "type": "action_result"}


# --- Lógica de Items ---

def _find_item_by_name(item_collection: dict | list, name_input: str) -> dict | None:
    name_input_formatted = name_input.lower().replace('_', ' ')
    if isinstance(item_collection, list):
        for item in item_collection:
            if name_input_formatted == item.get('name', '').lower():
                return item
    elif isinstance(item_collection, dict):
        for item_id, item_data in item_collection.items():
            if name_input_formatted == item_data.get('name', '').lower():
                return {'id': item_id, **item_data}
    return None

def pick_up_item(game_state: dict, world_definition: dict, item_name_input: str) -> tuple[dict, dict]:
    loc_id = game_state['player']['location']
    items_in_loc = game_state['locations'][loc_id].get('items', {})
    
    target_item_with_loc_id = _find_item_by_name(items_in_loc, item_name_input)

    if not target_item_with_loc_id:
        return game_state, {"message": f"There is no '{item_name_input.replace('_', ' ')}' here.", "type": "error"}
    
    item_id_to_remove = target_item_with_loc_id['id'] 
    
    # El objeto que va al inventario es el que estaba en el suelo
    item_for_inventory = items_in_loc.pop(item_id_to_remove)
    
    # Aseguramos que el objeto en el inventario tenga su ID correcto
    item_for_inventory['id'] = item_id_to_remove
    
    game_state['player']['inventory'].append(item_for_inventory)
    
    result = {"message": f"You picked up {item_for_inventory.get('name', 'an item')}.", "type": "inventory_add"}
    
    # Se comprueba el progreso de la misión al final del turno.
    return game_state, result

def drop_item(game_state: dict, world_definition: dict, item_name_input: str) -> tuple[dict, dict]:
    inventory = game_state['player']['inventory']
    item_to_drop = _find_item_by_name(inventory, item_name_input)
    
    if not item_to_drop:
        return game_state, {"message": f"You don't have '{item_name_input.replace('_', ' ')}'.", "type": "error"}
        
    inventory.remove(item_to_drop)
    
    loc_id = game_state['player']['location']
    item_id_on_ground = item_to_drop.get('id', item_to_drop.get('name', 'dropped_item').lower().replace(' ', '_'))
    
    game_state['locations'][loc_id].setdefault('items', {})[item_id_on_ground] = item_to_drop
    
    return game_state, {"message": f"You dropped the {item_to_drop.get('name', 'an item')}.", "type": "inventory_remove"}

def use_item(game_state: dict, world_definition: dict, item_name_input: str) -> tuple[dict, dict]:
    inventory = game_state['player']['inventory']
    item_to_use = _find_item_by_name(inventory, item_name_input)

    if not item_to_use:
        return game_state, {"message": f"You don't have '{item_name_input.replace('_', ' ')}'.", "type": "error"}
    
    item_type = item_to_use.get("type")
    player = game_state['player']
    
    if item_type == "healing":
        if player['hp'] >= player['max_hp']:
            return game_state, {"message": "Your health is full.", "type": "info"}
        
        healed = min(item_to_use.get('healing_amount', 0), player['max_hp'] - player['hp'])
        player['hp'] += healed
        
        if "consumable" in item_to_use.get('properties', []):
            inventory.remove(item_to_use)
            message = f"You used the {item_to_use.get('name')} and restored {healed} HP. It has been consumed."
        else:
            message = f"You used the {item_to_use.get('name')} and restored {healed} HP."
        
        return game_state, {"message": message, "type": "stat_change"}
    
    elif item_type == "weapon":
        return game_state, {"message": f"You can't 'use' the {item_to_use.get('name')} like that. Try fighting with it instead.", "type": "info"}
        
    return game_state, {"message": f"The {item_to_use.get('name')} has no immediate use.", "type": "info"}


# --- Lógica de Combate ---

def process_combat_turn(game_state: dict, npc_name: str) -> tuple[dict, list[dict]]:
    player = game_state['player']
    npc = game_state['locations'][player['location']]['npcs'][npc_name]
    turn_results = []
    
    _, p_roll = perform_skill_check("simple")
    p_damage = player['attack'] + p_roll
    npc['hp'] = max(0, npc['hp'] - p_damage)
    turn_results.append({"actor": "Player", "action": "attack", "damage": p_damage, "target": npc_name, "roll": p_roll})
    
    if npc['hp'] <= 0:
        npc['status'] = 'defeated'
        xp = npc.get('xp', 20)
        player['xp'] += xp
        turn_results.append({"actor": "System", "action": "defeat", "target": npc_name, "xp": xp})
        
        if player['xp'] >= player['xp_to_next_level']:
            player['level'] += 1
            player['xp'] -= player['xp_to_next_level']
            player['xp_to_next_level'] = int(player['xp_to_next_level'] * 1.5)
            player['max_hp'] += 10; player['hp'] = player['max_hp']; player['attack'] += 2
            turn_results.append({"actor": "System", "action": "level_up", "new_level": player['level']})

        # La comprobación de quests se hace al final del turno en el bucle principal.
        return game_state, turn_results

    _, n_roll = perform_skill_check("simple")
    n_damage = npc.get('attack', 5) + n_roll
    player['hp'] = max(0, player['hp'] - n_damage)
    turn_results.append({"actor": npc_name, "action": "attack", "damage": n_damage, "target": "Player", "roll": n_roll})

    if player['hp'] <= 0: turn_results.append({"actor": "System", "action": "player_defeat"})
    return game_state, turn_results


# --- Lógica de Quests ---

def accept_quest(game_state: dict, world_definition: dict, quest_id: str) -> tuple[dict, dict]:
    """Añade una misión a la lista de misiones activas del jugador."""
    player = game_state['player']
    
    if quest_id in player.get('active_quests', {}):
        return game_state, {"message": "You are already on that quest.", "type": "info"}

    quest_def = world_definition['quests'].get(quest_id)
    if not quest_def:
        return game_state, {"message": f"Error: Quest '{quest_id}' not found in world definition.", "type": "error"}

    if 'active_quests' not in player: player['active_quests'] = {}
    
    # Extraemos el ID del primer paso
    first_step = quest_def.get('steps', [{}])[0]
    first_step_id = first_step.get('id', 'step_1') # Default a 'step_1' si no hay ID

    # Se crea el estado inicial de la misión para el jugador
    player['active_quests'][quest_id] = {
        "quest_id": quest_id,
        "title": quest_def.get('title', 'Untitled Quest'),
        # --- ¡CORRECCIÓN CLAVE AQUÍ! ---
        # Aseguramos que el ID siempre se guarde como un string.
        "current_step_id": str(first_step_id), 
        "completed": False,
        "status": "active"
    }
    
    # ... (Lógica de RAG si la tienes) ...

    first_step_desc = first_step.get('description', 'Begin your journey.')
    result_message = f"New Quest Started: {quest_def.get('title')}\nObjective: {first_step_desc}"
    
    return game_state, {"message": result_message, "type": "quest_accepted"}

def check_quest_progress(game_state: dict, world_definition: dict) -> tuple[dict, dict | None]:
    """
    Comprueba todas las misiones activas del jugador para ver si se ha cumplido el objetivo.
    Esta función ahora funcionará gracias a los IDs corregidos por el Director.
    """
    player = game_state['player']
    active_quests = player.get('active_quests', {})
    if not active_quests:
        return game_state, None

    updated_quests_messages = []

    # Obtenemos el estado actual del mundo para las comprobaciones
    defeated_npcs_ids = {
        npc_id for loc in game_state.get('locations', {}).values() 
        for npc_id, npc_data in loc.get('npcs', {}).items() 
        if npc_data.get('status') == 'defeated'
    }
    inventory_item_ids = {item['id'] for item in player.get('inventory', [])}
    current_location_id = player['location']

    for quest_id, quest_status in list(active_quests.items()): # Usamos list() para poder modificar el dict mientras iteramos
        if quest_status.get('completed') or quest_status.get('status') == 'ready_to_turn_in':
            continue

        quest_def = world_definition['quests'].get(quest_id)
        if not quest_def: continue

        current_step_id = quest_status.get('current_step_id')
        all_steps = quest_def.get('steps', [])
        
        # Encontrar el step actual y su índice
        current_step_index = -1
        step_def = None
        for i, step in enumerate(all_steps):
            if step.get('id') == current_step_id:
                step_def = step
                current_step_index = i
                break
        
        if not step_def or 'objective' not in step_def: continue

        # --- LÓGICA DE COMPROBACIÓN DE OBJETIVOS (¡AHORA FUNCIONA!) ---
        objective = step_def['objective']
        obj_type = objective.get('type')
        obj_id = objective.get('id') # Este es el ID REAL del item/npc/loc
        objective_complete = False

        print(f"[DEBUG] Checking Quest '{quest_def['title']}', Step '{step_def['description']}'")
        print(f"[DEBUG] -> Objective: type={obj_type}, id={obj_id}")

        if obj_type == 'item' and obj_id in inventory_item_ids:
            objective_complete = True
            print(f"[DEBUG] -> SUCCESS: Item '{obj_id}' found in inventory.")
        elif obj_type == 'npc' and obj_id in defeated_npcs_ids:
            objective_complete = True
            print(f"[DEBUG] -> SUCCESS: Defeated NPC '{obj_id}' found.")
        elif obj_type == 'location' and obj_id == current_location_id:
            objective_complete = True
            print(f"[DEBUG] -> SUCCESS: Player is at location '{obj_id}'.")

        if objective_complete:
            is_last_step = (current_step_index == len(all_steps) - 1)
            message = ""

            if is_last_step:
                quest_status['status'] = 'ready_to_turn_in' # O 'completed' si no hay que entregarla
                quest_status['completed'] = True # Simplificamos: la marcamos como completada
                message = f"Quest Complete: {quest_def.get('title')}!\nYou have fulfilled the final objective."
            else:
                next_step = all_steps[current_step_index + 1]
                quest_status['current_step_id'] = next_step['id']
                message = f"Quest Updated: {quest_def.get('title')}\nNew Objective: {next_step.get('description')}"

            updated_quests_messages.append({"message": message})
            
    if updated_quests_messages:
        # Devolvemos un formato consistente para que el game_loop lo procese
        return game_state, {"updates": updated_quests_messages}
    
    return game_state, None
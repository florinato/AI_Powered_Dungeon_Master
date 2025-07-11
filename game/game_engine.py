# refact/game_engine.py

import random

# --- Lógica de Habilidades y Eventos ---

def perform_skill_check(difficulty: str) -> tuple[bool, int]:
    roll = random.randint(1, 10)
    thresholds = {"simple": 3, "challenging": 6, "very_challenging": 8}
    return roll >= thresholds.get(difficulty, 3), roll

def trigger_trap(game_state: dict, trap_info: tuple) -> tuple[dict, dict]:
    trap_name, trap_data = trap_info
    damage = trap_data.get('damage', 10)
    game_state['player']['hp'] = max(0, game_state['player']['hp'] - damage)
    
    # Marcar la trampa como activada
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
        return game_state, {"message": f"The path to {new_loc_id.replace('_', ' ').title()} is locked.", "type": "info"}
    
    game_state['player']['location_history'].append(loc_id)
    game_state['player']['location'] = new_loc_id
    
    result = {"message": f"You move {direction} to {new_loc_id.replace('_', ' ').title()}.", "type": "move"}
    
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
    return game_state, {"message": f"You move back to {prev_loc_id.replace('_', ' ').title()}.", "type": "move"}

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

def pick_up_item(game_state: dict, world_definition: dict, item_name: str) -> tuple[dict, dict]:
    loc_id = game_state['player']['location']
    items_in_loc = game_state['locations'][loc_id].get('items', {})
    if item_name not in items_in_loc:
        return game_state, {"message": f"There is no '{item_name}' here.", "type": "error"}
        
    item_data = items_in_loc.pop(item_name)
    game_state['player']['inventory'].append({"name": item_name, **item_data})
    
    result = {"message": f"You picked up {item_name.replace('_', ' ')}.", "type": "inventory_add"}
    game_state, quest_update = check_all_quests(game_state, world_definition)
    if quest_update: result['quest_update'] = quest_update
    return game_state, result

def drop_item(game_state: dict, world_definition: dict, item_name: str) -> tuple[dict, dict]:
    item_to_drop = next((item for item in game_state['player']['inventory'] if item["name"] == item_name), None)
    if not item_to_drop:
        return game_state, {"message": f"You don't have '{item_name}'.", "type": "error"}
        
    game_state['player']['inventory'].remove(item_to_drop)
    loc_id = game_state['player']['location']
    game_state['locations'][loc_id].setdefault('items', {})[item_name] = {k: v for k, v in item_to_drop.items() if k != 'name'}
    return game_state, {"message": f"You dropped the {item_name.replace('_', ' ')}.", "type": "inventory_remove"}

def use_item(game_state: dict, world_definition: dict, item_name: str) -> tuple[dict, dict]:
    item_to_use = next((item for item in game_state['player']['inventory'] if item["name"] == item_name), None)
    if not item_to_use: return game_state, {"message": f"You don't have '{item_name}'.", "type": "error"}
    
    item_type = item_to_use.get("type")
    player = game_state['player']
    if item_type == "healing":
        if player['hp'] >= player['max_hp']: return game_state, {"message": "HP is full.", "type": "info"}
        healed = min(item_to_use.get('healing_amount', 0), player['max_hp'] - player['hp'])
        player['hp'] += healed
        game_state['player']['inventory'].remove(item_to_use)
        return game_state, {"message": f"You used {item_name.replace('_',' ')} and restored {healed} HP.", "type": "stat_change"}
    
    elif item_type == "weapon":
        boost = item_to_use.get('attack_boost', 0)
        player['attack'] += boost
        game_state['player']['inventory'].remove(item_to_use)
        return game_state, {"message": f"You equipped {item_name.replace('_', ' ')}, increasing attack by {boost}!", "type": "stat_change"}
        
    return game_state, {"message": f"The {item_name.replace('_', ' ')} has no immediate use.", "type": "info"}


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

        game_state, quest_update = check_all_quests(game_state, {}) # world_def no es necesaria aquí
        if quest_update: turn_results.append({"actor": "System", "action": "quest_complete", "quests": quest_update})
        return game_state, turn_results

    _, n_roll = perform_skill_check("simple")
    n_damage = npc.get('attack', 5) + n_roll
    player['hp'] = max(0, player['hp'] - n_damage)
    turn_results.append({"actor": npc_name, "action": "attack", "damage": n_damage, "target": "Player", "roll": n_roll})

    if player['hp'] <= 0: turn_results.append({"actor": "System", "action": "player_defeat"})
    return game_state, turn_results


# --- Lógica de Quests ---

def check_all_quests(game_state: dict, world_definition: dict) -> tuple[dict, list[dict] | None]:
    """
    Comprueba las misiones y actualiza su estado a 'ready_to_turn_in' si se cumplen los requisitos.
    Devuelve las misiones que acaban de cambiar de estado.
    """
    updated_quests_info = []
    quests = game_state.get('quests', {})
    inventory_names = {item['name'] for item in game_state['player']['inventory']}
    defeated_npcs = {n for loc in game_state['locations'].values() for n, d in loc.get('npcs', {}).items() if d.get('status') == 'defeated'}

    for quest_name, quest_data in quests.items():
        # Solo comprobamos misiones que están activas
        if quest_data.get("status", "active") == "active":
            required_items = set(quest_data.get("required_items", []))
            required_npcs = set(quest_data.get("required_npcs", []))
            
            items_ok = required_items.issubset(inventory_names)
            npcs_ok = required_npcs.issubset(defeated_npcs)

            if items_ok and npcs_ok:
                # ¡Cambio clave! No la completamos, la marcamos como lista para entregar.
                quest_data["status"] = "ready_to_turn_in"
                updated_quests_info.append({
                    "name": quest_name.replace('_', ' ').title(),
                    "message": "You have met the requirements for this quest. Find the right person to report your success."
                })
    
    return game_state, updated_quests_info if updated_quests_info else None
# game/event_handlers.py

from game.ai import game_narrator
from game.core.game_engine import (accept_quest, perform_skill_check,
                                   process_combat_turn, trigger_trap)
from game.core.models import PlayerState
from game.data import db_manager

# --- Gestores de Sub-Bucles y Eventos ---

def handle_trap(game_state, trap_info, presenter):
    trap_name, trap_data = trap_info
    presenter.speak(f"\nYou feel something is amiss... It's a trap! ({trap_name.replace('_',' ').title()})")
    action = input("What do you do? (1. Proceed carefully, 2. Search, 3. Do nothing): ").strip()
    
    if action == "3":
        game_state, result = trigger_trap(game_state, trap_info)
        presenter.speak(result['message'])
        return game_state

    success, roll = perform_skill_check(trap_data.get('disarm_difficulty', 'simple'))
    presenter.speak(f"You rolled a {roll}. {'Success!' if success else 'Failure!'}")
    
    if action == "1" and not success:
        game_state, result = trigger_trap(game_state, trap_info)
        presenter.speak(result['message'])
    elif action == "2" and success:
        game_state['locations'][game_state['player']['location']]['traps'][trap_name]['triggered'] = True
        presenter.speak(f"You found and disarmed the {trap_name.replace('_',' ').title()}!")
    elif action == "2" and not success:
        game_state, result = trigger_trap(game_state, trap_info)
        presenter.speak(result['message'])
    else:
        presenter.speak("You proceed and nothing happens.")
    return game_state

def handle_combat(game_state, presenter):
    loc_id = game_state['player']['location']
    active_npcs = [npc_id for npc_id, npc_data in game_state['locations'][loc_id].get('npcs', {}).items() if npc_data.get('status') != 'defeated']
    if not active_npcs:
        presenter.speak("There is no one to fight here.")
        return game_state
    
    target_name = None
    if len(active_npcs) > 1:
        presenter.speak("Who do you want to fight?")
        for i, npc_id in enumerate(active_npcs, 1):
            npc_name = game_state['locations'][loc_id]['npcs'][npc_id].get('name', npc_id)
            presenter.speak(f"  {i}. {npc_name.replace('_', ' ').title()}")
        try:
            choice = input("> ")
            target_name = active_npcs[int(choice) - 1]
        except (ValueError, IndexError):
            presenter.speak("Invalid choice. Combat canceled.")
            return game_state
    else:
        target_name = active_npcs[0]
        
    display_name = game_state['locations'][loc_id]['npcs'][target_name].get('name', target_name)
    presenter.speak(f"You engage in combat with {display_name.replace('_', ' ').title()}!")
    
    while True:
        game_state, results = process_combat_turn(game_state, target_name)
        
        for res in results:
            if res.get('message'): presenter.speak(res['message'])
            elif res['action'] == 'attack': presenter.speak(f"-> {res['actor'].replace('_',' ').title()} attacks {res['target'].replace('_',' ').title()} for {res['damage']} damage (Rolled {res['roll']})!")
            elif res['action'] == 'defeat': presenter.speak(f"-> {res['target'].replace('_',' ').title()} is defeated! You gain {res['xp']} XP.")
            elif res['action'] == 'level_up': presenter.speak(f"-> LEVEL UP! You are now level {res['new_level']}!")
            elif res['action'] == 'player_defeat': presenter.speak("You have fallen in combat."); return game_state
        
        if game_state['player']['hp'] <= 0 or game_state['locations'][loc_id]['npcs'][target_name]['status'] == 'defeated':
            break
        input("Press Enter to continue combat...")
    return game_state

def handle_dialogue(game_state: dict, world_definition: dict, presenter, ai_provider):
    loc_id = game_state['player']['location']
    npcs_in_location = game_state['locations'][loc_id].get('npcs', {})
    talkable_npcs = {
        npc_id: npc_data 
        for npc_id, npc_data in npcs_in_location.items() 
        if npc_data.get('status') != 'defeated'
    }

    if not talkable_npcs:
        presenter.speak("There is no one to talk to.")
        return game_state

    target_id = None
    if len(talkable_npcs) == 1:
        target_id = list(talkable_npcs.keys())[0]
    else:
        presenter.speak("Who do you want to talk to?")
        npc_options = list(talkable_npcs.items())
        for i, (npc_id, npc_data) in enumerate(npc_options, 1):
            display_name = npc_data.get('name', npc_id).replace('_', ' ').title()
            presenter.speak(f"  {i}. {display_name}")
        try:
            choice_num = int(input("> "))
            if 1 <= choice_num <= len(npc_options):
                target_id = npc_options[choice_num - 1][0]
            else:
                presenter.speak("Invalid choice. Dialogue canceled."); return game_state
        except (ValueError, IndexError):
            presenter.speak("Invalid choice. Dialogue canceled."); return game_state
    
    if not target_id: return game_state
        
    target_npc_data = talkable_npcs[target_id]
    target_display_name = target_npc_data.get('name', target_id).replace('_', ' ').title()
    
    presenter.speak(f"You approach {target_display_name}. (Type 'bye' to end the conversation)")

    world_theme = world_definition.get('style', 'A generic world theme.')
    language = world_definition.get('language', 'English')
    player_quests = game_state['player'].get('active_quests', {})
    
    first_turn = True
    while True:
        if first_turn:
            first_turn = False
            quest_to_offer = None
            
            for quest_id, quest_data in world_definition.get('quests', {}).items():
                if quest_data.get('starting_npc_id') == target_id and quest_id not in player_quests:
                    quest_to_offer = quest_id
                    break
            
            if quest_to_offer:
                quest_def = world_definition['quests'][quest_to_offer]
                
                initial_prompt = (f"You are the NPC '{target_display_name}'. Your personality is: {target_npc_data.get('dialogue_prompt')}. Start a conversation and greet the player. Your response must be in {language}.")
                opening_line = ai_provider.generate_text(initial_prompt)
                presenter.speak(f"{target_display_name}: \"{opening_line}\"")

                player_input = input("You: ").strip()
                if player_input.lower() in ['bye', 'stop', 'quit', 'adios']:
                    presenter.speak("You end the conversation."); break

                offer_prompt = (f"You are the NPC '{target_display_name}'. After the player's last line ('{player_input}'), transition into explaining your problem. Reveal the situation from the quest '{quest_def.get('title')}': '{quest_def.get('description')}'. End by expressing hope they will help. Your response must be in {language}.")
                mission_pitch = ai_provider.generate_text(offer_prompt)
                presenter.speak(f"{target_display_name}: \"{mission_pitch}\"")

                game_state, result = accept_quest(game_state, world_definition, quest_to_offer)
                presenter.speak(f"\n* {result['message']} *")
                
                player_state = PlayerState(**game_state['player'])
                db_manager.save_player_state(player_state)
                continue

        player_input = input("You: ").strip()
        if player_input.lower() in ['bye', 'stop', 'quit', 'adios']:
            presenter.speak("You end the conversation."); break
        
        response = game_narrator.generate_npc_response_text(
            provider=ai_provider, game_state=game_state, npc_id=target_id,
            player_input=player_input, world_theme=world_theme, language=language
        )
        presenter.speak(f"{target_display_name}: {response}")
        
    return game_state


def handle_quest_scene(game_state: dict, active_scene_data: dict, world_definition: dict, presenter, ai_provider):
    """
    Maneja una escena de misión activa (Modo Aventura).
    Usa el motor narrativo para generar experiencias inmersivas.
    Ahora con gestión de bucles infinitos mejorada.
    
    Returns:
        tuple: (game_state_updated, result_dict)
    """
    from game.ai import game_narrator
    
    quest_id = active_scene_data["quest_id"]
    quest_title = active_scene_data["quest_title"]
    step_id = active_scene_data["step_id"]
    quest_status = active_scene_data["quest_status"]
    
    # --- NUEVA LÓGICA: GESTIÓN DE BUCLES ---
    scene_state = quest_status.setdefault('scene_state', {})
    action_count = scene_state.get('action_count', 0)
    action_count += 1
    scene_state['action_count'] = action_count
    
    # Si el jugador lleva muchas acciones en la misma escena, forzamos el objetivo
    if action_count > 5:  # Límite de 5 acciones
        presenter.speak("[DM]: El tiempo apremia, es hora de actuar decisivamente...")
        # Forzamos la compleción del objetivo
        game_state['player']['active_quests'][quest_id]['step_completed_flag'] = True
        # Reseteamos el contador para la nueva escena
        scene_state.pop('action_count', None)
        scene_state.clear()  # Limpiar todo el estado de la escena
        
        return game_state, {
            'type': 'quest_scene',
            'message': f"¡Paso forzado a completar en {quest_title}!",
            'quest_title': quest_title,
            'quest_id': quest_id,
            'quest_completed': True
        }
    
    # Preparar el contexto completo para el motor narrativo
    enhanced_game_state = game_state.copy()
    enhanced_game_state["world_definition"] = world_definition
    
    # Usar el motor narrativo para generar la escena
    try:
        narration, options = game_narrator.narrate_quest_scene(
            ai_provider, 
            enhanced_game_state, 
            active_scene_data
        )
        
        # Mostrar la narrativa y opciones
        presenter.speak(f"\n=== {quest_title} ===")
        presenter.speak(narration)
        presenter.speak("\n¿Qué decides hacer?")
        
        for i, option in enumerate(options, 1):
            presenter.speak(f"  {i}. {option}")
        
        # Obtener la elección del jugador
        choice_input = input("\nElige tu acción (número): ").strip()
        
        try:
            choice_num = int(choice_input)
            if 1 <= choice_num <= len(options):
                selected_option = options[choice_num - 1]
                
                # Resolver la acción usando el motor narrativo
                outcome_narration, outcome_data = game_narrator.resolve_quest_action(
                    ai_provider,
                    enhanced_game_state,
                    active_scene_data,
                    selected_option
                )
                
                # Mostrar el resultado
                presenter.speak(f"\n{outcome_narration}")
                
                # Procesar los efectos mecánicos
                quest_completed = False
                
                if outcome_data.get("objective_completed", False):
                    game_state['player']['active_quests'][quest_id]['step_completed_flag'] = True
                    quest_completed = True
                
                if "item_gained" in outcome_data:
                    item_id = outcome_data["item_gained"]
                    # Aquí podrías añadir lógica para añadir el item al inventario
                    presenter.speak(f"¡Has obtenido: {item_id}!")
                
                if "damage_taken" in outcome_data:
                    damage = outcome_data["damage_taken"]
                    game_state['player']['hp'] = max(0, game_state['player']['hp'] - damage)
                    presenter.speak(f"¡Has recibido {damage} puntos de daño!")
                
                if "start_combat" in outcome_data:
                    npc_id = outcome_data["start_combat"]
                    presenter.speak(f"¡El combate comienza contra {npc_id}!")
                    # Aquí podrías activar el sistema de combate
                
                if "update_scene_state" in outcome_data:
                    scene_updates = outcome_data["update_scene_state"]
                    current_scene_state = game_state['player']['active_quests'][quest_id].get('scene_state', {})
                    current_scene_state.update(scene_updates)
                    game_state['player']['active_quests'][quest_id]['scene_state'] = current_scene_state
                
                # Mensaje de resultado mejorado
                if quest_completed:
                    result_message = f"¡Paso completado en {quest_title}!"
                else:
                    result_message = f"Acción realizada en {quest_title}"
                
                return game_state, {
                    'type': 'quest_scene',
                    'message': result_message,
                    'quest_id': quest_id,
                    'quest_title': quest_title,  # Añadir quest_title para evitar el error
                    'quest_completed': quest_completed
                }
                
            else:
                presenter.speak("Opción inválida. Intenta de nuevo.")
                return game_state, None
                
        except ValueError:
            presenter.speak("Por favor, introduce un número válido.")
            return game_state, None
            
    except Exception as e:
        print(f"[DEBUG] Error in handle_quest_scene: {e}")
        presenter.speak("Ha ocurrido un error en la narrativa. Continuando...")
        
        # Fallback básico
        game_state['player']['active_quests'][quest_id]['step_completed_flag'] = True
        return game_state, {
            'type': 'quest_scene',
            'message': f"Progreso en {quest_title}",
            'quest_title': quest_title,  # Añadir quest_title para evitar el error
            'quest_id': quest_id
        }
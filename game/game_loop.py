# game/game_loop.py

import os
import random

import db_manager
import game_narrator
import game_setup
import gemini_provider
import image_generator
import pyttsx3
from command_parser import parse_command
# Importar los módulos refactorizados
from game_engine import (accept_quest, check_quest_progress, drop_item,
                         move_back, move_player, perform_skill_check,
                         pick_up_item, process_combat_turn, trigger_trap,
                         unlock_path, use_item)
from game_setup import create_game_world_instance
from models import PlayerState
from state_manager import save_game_state


# --- Capa de Presentación (Presenter) ---
class Presenter:
    def __init__(self, use_voice=True):
        self.use_voice = use_voice
        try:
            self.speech_engine = pyttsx3.init()
            self.speech_engine.setProperty("rate", 180)
        except Exception:
            self.speech_engine = None
            self.use_voice = False
    
    def speak(self, text: str):
        print(text)
        if self.use_voice and self.speech_engine:
            self.speech_engine.say(text)
            self.speech_engine.runAndWait()

    def display_location(self, game_state: dict, world_definition: dict, ai_provider):
        loc_id = game_state['player']['location']
        loc_data = game_state['locations'].get(loc_id)
        if not loc_data:
            self.speak(f"ERROR: Location data for '{loc_id}' not found in game state.")
            return
        
        location_name = loc_data.get('name', loc_id.replace('_', ' ').title())

        if "generated_description" not in loc_data:
            print("(Generating atmospheric description, please wait...)")
            loc_description_base = loc_data.get('description', 'A non-descript place.')
            world_theme = world_definition.get('style', 'A generic world theme.')
            language = world_definition.get('language')
            
            loc_data["generated_description"] = game_narrator.generate_location_description(
                provider=ai_provider,
                base_description=loc_description_base,
                location_name=location_name,
                world_theme=world_theme,
                language=language
            )
        
        self.speak(f"\n--- {location_name} ---")
        self.speak(loc_data["generated_description"])

        if loc_data.get('npcs'):
            self.speak("\nNPCs Here:")
            for npc_id, npc_data in loc_data['npcs'].items():
                if npc_data.get('status') != 'defeated':
                    display_name = npc_data.get('name', npc_id).replace('_', ' ').title()
                    self.speak(f"- {display_name}")
        
        if loc_data.get('items'):
            self.speak("\nItems:")
            for item_id, item_data in loc_data['items'].items():
                display_name = item_data.get('name', item_id).replace('_', ' ').title()
                self.speak(f"- {display_name}")

        if loc_data.get('connections'):
            self.speak("\nPaths:")
            for direction, dest_id in loc_data['connections'].items():
                dest_location_data = game_state['locations'].get(dest_id)
                dest_name = dest_location_data.get('name', dest_id) if dest_location_data else f"{dest_id} (Unknown)"
                self.speak(f"- {direction.capitalize()}: {dest_name}")
                
    def display_inventory(self, game_state: dict):
        self.speak("\n--- Inventory ---")
        inventory = game_state['player'].get('inventory', [])
        if not inventory:
            self.speak("Your inventory is empty.")
            return
        for item in inventory:
            self.speak(f"- {item.get('name', 'Unknown Item').replace('_', ' ').title()}: {item.get('description', '')}")
    
    def display_stats(self, game_state: dict):
        p = game_state['player']
        self.speak(f"\n--- Stats ---\nLevel: {p.get('level', 1)}, HP: {p.get('hp', 0)}/{p.get('max_hp', 0)}, Attack: {p.get('attack', 0)}, XP: {p.get('xp', 0)}/{p.get('xp_to_next_level', 0)}")

    def display_quests(self, game_state: dict, world_definition: dict):
        self.speak("\n--- Diario de Misiones ---")
        
        player_quests = game_state['player'].get('active_quests', {})
        all_quests_def = world_definition.get('quests', {})

        if not player_quests:
            self.speak("No tienes ninguna misión activa.")
            return

        for quest_id, quest_status in player_quests.items():
            quest_def = all_quests_def.get(quest_id)
            if not quest_def:
                self.speak(f"Error: No se encontraron los datos para la misión '{quest_id}'.")
                continue

            status_text = "[Completada]" if quest_status.get('completed') else "[Activa]"
            self.speak(f"\n{status_text} {quest_def.get('title', quest_id)}")
            
            current_step_id = quest_status.get('current_step_id')
            if current_step_id:
                step_def = next((step for step in quest_def.get('steps', []) if step.get('id') == current_step_id), None)
                if step_def:
                    self.speak(f"  └─ Objetivo: {step_def.get('description', 'No hay un objetivo claro...')}")
            
            if quest_status.get('status') == 'ready_to_turn_in':
                self.speak(f"  └─ Tienes que informar de tus progresos para completar la misión.")
                
    def show_help(self):
        self.speak("\n--- Commands ---\nlook, move <dir>, back, get <item>, use <item>, drop <item>, inv, stats, quests, fight, talk, unlock <dir>, image, help, quit")
        
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

# --- Bucle Principal ---
def run_game():
    presenter = Presenter()
    ai_provider = gemini_provider.GeminiProvider()

    # --- 1. SELECCIÓN DE MUNDO ---
    available_worlds = db_manager.get_available_worlds()
    if not available_worlds:
        presenter.speak("No worlds found. Please run db_manager.py to import a world.")
        return
    
    print("Available Worlds:")
    for i, world in enumerate(available_worlds):
        print(f"  {i + 1}. {world['name']} ({world.get('style', 'Unknown Style')})")
    
    chosen_world_id = None
    while not chosen_world_id:
        try:
            choice = int(input("> "))
            if 1 <= choice <= len(available_worlds):
                chosen_world_id = available_worlds[choice - 1]['id']
            else:
                presenter.speak("Invalid choice.")
        except (ValueError, IndexError):
            presenter.speak("Please enter a valid number.")
    
    # --- 2. CARGA DE MUNDO Y JUGADOR ---
    print(f"\nLoading world '{chosen_world_id}'...")
    world_definition = db_manager.load_world_definition(chosen_world_id)
    if not world_definition:
        presenter.speak("Fatal Error: Could not load world definition.")
        return

    available_saves = db_manager.get_available_saves(chosen_world_id)
    player_state: PlayerState | None = None
    
    if available_saves:
        print("\nAvailable characters:")
        for i, save in enumerate(available_saves):
            print(f"  {i + 1}. {save['player_name']} (Level {save['level']})")
    new_char_option = len(available_saves) + 1
    print(f"  {new_char_option}. Create a new character")

    while player_state is None:
        choice_str = input("\nChoose a character or create a new one: ")
        try:
            choice_num = int(choice_str)
            if 1 <= choice_num <= len(available_saves):
                player_id = available_saves[choice_num - 1]['id']
                player_state = db_manager.get_player_state(player_id)
                presenter.speak(f"Welcome back, {player_state.player_name}!")
            elif choice_num == new_char_option:
                player_name = input("Enter your character's name: ").strip() or "Adventurer"
                player_state = game_setup.create_new_character(chosen_world_id, player_name)
                presenter.speak(f"Welcome to {world_definition['name']}, {player_state.player_name}!")
        except (ValueError, IndexError):
            presenter.speak("Invalid choice.")

    if not player_state: return

    # --- 3. CONSTRUCCIÓN DEL ESTADO DE JUEGO ---
    world_instance = create_game_world_instance(world_definition, player_state)
    
    game_state = {
        "player": player_state.model_dump(),
        "locations": world_instance.get('locations', {}),
        "item_templates": world_definition.get('item_templates', {}),
        "npc_templates": world_definition.get('npc_templates', {}),
        "quests": world_definition.get('quests', {}) 
    }
    game_state['player']['location'] = player_state.current_location_id

    # --- 4. COMIENZA EL JUEGO ---
    presenter.display_location(game_state, world_definition, ai_provider)
    
    running = True
    while running:
        command_input = input("\n> ").strip()
        if not command_input: continue
        
        action = parse_command(command_input)
        action_type = action.get('action')
        result = None
        
        # --- BLOQUE DE PROCESAMIENTO DE ACCIONES ---
        if action_type == 'quit': running = False; continue
        elif action_type == 'help': presenter.show_help()
        elif action_type == 'inventory': presenter.display_inventory(game_state)
        elif action_type == 'stats': presenter.display_stats(game_state)
        elif action_type == 'quests': presenter.display_quests(game_state, world_definition)
        elif action_type == 'look': presenter.display_location(game_state, world_definition, ai_provider)
        elif action_type == 'error': presenter.speak(action['message'])
        elif action_type == 'image':
            current_loc_id = game_state['player']['location']
            loc_data = game_state['locations'][current_loc_id]
            description = loc_data.get('generated_description') or loc_data.get('description')
            location_name = loc_data.get('name', current_loc_id)
            world_id = world_definition.get('id', 'unknown_world')
            world_theme = world_definition.get('style', '')
            historical_context = world_definition.get('historical_context')
            inhabitant_description = world_definition.get('inhabitant_description')
            presenter.speak("Generating location image...")
            saved_image_path = image_generator.generate_image_with_gradio(
                description, location_name, world_id, world_theme, historical_context, inhabitant_description
            )
            if saved_image_path:
                presenter.speak(f"Image for {location_name} is ready at: {saved_image_path}")
                loc_data['generated_image_path'] = saved_image_path
                try: from PIL import Image; Image.open(saved_image_path).show()
                except Exception as e: print(f"Could not open image automatically: {e}")
            else:
                presenter.speak("Sorry, image generation failed.")
        elif action_type == 'move': game_state, result = move_player(game_state, world_definition, action['direction'])
        elif action_type == 'back': game_state, result = move_back(game_state, world_definition)
        elif action_type == 'pick': game_state, result = pick_up_item(game_state, world_definition, action['item_name'])
        elif action_type == 'drop': game_state, result = drop_item(game_state, world_definition, action['item_name'])
        elif action_type == 'use': game_state, result = use_item(game_state, world_definition, action['item_name'])
        elif action_type == 'unlock': game_state, result = unlock_path(game_state, world_definition, action['direction'])
        elif action_type == 'fight_intent': game_state = handle_combat(game_state, presenter)
        elif action_type == 'talk_intent': game_state = handle_dialogue(game_state, world_definition, presenter, ai_provider)
        else: presenter.speak(f"Command '{action_type}' not fully implemented.")

        # --- COMPROBACIÓN DEL PROGRESO DE LA MISIÓN ---
        game_state_after_action, quest_progress_result = check_quest_progress(game_state, world_definition)
        game_state = game_state_after_action

        # --- PROCESAMIENTO DE RESULTADOS Y ACTUALIZACIONES ---
        if result:
            if result.get('message'): presenter.speak(result['message'])
            if result.get('type') == 'move':
                # Al movernos, la descripción del lugar es lo más importante
                presenter.display_location(game_state, world_definition, ai_provider)
                # Volvemos a comprobar las misiones por si el objetivo era llegar a un sitio
                game_state_after_move, move_quest_result = check_quest_progress(game_state, world_definition)
                game_state = game_state_after_move
                if move_quest_result:
                    for update in move_quest_result.get('updates', []):
                        presenter.speak(update['message'])

                if result.get('event') == 'trap_encountered':
                    game_state = handle_trap(game_state, result['trap_info'], presenter)
        
        if quest_progress_result:
            for update in quest_progress_result.get('updates', []):
                presenter.speak(update['message'])

        # --- COMPROBACIÓN DE FIN DE JUEGO Y GUARDADO ---
        if game_state['player']['hp'] <= 0:
            presenter.speak("Game Over.")
            running = False
        
        # Sincronizamos el objeto Pydantic y lo guardamos en la BD
        player_state = PlayerState(**game_state['player'])
        db_manager.save_player_state(player_state)

    presenter.speak("\nSaving final game state and exiting...")
    # Guardamos una copia de seguridad final en JSON
    save_game_state(game_state, f"backup_save_{player_state.player_name}.json")

if __name__ == "__main__":
    run_game()
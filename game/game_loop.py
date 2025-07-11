# refact/game_loop.py

import os
import random

import game_narrator
import gemini_provider
import image_generator
import pyttsx3
import world_generator
from command_parser import parse_command
# Importar los módulos refactorizados
from game_engine import (check_all_quests, drop_item, move_back, move_player,
                         perform_skill_check, pick_up_item,
                         process_combat_turn, trigger_trap, unlock_path,
                         use_item)
from state_manager import load_game_state, save_game_state


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

    def display_location(self, game_state: dict, ai_provider):
        loc_id = game_state['player']['location']
        loc_data = game_state['locations'][loc_id]
        if "generated_description" not in loc_data:
            loc_data["generated_description"] = game_narrator.generate_location_description(ai_provider, game_state)
        
        self.speak(f"\n--- {loc_id.replace('_', ' ').title()} ---")
        self.speak(loc_data["generated_description"])
        
        if loc_data.get('npcs'):
            print("\nNPCs Here:")
            for name, data in loc_data['npcs'].items():
                print(f"- {name.replace('_', ' ').title()} ({data.get('status', 'active')})")
        if loc_data.get('items'):
            print("\nItems:")
            for name in loc_data['items']:
                print(f"- {name.replace('_', ' ').title()}")
        if loc_data.get('connections'):
            print("\nPaths:")
            for direction, dest in loc_data['connections'].items():
                locked_status = "(Locked)" if loc_data.get('locked_paths', {}).get(direction) else ""
                print(f"- {direction.capitalize()}: {dest.replace('_', ' ').title()} {locked_status}")

    def display_inventory(self, game_state: dict):
        self.speak("\n--- Inventory ---")
        inventory = game_state['player']['inventory']
        if not inventory: self.speak("Your inventory is empty."); return
        for item in inventory:
            self.speak(f"- {item['name'].replace('_', ' ').title()}: {item['description']}")
    
    def display_stats(self, game_state: dict):
        p = game_state['player']
        self.speak(f"\n--- Stats ---\nLevel: {p['level']}, HP: {p['hp']}/{p['max_hp']}, Attack: {p['attack']}, XP: {p['xp']}/{p['xp_to_next_level']}")

    def display_quests(self, game_state: dict):
        self.speak("\n--- Quests ---")
        quests = game_state.get('quests', {})
        if not quests: self.speak("No active quests."); return
        for name, data in quests.items():
            self.speak(f"[{'DONE' if data.get('completed') else 'Active'}] {name.replace('_',' ').title()}: {data['description']}")

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
    active_npcs = [n for n, d in game_state['locations'][loc_id].get('npcs', {}).items() if d.get('status') != 'defeated']
    if not active_npcs:
        presenter.speak("There is no one to fight here.")
        return game_state
    
    if len(active_npcs) > 1:
        presenter.speak("Who do you want to fight?")
        for i, name in enumerate(active_npcs, 1):
            presenter.speak(f"  {i}. {name.replace('_', ' ').title()}")
        try:
            choice = input("> ")
            target_name = active_npcs[int(choice) - 1]
        except (ValueError, IndexError):
            presenter.speak("Invalid choice. Combat canceled.")
            return game_state
    else:
        target_name = active_npcs[0]
        
    presenter.speak(f"You engage in combat with {target_name.replace('_', ' ').title()}!")
    
    while True:
        game_state, results = process_combat_turn(game_state, target_name)
        
        for res in results:
            if res.get('message'): presenter.speak(res['message'])
            elif res['action'] == 'attack': presenter.speak(f"-> {res['actor'].replace('_',' ').title()} attacks {res['target'].replace('_',' ').title()} for {res['damage']} damage (Rolled {res['roll']})!")
            elif res['action'] == 'defeat': presenter.speak(f"-> {res['target'].replace('_',' ').title()} is defeated! You gain {res['xp']} XP.")
            elif res['action'] == 'level_up': presenter.speak(f"-> LEVEL UP! You are now level {res['new_level']}!")
            elif res['action'] == 'quest_complete': [presenter.speak(f"-> Quest Completed: {q['name']}!") for q in res['quests']]
            elif res['action'] == 'player_defeat': presenter.speak("You have fallen in combat."); return game_state
        
        if game_state['player']['hp'] <= 0 or game_state['locations'][loc_id]['npcs'][target_name]['status'] == 'defeated':
            break
        input("Press Enter to continue combat...")
    return game_state

def handle_dialogue(game_state, presenter, ai_provider):
    loc_id = game_state['player']['location']
    talkable_npcs = [n for n, d in game_state['locations'][loc_id].get('npcs', {}).items() if d.get('status') != 'defeated']
    if not talkable_npcs:
        presenter.speak("There is no one to talk to.")
        return game_state
    
    # ... (Lógica de selección de NPC, que resulta en 'target_name') ...
    target_name = talkable_npcs[0] # Simplificando la selección

    # --- NUEVA LÓGICA DE ENTREGA DE QUEST ---
    quests = game_state.get('quests', {})
    quest_to_turn_in = None
    for quest_name, quest_data in quests.items():
        # Comprobamos si hay una quest lista para entregar A ESTE NPC
        if quest_data.get("status") == "ready_to_turn_in" and quest_data.get("turn_in_npc") == target_name:
            quest_to_turn_in = quest_name
            break # Encontramos una, salimos del bucle

    if quest_to_turn_in:
        presenter.speak(f"You approach {target_name.replace('_', ' ').title()}, who seems to be expecting you.")
        
        # Marcar la quest como completada
        quest_data = quests[quest_to_turn_in]
        quest_data["status"] = "completed"
        
        # Eliminar objetos de quest del inventario (opcional)
        required_items = quest_data.get("required_items", [])
        game_state['player']['inventory'] = [item for item in game_state['player']['inventory'] if item['name'] not in required_items]
        
        # Dar recompensas (XP, etc. - esta lógica iría en el game_engine)
        reward_xp = quest_data.get("reward_xp", 50)
        game_state['player']['xp'] += reward_xp
        
        presenter.speak(f"QUEST COMPLETED: {quest_to_turn_in.replace('_', ' ').title()}!")
        presenter.speak(f"You received {reward_xp} XP as a reward.")
        # Aquí la IA podría generar un diálogo de agradecimiento del NPC
        # ...
        return game_state # Terminamos la interacción después de entregar la quest

    # --- FIN DE LA NUEVA LÓGICA ---

    # Si no hay quests para entregar, procedemos con el diálogo normal
    presenter.speak(f"You start a conversation with {target_name.replace('_', ' ').title()}. (Type 'bye' to end)")
    while True:
        player_input = input("You: ").strip()
        if player_input.lower() in ['bye', 'stop', 'quit', 'adios']:
            presenter.speak("You end the conversation.")
            break
        response = game_narrator.generate_npc_response_text(ai_provider, game_state, target_name, player_input)
        presenter.speak(f"{target_name.replace('_', ' ').title()}: {response}")
        
    return game_state
# --- Bucle Principal ---
def run_game():
    presenter = Presenter()
    ai_provider = gemini_provider.GeminiProvider()
    
    game_state = load_game_state()
    if not game_state:
        presenter.speak("No save game found. Generating a new world...")
        game_state = world_generator.generate_initial_game_state(ai_provider)
        if not game_state:
            presenter.speak("Fatal Error: Could not generate a new world. Exiting.")
            return
    
    # Este 'world_definition' es un parche temporal
    world_definition = game_state

    presenter.speak("Welcome to the AI Dungeon Master Game!")
    presenter.display_location(game_state, ai_provider)
    
    running = True
    while running:
        command_input = input("\n> ").strip()
        if not command_input: continue
        
        action = parse_command(command_input)
        action_type = action.get('action')
        
        result = None
        if action_type == 'quit': running = False; continue
        elif action_type == 'help': presenter.show_help()
        elif action_type == 'inventory': presenter.display_inventory(game_state)
        elif action_type == 'stats': presenter.display_stats(game_state)
        elif action_type == 'quests': presenter.display_quests(game_state)
        elif action_type == 'look': presenter.display_location(game_state, ai_provider)
        elif action_type == 'error': presenter.speak(action['message'])
        elif action_type == 'image':
            loc = game_state['locations'][game_state['player']['location']]
            image_generator.generate_image_with_gradio(loc.get('generated_description', loc['description']), game_state['player']['location'])
        elif action_type == 'move':
            game_state, result = move_player(game_state, world_definition, action['direction'])
        elif action_type == 'back':
            game_state, result = move_back(game_state, world_definition)
        elif action_type == 'pick':
            game_state, result = pick_up_item(game_state, world_definition, action['item_name'])
        elif action_type == 'drop':
            game_state, result = drop_item(game_state, world_definition, action['item_name'])
        elif action_type == 'use':
            game_state, result = use_item(game_state, world_definition, action['item_name'])
        elif action_type == 'unlock':
            game_state, result = unlock_path(game_state, world_definition, action['direction'])
        elif action_type == 'fight_intent':
            game_state = handle_combat(game_state, presenter)
        elif action_type == 'talk_intent':
            game_state = handle_dialogue(game_state, presenter, ai_provider)
        else:
            presenter.speak(f"Command '{action_type}' not fully implemented.")

        if result:
            if result.get('message'): presenter.speak(result['message'])
            if result.get('quest_update'):
                for q in result['quest_update']: presenter.speak(f"Quest Completed: {q['name']}!")
            
            if result.get('type') == 'move':
                presenter.display_location(game_state, ai_provider)
                if result.get('event') == 'trap_encountered':
                    game_state = handle_trap(game_state, result['trap_info'], presenter)

        if game_state['player']['hp'] <= 0:
            presenter.speak("Game Over.")
            running = False

    presenter.speak("\nSaving game...")
    save_game_state(game_state)

if __name__ == "__main__":
    run_game()
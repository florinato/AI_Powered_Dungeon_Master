# main.py (antes game_loop.py)

import os

from game.ai.ai_factory import get_ai_provider
# Importamos las funciones de lógica de juego que usa el bucle principal
from game.core.game_engine import (check_quest_progress, drop_item, move_back,
                                   move_player, pick_up_item, unlock_path,
                                   use_item)
from game.core.models import PlayerState
from game.core.state_manager import save_game_state
from game.data import db_manager
from game.ui.command_parser import parse_command
# Importamos los manejadores de eventos desde su nuevo módulo
from game.ui.event_handlers import handle_combat, handle_dialogue, handle_trap
from game.ui.presenter import Presenter
from game.utils import \
    image_generator  # Mantenemos la importación para el comando 'image'
from game.utils import \
    map_generator  # Importación necesaria para el comando 'map'
from game.utils import game_setup
from game.utils.game_setup import create_game_world_instance


def run_game():
    """
    Función principal que orquesta el flujo completo del juego.
    """
    presenter = Presenter()
    ai_provider = get_ai_provider()

    # --- 1. SELECCIÓN DE MUNDO ---
    available_worlds = db_manager.get_available_worlds()
    if not available_worlds:
        presenter.speak("No worlds found in the database. Please run 'python game/db_manager.py' to import a world.")
        return
    
    print("Available Worlds:")
    for i, world in enumerate(available_worlds):
        print(f"  {i + 1}. {world['name']} ({world.get('style', 'Unknown Style')})")
    
    chosen_world_id = None
    while not chosen_world_id:
        try:
            choice_str = input("> ")
            if not choice_str: continue
            choice = int(choice_str)
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
            if not choice_str: continue
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

    # --- 4. COMIENZA EL BUCLE PRINCIPAL ---
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
        elif action_type == 'map':
            # Asume que el blueprint está en la raíz. A futuro, se podría guardar su nombre en la BD.
            blueprint_file = f"grid_map_3x3_p100_blueprint.json" # Ejemplo
            if os.path.exists(blueprint_file):
                presenter.speak("Generating your map...")
                map_path = map_generator.generate_map_image(world_definition, game_state, blueprint_file)
                if map_path and os.path.exists(map_path):
                    presenter.speak(f"Map is ready at: {map_path}")
                    try: from PIL import Image; Image.open(map_path).show()
                    except Exception as e: print(f"Could not open map image automatically: {e}")
                else:
                    presenter.speak("Sorry, could not generate the map.")
            else:
                presenter.speak(f"Map file '{blueprint_file}' not found.")

        # Acciones que llaman al game_engine
        elif action_type == 'move': game_state, result = move_player(game_state, world_definition, action['direction'])
        elif action_type == 'back': game_state, result = move_back(game_state, world_definition)
        elif action_type == 'pick': game_state, result = pick_up_item(game_state, world_definition, action['item_name'])
        elif action_type == 'drop': game_state, result = drop_item(game_state, world_definition, action['item_name'])
        elif action_type == 'use': game_state, result = use_item(game_state, world_definition, action['item_name'])
        elif action_type == 'unlock': game_state, result = unlock_path(game_state, world_definition, action['direction'])
        
        # Acciones que llaman a los event_handlers
        elif action_type == 'fight_intent':
            game_state = handle_combat(game_state, presenter)
        elif action_type == 'talk_intent':
            game_state = handle_dialogue(game_state, world_definition, presenter, ai_provider)
        
        else: presenter.speak(f"Command '{action_type}' not fully implemented.")

        # --- LÓGICA DE FIN DE TURNO ---
        # 1. Comprobar progreso de misiones
        game_state, quest_progress_result = check_quest_progress(game_state, world_definition)
        
        # 2. Procesar resultado de la acción principal
        if result:
            if result.get('message'): presenter.speak(result['message'])
            if result.get('type') == 'move':
                presenter.display_location(game_state, world_definition, ai_provider)
                # Volver a comprobar misiones por si el objetivo era llegar a un sitio
                game_state, move_quest_result = check_quest_progress(game_state, world_definition)
                if move_quest_result:
                    for update in move_quest_result.get('updates', []):
                        presenter.speak(update['message'])
                if result.get('event') == 'trap_encountered':
                    game_state = handle_trap(game_state, result['trap_info'], presenter)
        
        # 3. Mostrar actualizaciones de misiones (si las hubo por acciones que no sean `move`)
        if quest_progress_result:
            for update in quest_progress_result.get('updates', []):
                presenter.speak(update['message'])

        # 4. Comprobar si el juego ha terminado
        if game_state['player']['hp'] <= 0:
            presenter.speak("Game Over.")
            running = False
        
        # 5. Sincronizar y guardar el estado en la BD
        player_state = PlayerState(**game_state['player'])
        db_manager.save_player_state(player_state)

    presenter.speak("\nSaving final game state and exiting...")
    save_game_state(game_state, f"backup_save_{player_state.player_name}.json")

if __name__ == "__main__":
    run_game()
# game/core/game_loop.py

import os

from game.ai.ai_factory import get_ai_provider
from game.core.game_engine import (check_quest_progress, drop_item, move_back,
                                   move_player, pick_up_item, unlock_path,
                                   use_item)
from game.core.models import PlayerState
from game.data import db_manager
from game.ui.command_parser import parse_command
# ¡IMPORTANTE! Importaremos la nueva función que vamos a crear
from game.ui.event_handlers import (handle_combat, handle_dialogue,
                                    handle_quest_scene, handle_trap)
from game.ui.presenter import Presenter
from game.utils import image_generator, map_generator
from game.utils.game_setup import (create_game_world_instance,
                                   create_new_character)


def get_active_quest_scene(game_state: dict, world_definition: dict) -> dict | None:
    """
    Revisa si el jugador está en medio de una misión. Si es así,
    construye y devuelve el "Objeto de Escena" para el turno actual.
    Esta es la función que determina si entramos en 'Modo Aventura'.
    """
    active_quests = game_state['player'].get('active_quests', {})
    for quest_id, quest_status in active_quests.items():
        # Si la misión no está completada, es candidata a estar activa.
        if not quest_status.get('completed'):
            quest_def = world_definition.get('quests', {}).get(quest_id)
            if not quest_def: continue
            
            current_step_id = quest_status.get('current_step_id')
            step_def = next((s for s in quest_def.get('steps', []) if s.get('id') == current_step_id), None)
            
            # NUEVO: Verificar si el paso actual ya fue completado
            step_completed_flag = quest_status.get('step_completed_flag', False)
            
            if step_def and not step_completed_flag:
                # ¡Hemos encontrado una escena activa!
                return {
                    "quest_id": quest_id,
                    "quest_title": quest_def.get('title'),
                    "step_id": current_step_id,
                    "step_definition": step_def,
                    "quest_status": quest_status
                }
    return None # No hay misiones activas, nos quedamos en 'Modo Exploración'


def run_game():
    """Función principal que orquesta el flujo completo del juego."""
    presenter = Presenter()
    ai_provider = get_ai_provider()

    # --- 1. SELECCIÓN DE MUNDO ---
    available_worlds = db_manager.get_available_worlds()
    if not available_worlds:
        presenter.speak(
            "No worlds found in the database. Please run 'python game/db_manager.py' to import a world."
        )
        return

    print("Available Worlds:")
    for i, world in enumerate(available_worlds):
        print(f"  {i + 1}. {world['name']} ({world.get('style', 'Unknown Style')})")

    chosen_world_id = None
    while not chosen_world_id:
        try:
            choice_str = input("> ")
            if not choice_str:
                continue
            choice = int(choice_str)
            if 1 <= choice <= len(available_worlds):
                chosen_world_id = available_worlds[choice - 1]["id"]
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
            if not choice_str:
                continue
            choice_num = int(choice_str)
            if 1 <= choice_num <= len(available_saves):
                player_id = available_saves[choice_num - 1]["id"]
                player_state = db_manager.get_player_state(player_id)
                presenter.speak(f"Welcome back, {player_state.player_name}!")
            elif choice_num == new_char_option:
                player_name = (
                    input("Enter your character's name: ").strip() or "Adventurer"
                )
                player_state = create_new_character(chosen_world_id, player_name)
                presenter.speak(
                    f"Welcome to {world_definition['name']}, {player_state.player_name}!"
                )
        except (ValueError, IndexError):
            presenter.speak("Invalid choice.")

    if not player_state:
        return

    # --- 3. CONSTRUCCIÓN DEL ESTADO DE JUEGO ---
    world_instance = create_game_world_instance(world_definition, player_state)

    game_state = {
        "player": player_state.model_dump(),
        "locations": world_instance.get("locations", {}),
        "item_templates": world_definition.get("item_templates", {}),
        "npc_templates": world_definition.get("npc_templates", {}),
        "quests": world_definition.get("quests", {}),
    }
    game_state["player"]["location"] = player_state.current_location_id

    # --- 4. COMIENZA EL BUCLE PRINCIPAL ---
    presenter.display_location(game_state, world_definition, ai_provider)
    
    running = True
    while running:
        
        # --- EL GUARDAAGUJAS ---
        # Al inicio de cada turno, comprobamos en qué modo estamos.
        active_scene_data = get_active_quest_scene(game_state, world_definition)
        
        result = None # Variable para almacenar el resultado de la acción del turno
        
        if active_scene_data:
            # --- MODO AVENTURA ---
            # El control se cede al manejador de escenas de misión.
            # Este manejador hará todo: narrar, mostrar opciones, procesar elección.
            game_state, result = handle_quest_scene(
                game_state, 
                active_scene_data, 
                world_definition, 
                presenter, 
                ai_provider
            )
            
        else:
            # --- MODO EXPLORACIÓN (El bucle antiguo) ---
            command_input = input("\n> ").strip()
            if not command_input: continue
            
            action = parse_command(command_input)
            action_type = action.get('action')
            
            if action_type == 'quit': running = False; continue
            elif action_type == 'help': presenter.show_help()
            elif action_type == 'inventory': presenter.display_inventory(game_state)
            elif action_type == 'stats': presenter.display_stats(game_state)
            elif action_type == 'quests': presenter.display_quests(game_state, world_definition)
            elif action_type == 'look': presenter.display_location(game_state, world_definition, ai_provider)
            elif action_type == "error": presenter.speak(action["message"])
            elif action_type == "image":
                current_loc_id = game_state["player"]["location"]
                loc_data = game_state["locations"][current_loc_id]
                description = loc_data.get("generated_description") or loc_data.get("description")
                location_name = loc_data.get("name", current_loc_id)
                world_id = world_definition.get("id", "unknown_world")
                world_theme = world_definition.get("style", "")
                historical_context = world_definition.get("historical_context")
                inhabitant_description = world_definition.get("inhabitant_description")
                presenter.speak("Generating location image...")
                saved_image_path = image_generator.generate_image_with_gradio(
                    description, location_name, world_id, world_theme,
                    historical_context, inhabitant_description,
                )
                if saved_image_path:
                    presenter.speak(f"Image for {location_name} is ready at: {saved_image_path}")
                    loc_data["generated_image_path"] = saved_image_path
                else:
                    presenter.speak("Sorry, image generation failed.")
            elif action_type == "map":
                blueprint_file = f"grid_map_3x3_p100_blueprint.json"
                if os.path.exists(blueprint_file):
                    presenter.speak("Generating your map...")
                    map_path = map_generator.generate_map_image(world_definition, game_state, blueprint_file)
                    if map_path and os.path.exists(map_path):
                        presenter.speak(f"Map is ready at: {map_path}")
                    else:
                        presenter.speak("Sorry, could not generate the map.")
                else:
                    presenter.speak(f"Map file '{blueprint_file}' not found.")
            
            # Acciones que llaman al game_engine
            elif action_type == 'move':
                game_state, result = move_player(game_state, world_definition, action['direction'])
            elif action_type == "back":
                game_state, result = move_back(game_state, world_definition)
            elif action_type == "pick":
                game_state, result = pick_up_item(game_state, world_definition, action["item_name"])
            elif action_type == "drop":
                game_state, result = drop_item(game_state, world_definition, action["item_name"])
            elif action_type == "use":
                game_state, result = use_item(game_state, world_definition, action["item_name"])
            elif action_type == "unlock":
                game_state, result = unlock_path(game_state, world_definition, action["direction"])
            
            # Acciones que llaman a los event_handlers
            elif action_type == "fight_intent":
                game_state = handle_combat(game_state, presenter)
            elif action_type == 'talk':
                # ¡Importante! 'talk' puede activar una misión, cambiando el estado
                # para que el siguiente bucle entre en Modo Aventura.
                game_state = handle_dialogue(game_state, world_definition, presenter, ai_provider)
            
            else:
                presenter.speak(f"Command '{action_type}' not fully implemented.")

        # --- LÓGICA DE FIN DE TURNO ---
        
        # 1. Procesar el resultado del turno (de cualquier modo)
        if result:
            if result.get('message'): presenter.speak(result['message'])
            # Si el resultado fue un movimiento en Modo Exploración...
            if result.get('type') == 'move':
                presenter.display_location(game_state, world_definition, ai_provider)
                if result.get('event') == 'trap_encountered':
                    game_state = handle_trap(game_state, result['trap_info'], presenter)
            # Si el resultado fue la finalización de un paso de misión...
            if result.get('quest_completed'):
                presenter.speak(f"¡Paso completado! Procesando progreso de la misión...")
                # No mostrar la ubicación aquí, se hará después del progreso
        
        # 2. Comprobar si hay que avanzar de paso en una misión
        # (Esto se activará por la bandera puesta en handle_quest_scene)
        game_state, quest_progress_result = check_quest_progress(game_state, world_definition.get('quests', {}))
        if quest_progress_result:
            for update in quest_progress_result.get('updates', []):
                presenter.speak(f"\n* {update['message']} *")
            # Mostrar la ubicación después del progreso de la misión
            presenter.display_location(game_state, world_definition, ai_provider)
        
        # 3. Comprobar si el juego ha terminado
        if game_state['player']['hp'] <= 0:
            presenter.speak("Game Over.")
            running = False
        
        # 4. Sincronizar y guardar el estado en la BD
        if game_state.get('player'):
            player_state = PlayerState(**game_state['player'])
            db_manager.save_player_state(player_state)

    presenter.speak("\nSaving final game state and exiting...")


if __name__ == "__main__":
    run_game()

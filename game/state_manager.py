# refact/state_manager.py

import json
import os

# Define el nombre del archivo de guardado.
# Podrías hacerlo más complejo para permitir múltiples partidas,
# pero por ahora, un solo archivo es suficiente.
SAVE_FILE_NAME = "savegame.json"

def save_game_state(game_state: dict, save_file: str = SAVE_FILE_NAME):
    """
    Guarda el diccionario del estado del juego en un archivo JSON.

    Args:
        game_state: El diccionario que contiene todo el estado actual del juego.
        save_file: El nombre del archivo donde se guardará la partida.
    """
    if not isinstance(game_state, dict):
        print("Error: El estado del juego debe ser un diccionario para poder guardarlo.")
        return

    try:
        # Usamos 'indent=4' para que el archivo JSON sea legible por humanos,
        # lo cual es muy útil para depurar.
        with open(save_file, "w", encoding="utf-8") as f:
            json.dump(game_state, f, indent=4)
        print(f"Game state successfully saved to '{save_file}'.")
    except TypeError as e:
        print(f"Error serializing game state to JSON: {e}")
        print("Asegúrate de que todos los datos en el game_state son compatibles con JSON (strings, números, listas, diccionarios).")
    except IOError as e:
        print(f"Error writing to save file '{save_file}': {e}")

def load_game_state(save_file: str = SAVE_FILE_NAME) -> dict | None:
    """
    Carga el estado del juego desde un archivo JSON.

    Args:
        save_file: El nombre del archivo desde donde se cargará la partida.

    Returns:
        Un diccionario con el estado del juego si el archivo existe y es válido,
        o None si el archivo no se encuentra o hay un error.
    """
    # Primero, comprobar si el archivo de guardado existe.
    if not os.path.exists(save_file):
        print(f"Save file '{save_file}' not found. A new game will be started.")
        return None

    try:
        with open(save_file, "r", encoding="utf-8") as f:
            game_state = json.load(f)
        
        # Es una buena práctica validar que lo que cargamos es un diccionario.
        if not isinstance(game_state, dict):
            print(f"Error: The content of '{save_file}' is not a valid game state dictionary.")
            return None

        print(f"Game state successfully loaded from '{save_file}'.")
        return game_state
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from '{save_file}': {e}")
        print("The save file might be corrupted. Starting a new game.")
        # Opcional: podrías mover el archivo corrupto a un '.bak' aquí.
        # os.rename(save_file, f"{save_file}.corrupted")
        return None
    except IOError as e:
        print(f"Error reading from save file '{save_file}': {e}")
        return None

# --- Bloque de prueba para el State Manager ---
if __name__ == "__main__":
    """
    Este bloque permite probar las funciones de guardado y carga de forma aislada.
    """
    print("--- Running State Manager Test ---")
    
    # 1. Crear un estado de juego de prueba
    test_state = {
        "player": {
            "name": "Tester",
            "hp": 50,
            "location": "test_room"
        },
        "locations": {
            "test_room": {
                "description": "A simple room for testing."
            }
        }
    }
    
    test_filename = "test_save.json"

    # 2. Probar el guardado
    print("\n--- Testing save_game_state ---")
    save_game_state(test_state, save_file=test_filename)

    # 3. Probar la carga
    print("\n--- Testing load_game_state ---")
    loaded_state = load_game_state(save_file=test_filename)

    # 4. Verificar que el estado cargado es igual al guardado
    if loaded_state == test_state:
        print("\nSUCCESS: Loaded state matches the original test state.")
    else:
        print("\nFAILURE: Loaded state does not match the original test state.")
        print("Original:", test_state)
        print("Loaded:", loaded_state)

    # 5. Probar la carga de un archivo que no existe
    print("\n--- Testing loading a non-existent file ---")
    non_existent_state = load_game_state(save_file="no_such_file.json")
    if non_existent_state is None:
        print("SUCCESS: load_game_state correctly returned None for a non-existent file.")
    else:
        print("FAILURE: load_game_state did not return None for a non-existent file.")
        
    # 6. Limpiar el archivo de prueba
    if os.path.exists(test_filename):
        os.remove(test_filename)
        print(f"\nCleaned up test file '{test_filename}'.")
        
    print("\n--- End of Test ---")
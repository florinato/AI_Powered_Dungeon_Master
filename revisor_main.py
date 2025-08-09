import os

from game.world_generation.revisor import WorldRevisor

if __name__ == '__main__':
    # 4. Rutas ajustadas para ser más robustas
    try:
        
        INPUT_FILE = os.path.join("world_import_generated.json")
        OUTPUT_FILE = os.path.join("world_import_revisado.json")

        if not os.path.exists(INPUT_FILE):
            print(f"Error: The input file '{INPUT_FILE}' does not exist.")
            print("Please run director.py first to generate it.")
        else:
            revisor = WorldRevisor(input_path=INPUT_FILE, output_path=OUTPUT_FILE)
            revisor.revise_and_save()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
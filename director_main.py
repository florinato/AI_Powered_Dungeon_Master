import json
import os

import yaml

# Es crucial importar los componentes necesarios desde sus módulos correctos.
# Python buscará dentro de la carpeta 'game' que está al mismo nivel que este script.
from game.ai.ai_factory import get_ai_provider
from game.core.models import WorldGraph
from game.world_generation.director import DirectorAgent

if __name__ == "__main__":
    try:

        GRAPH_FILE = os.path.join("grid_map_3x3_p100_blueprint.json")
        MANIFEST_FILE = os.path.join("manifest_world.yaml")
        BASE_ITEMS_FILE = os.path.join("base_item_templates.json")
        OUTPUT_FILE = os.path.join("world_import_generated.json")

        with open(GRAPH_FILE, "r", encoding="utf-8") as f:
            world_graph = WorldGraph(**json.load(f))

        ai_provider = get_ai_provider()
        director = DirectorAgent(
            provider=ai_provider,
            manifest_path=MANIFEST_FILE,
            base_items_path=BASE_ITEMS_FILE,
        )

        director.orchestrate_world_creation(world_graph)
        director.assemble_and_save(output_path=OUTPUT_FILE)

    except FileNotFoundError as e:
        print(f"\nERROR: Could not find a required file: {e}.")
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        print(f"\nERROR: Failed to parse configuration file: {e}")
    except (ValueError, KeyError) as e:
        print(f"\nERROR: Invalid configuration or data: {e}")
    except OSError as e:
        print(f"\nERROR: File system error: {e}")

"""
Story Forge Main - Entry point for the interactive narrative design tool.

This script launches the Story Forge, which allows users to collaboratively
develop story concepts with AI agents (Creator and Critic) and convert them
into structured game manifests.
"""

import os

import yaml

from game.world_generation.story_forge import StoryForge

if __name__ == "__main__":
    try:

        SEED_MANIFEST_PATH = os.path.join("manifest_seed.yaml")
        OUTPUT_MANIFEST_PATH = os.path.join("manifest_world.yaml")

        forge = StoryForge(
            seed_manifest_path=SEED_MANIFEST_PATH, output_path=OUTPUT_MANIFEST_PATH
        )
        forge.forge_manifest()

    except FileNotFoundError as e:
        print(f"ERROR: No se pudo encontrar un archivo requerido: {e}")
    except yaml.YAMLError as e:
        print(f"ERROR: Error al procesar archivo YAML: {e}")
    except (ValueError, KeyError) as e:
        print(f"ERROR: Configuración o datos inválidos: {e}")
    except OSError as e:
        print(f"ERROR: Error del sistema de archivos: {e}")

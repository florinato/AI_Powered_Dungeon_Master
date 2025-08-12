# game/world_generation/story_forge.py

import os
import time

import yaml

from game.ai.ai_factory import get_ai_provider


class StoryForge:
    """
    Actúa como un 'Expansor de Manifiestos'.
    Colabora con el usuario para transformar un 'manifiesto semilla' de alto nivel
    en un manifiesto de producción completo y estructurado, listo para el Director.
    """

    def __init__(self, seed_manifest_path: str, output_path: str):
        print("--- StoryForge: Manifesto Expander Initialized ---")

        self.output_path = output_path
        self.ai_provider = get_ai_provider()

        try:
            with open(seed_manifest_path, "r", encoding="utf-8") as f:
                self.seed_manifest = yaml.safe_load(f)
            print(f"-> Seed manifest '{seed_manifest_path}' loaded.")
        except FileNotFoundError:
            print(f"ERROR: Seed manifest not found at '{seed_manifest_path}'")
            exit()

        self.language = self.seed_manifest.get("language", "Español")

        # El manifiesto final que construiremos. Empezamos con los datos de la semilla.
        self.final_manifest = self.seed_manifest.copy()

    def _call_ai_for_yaml(self, prompt: str) -> str:
        """Llama a la IA esperando una respuesta en formato YAML."""
        full_prompt = (
            f"You are a creative world-building assistant. Your task is to expand upon a user's ideas. "
            f"You MUST respond in the following language: {self.language}.\n"
            "Your response must be ONLY a valid YAML block, without any introductory text or markdown fences (```yaml).\n\n"
            f"--- PROMPT ---\n{prompt}"
        )

        print("\n>>> [AI is generating a proposal...]...")
        time.sleep(2)
        response = self.ai_provider.generate_text(
            full_prompt, temperature=0.8, max_tokens=2500
        )

        # Limpiamos la respuesta para quedarnos solo con el YAML
        response = response.strip().replace("```yaml", "").replace("```", "").strip()
        print(f"--- AI Proposal ---\n{response}\n-------------------")
        return response

    def _get_user_feedback(self, section_name: str) -> str:
        """Obtiene y formatea el feedback del usuario para una sección."""
        prompt = f"-> Review the proposal for '{section_name}'.\n   Press ENTER to APPROVE, 'exit' to cancel, or type your notes to REFINE:\n> "
        feedback = input(prompt).strip()

        if feedback.lower() in ["aprobar", "ok", "listo", "sí", "si", ""]:
            return "APPROVE"
        if feedback.lower() == "exit":
            return "EXIT"
        return feedback

    def _refine_section(self, section_name: str, generation_prompt: str):
        """Gestiona el ciclo de propuesta y refinamiento para una sección del manifiesto."""
        print(f"\n--- Expanding Section: {section_name.upper()} ---")

        context = f"**Current state of the manifest:**\n```yaml\n{yaml.dump(self.final_manifest, allow_unicode=True)}\n```\n\n"

        current_proposal_yaml = self._call_ai_for_yaml(context + generation_prompt)

        # Límite de intentos para evitar bucles infinitos
        yaml_correction_attempts = 0
        max_yaml_attempts = 3

        while True:
            try:
                parsed_proposal = yaml.safe_load(current_proposal_yaml)
                break  # YAML válido, salir del bucle de corrección
            except yaml.YAMLError as e:
                yaml_correction_attempts += 1
                print(
                    f"WARNING: AI generated invalid YAML (attempt {yaml_correction_attempts}/{max_yaml_attempts}). Error: {e}"
                )

                if yaml_correction_attempts >= max_yaml_attempts:
                    print(
                        f"ERROR: Failed to get valid YAML after {max_yaml_attempts} attempts. Skipping section '{section_name}'."
                    )
                    return

                current_proposal_yaml = self._call_ai_for_yaml(
                    f"The previous YAML was invalid. Please fix it and provide only the corrected YAML.\n"
                    f"Error: {e}\n"
                    f"Previous attempt:\n{current_proposal_yaml}"
                )

        # Bucle principal de refinamiento
        while True:

            feedback = self._get_user_feedback(section_name)

            if feedback == "APPROVE":
                self.final_manifest.update(parsed_proposal)
                print(f"-> Section '{section_name}' approved and merged.")
                break
            if feedback == "EXIT":
                print("-> Exiting session without saving.")
                exit()

            # Refinamiento basado en feedback del usuario
            refinement_prompt = (
                f"The user wants to refine the last proposal for '{section_name}'.\n"
                f"**User Feedback:** '{feedback}'\n"
                f"**Your Previous Proposal:**\n```yaml\n{current_proposal_yaml}\n```\n"
                "Please generate a new, complete YAML block for this section that incorporates the user's feedback."
            )
            current_proposal_yaml = self._call_ai_for_yaml(context + refinement_prompt)

            # Resetear el contador de intentos YAML para el nuevo intento
            yaml_correction_attempts = 0

    def forge_manifest(self):
        """Orquesta la expansión completa del manifiesto semilla."""

        # --- SECCIÓN 1: CREATIVE EXAMPLES (con el formato rico y detallado de diccionarios) ---
        creative_examples_prompt = (
            "Based on the `high_level_inspiration` and `inhabitant_description`, expand the `creative_examples` section. "
            "Generate `location_suggestions` and `npc_archetypes_examples`.\n"
            "**CRITICAL:** The value for each suggestion MUST be a YAML dictionary with 'name', 'description', and 'aspects' (a list of strings).\n\n"
            "**CORRECT FORMAT EXAMPLE:**\n"
            "```yaml\n"
            "creative_examples:\n"
            "  location_suggestions:\n"
            "    - name: 'El Palacio de la Princesa Zz'\n"
            "      description: 'Un palacio rosa brillante flotando sobre un planeta de algodón de azúcar.'\n"
            "      aspects:\n"
            "        - 'Decoración excesivamente cursi'\n"
            "        - 'Guardias reales distraídos y torpes'\n"
            "```"
        )

        self._refine_section("creative_examples", creative_examples_prompt)

        # --- SECCIÓN 2: NARRATIVE BIBLE (este ya estaba bien) ---
        narrative_bible_prompt = "Now, create the `narrative_bible`. Based on all the information so far, generate a `synopsis`, a list of `main_characters` (each with name, aspect, description), a list of `key_locations` (each with name, aspects, description), and a list of `plot_hooks` (each with title, description)."

        self._refine_section("narrative_bible", narrative_bible_prompt)

        # Guardado final
        print(
            "\n--- Manifest expansion complete! Saving the full Adventure Bible... ---"
        )
        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.final_manifest,
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2,
                )
            print(f"-> Full manifest successfully saved to '{self.output_path}'")
        except (OSError, IOError) as e:
            print(f"ERROR: Could not save the file. {e}")
        except yaml.YAMLError as e:
            print(f"ERROR: Error generating YAML output. {e}")


if __name__ == "__main__":
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))

        SEED_MANIFEST_PATH = os.path.join(project_root, "manifest_seed.yaml")
        OUTPUT_MANIFEST_PATH = os.path.join(project_root, "manifest_world.yaml")

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

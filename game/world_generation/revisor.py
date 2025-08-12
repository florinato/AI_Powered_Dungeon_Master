# game/world_generation/revisor.py

import json
import random
from typing import Dict, List


class WorldRevisor:
    """
    Actúa como un Asistente de Producción y Corrector Técnico.
    Toma un mundo generado narrativamente rico y lo estandariza para
    asegurar que sea técnicamente robusto y 100% jugable por el motor del juego.
    """

    def __init__(self, input_path: str, output_path: str):
        print("--- World Revisor (Technical & Design Polish Mode) Initialized ---")
        self.input_path = input_path
        self.output_path = output_path

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                self.world_data = json.load(f)
            print(f"Successfully loaded raw world data from '{input_path}'")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"FATAL: Could not load or parse the input file. Error: {e}")
            raise

        # Creamos los mapas de assets una vez, se actualizarán si es necesario
        self._update_asset_maps()

    def revise_and_save(self):
        """Orquesta las pasadas de validación y estandarización."""
        print("\n--- Beginning Technical & Design Revision ---")

        # 1. Pasadas de estandarización de datos en bruto
        self._standardize_quest_objective_types()
        self._resolve_objective_names_to_ids()

        # 2. Pasadas de lógica de diseño y colocación
        self._consolidate_unique_npc_placements()
        self._place_mission_bosses()

        # 3. Pasada final de limpieza
        self._final_technical_pass()

        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(self.world_data, f, indent=2, ensure_ascii=False)
            print(
                f"\n--- SUCCESS! Fully revised world saved to '{self.output_path}' ---"
            )
        except Exception as e:
            print(f"FATAL: Could not save revised world file. Error: {e}")

    def _update_asset_maps(self):
        """Crea diccionarios para un acceso rápido a los assets por su ID y nombre."""
        self.locations = {
            loc["id"]: loc for loc in self.world_data.get("locations", [])
        }
        self.items = {
            item["id"]: item for item in self.world_data.get("item_templates", [])
        }
        self.npcs = {npc["id"]: npc for npc in self.world_data.get("npc_templates", [])}
        self.quests = {q["id"]: q for q in self.world_data.get("quests", [])}

        # Mapas inversos para buscar IDs por nombre
        self.item_name_to_id = {
            data["name"].lower(): id for id, data in self.items.items()
        }
        self.npc_name_to_id = {
            data["name"].lower(): id for id, data in self.npcs.items()
        }

    # --- NUEVA FUNCIÓN ---
    def _standardize_quest_objective_types(self):
        """Recorre todas las misiones y unifica los 'type' de los objetivos."""
        print("\n[Pass 1] Standardizing quest objective types...")
        type_map = {
            "meet_npc": "npc",
            "find_item": "item",
            "use_item": "item",  # Asumimos que usar un item implica tenerlo primero
            "fight": "npc",  # Asumimos que pelear implica un PNJ
            "boss_fight": "npc",
            "defeat_boss": "npc",
            "defeat": "npc",
            "interact": "npc",
        }
        for quest in self.world_data.get("quests", []):
            for step in quest.get("steps", []):
                obj = step.get("objective", {})
                if not isinstance(obj, dict):
                    continue

                original_type = obj.get("type")
                if original_type in type_map:
                    new_type = type_map[original_type]
                    obj["type"] = new_type
                    print(
                        f"  -> Standardized objective type in '{quest['title']}': '{original_type}' -> '{new_type}'."
                    )

    # --- NUEVA FUNCIÓN ---
    def _resolve_objective_names_to_ids(self):
        """Reemplaza nombres en los objetivos por sus IDs de asset reales."""
        print("\n[Pass 2] Resolving objective names to asset IDs...")
        for quest in self.world_data.get("quests", []):
            for step in quest.get("steps", []):
                obj = step.get("objective", {})
                if not isinstance(obj, dict):
                    continue

                obj_type = obj.get("type")
                obj_id_or_name = obj.get("id", "").lower()

                if obj_type == "item":
                    if obj_id_or_name in self.item_name_to_id:
                        obj["id"] = self.item_name_to_id[obj_id_or_name]
                        print(
                            f"  -> Resolved item objective in '{quest['title']}': '{obj_id_or_name}' -> '{obj['id']}'."
                        )

                elif obj_type == "npc":
                    # Maneja tanto el nombre del PNJ como el nombre del jefe
                    if obj_id_or_name in self.npc_name_to_id:
                        obj["id"] = self.npc_name_to_id[obj_id_or_name]
                        print(
                            f"  -> Resolved NPC objective in '{quest['title']}': '{obj_id_or_name}' -> '{obj['id']}'."
                        )
                    elif quest.get("final_boss_id"):
                        boss_data = self.npcs.get(quest["final_boss_id"])
                        if boss_data and boss_data["name"].lower() == obj_id_or_name:
                            obj["id"] = quest["final_boss_id"]
                            print(
                                f"  -> Resolved Boss objective in '{quest['title']}': '{obj_id_or_name}' -> '{obj['id']}'."
                            )

    def _consolidate_unique_npc_placements(self):
        """Asegura que los PNJs únicos del reparto principal solo aparezcan en un nodo."""
        print("\n[Pass 3] Consolidating unique NPC placements...")
        unique_npcs = {
            npc_id
            for npc_id, data in self.npcs.items()
            if data.get("assigned_role") != "extra"
        }

        placement_map: Dict[str, str] = {}
        duplicates_to_remove: List[tuple[str, str]] = []

        for loc_id, loc_data in self.locations.items():
            # Usamos list() para poder modificar la lista mientras iteramos
            for npc_id in list(loc_data.get("initial_npcs", [])):
                if npc_id in unique_npcs:
                    if npc_id not in placement_map:
                        placement_map[npc_id] = loc_id
                    else:
                        duplicates_to_remove.append((loc_id, npc_id))

        for loc_id, npc_id in duplicates_to_remove:
            if npc_id in self.locations[loc_id].get("initial_npcs", []):
                self.locations[loc_id]["initial_npcs"].remove(npc_id)
                print(
                    f"  -> Removed duplicate placement of '{npc_id}' from '{loc_id}'."
                )

    # --- NUEVA FUNCIÓN ---
    def _place_mission_bosses(self):
        """Coloca a los jefes de misión en la localización de su último paso."""
        print("\n[Pass 4] Placing mission bosses in final locations...")
        for quest in self.world_data.get("quests", []):
            boss_id = quest.get("final_boss_id")
            if not boss_id:
                continue

            # Encontrar la localización del último paso
            last_step = quest.get("steps", [])[-1] if quest.get("steps") else None
            if not last_step or not isinstance(last_step, dict):
                continue

            last_step_obj = last_step.get("objective", {})
            target_loc_id = None

            if last_step_obj.get("type") == "location":
                target_loc_id = last_step_obj.get("id")
            elif last_step_obj.get("type") == "npc":
                # Si el último paso es derrotar al jefe, lo colocamos en la misma sala.
                # Pero si es otro PNJ, lo colocamos en una sala aleatoria.
                # Lógica simplificada: lo ponemos en una sala aleatoria que no sea el inicio.
                start_loc = self.world_data["world"]["starting_location_id"]
                available_locs = [lid for lid in self.locations if lid != start_loc]
                if available_locs:
                    target_loc_id = random.choice(available_locs)

            if target_loc_id and target_loc_id in self.locations:
                # Quitar al jefe de cualquier otra ubicación
                for loc in self.locations.values():
                    if boss_id in loc.get("initial_npcs", []):
                        loc["initial_npcs"].remove(boss_id)

                # Colocarlo en la ubicación correcta
                self.locations[target_loc_id].setdefault("initial_npcs", []).append(
                    boss_id
                )
                print(
                    f"  -> Placed boss '{boss_id}' for quest '{quest['title']}' in final location '{target_loc_id}'."
                )

    def _final_technical_pass(self):
        """Realiza la limpieza final, como estandarizar IDs de pasos."""
        print("\n[Final Pass] Performing technical cleanup...")
        for quest in self.world_data.get("quests", []):
            for i, step in enumerate(quest.get("steps", [])):
                if not isinstance(step, dict):
                    continue
                step["id"] = f"step_{i+1}"

# game/grid_map_generator.py
import json
import random

import matplotlib.pyplot as plt
import networkx as nx


class GridMapGenerator:
    """
    Actúa como un Arquitecto de Mundos, generando un plano estructural
    completo y parametrizado para el DirectorAgent.
    """
    def __init__(self, width: int, height: int, pruning_ratio: float, 
                 generic_npc_range: tuple, item_range: tuple, 
                 quest_node_count: int, trap_chance: float):
        # --- Parámetros de Control ---
        self.width = width
        self.height = height
        self.pruning_ratio = pruning_ratio
        self.generic_npc_range = generic_npc_range # Rango para PNJs "extra"
        self.item_range = item_range
        self.quest_node_count = quest_node_count # Número EXACTO de nodos con misión
        self.trap_chance = trap_chance
        
        # --- Estructuras de Datos Internas ---
        self.graph = nx.Graph()
        self.nodes_dict = {}
        self.node_positions = {}

    def generate_map(self):
        """Orquesta todo el proceso: rejilla, podado y población de cada nodo."""
        print("--- World Architect Initialized (Full Control Mode) ---")
        self._generate_base_grid()
        self._prune_edges()
        self._designate_special_nodes()
        self._populate_all_nodes_with_content()
        print("--- World Architecture Blueprint Complete ---")

    def _generate_base_grid(self):
        print(f"[Step 1/4] Generating {self.width}x{self.height} base grid...")
        for y in range(self.height):
            for x in range(self.width):
                node_id = f"node_{x}_{y}"
                # Inicializamos el diccionario del nodo con valores por defecto
                self.nodes_dict[node_id] = {
                    "id": node_id,
                    "has_quest_start": False, # Por defecto, ningún nodo tiene misión
                    "has_trap": False
                }
                self.node_positions[node_id] = (x, -y)
                self.graph.add_node(node_id)
        
        for y in range(self.height):
            for x in range(self.width):
                if x < self.width - 1: self.graph.add_edge(f"node_{x}_{y}", f"node_{x+1}_{y}")
                if y < self.height - 1: self.graph.add_edge(f"node_{x}_{y}", f"node_{x}_{y+1}")

    def _prune_edges(self):
        print(f"[Step 2/4] Pruning {self.pruning_ratio*100:.0f}% of connections...")
        edges_to_check = list(self.graph.edges())
        random.shuffle(edges_to_check)
        target_removal = int(len(edges_to_check) * self.pruning_ratio)
        removed_count = 0
        for edge in edges_to_check:
            if removed_count >= target_removal: break
            self.graph.remove_edge(*edge)
            if not nx.is_connected(self.graph):
                self.graph.add_edge(*edge)
            else:
                removed_count += 1
        print(f"  -> Pruning complete. Removed {removed_count} edges.")

    def _designate_special_nodes(self):
        """Elige aleatoriamente qué nodos tendrán el inicio de una misión."""
        print(f"[Step 3/4] Designating {self.quest_node_count} nodes as quest start points...")
        all_node_ids = list(self.nodes_dict.keys())
        num_to_designate = min(self.quest_node_count, len(all_node_ids))
        
        quest_start_nodes = random.sample(all_node_ids, num_to_designate)
        
        for node_id in quest_start_nodes:
            self.nodes_dict[node_id]['has_quest_start'] = True

    def _populate_all_nodes_with_content(self):
        """Itera sobre cada nodo y le asigna contadores de PNJs genéricos, items y trampas."""
        print(f"[Step 4/4] Populating ALL nodes with content blueprints...")
        totals = {"generic_npcs": 0, "items": 0, "quests": 0, "traps": 0}

        for node_id in self.nodes_dict:
            # Asignar PNJs "extra" e Items
            num_generic_npcs = random.randint(*self.generic_npc_range)
            num_items = random.randint(*self.item_range)
            
            # Asignar trampa basado en probabilidad
            has_trap = random.random() < self.trap_chance
            self.nodes_dict[node_id]['has_trap'] = has_trap

            # Guardamos los contadores. Los PNJs de misión no se cuentan aquí.
            self.nodes_dict[node_id]['generic_npc_count'] = num_generic_npcs
            self.nodes_dict[node_id]['item_count'] = num_items

            # Actualizar totales para el informe final
            totals["generic_npcs"] += num_generic_npcs
            totals["items"] += num_items
            if self.nodes_dict[node_id]['has_quest_start']: totals["quests"] += 1
            if has_trap: totals["traps"] += 1
            
        print(f"  -> Generated a total of {totals['generic_npcs']} generic NPC placeholders.")
        print(f"  -> Generated a total of {totals['items']} Item placeholders.")
        print(f"  -> Designated {totals['quests']} nodes as quest start points.")
        print(f"  -> Placed {totals['traps']} trap placeholders.")

    def assemble_output(self) -> dict:
        """Prepara el diccionario final para el DirectorAgent, combinando toda la información."""
        nodes_output_dict = {}
        for node_id, node_data in self.nodes_dict.items():
            # ¡CORRECCIÓN CLAVE!
            # El blueprint final ahora usa los nombres exactos que espera el modelo Pydantic:
            # 'npc_count' en lugar de 'generic_npc_count'.
            nodes_output_dict[node_id] = {
                "id": node_id,
                "type": "sala",
                "tags": [],
                "connections": [],
                "npc_count": node_data.get('generic_npc_count', 0), # Mapeamos aquí
                "item_count": node_data.get('item_count', 0),
                "has_quest_start": node_data.get('has_quest_start', False),
                "has_trap": node_data.get('has_trap', False)
            }
        
        # Esta parte de las conexiones estaba mal, usaba 'sur'/'norte'/'este'/'oeste'
        # cuando debería usar las coordenadas para determinar la dirección.
        for u, v in self.graph.edges():
            # Extraemos coordenadas para una lógica de dirección robusta
            try:
                x1, y1 = map(int, u.split('_')[1:])
                x2, y2 = map(int, v.split('_')[1:])

                if y1 < y2:
                    dir_uv, dir_vu = "sur", "norte"
                elif y1 > y2:
                    dir_uv, dir_vu = "norte", "sur"
                elif x1 < x2:
                    dir_uv, dir_vu = "este", "oeste"
                else: # x1 > x2
                    dir_uv, dir_vu = "oeste", "este"
            except (ValueError, IndexError):
                 # Fallback si los IDs no son numéricos
                 dir_uv, dir_vu = "conexion", "conexion"

            nodes_output_dict[u]['connections'].append({"target_node_id": v, "direction": dir_uv})
            nodes_output_dict[v]['connections'].append({"target_node_id": u, "direction": dir_vu})

        graph_id = f"grid_map_{self.width}x{self.height}_p{int(self.pruning_ratio*100)}"
        return {"graph_id": graph_id, "nodes": nodes_output_dict}
    def visualize_map(self):
        """Visualiza el mapa con información de la densidad de contenido."""
        plt.figure(figsize=(self.width * 2.5, self.height * 2.5))
        
        node_colors = []
        for nid in self.graph.nodes():
            if self.nodes_dict[nid].get('has_quest_start'):
                node_colors.append('gold')
            elif self.nodes_dict[nid].get('has_trap'):
                node_colors.append('firebrick')
            else:
                node_colors.append('skyblue')

        nx.draw(self.graph, self.node_positions, with_labels=False, node_size=1000, node_color=node_colors)
        
        labels = {
            nid: (f"ID: {nid.split('_')[1]},{nid.split('_')[2]}\n"
                  f"Extras: {data.get('generic_npc_count', 0)}\n"
                  f"Items: {data.get('item_count', 0)}\n"
                  f"{'QUEST' if data.get('has_quest_start') else ''}\n"
                  f"{'TRAP' if data.get('has_trap') else ''}")
            for nid, data in self.nodes_dict.items()
        }
        nx.draw_networkx_labels(self.graph, self.node_positions, labels=labels, font_color='black', font_size=7)
        
        plt.title(f"Content Blueprint ({self.width}x{self.height})")
        plt.show()

# --- BLOQUE PRINCIPAL: TU PANEL DE CONTROL FINAL ---

if __name__ == "__main__":
    
    # ------------------------------------------------------------------
    # --- PARÁMETROS DEL MUNDO: ¡MÁXIMO CONTROL AQUÍ! ---
    # ------------------------------------------------------------------
    
    # 1. TAMAÑO DEL MAPA
    MAP_WIDTH = 3
    MAP_HEIGHT = 3
    
    # 2. CONECTIVIDAD (0.0 = laberinto, 1.0 = rejilla completa)
    PRUNING_RATIO = 1
    
    # 3. NÚMERO TOTAL DE MISIONES EN EL MUNDO
    TOTAL_QUESTS = 3
    
    # 4. PNJS "EXTRA" POR SALA (min, max) - Estos se suman a los de las misiones
    GENERIC_NPCS_PER_NODE = (0, 1)
    
    # 5. OBJETOS TOTALES POR SALA (min, max)
    ITEMS_PER_NODE = (0, 1)
    
    # 6. PROBABILIDAD DE TRAMPA POR NODO
    TRAP_CHANCE = 0.50 # 20% de las salas
    
    # ------------------------------------------------------------------
    
    try:
        print(f"Generating a {MAP_WIDTH}x{MAP_HEIGHT} map blueprint with specified parameters...")

        generator = GridMapGenerator(
            width=MAP_WIDTH, height=MAP_HEIGHT,
            pruning_ratio=PRUNING_RATIO,
            generic_npc_range=GENERIC_NPCS_PER_NODE, item_range=ITEMS_PER_NODE,
            quest_node_count=TOTAL_QUESTS, trap_chance=TRAP_CHANCE
        )
        
        generator.generate_map()
        generator.visualize_map()

        final_structure = generator.assemble_output()
        output_filename = f"{final_structure['graph_id']}_blueprint.json"
        with open(output_filename, "w") as f:
            json.dump(final_structure, f, indent=2)
        
        print(f"\nWorld blueprint saved to '{output_filename}'!")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
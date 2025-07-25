# game/grid_map_generator.py
import json
import math
import random

import matplotlib.pyplot as plt
import networkx as nx


class GridMapGenerator:
    def __init__(self, width: int, height: int, target_pruning_ratio: float = 0.5):
        if width < 2 or height < 2:
            raise ValueError("Width and height must be at least 2.")
        if not (0.0 <= target_pruning_ratio <= 1.0):
            raise ValueError("Pruning ratio must be between 0.0 and 1.0.")
            
        self.width = width
        self.height = height
        self.target_pruning_ratio = target_pruning_ratio
        
        self.nodes_dict = {} # Usaremos un diccionario para acceder fácilmente
        self.edges_list = []
        self.node_positions = {}
        self.graph = nx.Graph()

    def _prune_edges_safely(self, initial_edges: set):
        self.graph.add_nodes_from(self.nodes_dict.keys())
        self.graph.add_edges_from(list(initial_edges))
        
        edges_to_check = list(self.graph.edges())
        random.shuffle(edges_to_check)
        
        num_edges_to_remove_target = int(len(edges_to_check) * self.target_pruning_ratio)
        edges_removed_count = 0

        for edge in edges_to_check:
            if edges_removed_count >= num_edges_to_remove_target: break
            self.graph.remove_edge(*edge)
            if nx.is_connected(self.graph):
                edges_removed_count += 1
            else:
                self.graph.add_edge(*edge)
        
        print(f"Pruning complete. Target: {num_edges_to_remove_target}, Actual removed: {edges_removed_count}")
        return set(self.graph.edges())

    def generate_map_structure(self):
        """Genera la estructura base de nodos y aristas."""
        for y in range(self.height):
            for x in range(self.width):
                node_id = f"node_{x}_{y}"
                self.nodes_dict[node_id] = {"id": node_id} # Llenamos el dict
                self.node_positions[node_id] = (x, -y)

        initial_edges = set()
        for y in range(self.height):
            for x in range(self.width):
                current_node = f"node_{x}_{y}"
                if x < self.width - 1:
                    initial_edges.add(tuple(sorted((current_node, f"node_{x+1}_{y}"))))
                if y < self.height - 1:
                    initial_edges.add(tuple(sorted((current_node, f"node_{x}_{y+1}"))))
        
        final_edges_set = self._prune_edges_safely(initial_edges)

        for node1, node2 in final_edges_set:
            x1, y1 = map(int, node1.split('_')[1:])
            x2, y2 = map(int, node2.split('_')[1:])
            dir1, dir2 = ("south", "north") if x1 == x2 else ("east", "west")
            self.edges_list.append({"source": node1, "target": node2, "direction": dir1})
            self.edges_list.append({"source": node2, "target": node1, "direction": dir2})

    def _zone_map(self, zoning_config: dict):
        """
        Asigna types y tags a los nodos del mapa basándose en una configuración y lógica procedural.
        """
        print("\n--- Zoning Map ---")
        all_node_ids = list(self.nodes_dict.keys())
        
        # 1. Identificar Nodos Clave
        center_x, center_y = self.width / 2, self.height / 2
        
        # Ordenar nodos por distancia al centro
        nodes_by_distance = sorted(all_node_ids, key=lambda nid: math.dist((int(nid.split('_')[1]), int(nid.split('_')[2])), (center_x, center_y)))
        
        # Nodos sin salida (dead ends)
        dead_ends = [nid for nid, degree in self.graph.degree() if degree == 1]
        print(f"Identified {len(dead_ends)} dead-end nodes.")

        # 2. Asignar Tipos (`type`)
        num_nodes = len(all_node_ids)
        num_hubs = int(num_nodes * zoning_config.get("hub_ratio", 0.15))
        num_landmarks = int(num_nodes * zoning_config.get("landmark_ratio", 0.10))
        
        assigned_nodes = set()
        
        # Asignar Hubs (priorizando el centro)
        hubs = []
        for nid in nodes_by_distance:
            if len(hubs) < num_hubs:
                self.nodes_dict[nid]['type'] = "hub"
                hubs.append(nid)
                assigned_nodes.add(nid)
        print(f"Assigned {len(hubs)} nodes as 'hub'.")

        # Asignar Landmarks (priorizando dead ends y periferia)
        landmarks = []
        # Primero, llenamos con dead ends si es posible
        for nid in dead_ends:
            if len(landmarks) < num_landmarks and nid not in assigned_nodes:
                self.nodes_dict[nid]['type'] = "landmark"
                landmarks.append(nid)
                assigned_nodes.add(nid)
        # Luego, rellenamos con nodos periféricos si faltan
        for nid in reversed(nodes_by_distance):
             if len(landmarks) < num_landmarks and nid not in assigned_nodes:
                self.nodes_dict[nid]['type'] = "landmark"
                landmarks.append(nid)
                assigned_nodes.add(nid)
        print(f"Assigned {len(landmarks)} nodes as 'landmark'.")
        
        # Asignar Fillers
        filler_type = zoning_config.get("filler_type", "pasaje")
        fillers = []
        for nid in all_node_ids:
            if nid not in assigned_nodes:
                self.nodes_dict[nid]['type'] = filler_type
                fillers.append(nid)
        print(f"Assigned {len(fillers)} nodes as '{filler_type}'.")

        # 3. Asignar Etiquetas (`tags`)
        for nid in all_node_ids:
            self.nodes_dict[nid]['tags'] = [] # Inicializar lista de tags
            node_type = self.nodes_dict[nid]['type']
            
            for tag, rules in zoning_config.get("tags", {}).items():
                # Reglas de probabilidad
                if "chance" in rules and node_type in rules.get("on_type", []):
                    if random.random() < rules["chance"]:
                        self.nodes_dict[nid]['tags'].append(tag)
        
        # Reglas de conteo (garantizan que existan ciertos tags)
        for tag, rules in zoning_config.get("tags", {}).items():
            if "count" in rules:
                potential_nodes = [nid for nid in all_node_ids if self.nodes_dict[nid]['type'] in rules.get("on_type", []) and tag not in self.nodes_dict[nid]['tags']]
                if not potential_nodes: # Fallback si no hay nodos adecuados
                    potential_nodes = all_node_ids
                
                chosen_nodes = random.sample(potential_nodes, min(rules["count"], len(potential_nodes)))
                for nid in chosen_nodes:
                    self.nodes_dict[nid]['tags'].append(tag)
                print(f"Assigned tag '{tag}' to {len(chosen_nodes)} specific node(s).")
        
        print("--- Zoning Complete ---")

    def assemble_output(self):
        """Prepara el diccionario final compatible con el modelo WorldGraph."""
        nodes_output_dict = {}
        for node_id, node_data in self.nodes_dict.items():
            nodes_output_dict[node_id] = {
                "id": node_id,
                "type": node_data.get('type', 'room'),
                "tags": node_data.get('tags', []),
                "size": "medium", # Por ahora, todos medium
                "connections": []
            }
        
        for edge in self.edges_list:
            source_id = edge['source']
            nodes_output_dict[source_id]['connections'].append({
                "target_node_id": edge['target'],
                "direction": edge['direction'],
                "properties": { "is_locked": False, "is_hidden": False, "is_one_way": False }
            })

        graph_id = f"grid_map_{self.width}x{self.height}_p{int(self.target_pruning_ratio*100)}"
        return {
            "graph_id": graph_id,
            "nodes": nodes_output_dict
        }

    def visualize_map(self):
        """Visualiza el mapa zonificado con colores."""
        color_map = {'hub': 'gold', 'landmark': 'firebrick', 'pasaje': 'skyblue'}
        node_colors = [color_map.get(self.nodes_dict[nid].get('type'), 'gray') for nid in self.graph.nodes()]

        plt.figure(figsize=(self.width * 1.5, self.height * 1.5))
        nx.draw(self.graph, self.node_positions, with_labels=False, node_size=300, node_color=node_colors)
        
        # Etiquetas: ID, Tipo y Tags
        labels = {nid: f"{nid.split('_')[1]},{nid.split('_')[2]}\n{data['type']}\n{','.join(data['tags'])}" for nid, data in self.nodes_dict.items()}
        nx.draw_networkx_labels(self.graph, self.node_positions, labels=labels, font_size=6, font_color='black')
        
        plt.title(f"Zoned Map ({self.width}x{self.height})")
        print("Displaying zoned map visualization. Close the plot window to continue.")
        plt.show()

# --- Bloque principal ---
if __name__ == "__main__":
    
    # --- ¡NUESTRA RECETA DE MAPA AJUSTABLE! ---
    ZONING_CONFIG = {
        "hub_ratio": 0.15,
        "landmark_ratio": 0.10,
        "filler_type": "pasaje",
        "tags": {
            "safe": {"chance": 0.9, "on_type": ["hub"]},
            "dangerous": {"chance": 0.7, "on_type": ["landmark", "pasaje"]},
            "rich": {"chance": 0.4, "on_type": ["hub", "landmark"]},
            "poor": {"chance": 0.5, "on_type": ["pasaje"]},
            "quest_start": {"count": 1, "on_type": ["hub"]},
            "quest_end": {"count": 1, "on_type": ["landmark"]}
        }
    }

    while True:
        try:
            width = int(input(f"Enter map width (default: 8): ") or 8)
            height = int(input(f"Enter map height (default: 6): ") or 6)
            pruning_ratio = float(input(f"Enter pruning ratio (default: 0.5): ") or 0.5)
            
            generator = GridMapGenerator(width, height, pruning_ratio)
            
            # 1. Generar la estructura
            generator.generate_map_structure()
            
            # 2. ¡Aplicar la zonificación!
            generator._zone_map(ZONING_CONFIG)

            # 3. Visualizar el resultado
            generator.visualize_map()

            save_map = input("Do you like this map? (yes/no): ").lower().strip()
            
            if save_map in ['y', 'yes']:
                # 4. Ensamblar y guardar
                final_structure = generator.assemble_output()
                
                output_filename = f"{final_structure['graph_id']}_zoned_structure.json"
                with open(output_filename, "w") as f:
                    json.dump(final_structure, f, indent=2)
                
                print(f"Zoned map structure saved to '{output_filename}'!")
                print("This file contains rich structural information for the DirectorAgent.")
                break
            else:
                print("Generating a new map...\n")

        except (ValueError, TypeError) as e:
            print(f"\nError: Invalid input. Please enter valid numbers. Details: {e}")
            break
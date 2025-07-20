# grid_map_generator.py (Versión 4.0 - Compatible con los modelos Pydantic)
import json
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
        
        # Atributos que se llenarán durante la generación
        self.nodes_list = []
        self.edges_list = []
        self.node_positions = {}

    def _prune_edges_safely(self, edges_set: set):
        G = nx.Graph()
        G.add_nodes_from([node['id'] for node in self.nodes_list])
        G.add_edges_from(list(edges_set))
        edges_to_check = list(G.edges())
        random.shuffle(edges_to_check)
        
        num_edges_to_remove_target = int(len(edges_to_check) * self.target_pruning_ratio)
        edges_removed_count = 0

        for edge in edges_to_check:
            if edges_removed_count >= num_edges_to_remove_target: break
            G.remove_edge(*edge)
            if nx.is_connected(G):
                edges_removed_count += 1
            else:
                G.add_edge(*edge)
        
        print(f"Pruning complete. Target: {num_edges_to_remove_target}, Actual removed: {edges_removed_count}")
        return set(G.edges())

    def generate_map_structure(self):
        """Genera la estructura base de nodos y aristas y la almacena en los atributos de la clase."""
        # 1. Crear nodos
        for y in range(self.height):
            for x in range(self.width):
                node_id = f"node_{x}_{y}"
                self.nodes_list.append({"id": node_id})
                self.node_positions[node_id] = (x, -y)

        # 2. Conectar todo
        initial_edges = set()
        for y in range(self.height):
            for x in range(self.width):
                current_node = f"node_{x}_{y}"
                if x < self.width - 1:
                    initial_edges.add(tuple(sorted((current_node, f"node_{x+1}_{y}"))))
                if y < self.height - 1:
                    initial_edges.add(tuple(sorted((current_node, f"node_{x}_{y+1}"))))
        
        # 3. Podar de forma segura
        final_edges_set = self._prune_edges_safely(initial_edges)

        # 4. Crear la lista final de aristas con direcciones
        for node1, node2 in final_edges_set:
            x1, y1 = map(int, node1.split('_')[1:])
            x2, y2 = map(int, node2.split('_')[1:])
            
            if x1 == x2: # Vertical
                dir1, dir2 = ("south", "north")
            else: # Horizontal
                dir1, dir2 = ("east", "west")

            self.edges_list.append({"source": node1, "target": node2, "direction": dir1})
            self.edges_list.append({"source": node2, "target": node1, "direction": dir2})

    def visualize_map(self):
        G = nx.Graph()
        G.add_nodes_from([node['id'] for node in self.nodes_list])
        G.add_edges_from([(edge['source'], edge['target']) for edge in self.edges_list if edge['direction'] in ['east', 'south']])
        
        plt.figure(figsize=(self.width * 1.5, self.height * 1.5))
        nx.draw(G, self.node_positions, with_labels=False, node_size=250, node_color='skyblue')
        labels = {nid: f"{nid.split('_')[1]},{nid.split('_')[2]}" for nid in G.nodes()}
        nx.draw_networkx_labels(G, self.node_positions, labels=labels, font_size=7, font_color='black')
        plt.title(f"Generated Map ({self.width}x{self.height}, Target Pruning: {self.target_pruning_ratio})")
        print("Displaying map visualization. Close the plot window to continue.")
        plt.show()

# --- Bloque principal ---
if __name__ == "__main__":
    while True:
        try:
            width = int(input(f"Enter map width (default: 8): ") or 8)
            height = int(input(f"Enter map height (default: 6): ") or 6)
            pruning_ratio = float(input(f"Enter target pruning ratio (0.0 to 1.0, default: 0.5): ") or 0.5)
            
            generator = GridMapGenerator(width, height, pruning_ratio)
            generator.generate_map_structure()
            generator.visualize_map()

            save_map = input("Do you like this map? (yes/no): ").lower().strip()
            
            if save_map in ['y', 'yes']:
                # --- AQUÍ ENSAMBLAMOS EL JSON CON EL FORMATO CORRECTO ---
                
                # 1. Crear el diccionario de nodos `LocationNode`
                nodes_dict = {}
                for node_data in generator.nodes_list:
                    node_id = node_data['id']
                    nodes_dict[node_id] = {
                        "id": node_id,
                        "type": "room", # Valor por defecto, el Director puede usarlo
                        "tags": ["dungeon"], # Valor por defecto
                        "size": "medium",
                        "connections": [] # Se rellenará a continuación
                    }

                # 2. Rellenar la lista `connections` de cada nodo
                for edge in generator.edges_list:
                    source_id = edge['source']
                    nodes_dict[source_id]['connections'].append({
                        "target_node_id": edge['target'],
                        "direction": edge['direction'],
                        "properties": { # Valores por defecto para WorldConnection
                            "is_locked": False,
                            "is_hidden": False,
                            "is_one_way": False
                        }
                    })

                # 3. Crear la estructura raíz `WorldGraph`
                graph_id = f"grid_map_{width}x{height}_p{int(pruning_ratio*100)}"
                final_structure = {
                    "graph_id": graph_id,
                    "nodes": nodes_dict
                }
                
                output_filename = f"{graph_id}_structure.json"
                with open(output_filename, "w") as f:
                    json.dump(final_structure, f, indent=2)
                
                print(f"Map structure saved successfully to '{output_filename}'!")
                print("This file is now 100% compatible with the DirectorAgent's WorldGraph model.")
                break
            else:
                print("Generating a new map...\n")

        except (ValueError, TypeError) as e:
            print(f"\nError: Invalid input. Please enter valid numbers. Details: {e}")
            break
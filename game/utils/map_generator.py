# game/map_generator.py

import json
import os
import random

import matplotlib.pyplot as plt
import networkx as nx


def generate_map_image(world_definition: dict, game_state: dict, blueprint_file: str) -> str | None:
    """
    Genera una imagen del mapa del mundo, mostrando nombres de localizaciones,
    PNJs clave y la posición actual del jugador.
    """
    print("Generating world map image...")
    
    try:
        # 1. Cargar el blueprint para obtener la estructura y posiciones de los nodos
        with open(blueprint_file, 'r', encoding='utf-8') as f:
            blueprint = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"ERROR: Could not load the blueprint file '{blueprint_file}'. Cannot generate map.")
        return None

    # 2. Reconstruir el grafo con NetworkX
    G = nx.Graph()
    node_positions = {}
    
    # Extraemos las coordenadas X, Y del ID para posicionar los nodos
    for node_id, node_data in blueprint['nodes'].items():
        G.add_node(node_id)
        try:
            x, y = map(int, node_id.split('_')[1:])
            node_positions[node_id] = (x, -y)
        except (ValueError, IndexError):
            # Si el ID no tiene formato x_y, le damos una posición aleatoria
            node_positions[node_id] = (random.random(), random.random())
            
    for node_id, node_data in blueprint['nodes'].items():
        for connection in node_data.get('connections', []):
            target_id = connection.get('target_node_id')
            if target_id:
                G.add_edge(node_id, target_id)

    # 3. Preparar las etiquetas y colores para el mapa
    player_location_id = game_state['player']['location']
    labels = {}
    node_colors = []

    for node_id in G.nodes():
        loc_data = world_definition['locations'].get(node_id)
        if not loc_data: continue

        # Etiqueta: Nombre del lugar y PNJs importantes
        loc_name = loc_data.get('name', node_id)
        # Acortamos nombres muy largos para que quepan en el nodo
        label = f"{loc_name[:15]}{'...' if len(loc_name) > 15 else ''}"
        
        # Añadimos PNJs de misión si los hay
        npcs_in_loc = game_state['locations'][node_id].get('npcs', {})
        quest_givers = [npc['name'] for npc in npcs_in_loc.values() if npc.get('assigned_role') == 'quest_giver']
        if quest_givers:
            label += f"\n(Giver: {quest_givers[0][:10]}..)"
        
        bosses = [npc['name'] for npc in npcs_in_loc.values() if npc.get('assigned_role') == 'boss']
        if bosses:
            label += f"\n(Boss: {bosses[0][:10]}..)"

        labels[node_id] = label
        
        # Color: Un color especial para la ubicación del jugador
        if node_id == player_location_id:
            node_colors.append('gold') # Dorado para la posición actual
        else:
            node_colors.append('skyblue')

    # 4. Dibujar y guardar el mapa
    plt.figure(figsize=(12, 12))
    nx.draw(G, node_positions, with_labels=False, node_size=3500, node_color=node_colors, edge_color='gray')
    nx.draw_networkx_labels(G, node_positions, labels=labels, font_size=8, font_color='black')
    
    plt.title(f"Map of {world_definition.get('name', 'the world')}", fontsize=16)
    plt.margins(0.1) # Añadir un poco de margen
    plt.box(False) # Quitar el recuadro

    # Guardamos la imagen en una carpeta de mapas
    output_folder = "generated_maps"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    map_filepath = os.path.join(output_folder, f"{world_definition['id']}_map.png")
    plt.savefig(map_filepath, bbox_inches='tight', pad_inches=0.2)
    plt.close() # Cerramos la figura para liberar memoria
    
    print(f"Map image successfully saved to '{map_filepath}'")
    return map_filepath
    
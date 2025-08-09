# game/game_narrator.py

import re

from game.ai.ai_provider_interface import AIProviderInterface


def generate_location_description(
    provider: AIProviderInterface, 
    base_description: str, 
    location_name: str,
    world_theme: str,
    language: str
) -> str:
    """
    Genera una descripción atmosférica para la ubicación actual del jugador,
    respetando el idioma y el tema del mundo.
    """
    # --- PROMPT CORREGIDO ---
    prompt = (
        f"You are a master storyteller writing in {language}. "
        f"The world's theme is: '{world_theme}'.\n"
        f"Based on this core description in {language} for a location named '{location_name}': '{base_description}', "
        f"write a new, more atmospheric and evocative paragraph (2-4 sentences) for a player arriving here. "
        f"The response MUST be entirely in {language} and the response MUST be in {language}. Focus on sights, sounds, and smells."
    )
    description_text = provider.generate_text(prompt, temperature=0.7)
    return description_text


def generate_npc_response_text(
    provider: AIProviderInterface, 
    game_state: dict, 
    npc_id: str, # Usamos el ID para buscar, es más robusto
    player_input: str,
    world_theme: str,
    language: str
) -> str:
    """
    Genera la respuesta de un NPC basada en el estado del juego, la entrada del jugador,
    el tema del mundo y el idioma.
    """
    # --- BÚSQUEDA CORRECTA DE DATOS ---
    # Los datos del NPC y la localización ahora se obtienen de los templates del game_state
    # que se cargan desde la Base de Datos.
    npc_data = game_state["npc_templates"].get(npc_id, {})
    location_id = game_state["player"]["location"]
    location_data = game_state["locations"].get(location_id, {})
    location_name = location_data.get('name', location_id.replace('_', ' '))
    npc_name = npc_data.get('name', npc_id)

    # --- PROMPT CORREGIDO ---
    context = (
        f"You are roleplaying an NPC. Your response MUST be in {language}.\n"
        f"WORLD CONTEXT:\n"
        f"- World Theme: {world_theme}\n"
        f"- Your Name: {npc_name}\n"
        f"- Your Personality: {npc_data.get('dialogue_prompt', 'Be a generic character.')}\n"
        f"GAME SITUATION:\n"
        f"- Location: {location_name}\n"
        f"- Player Name: {game_state['player'].get('player_name', 'The Adventurer')}\n"
        f"INSTRUCTIONS: Based on your personality and the situation, give a concise, in-character response (1-3 sentences) to what the player said. Respond ONLY with your dialogue."
    )
    
    full_prompt = f"{context}\n\nPlayer says: \"{player_input}\"\n{npc_name}:"

    response = provider.generate_text(full_prompt, max_tokens=150, temperature=0.8)
    
    # La lógica de limpieza se mantiene y mejora ligeramente.
    # Elimina el prefijo "NombreNPC:" si la IA lo añade.
    response = response.strip()
    if response.lower().startswith(f"{npc_name.lower()}:"):
        response = response[len(npc_name):].lstrip(' :').strip()
        
    # Limpia las comillas que a veces la IA añade al principio y al final.
    if response.startswith('"') and response.endswith('"'):
        response = response[1:-1]
    
    return response.strip()

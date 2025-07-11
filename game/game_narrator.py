# ai_interactions/game_narrator.py

import re

from ai_provider_interface import AIProviderInterface
from models import \
    PlayerState  # Solo para type hinting, aunque ahora pasamos un dict


def generate_location_description(provider: AIProviderInterface, game_state: dict) -> str:
    """
    Genera una descripción atmosférica para la ubicación actual del jugador.
    """
    location_id = game_state['player']['location']
    location_data = game_state['locations'][location_id]
    
    # Esta función no necesita modificar el game_state, solo leerlo.
    # El bucle principal se encargará de guardar la descripción generada.
    prompt = f"{location_data.get('description', 'A mysterious place.')} Give a brief, atmospheric paragraph in D&D style, no more than 5 sentences."
    description_text = provider.generate_text(prompt)
    return description_text

def generate_npc_response_text(provider: AIProviderInterface, game_state: dict, npc_name: str, player_input: str) -> str:
    """
    Genera la respuesta de un NPC basada en el estado del juego y la entrada del jugador.
    """
    location = game_state["player"]["location"]
    npc_data = game_state["locations"][location]["npcs"].get(npc_name, {})
    
    context = (
        f"You are roleplaying as the NPC named {npc_name.capitalize()} in a fantasy RPG.\n"
        f"Your personality instructions: {npc_data.get('dialogue_prompt', 'Be a generic fantasy character.')}\n\n"
        f"GAME CONTEXT:\n"
        f"- Player's Location: {location.replace('_', ' ')}\n"
        f"- Player's HP: {game_state['player']['hp']}/{game_state['player']['max_hp']}\n"
        f"- Player's Inventory: {', '.join(item['name'] for item in game_state['player']['inventory']) or 'empty'}\n\n"
        f"INSTRUCTIONS: Based on your personality and the game context, respond to the player's last line. Keep your response concise (1-3 sentences)."
    )
    
    full_prompt = f"{context}\n\nPlayer: \"{player_input}\"\n{npc_name.capitalize()}:"

    response = provider.generate_text(full_prompt, max_tokens=150, temperature=0.8)
    
    # Limpieza de la respuesta
    if response.strip().lower().startswith(f"{npc_name.lower()}:"):
        response = response.split(":", 1)[1].strip()
        
    sentences = re.split(r'(?<=[.!?]) +', response)
    if len(sentences) > 2:
        response = ' '.join(sentences[:2])
    
    return response.strip()
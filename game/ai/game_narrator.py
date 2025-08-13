# game/game_narrator.py

import json
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


def narrate_quest_scene(
    provider: AIProviderInterface,
    game_state: dict,
    scene_data: dict
) -> tuple[str, list]:
    """
    Genera la descripción de una escena de misión y las opciones del jugador.
    Ahora con intención de escena para evitar bucles infinitos.
    """
    # Extraer datos del contexto
    quest_title = scene_data.get("quest_title", "Unknown Quest")
    step_definition = scene_data.get("step_definition", {})
    step_description = step_definition.get("description", "Continue your journey")
    step_objective = step_definition.get("objective", {})
    quest_status = scene_data.get("quest_status", {})
    scene_state = quest_status.get("scene_state", {})
    
    # Contexto del mundo y jugador
    world_definition = game_state.get("world_definition", {})
    world_theme = world_definition.get("style", "A fantasy adventure")
    language = world_definition.get("language", "English")
    player_name = game_state.get("player", {}).get("player_name", "Adventurer")
    current_location = game_state.get("player", {}).get("location", "unknown")
    
    # --- NUEVA LÓGICA: DETERMINAR LA INTENCIÓN DE LA ESCENA ---
    objective_type = step_objective.get('type', 'unknown')
    objective_id = step_objective.get('id', 'unknown')
    
    scene_intent = "EXPLORATION"  # Por defecto
    if objective_type == 'npc':
        scene_intent = "CONFRONTATION"
    elif objective_type == 'item':
        scene_intent = "DISCOVERY"
    elif objective_type == 'location':
        scene_intent = "NAVIGATION"
    
    # Contar acciones para determinar urgencia
    action_count = len([k for k in scene_state.keys() if k.startswith('action_taken')])
    urgency_level = "NORMAL"
    if action_count >= 3:
        urgency_level = "HIGH"
    elif action_count >= 5:
        urgency_level = "CRITICAL"
    
    # Construir el prompt con intención de escena
    prompt = f"""Eres un Dungeon Master experto. El jugador está en una escena de una misión. Tu trabajo es describir la situación y ofrecerle opciones claras.

**Título de la Misión:** {quest_title}
**Descripción del Paso Actual:** {step_description}
**Objetivo Mecánico Final:** El jugador necesita cumplir el objetivo '{objective_type}: {objective_id}'.

**Intención de esta Escena:** {scene_intent}. Tus opciones deben reflejar esto:
- Si es CONFRONTATION, ofrece opciones que lleven al combate o a la resolución final.
- Si es DISCOVERY, ofrece opciones de investigación y búsqueda.
- Si es NAVIGATION, ofrece opciones de movimiento y exploración.

**Nivel de Urgencia:** {urgency_level}
- Si es HIGH o CRITICAL, al menos 2 opciones deben ser directas hacia el objetivo.

**Contexto de Acciones Previas:** {action_count} acciones tomadas en esta escena.
**Estado de la Escena:** {scene_state}

**Tu Tarea:**
1. Narra la Escena: Escribe un párrafo inmersivo en {language}.
2. Propón Opciones: Crea de 2 a 4 opciones de acción lógicas y creativas que avancen hacia el objetivo.

**Formato de Respuesta:** Responde con un ÚNICO objeto JSON con claves 'narration' y 'options'.

{{
    "narration": "Tu descripción inmersiva aquí...",
    "options": [
        "Opción 1 que avanza hacia el objetivo",
        "Opción 2 alternativa",
        "Opción 3 creativa"
    ]
}}"""

    try:
        # Llamar al proveedor de IA para generar JSON
        response_json = provider.generate_json(prompt)
        
        # Parsear la respuesta
        if isinstance(response_json, str):
            response_data = json.loads(response_json)
        else:
            response_data = response_json
            
        # Extraer narrativa y opciones
        narration = response_data.get("narration", f"You are on a quest: {quest_title}. {step_description}")
        options = response_data.get("options", ["Continue forward", "Look around carefully", "Wait and observe"])
        
        # Validar que options sea una lista
        if not isinstance(options, list):
            options = ["Continue forward", "Look around carefully", "Wait and observe"]
            
        return narration, options
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # Valores por defecto seguros en caso de error
        print(f"[DEBUG] Error in narrate_quest_scene: {e}")
        default_narration = f"You are on a quest: {quest_title}. {step_description}"
        default_options = ["Continue forward", "Look around carefully", "Wait and observe"]
        return default_narration, default_options


def resolve_quest_action(
    provider: AIProviderInterface,
    game_state: dict,
    scene_data: dict,
    player_choice: str
) -> tuple[str, dict]:
    """
    Determina el resultado de la acción elegida por el jugador en una escena.
    Ahora con fidelidad al guion original para evitar improvisaciones excesivas.
    """
    # Extraer datos del contexto
    quest_id = scene_data.get("quest_id", "unknown_quest")
    quest_title = scene_data.get("quest_title", "Unknown Quest")
    step_definition = scene_data.get("step_definition", {})
    step_description = step_definition.get("description", "Continue your journey")
    step_objective = step_definition.get("objective", {})
    quest_status = scene_data.get("quest_status", {})
    scene_state = quest_status.get("scene_state", {})
    
    # Contexto del mundo y jugador
    world_definition = game_state.get("world_definition", {})
    world_theme = world_definition.get("style", "A fantasy adventure")
    language = world_definition.get("language", "English")
    player_name = game_state.get("player", {}).get("player_name", "Adventurer")
    player_hp = game_state.get("player", {}).get("hp", 100)
    player_level = game_state.get("player", {}).get("level", 1)
    
    # NUEVO: Obtener el guion original de la misión
    quest_def = world_definition.get('quests', {}).get(quest_id, {})
    final_boss = quest_def.get('final_boss_id', 'Unknown Antagonist')
    key_item = next((s['objective']['id'] for s in quest_def.get('steps', []) if s['objective'].get('type') == 'item'), 'Unknown Item')
    
    # Lógica de progresión inteligente
    objective_type = step_objective.get('type', 'unknown')
    objective_id = step_objective.get('id', 'unknown')
    
    # Contar acciones tomadas para evitar bucles infinitos
    action_count = len([k for k in scene_state.keys() if k.startswith('action_taken')])
    
    # Construir el prompt con guion original
    prompt = f"""Eres el motor de un juego de rol. El jugador ha tomado una decisión en una escena. Tu trabajo es determinar el resultado y narrarlo, siendo fiel al guion original de la misión.

**Guion Original de la Misión:**
- Título: {quest_title}
- Antagonista Principal: {final_boss}
- Objeto Clave: {key_item}
- Tema del Mundo: {world_theme}

**Contexto de la Escena Actual:** {step_description}
**Objetivo del Paso:** {objective_type}: {objective_id}
**Acción del Jugador:** '{player_choice}'
**Acciones Previas:** {action_count} acciones tomadas en esta escena
**Estado de la Escena:** {scene_state}

**Tu Tarea:**
1. **Determina el Resultado:** ¿La acción del jugador le acerca a cumplir el objetivo? ¿Tiene éxito o falla? 
2. **MANTENTE FIEL AL GUION ORIGINAL:** No inventes nuevos villanos ni cambies la trama principal. El antagonista es {final_boss}, no otro personaje.
3. **Evita Bucles Infinitos:** Si el jugador ha tomado {action_count + 1} acciones y está progresando razonablemente, considera completar el objetivo.

**Lógica de Completado:**
- Si {objective_type} es "npc" y la acción involucra interactuar/combatir con "{objective_id}" → completar
- Si {objective_type} es "item" y la acción involucra encontrar/obtener "{objective_id}" → completar
- Si {objective_type} es "location" y la acción involucra llegar a "{objective_id}" → completar

**Formato de Respuesta:** Responde con un ÚNICO objeto JSON con claves 'outcome_narration' y 'outcome_data'.
En `outcome_data`, incluye `"objective_completed": true` si la acción cumple el objetivo del paso.

{{
    "outcome_narration": "Describe lo que sucede como resultado en {language}...",
    "outcome_data": {{
        "objective_completed": false,
        "update_scene_state": {{"action_taken_{action_count + 1}": "{player_choice}"}}
    }}
}}"""

    try:
        # Llamar al proveedor de IA para generar JSON
        response_json = provider.generate_json(prompt)
        
        # Parsear la respuesta
        if isinstance(response_json, str):
            response_data = json.loads(response_json)
        else:
            response_data = response_json
            
        # Extraer narrativa y datos de resultado
        outcome_narration = response_data.get("outcome_narration", f"You attempt: {player_choice}")
        outcome_data = response_data.get("outcome_data", {})
        
        # Validar que outcome_data sea un diccionario
        if not isinstance(outcome_data, dict):
            outcome_data = {"update_scene_state": {f"action_taken_{action_count + 1}": player_choice}}
        
        # NUEVO: Lógica de seguridad mejorada para evitar bucles infinitos
        if action_count >= 4 and not outcome_data.get("objective_completed", False):
            print(f"[DEBUG] Auto-completing objective after {action_count + 1} actions to prevent infinite loop")
            outcome_data["objective_completed"] = True
            outcome_narration += f" After persistent effort, you successfully achieve your goal regarding {objective_id}."
            
        return outcome_narration, outcome_data
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # Valores por defecto seguros en caso de error
        print(f"[DEBUG] Error in resolve_quest_action: {e}")
        default_narration = f"You attempt: {player_choice}. The outcome is uncertain."
        default_outcome = {"update_scene_state": {f"action_taken_{action_count + 1}": player_choice}}
        return default_narration, default_outcome
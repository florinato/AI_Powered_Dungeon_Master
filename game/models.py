# game/models.py

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# --- Modelos para el Grafo Estructural del Mundo (Salida del Arquitecto) ---

class LocationNode(BaseModel):
    """
    Representa un nodo en el grafo del mundo, incluyendo el blueprint de contenido.
    Su estructura ahora coincide 1:1 con la salida de GridMapGenerator.
    """
    id: str
    type: str = "sala"
    tags: List[str] = Field(default_factory=list)
    
    # Se ajusta para aceptar la lista de diccionarios simple del generador.
    connections: List[Dict[str, Any]] = Field(default_factory=list)

    # Campos del blueprint que el Director leerá.
    npc_count: int = 0
    item_count: int = 0
    has_quest_start: bool = False
    has_trap: bool = False

class WorldGraph(BaseModel):
    """El modelo raíz para el esqueleto estructural del mundo."""
    graph_id: str
    nodes: Dict[str, LocationNode] # Usar un dict con ID como clave para acceso rápido


# --- Modelos para Definiciones de Mundo (Plantillas Generadas por el Director) ---

class WorldDefinition(BaseModel):
    """Define la metainformación de un mundo."""
    id: str
    name: str
    style: str
    lore: str
    language: str
    inhabitant_description: Optional[str] = None
    starting_location_id: str
    main_quests: Dict[str, Any] = Field(default_factory=dict)

class LocationDefinition(BaseModel):
    """Define la plantilla de una ubicación en un mundo."""
    id: str
    world_id: str
    name: str
    description: str
    type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    connections: Dict[str, str] = Field(default_factory=dict)
    initial_npcs: List[str] = Field(default_factory=list)
    initial_items: List[str] = Field(default_factory=list)
    traps: Dict[str, Any] = Field(default_factory=dict) # Añadido para guardar las trampas

class ItemDefinition(BaseModel):
    """Define la plantilla de un objeto específico de un mundo."""
    id: str
    template_id: str
    name: str
    description: str
    type: str
    damage_base: Optional[int] = None
    healing_amount: Optional[int] = None
    properties: List[str] = Field(default_factory=list)

class NpcDefinition(BaseModel):
    """Define la plantilla de un NPC específico de un mundo."""
    id: str
    name: str
    description: str
    hp: int
    attack: int
    status: str = "neutral"
    xp: int = 0
    dialogue_prompt: Optional[str] = None
    # Podríamos añadir más campos generados por el Director aquí

class QuestStep(BaseModel):
    """Define un paso o etapa dentro de una misión."""
    id: str
    description: str
    objective: Dict[str, str] = Field(default_factory=dict) # Para objetivos estructurados

class QuestDefinition(BaseModel):
    """Define la plantilla de una misión en un mundo."""
    id: str
    title: str
    description: str
    steps: List[QuestStep] = Field(default_factory=list)
    starting_npc_id: Optional[str] = None
    # Podríamos añadir más campos como `final_boss_id`, etc.


# --- Modelos para el Estado de la Partida (Datos del Jugador) ---

class PlayerQuestState(BaseModel):
    """Representa el estado de una misión para un jugador."""
    quest_id: str
    current_step_id: str
    completed: bool = False
    status: str = "active" 

class PlayerState(BaseModel):
    """Representa el estado completo de un jugador en una partida."""
    player_id: Optional[int] = None
    player_name: str
    world_id: str
    
    level: int = 1
    hp: int = 100
    max_hp: int = 100
    attack: int = 10
    xp: int = 0
    xp_to_next_level: int = 100
    
    current_location_id: str
    location_history: List[str] = Field(default_factory=list)
    
    # AJUSTADO: Acepta una lista de diccionarios, solucionando el ValidationError.
    inventory: List[Dict[str, Any]] = Field(default_factory=list)
    
    active_quests: Dict[str, PlayerQuestState] = Field(default_factory=dict)
    world_state_delta: Dict[str, Any] = Field(default_factory=dict)
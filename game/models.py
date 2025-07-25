# game/models.py

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# --- Modelos para Definiciones de Mundo (Plantillas Inmutables) ---

class WorldDefinition(BaseModel):
    """Define la metainformación de un mundo."""
    id: str = Field(..., description="Identificador único del mundo, ej: 'eldoria'")
    name: str = Field(..., description="Nombre completo y legible del mundo.")
    style: str = Field(..., description="Estilo o género, ej: 'High Fantasy, Post-Apocalypse'")
    lore: str = Field(..., description="Descripción narrativa y lore del mundo.")
    language: str  
    starting_location_id: str = Field(..., description="ID de la ubicación donde empiezan los nuevos jugadores.")
    main_quests: Dict[str, Any] = Field({}, description="Diccionario con las misiones principales disponibles en este mundo.")

class LocationDefinition(BaseModel):
    """Define la plantilla de una ubicación en un mundo."""
    id: str = Field(..., description="ID único de la ubicación.")
    world_id: str = Field(..., description="ID del mundo al que pertenece.")
    name: str = Field(..., description="Nombre legible de la ubicación.")
    description: str = Field(..., description="Descripción base de la ubicación.")
    connections: Dict[str, str] = Field({}, description="Conexiones a otras ubicaciones, ej: {'north': 'forest_id'}")
    initial_npcs: List[str] = Field([], description="Lista de IDs de NPCs que aparecen aquí al inicio.")
    initial_items: List[str] = Field([], description="Lista de IDs de objetos que se encuentran aquí al inicio.")

class ItemDefinition(BaseModel):
    """Define la plantilla de un objeto específico de un mundo."""
    id: str = Field(..., description="ID único del objeto en el mundo, ej: 'rusty_sword_t1'")
    template_id: str = Field(..., description="ID de la plantilla de reglas base, ej: 'WEAPON_MELEE_SMALL_T1'")
    name: str
    description: str
    type: str
    damage_base: Optional[int] = None
    healing_amount: Optional[int] = None
    properties: List[str] = []

class NpcDefinition(BaseModel):
    """Define la plantilla de un NPC específico de un mundo."""
    id: str = Field(..., description="ID único del NPC en el mundo.")
    name: str
    description: str
    hp: int = Field(..., gt=0, description="Puntos de vida base.")
    attack: int = Field(..., ge=0, description="Daño de ataque base.")
    status: str = Field("neutral", description="Estado inicial: 'hostile', 'friendly', 'neutral'")
    xp: int = Field(0, description="Experiencia que otorga al ser derrotado.")
    dialogue_prompt: Optional[str] = Field(None, description="Prompt base para la IA al generar su diálogo.")

class QuestStep(BaseModel):
    """Define un paso o etapa dentro de una misión."""
    id: str
    description: str
    location_id: Optional[str] = None
    required_items: List[str] = []
    reward_xp: int = 0
    # Podrías añadir más campos como 'required_npcs_defeated', 'reward_items', 'next_step_id', etc.

class QuestDefinition(BaseModel):
    """Define la plantilla de una misión en un mundo."""
    id: str
    world_id: str
    title: str
    description: str
    starting_npc: Optional[str] = None
    steps: List[QuestStep] = []


# --- Modelos para el Estado de la Partida (Datos del Jugador) ---

class PlayerInventoryItem(BaseModel):
    """Representa una instancia única de un objeto en el inventario del jugador."""
    instance_id: int
    item_id: str

class PlayerQuestState(BaseModel):
    """Representa el estado de una misión para un jugador."""
    quest_id: str
    current_step_id: str
    completed: bool = False
    status: str = "active" 

class PlayerState(BaseModel):
    """Representa el estado completo de un jugador en una partida."""
    player_id: Optional[int] = None # Opcional al crear, la BD lo asignará
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
    
    # --- ¡EL CAMBIO CLAVE! ---
    # En lugar de `List[PlayerInventoryItem]`, ahora es una lista de diccionarios.
    # Esto acepta directamente los objetos que vienen del `game_engine`.
    inventory: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Hemos ajustado el modelo `PlayerQuestState` para que sea más completo
    active_quests: Dict[str, PlayerQuestState] = Field(default_factory=dict)

    world_state_delta: Dict[str, Any] = Field(default_factory=dict)

class ConnectionProperties(BaseModel):
    """Propiedades de una conexión entre nodos."""
    is_locked: bool = False
    is_hidden: bool = False
    is_one_way: bool = False
    # Podríamos añadir más, como 'coste_de_viaje', 'dificultad', etc.

class WorldConnection(BaseModel):
    """Representa una arista en el grafo del mundo."""
    target_node_id: str
    direction: str # ej: 'north', 'hyperlane_to', 'portal_a'
    properties: ConnectionProperties = Field(default_factory=ConnectionProperties)

class LocationNode(BaseModel):
    """Representa un nodo en el grafo del mundo. Es un contenedor abstracto."""
    id: str = Field(..., description="ID único del nodo, ej: 'node_001'")
    type: str = Field(..., description="Tipo de localización, ej: 'city', 'dungeon', 'wilderness'")
    tags: List[str] = Field([], description="Etiquetas para ayudar a la IA, ej: ['safe_zone', 'quest_hub']")
    size: str = Field('medium', description="Tamaño relativo: 'small', 'medium', 'large'")
    connections: List[WorldConnection] = []

class WorldGraph(BaseModel):
    """El modelo raíz para el esqueleto estructural del mundo."""
    graph_id: str
    nodes: Dict[str, LocationNode] = {} # Usar un dict con ID como clave para acceso rápido

class LocationDefinition(BaseModel):
    """Define la plantilla de una ubicación en un mundo."""
    id: str # Este ID sería el mismo que el del LocationNode original
    world_id: str
    name: str # Generado por la IA
    description: str # Generado por la IA
    
    # Metadatos heredados del nodo para consistencia (opcional, pero útil)
    type: Optional[str] = None # ej: 'city', 'dungeon'
    tags: List[str] = Field([], description="Etiquetas que describen la localización.")
    
    # La transformación clave: List[WorldConnection] -> Dict[str, str]
    connections: Dict[str, str] = Field({}, description="Conexiones a otras ubicaciones, ej: {'north': 'forest_id'}")
    
    initial_npcs: List[str] = Field([], description="Lista de IDs de NPCs que aparecen aquí al inicio.")
    initial_items: List[str] = Field([], description="Lista de IDs de objetos que se encuentran aquí al inicio.")
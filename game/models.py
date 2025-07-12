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
    # Se podrían añadir más detalles, como un log de objetivos cumplidos
    # objectives_completed: List[str] = []

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
    location_history: List[str] = []
    
    inventory: List[PlayerInventoryItem] = []
    active_quests: Dict[str, PlayerQuestState] = {}

    world_state_delta: Dict[str, Any] = {}
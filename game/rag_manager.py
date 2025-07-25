# game/rag_manager.py

import json
import os
import sqlite3

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

# --- CONFIGURACIÓN ---
# La clave de API se cargará automáticamente de tu archivo .env
CHROMA_PATH = "rag_memory_db"  # Carpeta donde ChromaDB guardará sus datos
DB_PATH = "game_database.db"  # Ruta a tu BD principal

# Cargar variables de entorno desde .env
load_dotenv()

# Usamos el modelo de embedding específico de la familia Gemini.
EMBEDDING_MODEL_NAME = "gemini-embedding-001"

# Inicializamos la función de embedding de Google, pasándole el nombre del modelo.
google_ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    api_key=os.getenv("GOOGLE_API_KEY"),
    model_name=EMBEDDING_MODEL_NAME
)

# Inicializamos el cliente de ChromaDB.
client = chromadb.PersistentClient(path=CHROMA_PATH)


# --- FUNCIONES DE INGESTA DE DATOS ---

def populate_chroma_from_world_json(world_json_path: str):
    """
    Lee un archivo de mundo, procesa su contenido y lo guarda como embeddings en ChromaDB.
    Esta función se ejecuta UNA SOLA VEZ por mundo.
    """
    print(f"--- Populating RAG Memory from '{world_json_path}' ---")

    with open(world_json_path, 'r', encoding='utf-8') as f:
        world_data = json.load(f)

    world_id = world_data['world']['id']

    # --- 1. Procesar Localizaciones ---
    # Pasamos la función de embedding de Google al crear la colección.
    locations_collection = client.get_or_create_collection(
        name="locations",
        embedding_function=google_ef
    )
    loc_docs, loc_metadatas, loc_ids = [], [], []
    for loc in world_data['locations']:
        doc_text = f"Nombre: {loc['name']}. Descripción: {loc['description']}. Tipo: {loc.get('type')}, Etiquetas: {', '.join(loc.get('tags', []))}"
        loc_docs.append(doc_text)
        loc_metadatas.append({"world_id": world_id, "type": loc.get('type', 'unknown')})
        loc_ids.append(f"loc_{loc['id']}")

    if loc_ids:
        locations_collection.upsert(documents=loc_docs, metadatas=loc_metadatas, ids=loc_ids)
        print(f"Upserted {len(loc_ids)} locations into ChromaDB for world '{world_id}'.")

    # --- 2. Procesar PNJs ---
    npcs_collection = client.get_or_create_collection(
        name="npcs",
        embedding_function=google_ef
    )
    npc_docs, npc_metadatas, npc_ids = [], [], []
    for npc in world_data['npc_templates']:
        doc_text = f"Nombre: {npc['name']}. Descripción: {npc['description']}. Personalidad/Rol: {npc.get('dialogue_prompt', '')} {npc.get('role', '')}"
        npc_docs.append(doc_text)
        npc_metadatas.append({"world_id": world_id, "status": npc.get('status', 'neutral')})
        npc_ids.append(f"npc_{npc['id']}")

    if npc_ids:
        npcs_collection.upsert(documents=npc_docs, metadatas=npc_metadatas, ids=npc_ids)
        print(f"Upserted {len(npc_ids)} NPCs into ChromaDB for world '{world_id}'.")

    # --- 3. Procesar Misiones ---
    quests_collection = client.get_or_create_collection(
        name="quests",
        embedding_function=google_ef
    )
    quest_docs, quest_metadatas, quest_ids = [], [], []
    for quest in world_data['quests']:
        steps_text = ' '.join(step['description'] for step in quest.get('steps', []))
        doc_text = f"Misión: {quest['title']}. Descripción: {quest['description']}. Pasos: {steps_text}"
        quest_docs.append(doc_text)
        quest_metadatas.append({"world_id": world_id})
        quest_ids.append(f"quest_{quest['id']}")

    if quest_ids:
        quests_collection.upsert(documents=quest_docs, metadatas=quest_metadatas, ids=quest_ids)
        print(f"Upserted {len(quest_ids)} quests into ChromaDB for world '{world_id}'.")

    print("--- RAG Memory Population Complete ---")


def add_log_entry(player_id: int, world_id: str, event_type: str, event_description: str):
    """
    Añade una entrada al diario de aventura.
    La guarda en SQLite (la verdad) Y la indexa en ChromaDB (el significado).
    """
    # 1. Guardar en SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO player_logs (player_id, world_id, event_type, event_description) VALUES (?, ?, ?, ?)",
        (player_id, world_id, event_type, event_description)
    )
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # 2. Indexar en ChromaDB
    logs_collection = client.get_or_create_collection(
        name="player_logs",
        embedding_function=google_ef
    )
    logs_collection.add(
        documents=[event_description],
        metadatas=[{"world_id": world_id, "player_id": player_id, "event_type": event_type}],
        ids=[f"log_{log_id}"]
    )
    print(f"Added and indexed new log entry (ID: {log_id}) for player {player_id}.")


# --- FUNCIONES DE BÚSQUEDA (El Master las usará) ---

def query_memory(collection_name: str, query_text: str, world_id: str, player_id: int | None = None, n_results: int = 3) -> list:
    """
    Busca en una colección de ChromaDB por significado, filtrando por el mundo y opcionalmente por el jugador.
    """
    collection = client.get_collection(name=collection_name)

    where_filter = {"world_id": world_id}
    if player_id and collection_name == "player_logs":
        where_filter["player_id"] = player_id

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=where_filter
    )
    return results if results.get('ids', [[]])[0] else []


if __name__ == '__main__':
    WORLD_FILE_TO_LOAD = "world_import_generated.json"

    print("Running RAG Manager standalone to populate memory...")
    if os.path.exists(WORLD_FILE_TO_LOAD):
        populate_chroma_from_world_json(WORLD_FILE_TO_LOAD)
    else:
        print(f"ERROR: World file '{WORLD_FILE_TO_LOAD}' not found. Please generate it first with director.py")

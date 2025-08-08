# AI Dungeon Master: The Architect & Director Engine

Welcome to **AI Dungeon Master: The Architect & Director Engine**, an advanced, text-based role-playing game that plunges you into worlds dynamically generated from the ground up. This project evolves the concept of AI-driven storytelling by separating world creation into two powerful phases: an **Architect** that builds a structural blueprint, and a **Director** that breathes life, narrative, and coherence into it using cutting-edge generative AI.

This game is being developed for the **Kiros Hackathon**, building upon an original concept with full permission from the base repository's owner PhanidharAkula/AI_Powered_Dungeon_Master.

---

## Table of Contents

-   [Introduction](#introduction)
-   [Core Features](#core-features)
-   [The Two-Phase Architecture](#the-two-phase-architecture)
-   [Technology Stack](#technology-stack)
-   [Requirements](#requirements)
-   [Installation & Setup](#installation--setup)
-   [How to Play](#how-to-play)
    -   [1. Generate a World Blueprint](#1-generate-a-world-blueprint)
    -   [2. Direct the World Creation](#2-direct-the-world-creation)
    -   [3. Prepare the Database](#3-prepare-the-database)
    -   [4. Run the Game](#4-run-the-game)
-   [Available Commands](#available-commands)
-   [Future Roadmap](#future-roadmap)
-   [Project Structure](#project-structure)
-   [Contributing](#contributing)
-   [Acknowledgments](#acknowledgments)

---

## Introduction

This project is not just a game, but a powerful engine for creating narrative experiences. By defining a high-level vision in a simple `manifest.yaml` file, you can direct the AI to generate entire worlds, complete with unique locations, thematic items, complex characters, and multi-step quests. The result is an immersive RPG experience where every world is a unique creation, ready to be explored.

---

## Core Features

### Procedural World Generation

*   **Architect Engine (`grid_map_generator.py`)**: Generates a structural blueprint of the world, defining the map layout and the density of content (NPCs, items, quests, traps) in each area.
*   **Director Engine (`director.py`)**: Takes the blueprint and a thematic `manifest.yaml` to creatively generate all narrative content:
    *   Thematically consistent locations, NPCs, items, and traps.
    *   Multi-step, original quests with structured objectives.
    *   Key characters (quest givers, bosses) invented on-the-fly to fit the generated plots.

### Deeply Interactive Gameplay

*   **Dynamic Quest System**: Quests are offered organically through NPC dialogue. The game tracks your progress through objectives like finding items, defeating enemies, or reaching specific locations.
*   **Intelligent NPC Dialogues**: Conversations are powered by Google's Gemini models, taking into account the world's theme, the NPC's personality, and the current game state.
*   **Context-Aware Image Generation**: Create unique, atmospheric images for any location. The AI prompt is enriched with the world's theme and historical context to ensure artistic coherence (e.g., "Ancient Rome" vs. "Cyberpunk Noir").

### Robust Backend

*   **SQLite Database**: All world definitions and player save states are stored in a robust SQLite database for persistence and scalability.
*   **RAG-Powered Memory (In Development)**: An integrated RAG (Retrieval-Augmented Generation) system using ChromaDB and Google's embedding models provides the foundation for an AI Master with long-term memory.
*   **Modular and Model-Driven**: Uses Pydantic models for strict data validation, ensuring stability and maintainability.

---

## The Two-Phase Architecture

The core of this project is its unique generation pipeline:

1.  **The Architect Phase**: You run `grid_map_generator.py`. This script acts as a technical planner, creating a `_blueprint.json` file. It doesn't know *what* the world is about, only its structure and density.
2.  **The Director Phase**: You run `director.py`. This script reads the `_blueprint.json` and your `manifest.yaml` (where you define the theme, e.g., "Roman thriller"). The Director then uses AI to fill the blueprint with creative, thematic content, producing the final `world_import_generated.json`.

This separation allows for maximum control and creativity. You can generate hundreds of map structures and apply any theme to them.

---

## Technology Stack

*   **Core Language**: Python 3.11+
*   **Generative AI**: Google Gemini Family (via `google-generativeai`)
*   **Image Generation**: Gradio Client (`gradio_client`) connecting to FLUX.1 models.
*   **Database**: SQLite (for core data) & ChromaDB (for RAG memory).
*   **AI Embeddings**: Google's `text-embedding` models.
*   **Data Validation**: Pydantic.
*   **Dependencies**: `PyYAML`, `matplotlib`, `networkx`, `python-dotenv`.

---

## Requirements

*   Python 3.11 or higher.
*   A Google API Key with the "Generative Language API" enabled.
*   Git for cloning the repository.

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/florinato/AI_Powered_Dungeon_Master/blob/creator
cd ../AI_Powered_Dungeon_Master
```

### 2. Set Up a Virtual Environment

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project's root directory and add your Google API key:

```code
GOOGLE_API_KEY="your_google_api_key_here"
```

---

## How to Play

The game is run in a sequence of steps that generate and then load the world.

1.  Generate a World Blueprint

    Run the Architect to create the map structure. You can configure the parameters inside the script.

    ```bash
    python game/grid_map_generator.py
    ```

    This creates a `_blueprint.json` file in your root folder.

2.  Direct the World Creation

    Run the Director to fill the blueprint with creative content based on your manifest.

    ```bash
    python game/director.py
    ```

    This creates the final `world_import_generated.json` file.

3.  Prepare the Database

    Run the database manager to import the generated world into SQLite and create the RAG memory.

    ```bash
    python game/db_manager.py
    python game/rag_manager.py
    ```

4.  Run the Game

    Finally, launch the game!

    ```bash
    python game/game_loop.py
    ```

---

## Available Commands

*   `look`: Get a description of your current location, including NPCs, items, and paths.
*   `move [direction]`: Move to a new location (e.g., `move norte`).
*   `get [item]`: Pick up an item from the location.
*   `talk`: Initiate a conversation with an NPC.
*   `fight`: Engage in combat.
*   `inventory / inv`: Display the items you are carrying.
*   `quests`: Check your journal for active quests and current objectives.
*   `stats`: Show your character's current stats.
*   `image`: Generate an AI image of your current location.
*   `map`: Display a visual map of the world.
*   `help`: Show this list of commands.
*   `quit`: Exit the game. Your progress is saved automatically.

---

## Future Roadmap

*   Activate the RAG Memory: Fully integrate the RAG system into the GameNarrator to give the AI Master long-term memory and contextual awareness.
*   Refine the Combat System: Add more depth, skills, and strategic options to combat.
*   GUI Development: Create a simple graphical user interface to enhance the player experience.
*   Sound and Music: Add background music and sound effects for key events.

---

## Project Structure

```code
AI_Powered_Dungeon_Master/
├── game/
│   ├── director.py             # The Director Engine (Creative)
│   ├── grid_map_generator.py   # The Architect Engine (Structural)
│   ├── db_manager.py           # Manages the SQLite database
│   ├── rag_manager.py          # Manages the ChromaDB RAG memory
│   ├── game_loop.py            # Main game executable
│   ├── game_engine.py          # Core game logic and rules
│   ├── game_narrator.py        # Handles dynamic AI narration
│   ├── models.py               # Pydantic data models
│   └── ...
├── *.json                     # Blueprint and World Import files
├── *.yaml                     # Manifest files for world themes
├── game_database.db           # SQLite database
├── rag_memory_db/             # ChromaDB vector store
└── README.md                  # This file
```

---

## Contributing

Contributions are welcome! Please fork the repository, create a feature branch, and submit a pull request.

---

## Acknowledgments

*   Google: For providing the powerful Gemini and Gemma family of models that serve as the creative core of this project.
*   The ChromaDB and SentenceTransformers teams: For their amazing open-source tools that power the RAG memory system.
*   The Gradio team: For making interactive model demos and APIs accessible to everyone.
*   A Special Thanks to AkulaPhanidhar: This project was developed for the Kiros Hackathon and is a significant evolution of the concepts and codebase from the AI_Powered_Dungeon_Master. We are deeply grateful for the permission to use and build upon this fantastic foundation.

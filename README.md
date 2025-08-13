# AI Dungeon Master Framework

Welcome to the **AI Dungeon Master Framework**, a comprehensive suite of AI agents designed for the creation and execution of dynamic, text-based role-playing games. More than just a game, this project is a powerful toolset for writers, designers, and players to collaboratively and autonomously generate rich narrative experiences.

The framework is built around a "cast" of specialized AI agents that handle everything from high-level creative brainstorming to the detailed, logical construction of a playable world, culminating in an innovative **dual-mode gameplay system** that seamlessly transitions between exploration and narrative-driven adventures.

This project is being developed for the **Kiro Hackathon**, building upon an original concept with full permission from the base repository's owner, PhanidharAkula/AI_Powered_Dungeon_Master.

---

## Table of Contents

- [The Vision](#the-vision)
- [Meet the AI Agents](#meet-the-ai-agents)
- [The Revolutionary Dual-Mode Gameplay System](#the-revolutionary-dual-mode-gameplay-system)
- [Core Features](#core-features)
- [The Autonomous World Generation Pipeline](#the-autonomous-world-generation-pipeline)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [How to Use the Framework](#how-to-use-the-framework)
- [In-Game Commands](#in-game-commands)
- [Future Roadmap](#future-roadmap)
- [Acknowledgments](#acknowledgments)

---

## The Vision

The goal of this project is to create a robust framework for generating infinite, high-quality RPG adventures. It addresses the entire creative lifecycle, from the initial spark of an idea to a fully realized, playable world. It achieves this through a clear separation of creative, structural, and editorial tasks, each managed by a dedicated AI agent.

---

## Meet the AI Agents

The framework's power comes from its suite of specialized AI agents, each with a distinct role:

- **The Story Forge**: An interactive brainstorming partner that uses a dual-persona AI (a creative writer and a shrewd critic) to help you collaboratively develop a story's plot, characters, and setting, resulting in a "Narrative Bible."

- **The Architect**: A procedural planner that designs the structural blueprint of the world map, focusing on layout, connectivity, and content density without worrying about the story.

- **The Director**: The creative powerhouse. It takes the Architect's blueprint and a thematic manifest (`.yaml`) to generate all the world's content: evocative locations, thematic quests, unique items, and memorable characters.

- **The Revisor**: The **AI Quality Assurance Lead**. This crucial agent audits the Director's creative "first draft." It performs iterative self-correction passes to fix gameplay pacing issues, resolve narrative inconsistencies, and ensure the final world is logical, coherent, and fun to play.

- **The Dungeon Master / Narrator**: The in-game performer. It uses AI to dynamically narrate atmospheric descriptions and voice the personalities of every character you meet, bringing the world to life. Now enhanced with disciplined narrative control and scene intention detection.

---

## The Revolutionary Dual-Mode Gameplay System

The framework features an innovative **"Guardaagujas" (Switchman)** architecture that creates two distinct but seamlessly integrated gameplay experiences:

### 🌍 **Exploration Mode**
Traditional RPG gameplay where players use commands to:
- Navigate the world (`move`, `look`, `back`)
- Interact with NPCs (`talk`) and objects (`get`, `use`, `drop`)
- Manage inventory and character stats (`inventory`, `stats`)
- Engage in combat (`fight`) and solve puzzles (`unlock`)

### 🎭 **Adventure Mode**
Immersive, choice-driven narrative scenes that activate during quest progression:
- **AI-Generated Scenarios**: Dynamic narrative descriptions based on quest context
- **Meaningful Choices**: 2-4 contextual options that advance the story
- **Consequence System**: Player choices affect scene state and quest progression
- **Scene Intention Detection**: AI recognizes when to create CONFRONTATION, DISCOVERY, or NAVIGATION scenarios
- **Anti-Loop Protection**: Intelligent systems prevent infinite exploration loops and guide toward quest completion

### 🔄 **The Switchman Logic**
The system automatically determines which mode to use:
```
Each Turn → Check for Active Quest Scene
    ↓
Active Quest? → Adventure Mode (AI-driven narrative)
No Active Quest? → Exploration Mode (command-based)
    ↓
Quest Step Completed → Return to Exploration or Continue to Next Step
```

### 🎯 **Disciplined AI Narrator**
The narrative engine includes sophisticated controls:
- **Scene Intent Recognition**: Automatically detects whether a scene should focus on combat, discovery, or navigation
- **Original Story Fidelity**: Maintains consistency with the original quest storyline, preventing AI from inventing new villains or plot threads
- **Progressive Urgency**: Escalates scene tension and options based on player actions taken
- **Automatic Resolution**: Prevents infinite loops by intelligently completing objectives after reasonable player engagement

---

## Core Features

- **Autonomous World Generation Pipeline**: A robust, three-phase pipeline (Architect -> Director -> Revisor) that translates a high-level manifest.yaml into a complete, polished, and playable game world.

- **AI-Powered Self-Correction**: The Revisor agent intelligently identifies and fixes design flaws, addressing issues with gameplay flow, narrative logic, and pacing by renaming, rewriting, and relocating game assets.

- **Dual-Mode Gameplay System**: Revolutionary "Guardaagujas" (Switchman) architecture that seamlessly transitions between:
  - **Exploration Mode**: Traditional command-based gameplay for world exploration, NPC interaction, and item management
  - **Adventure Mode**: Immersive, choice-driven narrative scenes with AI-generated options and consequences

- **Disciplined AI Narrator**: Advanced narrative engine with scene intention detection (CONFRONTATION, DISCOVERY, NAVIGATION) and fidelity to original storylines, preventing infinite loops and maintaining narrative coherence.

- **Deeply Thematic Content**: The AI is strictly guided by your manifest, ensuring all generated content—from quest plots to item descriptions—is perfectly aligned with your chosen theme.

- **Dynamic and Intelligent Gameplay**: Quests are offered organically through AI-driven dialogues. The game tracks progress through clear, mechanically sound objectives, all within a persistent world managed by a SQLite database.

- **Interactive Narrative Development**: Use the StoryForge to brainstorm and refine a complete story concept with an AI partner, exporting the result as a narrative_bible.txt.

- **Context-Aware Visuals**: Generate unique, atmospheric images (`image` command) and a visual map of the world (`map` command).

---

## The Autonomous World Generation Pipeline

The core of the framework is its unique, quality-focused generation pipeline:

1. **Architecture**: The `Architect` (`grid_map_generator.py`) creates a structural `_blueprint.json` file, defining the world's map and content density.
2. **Direction**: The `Director` (`director.py`) reads the blueprint and your thematic `manifest.yaml`. It then creatively fills the structure with a narrative, characters, and quests, producing a vibrant "first draft" (`world_import_generated.json`).
3. **Revision**: The `Revisor` (`revisor.py`) acts as the editor-in-chief. It analyzes the draft for logical flaws, pacing issues, and narrative contradictions. It then autonomously corrects these issues, producing the final, polished, and highly playable `world_import_revisado.json`.

---

## Technology Stack

- **Core Language**: Python 3.11+
- **Generative AI**: Google Gemini Family (via `google-generativeai`)
- **Database**: SQLite (for core data) & ChromaDB (for RAG memory).
- **Data Validation**: Pydantic.
- **Dependencies**: `PyYAML`, `matplotlib`, `networkx`, `python-dotenv`, `gradio_client`.

---

## Project Structure

The project is organized into a modular structure within the `game/` directory:

```
game/
├── ai/                  # Handles all interactions with AI models (LLMs, Embeddings).
│   ├── ai_factory.py
│   └── game_narrator.py
├── core/                # The heart of the game engine and main loop.
│   ├── game_engine.py
│   ├── game_loop.py
│   └── models.py
├── data/                # Database management and persistence.
│   └── db_manager.py
├── ui/                  # User interface components like the command parser and presenter.
│   ├── command_parser.py
│   └── presenter.py
├── utils/               # Utility scripts for setup and asset generation.
│   ├── image_generator.py
│   └── map_generator.py
└── world_generation/    # The complete pipeline for creating worlds.
    ├── grid_map_generator.py  # Architect
    ├── director.py            # Director
    ├── revisor.py             # Revisor
    └── story_forge.py         # Interactive storyteller
```

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/florinato/AI_Powered_Dungeon_Master.git
cd AI_Powered_Dungeon_Master
```
*(Note: Adjust URL if you are working on a different fork/branch)*

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
```
GOOGLE_API_KEY="your_google_api_key_here"
```

---

## How to Use the Framework

### Workflow 1: Autonomous World Generation & Gameplay
Use this workflow to generate and play a complete RPG from a theme.

1. **Generate a World Blueprint**: Run the Architect to create the map structure.
```bash
python -m game.world_generation.grid_map_generator
```
Creates a `_blueprint.json` file.

2. **Direct the Creative Generation**: Run the Director to creatively fill the blueprint based on your `manifest.yaml`.
```bash
python -m game.world_generation.director
```
Creates the "first draft" `world_import_generated.json`.

3. **Revise and Polish the World**: Run the Revisor to audit and automatically correct the world.
```bash
python -m game.world_generation.revisor
```
Creates the final, polished `world_import_revisado.json`.

4. **Prepare the Database**: Import the revised world into the game database.
```bash
python -m game.data.db_manager
```

5. **Run the Game**: Launch the game and start your adventure!
```bash
python -m game.core.game_loop
```

### Workflow 2: Interactive Narrative Design with the Story Forge
Use this workflow to brainstorm a story idea with an AI partner.

1. **Define Your Vision**: Edit a manifest file (e.g., `manifest_inspiracion.yaml`) with your high-level concept.
2. **Run the Story Forge**:
```bash
python -m game.world_generation.story_forge
```
This starts an interactive session and outputs a `narrative_bible.txt`.

---

## In-Game Commands

- `look`: Describe the current location.
- `move [direction]`: Move to a new location.
- `get [item]`: Pick up an item.
- `talk`: Speak with an NPC.
- `fight`: Engage in combat.
- `inventory` / `inv`: Display your items.
- `quests`: Check your active quests.
- `stats`: Show your character's stats.
- `image`: Generate an AI image of your location.
- `map`: Display a visual map of the world.
- `help`: Show this list of commands.
- `quit`: Exit the game (progress is saved).

---

## Future Roadmap

**✅ COMPLETED: Adventure Mode Implementation**: The revolutionary dual-mode gameplay system is now fully functional! The "Guardaagujas" (Switchman) architecture seamlessly transitions between Exploration and Adventure modes, with disciplined AI narrative control preventing infinite loops and maintaining story fidelity.

**🎯 Next Priority: Enhanced RAG Memory**: Fully integrate the RAG system to give the in-game DM long-term, contextual memory of player actions, enabling a truly reactive and personalized world that remembers your choices across sessions.

**📚 Director-Bible Integration**: Allow the Director to use a `narrative_bible.txt` (generated by the StoryForge) as its primary source of truth, creating a seamless pipeline from high-level idea to playable game.

**🎬 Vision: Real-Time Cinematic Engine**: The ultimate goal is to evolve beyond static images. We will explore integrating emerging real-time video generation models to transform the Narrator's atmospheric descriptions into live, animated scenes, with player actions triggering dynamically generated video clips for unprecedented immersion.

---

## Acknowledgments

- **Google**: For providing the powerful Gemini models that serve as the creative and analytical core of this project.
- **The open-source community**: Including the teams behind ChromaDB, Pydantic, Gradio, and many other libraries that made this possible.
- **A Special Thanks to AkulaPhanidhar**: This project was developed for the Kiro Hackathon and is a significant evolution of the concepts from the original AI_Powered_Dungeon_Master. We are deeply grateful for the permission to build upon this fantastic foundation.
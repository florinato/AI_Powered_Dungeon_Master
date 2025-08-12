#!/usr/bin/env python3
"""
AI Dungeon Master Framework - Main Entry Point
"""

if __name__ == "__main__":
    from game.core.game_loop import run_game

    print("=== AI Dungeon Master Framework ===")
    print("Welcome to the AI-powered RPG experience!")
    print("=" * 40)

    try:
        run_game()
    except KeyboardInterrupt:
        print("\n\nGame interrupted by user. Goodbye!")
    except ImportError as e:
        print(f"\nImport error: {e}")
        print(
            "Make sure all dependencies are installed and you're in the correct directory."
        )
    except FileNotFoundError as e:
        print(f"\nFile not found: {e}")
        print("Make sure the game database and configuration files exist.")
    except (ValueError, KeyError) as e:
        print(f"\nConfiguration error: {e}")
        print("Please check your game configuration and world data.")
    except OSError as e:
        print(f"\nSystem error: {e}")
        print("Please check file permissions and available disk space.")

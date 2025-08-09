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
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please check your configuration and try again.")
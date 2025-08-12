#!/usr/bin/env python3
"""
Database Manager Main - Entry point for database operations.

This script provides a convenient way to run database operations like
importing world data, managing player states, and database maintenance
from the project root directory.
"""

import os
import sys


def main():
    """Main entry point for database operations."""
    print("=== AI Dungeon Master - Database Manager ===")
    print("Database operations and world import utility")
    print("=" * 45)
    
    try:
        # Import necessary functions from db_manager
        from game.data.db_manager import (DB_FILE, create_schema,
                                          get_db_connection,
                                          import_world_from_json)
        
        print("--- Running DB Manager Initializer and Importer ---")
        
        # Remove old database to start fresh (optional)
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            print(f"Removed old database file '{DB_FILE}'.")

        # Create database connection and schema
        conn = get_db_connection()
        create_schema(conn)
        
        # Import the revised world data
        world_file = "world_import_revisado.json"
        if os.path.exists(world_file):
            import_world_from_json(conn, world_file)
            print(f"Successfully imported world from '{world_file}'")
        else:
            print(f"WARNING: World file '{world_file}' not found.")
            print("Available world files:")
            for file in os.listdir("."):
                if file.startswith("world_import") and file.endswith(".json"):
                    print(f"  - {file}")
        
        conn.close()
        print("\n--- DB Manager script finished ---")
        
    except ImportError as e:
        print(f"ERROR: Could not import database manager: {e}")
        print("Make sure you're running from the project root directory.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nDatabase operation interrupted by user. Goodbye!")
        sys.exit(0)
    except (OSError, IOError) as e:
        print(f"\nFile system error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        print("Please check your configuration and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
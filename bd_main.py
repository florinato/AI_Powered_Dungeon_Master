if __name__ == "__main__":
    import os
    DB_FILE = "game_database.db"  # Define the database file path

    from game.data.db_manager import (create_schema, get_db_connection,
                                      import_world_from_json)
    print("--- Running DB Manager Initializer and Importer ---")
    
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Removed old database file '{DB_FILE}'.")

    conn = get_db_connection()
    create_schema(conn)
    
    import_world_from_json(conn, "world_import_revisado.json")
    
    conn.close()
        
    print("\n--- DB Manager script finished ---")

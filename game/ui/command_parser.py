# refact/command_parser.py

def parse_command(command_input: str) -> dict:
    """
    Parsea la entrada del jugador y la convierte en un diccionario de acción.
    NO modifica el estado, solo interpreta la intención.
    """
    parts = command_input.lower().strip().split()
    if not parts:
        return {"action": "error", "message": "Please enter a command."}

    command = parts[0]
    args = parts[1:]

    if command in ["go", "move"]:
        if not args:
            return {"action": "error", "message": "Move where? (e.g., 'move north')"}
        return {"action": "move", "direction": args[0]}
    
    elif command == "back":
        return {"action": "back"}

    elif command in ["get", "take", "pick"]:
        if not args:
            return {"action": "error", "message": "Pick up what?"}
        return {"action": "pick", "item_name": "_".join(args)}

    elif command == "drop":
        if not args:
            return {"action": "error", "message": "Drop what?"}
        return {"action": "drop", "item_name": "_".join(args)}

    elif command == "use":
        if not args:
            return {"action": "error", "message": "Use what?"}
        return {"action": "use", "item_name": "_".join(args)}

    elif command == "unlock":
        if not args:
            return {"action": "error", "message": "Unlock which direction?"}
        return {"action": "unlock", "direction": args[0]}

    elif command in ["look", "l", "examine"]:
        # El comando 'look' puede tener un objetivo, ej. 'look at the table'
        # Por ahora, lo mantenemos simple.
        return {"action": "look"}

    elif command in ["i", "inventory", "inv"]:
        return {"action": "inventory"}

    elif command in ["stats", "char", "character"]:
        return {"action": "stats"}

    elif command in ["quests", "goal", "log"]:
        return {"action": "quests"}
    
    elif command == "map":
        return {"action": "map"}
    
    elif command == "image":
        return {"action": "image"}
        
    elif command == "fight":
        # El parser solo indica la intención de luchar.
        # El bucle principal manejará la selección de NPC si hay más de uno.
        return {"action": "fight_intent"}
        
    elif command == "talk":
        return {"action": "talk"}

    elif command == "help":
        return {"action": "help"}
        
    elif command == "quit":
        return {"action": "quit"}

    else:
        return {"action": "error", "message": f"Unknown command: '{command}'"}
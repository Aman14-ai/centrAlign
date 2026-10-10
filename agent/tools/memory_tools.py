def remember(note: str) -> dict:
    """
    Save a scratchpad note. The note is stored by the observer
    into the world model's scratchpad.
    """
    if not note:
        return {"success": False, "result": {}, "error": "empty note"}
    return {
        "success": True,
        "result": {"stored": note},
        "error": None,
    }
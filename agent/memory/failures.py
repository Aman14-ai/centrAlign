from enum import Enum


class FailureType(str, Enum):
    SELECTOR_NOT_FOUND = "selector_not_found"
    API_500 = "api_500"
    TIMEOUT = "timeout"
    MISSING_FIELD = "missing_field"
    DUPLICATE_RECORD = "duplicate_record"
    PERMISSION_DENIED = "permission_denied"
    AMBIGUOUS_DATA = "ambiguous_data"
    FILE_NOT_FOUND = "file_not_found"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


# Prefixes used by tools to signal failure type in the error string.
ERROR_PREFIXES = {
    "selector_not_found": FailureType.SELECTOR_NOT_FOUND,
    "api_500": FailureType.API_500,
    "api_error_500": FailureType.API_500,
    "timeout": FailureType.TIMEOUT,
    "api_error_409": FailureType.DUPLICATE_RECORD,
    "api_error_401": FailureType.PERMISSION_DENIED,
    "api_error_403": FailureType.PERMISSION_DENIED,
    "api_error_400": FailureType.VALIDATION_ERROR,
    "file_not_found": FailureType.FILE_NOT_FOUND,
}


def classify_from_error_string(error: str) -> FailureType:
    """
    Fast deterministic classification based on error prefix.
    Returns UNKNOWN if no prefix matches.
    """
    if not error:
        return FailureType.UNKNOWN
    for prefix, ftype in ERROR_PREFIXES.items():
        if error.lower().startswith(prefix) or f" {prefix}:" in error.lower():
            return ftype
    # Substring fallback
    if "not found" in error.lower() and "file" in error.lower():
        return FailureType.FILE_NOT_FOUND
    if "duplicate" in error.lower() or "already exists" in error.lower():
        return FailureType.DUPLICATE_RECORD
    if "timeout" in error.lower():
        return FailureType.TIMEOUT
    return FailureType.UNKNOWN


def make_signature(ftype: FailureType, tool: str, context_key: str = "") -> str:
    """
    Build a canonical signature. Keep it short and stable.
    Example: "selector_not_found::browser_click::erp::#submit-btn"
    """
    parts = [ftype.value, tool]
    if context_key:
        parts.append(context_key)
    return "::".join(parts)
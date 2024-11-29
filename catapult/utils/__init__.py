from .archive import find_all_archives
from .image_processing import archive_contains_corrupted_image, image_is_corrupted

def get_version() -> str:
    import importlib.metadata
    return importlib.metadata.version("catapult")

def coalesce(*args):
    """
    Return the first non-None argument. If all arguments are None, return None.
    """
    for arg in args:
        if arg is not None:
            return arg
    return None

def mask_string(s) -> str:
    if len(s) <= 2:
        return "*" * len(s)
    return s[0] + '*' * (len(s) - 2) + s[-1]
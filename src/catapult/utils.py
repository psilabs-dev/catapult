import base64
import hashlib
import logging
import requests
import time

logger = logging.getLogger(__name__)

def get_version() -> str:
    import importlib.metadata
    return importlib.metadata.version("catapult")

def mask_string(s) -> str:
    if len(s) <= 2:
        return "*" * len(s)
    return s[0] + '*' * (len(s) - 2) + s[-1]

def calculate_sha1(file_path: str):
    """
    Calculate SHA1 of entire file. Used for in-transit file integrity validation.
    """
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as fb:
        while chunk := fb.read(8192):
            sha1.update(chunk)
    return sha1.hexdigest()

def lrr_compute_id(file_path: str) -> str:
    """
    Compute the ID of a file in the same way as the server.
    """
    with open(file_path, 'rb') as fb:
        data = fb.read(512000)
    
    sha1 = hashlib.sha1()
    sha1.update(data)
    digest = sha1.hexdigest()
    if digest == "da39a3ee5e6b4b0d3255bfef95601890afd80709":
        raise ValueError("Computed ID is for a null value, invalid source file.")
    return digest

def lrr_build_auth(lrr_api_key: str) -> str:
    bearer = base64.b64encode(lrr_api_key.encode(encoding='utf-8')).decode('utf-8')
    return f"Bearer {bearer}"

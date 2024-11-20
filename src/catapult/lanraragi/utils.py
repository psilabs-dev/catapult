import base64
import hashlib
import io
from pathlib import Path
from typing import overload, Union

from .constants import ALLOWED_SIGNATURES

def build_auth_header(lrr_api_key: str) -> str:
    bearer = base64.b64encode(lrr_api_key.encode(encoding='utf-8')).decode('utf-8')
    return f"Bearer {bearer}"

@overload
def compute_sha1(br: io.IOBase) -> str:
    ...

@overload
def compute_sha1(file_path: Path) -> str:
    ...

@overload
def compute_sha1(file_path: str) -> str:
    ...

def compute_sha1(file: Union[io.IOBase, Path, str]) -> str:
    sha1 = hashlib.sha1()
    if isinstance(file, io.IOBase):
        while chunk := file.read(8192):
            sha1.update(chunk)
        return sha1.hexdigest()
    elif isinstance(file, Path) or isinstance(file, str):
        with open(file, 'rb') as file_br:
            while chunk := file_br.read(8192):
                sha1.update(chunk)
            return sha1.hexdigest()
    else:
        raise TypeError(f"Unsupported file type {type(file)}")

@overload
def compute_archive_id(file_path: str) -> str:
    ...

@overload
def compute_archive_id(file_path: Path) -> str:
    ...

def compute_archive_id(file_path: Union[Path, str]) -> str:
    """
    Compute the ID of a file in the same way as the server.
    """
    if isinstance(file_path, Path) or isinstance(file_path, str):
        with open(file_path, 'rb') as fb:
            data = fb.read(512000)
        
        sha1 = hashlib.sha1()
        sha1.update(data)
        digest = sha1.hexdigest()
        if digest == "da39a3ee5e6b4b0d3255bfef95601890afd80709":
            raise ValueError("Computed ID is for a null value, invalid source file.")
        return digest
    else:
        raise TypeError(f"Unsupported type: {type(file_path)}")

@overload
def get_signature_hex(archive_path: str) -> str:
    ...

@overload
def get_signature_hex(archive_path: Path) -> str:
    ...

def get_signature_hex(archive_path: Union[Path, str]) -> str:
    """
    Get first 8 bytes of archive in hex repr.
    """
    if isinstance(archive_path, str) or isinstance(archive_path, Path):
        with open(archive_path, 'rb') as fb:
            signature = fb.read(8).hex()
            return signature
    else:
        raise TypeError(f"Unsupported file type: {type(archive_path)}")

def is_valid_signature_hex(signature: str) -> bool:
    """
    Check if the hex signature corresponds to a file type supported by LANraragi.
    """
    is_allowed_mime = False
    for allowed_signature in ALLOWED_SIGNATURES:
        if signature.strip().startswith(allowed_signature):
            is_allowed_mime = True
    return is_allowed_mime

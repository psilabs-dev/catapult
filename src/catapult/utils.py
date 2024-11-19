import base64
import hashlib
import logging
import numpy as np
import os
from pathlib import Path
from PIL import Image
import tempfile
from typing import List
import zipfile

logger = logging.getLogger(__name__)

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

def find_all_archives(root_directory: str) -> List[str]:
    # find all archives in subdirectories of a root directory.
    # checked extensions:
    file_paths = list()
    for dir, _, filenames in os.walk(root_directory):
        for filename in filenames:
            extension = os.path.splitext(filename)[1]
            if extension[1:] not in {"zip", "rar", "targz", "lzma", "7z", "xz", "cbz", "cbr", "pdf"}:
                continue
            file_path = os.path.join(dir, filename)
            file_paths.append(file_path)
    return file_paths

def image_is_corrupted(image_path: Path) -> bool:
    # quick/dirty method to check if image is corrupted.
    if isinstance(image_path, str):
        image_path = Path(image_path)

    image = Image.open(image_path)
    try:
        np.asarray(image)
        return False
    except OSError:
        return True

def archive_contains_corrupted_image(archive_path: Path) -> bool:
    # quick/dirty method to check if archive contains corrupted image
    if isinstance(archive_path, str):
        archive_path = Path(archive_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        extracted_archive_folder = Path(tmpdir) / archive_path.name
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extracted_archive_folder)
            for image in extracted_archive_folder.iterdir():
                if image.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                    if image_is_corrupted(image):
                        return True
    return False

def mask_string(s) -> str:
    if len(s) <= 2:
        return "*" * len(s)
    return s[0] + '*' * (len(s) - 2) + s[-1]

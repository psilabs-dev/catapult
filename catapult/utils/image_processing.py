import numpy as np
from pathlib import Path
from PIL import Image
import tempfile
from typing import overload, Union
import zipfile

@overload
def image_is_corrupted(image_path: str) -> bool:
    ...

@overload
def image_is_corrupted(image_path: Path) -> bool:
    ...

def image_is_corrupted(image_path: Union[Path, str]) -> bool:
    """
    Quick-and-dirty method to check if an image is corrupted.
    """
    if isinstance(image_path, (str, Path)):
        image = Image.open(image_path)
    else:
        raise TypeError(f"Unsupported image path type: {type(image_path)}")
    try:
        np.asarray(image)
        return False
    except OSError:
        return True

@overload
def archive_contains_corrupted_image(archive_path: str) -> bool:
    ...

@overload
def archive_contains_corrupted_image(archive_path: Path) -> bool:
    ...

def archive_contains_corrupted_image(archive_path: Union[Path, str]) -> bool:
    """
    Quick-and-dirty method to check if a zip Archive contains a corrupted image.
    """
    if isinstance(archive_path, str):
        archive_path = Path(archive_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        extracted_archive_folder = Path(tmpdir) / archive_path.name
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extracted_archive_folder)
            for image in extracted_archive_folder.iterdir():
                if image.suffix.lower() in {".png", ".jpg", ".jpeg"} and image_is_corrupted(image):
                    return True
    return False

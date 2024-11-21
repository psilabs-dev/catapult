from pathlib import Path
from typing import Union
import zipfile

from catapult.lanraragi.constants import IMAGE_SIGNATURES
from catapult.lanraragi.utils import get_signature_hex, is_valid_signature_hex

# convenience compression algorithms.
def flat_folder_to_zip(src_folder: Union[str, Path], trg_zip: Union[str, Path]):
    """
    Compress a flat folder containing only images into a target file using zip.
    """
    if isinstance(src_folder, str):
        src_folder = Path(src_folder)
    if isinstance(trg_zip, str):
        trg_zip = Path(trg_zip)

    if not isinstance(src_folder, Path):
        raise TypeError(f"Unsupported source folder type: {type(src_folder)}")
    if not isinstance(trg_zip, Path):
        raise TypeError(f"Unsupported target folder type: {type(trg_zip)}")

    if not src_folder.is_dir():
        raise TypeError(f"Path {src_folder} is not a directory.")
    with zipfile.ZipFile(trg_zip, 'w') as zip_obj:
        for path in src_folder.iterdir():
            # check if it is an image.
            ext = path.suffix
            filename = path.name
            if not ext:
                print("No file extension.")
                continue
            signature = get_signature_hex(path)
            if not is_valid_signature_hex(signature, allowed_signatures=IMAGE_SIGNATURES):
                print(f"Is not valid signature: {signature} not in {IMAGE_SIGNATURES}")
                continue
            zip_obj.write(path, filename)
            print(f"Wrote {path}")
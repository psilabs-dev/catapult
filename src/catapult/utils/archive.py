from enum import Enum
from pathlib import Path
from typing import List, Union, overload

@overload
def find_all_archives(root_directory: str) -> List[Path]:
    ...

@overload
def find_all_archives(root_directory: Path) -> List[Path]:
    ...

def find_all_archives(root_directory: Union[Path, str]) -> List[Path]:
    """
    Find all files in a directory with qualifying file extensions.
    """
    if isinstance(root_directory, str):
        root_directory = Path(root_directory)

    if isinstance(root_directory, Path):
        file_paths = list()
        for item in root_directory.rglob("*"):
            suffix = item.suffix
            if not suffix:
                continue
            if suffix[1:] not in {"zip", "rar", "targz", "lzma", "7z", "xz", "cbz", "cbr", "pdf"}:
                continue
            file_paths.append(item)
        return file_paths
    else:
        raise TypeError(f"Unsupported root directory type: {type(root_directory)}")

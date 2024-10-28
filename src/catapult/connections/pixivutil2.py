from typing import List

from catapult.models import ArchiveUploadRequest

def is_available(db: str, contents_directory: str) -> bool:
    """
    TODO: Check if pixivutil2 is available.
    """
    return False

def build_upload_requests(db: str, contents_directory: str) -> List[ArchiveUploadRequest]:
    """
    TODO: Build upload requests for pixivutil2.
    """
    raise NotImplementedError
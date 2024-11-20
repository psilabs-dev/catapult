from pathlib import Path
from typing import List

from catapult.models import ArchiveUploadRequest, ArchiveMetadata
from catapult.utils import find_all_archives

def build_upload_requests(contents_directory: str) -> List[ArchiveUploadRequest]:
    """
    Build upload requests for archives in a given folder. No archive metadata is injected.
    """

    archive_file_path_list = find_all_archives(contents_directory)
    upload_requests = list()

    for archive_file_path in archive_file_path_list:
        archive_file_name = archive_file_path.name
        metadata = ArchiveMetadata()
        upload_request = ArchiveUploadRequest(archive_file_path, archive_file_name, metadata)
        upload_requests.append(upload_request)
    
    return upload_requests

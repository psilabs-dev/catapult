from enum import Enum
from pathlib import Path
from typing import List

class ArchiveValidateUploadStatus(Enum):
    SUCCESS = 0
    FAILURE = 1 # general failure

    FILE_NOT_EXIST = 10
    UNSUPPORTED_FILE_EXTENSION = 11
    INVALID_MIME_TYPE = 12
    INVALID_EXTENSION = 13
    CONTAINS_CORRUPTED_IMAGE = 14
    NOT_A_FILE = 15

    # server response
    NETWORK_FAILURE = 20
    CHECKSUM_MISMATCH = 21
    UNPROCESSABLE_ENTITY = 22
    INTERNAL_SERVER_ERROR = 23
    IS_DUPLICATE = 24
    LOCKED = 25

class ArchiveMetadata:

    def __init__(self, title: str=None, tags: str=None, summary: str=None, category_id: int=None):
        self.title = title
        self.tags = tags
        self.summary = summary
        self.category_id = category_id

class ArchiveUploadRequest:

    def __init__(self, archive_file_path: Path, archive_file_name: str, metadata: ArchiveMetadata):
        self.archive_file_path = archive_file_path
        self.archive_file_name = archive_file_name
        self.metadata = metadata

class ArchiveValidateResponse:
    
    archive_file_path: Path
    status_code: ArchiveValidateUploadStatus
    message: str

class ArchiveUploadResponse:

    archive_file_path: Path
    status_code: ArchiveValidateUploadStatus
    message: str

class MultiArchiveUploadResponse:
    """
    Response object for multiple archive uploads.
    """
    upload_responses: List[ArchiveUploadResponse]

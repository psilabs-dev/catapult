import hashlib
import logging
import os
from pathlib import Path
import requests
import time
from typing import Dict, List, Tuple

from .constants import ALLOWED_SIGNATURES
from .models import ArchiveMetadata
from .utils import calculate_sha1, lrr_build_auth

logger = logging.getLogger(__name__)

def validate_archive_file(archive_file_path: str) -> Tuple[bool, str]:
    """
    Validate the archive file path for upload by checking its extension and MIME type.

    Returns True, success if archive can be submitted to LRR server, otherwise False with corresponding error.
    """
    if not os.path.exists(archive_file_path):
        return False, "file does not exist"
    ext = os.path.splitext(archive_file_path)[1]
    if not ext:
        return False, "cannot have no extension" # cannot have no extension.
    if ext[1:] not in {"zip", "rar", "targz", "lzma", "7z", "xz", "cbz", "cbr", "pdf"}:
        return False, "unsupported extension" # extension not supported by LANraragi.
    with open(archive_file_path, 'rb') as fb:
        signature = fb.read(8).hex()
    for allowed_signature in ALLOWED_SIGNATURES:
        if signature.startswith(allowed_signature):
            return True, "success"
    return False, "failed the MIME test" # file MIME type not supported by LANraragi.

def upload_archive_to_server(
        archive_file_path: str,
        metadata: ArchiveMetadata,
        lrr_host: str,
        archive_file_name: str=None,
        lrr_api_key: str=None,
        max_retries: int=3
) -> requests.Response:
    """
    Uploads an Archive to the LANraragi server. In case of connection error, implements exponential backoff.

    Parameters
    ----------
    archive_file_path : str
        Full path to an archive file. File must exist and be a valid file type.
    metadata : ArchiveMetadata
        Archive metadata.
    lrr_host : str
        Absolute URL of the LANraragi host (e.g. `http://localhost:3000` or `https://lanraragi`).
    archive_file_name : str, optional
        Name of the Archive in the server. Defaults to the basename of the Archive path in the client's machine.
    lrr_api_key : str, optional
        API key for LANraragi server. Defaults to no key.
    max_retries : int, optional
        Max number of retries before client gives up; defaults to 3. If `max_retries` is set to -1, it will try forever.

    Returns
    -------
    Response
        A requests.Response object. Will return the following status codes. It is the caller's responsibility to handle these status codes.
        - 200 success
        - 400 no file attached
        - 401 require authentication/wrong credentials
        - 409 duplicate archive
        - 415 unsupported file
        - 422 checksum mismatch
        - 500 internal server error
    
    Raises
    ------
    requests.ConnectionError
        Cannot reach LANraragi server, SSL certificate invalid, or a general connection error.
    requests.Timeout
    """

    if not archive_file_name:
        archive_file_name = Path(archive_file_path).name

    headers = dict()
    if lrr_api_key:
        auth = lrr_build_auth(lrr_api_key)
        headers["Authorization"] = auth

    archive_checksum = calculate_sha1(archive_file_path)
    data = dict()

    data["file_checksum"] = archive_checksum
    if metadata.title:
        data["title"] = metadata.title
    if metadata.tags:
        data["tags"] = metadata.tags
    if metadata.summary:
        data["summary"] = metadata.summary
    if metadata.category_id:
        data["category_id"] = metadata.category_id

    # handle connection errors.
    with open(archive_file_path, 'rb') as fb:
        files = {'file': (archive_file_name, fb)}
        url = f"{lrr_host}/api/archives/upload"

        # attempt to send put request.
        retry_count = 0
        while True:
            try:
                response = requests.put(
                    url,
                    files=files,
                    data=data,
                    headers=headers
                )
                return response
            except requests.ConnectionError as conn_err:
                if max_retries < 0 or retry_count < max_retries:
                    time_to_sleep = 2 ** retry_count
                    logger.warning(f"Encountered connection error (is the server \"{lrr_host}\" online?); sleeping for {time_to_sleep}s...")
                    time.sleep(time_to_sleep)
                    retry_count += 1
                    continue
                else:
                    raise requests.ConnectionError("Encountered persistent connection error: ", conn_err)
            except requests.Timeout as timeout_err:
                if max_retries < 0 or retry_count < max_retries:
                    time_to_sleep = 2 ** (retry_count + 5)
                    logger.warning(f"Encountered timeout; backing off for {time_to_sleep}s...")
                    time.sleep(time_to_sleep)
                    retry_count += 1
                    continue
                else:
                    raise requests.Timeout(f"Failed to resolve server timeout: ", timeout_err)

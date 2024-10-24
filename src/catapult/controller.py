import hashlib
import logging
import os
from pathlib import Path
import requests
import threading
import time
from typing import Dict, List, Set, Tuple

from .constants import ALLOWED_SIGNATURES
from .models import ArchiveMetadata, ArchiveUploadRequest
from .services import nhentai_archivist
from .utils import calculate_sha1, lrr_build_auth, lrr_compute_id

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

def test_connection(lrr_host: str, lrr_api_key: str=None, max_retries: int=3):
    """
    Test connection to LANraragi server.
    """
    retry_count = 0
    url = f"{lrr_host}/api/info"

    headers = dict()
    if lrr_api_key:
        auth = lrr_build_auth(lrr_api_key)
        headers["Authorization"] = auth

    while True:
        try:
            response = requests.get(
                url,
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

def get_archive_ids(lrr_host: str, lrr_api_key: str=None, max_retries: int=3) -> Set[str]:
    """
    Get all archive IDs as a set.
    """
    retry_count = 0
    url = f"{lrr_host}/api/archives"

    headers = dict()
    if lrr_api_key:
        auth = lrr_build_auth(lrr_api_key)
        headers["Authorization"] = auth

    while True:
        try:
            response = requests.get(
                url,
                headers=headers
            )
            status_code = response.status_code
            if status_code == 200:
                archive_ids = set()
                for obj in response.json():
                    archive_ids.add(obj['arcid'])
                return archive_ids
            else:
                requests.HTTPError(f"Unhandled status code {status_code}: {response.text}")

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

def __handle_upload_job(
        upload_request: ArchiveUploadRequest, lrr_host: str, lrr_api_key: str, upload_counter: List[int], 
        lock: threading.Lock=None, checksum_max_retries: int=None
):
    archive_filename = upload_request.archive_file_name
    logger.debug(f"Uploading {archive_filename}...")
    checksum_retry_count = 0
    while True:
        response = upload_archive_to_server(
            upload_request.archive_file_path,
            upload_request.metadata,
            lrr_host,
            archive_file_name=upload_request.archive_file_name,
            lrr_api_key=lrr_api_key
        )
        status_code = response.status_code
        if status_code == 200:
            logger.info(f"Successfully uploaded {archive_filename} to {lrr_host}.")
            if lock:
                with lock:
                    upload_counter[0] += 1
            else:
                upload_counter[0] += 1
            return
        elif status_code == 401:
            raise ConnectionError(f"Invalid credentials while authenticating to LANraragi server {lrr_host}.")
        elif status_code == 409: # duplicate archive
            logger.warning(f"Duplicate archive: {upload_request.archive_file_name}.")
            return
        elif status_code == 415: # unsupported file
            logger.warning(f"Unsupported file: {upload_request.archive_file_name}.")
            return
        elif status_code == 422: # checksum mismatch, try again.
            if checksum_retry_count < checksum_max_retries:
                logger.warning(f"Checksum mismatch while handling {upload_request.archive_file_name}; trying again...")
                checksum_retry_count += 1
                continue
            else:
                raise ConnectionError(f"Persistent checksum issues with {lrr_host} while uploading {archive_filename}.")
        elif status_code == 500: # server error
            raise requests.HTTPError(f"A server error has occurred! {response.text}")
        else:
            raise requests.HTTPError(f"status code {status_code}; error {response.text}")

def upload_archives_to_server(
        upload_requests: List[ArchiveUploadRequest], lrr_host: str, lrr_api_key: str=None, use_threading: bool=False,
        remove_duplicates: bool=False,
):
    """
    Execute multiple archive uploads to LANraragi.
    """
    fn_call_start = time.time()

    # connection must be available.
    logger.info("Testing connection to LANraragi server...")
    is_connected = test_connection(lrr_host, lrr_api_key=lrr_api_key).status_code == 200
    if not is_connected:
        raise ConnectionError(f"Cannot connect to LANraragi server {lrr_host}! Test your connection before trying again.")
    logger.info("Successfully connected.")


    # remove requests that have same ID. (can be very slow)
    if remove_duplicates:
        # get all existing archive IDs from server first; this will be used to prevent uploading duplicates and wasting requests later.
        logger.info("Fetching Archive IDs...")
        archive_id_set = get_archive_ids(lrr_host, lrr_api_key=lrr_api_key)
        logger.info("Fetched Archive IDs.")

        logger.info("Removing duplicate requests...")
        num_duplicates = 0
        nonduplicate_upload_requests = list()
        for upload_request in upload_requests:
            archive_file_path = upload_request.archive_file_path
            local_archive_id = lrr_compute_id(archive_file_path)
            if local_archive_id in archive_id_set: # duplicate detected
                num_duplicates += 1
                continue
            else:
                nonduplicate_upload_requests.append(upload_request)
        logger.info(f"Removed {num_duplicates} duplicates from being uploaded.")
        upload_requests = nonduplicate_upload_requests

    logger.info("Starting upload job...")
    upload_counter = [0]
    if use_threading:
        lock = threading.Lock()
        threads:List[threading.Thread] = list()
        for upload_request in upload_requests:
            thread = threading.Thread(
                target=__handle_upload_job, 
                args=(upload_request, lrr_host, lrr_api_key, upload_counter),
                kwargs={'lock': lock}
            )
            threads.append(thread)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    else:
        for upload_request in nonduplicate_upload_requests:
            __handle_upload_job(upload_request, lrr_host, lrr_api_key, upload_counter)

    fn_call_time = time.time() - fn_call_start
    logger.info(f"Uploaded {upload_counter} new archives; elapsed time: {fn_call_time}s.")
    return upload_counter[0]

def start_nhentai_archivist_upload_process(db: str, contents_directory: str, lrr_host: str, lrr_api_key: str=None, use_threading: bool=False):
    """
    Upload archives downloaded by nhentai archivist.
    """
    if not nhentai_archivist.is_available(db, contents_directory):
        logger.error("Nhentai archivist is not available.")
        return
    logger.info("Building nhentai archivist upload requests...")
    upload_requests = nhentai_archivist.build_upload_requests(db, contents_directory)
    logger.info("Running upload job for nhentai archivist...")
    uploads = upload_archives_to_server(upload_requests, lrr_host, lrr_api_key=lrr_api_key, use_threading=use_threading)
    return uploads

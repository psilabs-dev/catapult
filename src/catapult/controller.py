import aiohttp
import asyncio
import hashlib
import logging
import os
from typing import Dict, List

from catapult.connections import common
from catapult.constants import ALLOWED_LRR_EXTENSIONS, ALLOWED_SIGNATURES
from catapult.cache import archive_hash_exists, insert_archive_hash
from catapult.models import ArchiveMetadata, ArchiveUploadRequest, ArchiveUploadResponse, ArchiveValidateResponse, ArchiveValidateUploadStatus, MultiArchiveUploadResponse
from catapult.utils import calculate_sha1, lrr_build_auth, lrr_compute_id, archive_contains_corrupted_image

logger = logging.getLogger(__name__)

async def __archive_id_exists(
        archive_id: str,
        lrr_host: str,
        headers: dict,
        max_retries: int=3,
        use_cache: bool=True,
) -> bool:
    """
    Return True if Archive ID exists in server.
    """
    url = f"{lrr_host}/api/archives/{archive_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url=url, headers=headers) as response:
            data = await response.json()
            return 'arcid' in data

def __get_signature(archive_file_path: str) -> str:
    with open(archive_file_path, 'rb') as fb:
        signature = fb.read(8).hex()
        return signature

def __is_valid_signature(signature: str) -> bool:
    is_allowed_mime = False
    for allowed_signature in ALLOWED_SIGNATURES:
        if signature.strip().startswith(allowed_signature.lower().replace(' ', '')):
            is_allowed_mime = True
    return is_allowed_mime

async def run_lrr_connection_test(lrr_host: str, lrr_api_key: str=None, max_retries: int=3):
    """
    Test connection to LANraragi server.

    Parameters
    ----------
    lrr_host : str
        URL of the LANraragi host
    lrr_api_key : str, optional
        API key for LANraragi server. Defaults to no key.
    max_retries : int, optional
        Max number of retries before client gives up; defaults to 3. If `max_retries` is set to -1, it will retry forever.

    Returns
    -------
    Response
        Returns the following status codes.
        - 200 success
        
    Raises
    ------
    ConnectionError
        Cannot reach LANraragi server, SSL certificate invalid, or general connection error.
    Timeout
    """
    retry_count = 0
    url = f"{lrr_host}/api/info"

    headers = dict()
    if lrr_api_key:
        auth = lrr_build_auth(lrr_api_key)
        headers["Authorization"] = auth

    async with aiohttp.ClientSession() as session:
        async with session.get(url=url, headers=headers) as response:
            return response

async def async_validate_archive(
        archive_file_path: str
) -> ArchiveValidateResponse:
    """
    Validates that an Archive can be uploaded.
    """
    validate_response = ArchiveValidateResponse()
    validate_response.archive_file_path = archive_file_path
    validate_response.message = ""

    # check if archive exists
    if not os.path.exists(archive_file_path):
        validate_response.status_code = ArchiveValidateUploadStatus.FILE_NOT_EXIST
        return validate_response
    
    # check if extension is exists and valid
    ext = os.path.splitext(archive_file_path)[1]
    if not ext:
        validate_response.status_code = ArchiveValidateUploadStatus.INVALID_EXTENSION
        validate_response.message = "No file extension."
        return validate_response
    if ext[1:] not in ALLOWED_LRR_EXTENSIONS:
        validate_response.status_code = ArchiveValidateUploadStatus.INVALID_EXTENSION
        validate_response.message = f"Invalid extension: \"{ext}\""
        return validate_response

    # check if file signature is valid.
    signature = __get_signature(archive_file_path)
    is_allowed_mime = __is_valid_signature(signature)
    if not is_allowed_mime:
        validate_response.status_code = ArchiveValidateUploadStatus.INVALID_MIME_TYPE
        validate_response.message = f"Invalid signature: {signature}"
        return validate_response

    # check if archive does not contain corrupted data
    if archive_contains_corrupted_image(archive_file_path):
        validate_response.status_code = ArchiveValidateUploadStatus.CONTAINS_CORRUPTED_IMAGE
        validate_response.message = "Archive contains corrupted image"
        return validate_response
    
    validate_response.status_code = ArchiveValidateUploadStatus.SUCCESS
    validate_response.message = "success"
    return validate_response

async def async_upload_archive_to_server(
        archive_file_path: str,
        metadata: ArchiveMetadata,
        lrr_host: str,
        archive_file_name: str=None,
        headers: Dict[str, str]=None,
        max_retries: int=3,
        use_cache: bool=True,
) -> ArchiveUploadResponse:
    """
    Async method to upload an Archive to the LANraragi server. Implements the following flows:
    1. check if Archive is a duplicate (using cache if necessary).
    1. validate Archive file structure.
    1. try to upload Archive to the Server.
    1. handle upload result and update cache on success.

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
    check_for_corruption : bool, False
        Check Archive for corrupted images.
    use_cache : bool, True
        Use cache to avoid uploading Archives the program assumes is already uploaded previously.
    
    Returns
    -------
    ArchiveUploadResponse object.

    Raises
    ------
    requests.ConnectionError
        Cannot reach LANraragi server, SSL certificate invalid, or a general connection error.
    requests.Timeout
    """
    upload_response = ArchiveUploadResponse()
    upload_response.archive_file_path = archive_file_path
    upload_response.message = ""
    archive_file_name = archive_file_name if archive_file_name else os.path.basename(archive_file_path)
    archive_md5 = hashlib.md5(archive_file_path.encode('utf-8')).hexdigest()

    # check if archive exists
    if not os.path.exists(archive_file_path):
        upload_response.status_code = ArchiveValidateUploadStatus.FILE_NOT_EXIST
        return upload_response

    # check if extension is exists and valid
    ext = os.path.splitext(archive_file_path)[1]
    if not ext:
        upload_response.status_code = ArchiveValidateUploadStatus.INVALID_EXTENSION
        upload_response.message = "No file extension."
        return upload_response
    if ext[1:] not in ALLOWED_LRR_EXTENSIONS:
        upload_response.status_code = ArchiveValidateUploadStatus.INVALID_EXTENSION
        upload_response.message = f"Invalid extension: \"{ext}\""
        return upload_response

    # check if archive is duplicate (locally)
    if use_cache:
        archive_uploaded = await archive_hash_exists(archive_md5)
        if archive_uploaded:
            upload_response.status_code = ArchiveValidateUploadStatus.IS_DUPLICATE
            upload_response.message = "Duplicate in cache"
            logger.info(f"Duplicate in cache: {archive_file_name}")
            return upload_response

    # check if file signature is valid.
    signature = __get_signature(archive_file_path)
    is_allowed_mime = __is_valid_signature(signature)
    if not is_allowed_mime:
        upload_response.status_code = ArchiveValidateUploadStatus.INVALID_MIME_TYPE
        upload_response.message = f"Invalid signature: {signature}"
        return upload_response

    # check if archive is duplicate (remotely)
    archive_id = lrr_compute_id(archive_file_path)
    archive_is_duplicate = await __archive_id_exists(archive_id, lrr_host, headers=headers)
    if archive_is_duplicate:
        upload_response.status_code = ArchiveValidateUploadStatus.IS_DUPLICATE
        upload_response.message = "Duplicate in server"
        logger.info(f"Duplicate in server: {archive_file_name}")
        return upload_response

    # TODO: check if archive is corrupted
    # this is probably something that is done better off on another machine or separate workload...

    # upload archive to server
    url = f"{lrr_host}/api/archives/upload"
    archive_checksum = calculate_sha1(archive_file_path)
    
    async with aiohttp.ClientSession() as session:
        with open(archive_file_path, 'rb') as fb:
            files = {'file': (archive_file_name, fb)}
            form_data = aiohttp.FormData(quote_fields=False)
            form_data.add_field('file', fb, filename=archive_file_name, content_type='application/octet-stream')
            form_data.add_field("file_checksum", archive_checksum)
            if metadata.title:
                form_data.add_field('title', metadata.title)
            if metadata.tags:
                form_data.add_field('tags', metadata.tags)
            if metadata.summary:
                form_data.add_field('summary', metadata.summary)
            if metadata.category_id:
                form_data.add_field('category_id', metadata.category_id)
            
            checksum_mismatch_retry_count = 0
            connection_error_retry_count = 0
            while True:
                try:
                    async with session.put(url=url, data=form_data, headers=headers) as response:
                        status_code = response.status
                        if status_code == 200:
                            upload_response.status_code = ArchiveValidateUploadStatus.SUCCESS
                            if use_cache:
                                await insert_archive_hash(archive_md5)
                            logger.info(f"Archive uploaded: {archive_file_name}")
                            return upload_response
                        elif status_code == 400: # shouldn't happen.
                            upload_response.status_code = ArchiveValidateUploadStatus.FILE_NOT_EXIST
                            return upload_response
                        elif status_code == 409: # shouldn't happen if checks are done.
                            upload_response.status_code = ArchiveValidateUploadStatus.IS_DUPLICATE
                            upload_response.message = "Duplicate in server"
                            return upload_response
                        elif status_code == 415: # shouldn't happen if checks are done beforehand.
                            upload_response.status_code = ArchiveValidateUploadStatus.UNSUPPORTED_FILE_EXTENSION
                            upload_response.message = await response.json()["error"]
                            return upload_response
                        elif status_code == 417: # try several times for checksum mismatch.
                            if checksum_mismatch_retry_count < 3:
                                checksum_mismatch_retry_count += 1
                                continue
                            else:
                                upload_response.status_code = ArchiveValidateUploadStatus.CHECKSUM_MISMATCH
                                upload_response.message = await response.json()["error"]
                                return upload_response
                        elif status_code == 422: # probably shouldn't happen.
                            upload_response.status_code = ArchiveValidateUploadStatus.UNPROCESSABLE_ENTITY
                            return upload_response
                        elif status_code == 423: # will happen if upload design is bad.
                            upload_response.status_code = ArchiveValidateUploadStatus.LOCKED
                            return upload_response
                        elif status_code == 500:
                            upload_response.status_code = ArchiveValidateUploadStatus.INTERNAL_SERVER_ERROR
                            upload_response.message = await response.json()["error"]
                            return upload_response
                        else:
                            logger.error(f"Unexpected error occurred with status {status_code}: {response.text}")
                            upload_response.status_code = ArchiveValidateUploadStatus.FAILURE
                            upload_response.message = response.text
                            return response
                except aiohttp.ClientConnectionError as e:
                    if connection_error_retry_count < max_retries or max_retries == -1:
                        time_to_sleep = 2 ** (connection_error_retry_count + 1)
                        asyncio.sleep(time_to_sleep)
                    else:
                        upload_response.status_code = ArchiveValidateUploadStatus.NETWORK_FAILURE
                        return upload_response

async def upload_multiple_archives_to_server(
        upload_requests: List[ArchiveUploadRequest], lrr_host: str, lrr_api_key: str=None, 
        use_cache: bool=True,
        semaphore_value: int=8,
) -> MultiArchiveUploadResponse:
    """
    Upload multiple Archives to the LANraragi server.

    Parameters
    ----------
    upload_requests : List[ArchiveUploadRequest]
        A list of requests representing Archives to upload.
    lrr_host : str
        Absolute URL of the LANraragi host (e.g. `http://localhost:3000` or `https://lanraragi`).
    lrr_api_key : str, optional
        API key for LANraragi server. Defaults to no key.
    use_cache : int, optional
        Use cache for Archive-to-server deduplication (Default: True).

    Returns
    -------
    MultiArchiveUploadResponse

    Raises
    ------
    ConnectionError
        Cannot reach LANraragi server.
    """
    batch_response = MultiArchiveUploadResponse()

    semaphore = asyncio.Semaphore(value=semaphore_value)
    async def __upload_archive_task(archive_file_path, metadata, lrr_host, archive_file_name, headers):
        async with semaphore:
            return await async_upload_archive_to_server(archive_file_path, metadata, lrr_host, archive_file_name, headers=headers)

    headers = dict()
    if lrr_api_key:
        headers["Authorization"] = lrr_build_auth(lrr_api_key)
    tasks = [
        asyncio.create_task(
            __upload_archive_task(upload_request.archive_file_path, upload_request.metadata, lrr_host, upload_request.archive_file_name, headers=headers)
        ) for upload_request in upload_requests
    ]
    upload_responses: List[ArchiveUploadResponse] = await asyncio.gather(*tasks)
    batch_response.upload_responses = upload_responses
    return batch_response

def start_folder_upload_process(
        contents_directory: str, lrr_host: str, lrr_api_key: str=None, use_cache: bool=True
):
    """
    Upload archives found in a folder.
    """
    logger.info("Building folder archive upload requests...")
    upload_requests = common.build_upload_requests(contents_directory)
    logger.info("Running upload job for folder...")
    batch_upload_response = asyncio.run(upload_multiple_archives_to_server(
        upload_requests, lrr_host, lrr_api_key=lrr_api_key,
        use_cache=use_cache
    ))
    return batch_upload_response

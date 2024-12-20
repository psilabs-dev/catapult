import aiohttp
import aiohttp.client_exceptions
import asyncio
import hashlib
import logging
from pathlib import Path
from typing import List, Union, overload

from aiolrr.client import LRRClient
from aiolrr.constants import ALLOWED_LRR_EXTENSIONS
from aiolrr.utils import compute_sha1, compute_archive_id, get_signature_hex, is_valid_signature_hex

from catapult import cache
from catapult.cache import ArchiveIntegrityStatus, get_archive, insert_archive
from catapult.metadata import MetadataClient
from catapult.models import ArchiveMetadata, ArchiveUploadRequest, ArchiveUploadResponse, ArchiveValidateResponse, ArchiveValidateUploadStatus, MultiArchiveUploadResponse
from catapult.utils import archive_contains_corrupted_image
from catapult.utils.archive import find_all_archives

logger = logging.getLogger(__name__)

async def __archive_id_exists(
        archive_id: str,
        lrr_host: str,
        lrr_api_key: str=None,
        max_retries: int=3,
        use_cache: bool=True,
) -> bool:
    """
    Return True if Archive ID exists in server.
    """
    client = LRRClient(lrr_host=lrr_host, lrr_api_key=lrr_api_key)
    retry_count = 0
    while True:
        try:
            response = await client.get_archive_metadata(archive_id)
            return hasattr(response, 'arcid')
        except aiohttp.client_exceptions.ClientConnectionError as e:
            if retry_count < max_retries or max_retries < 0:
                time_to_sleep = 2 ** (retry_count + 1)
                logger.error(f"Connection error occurred (retrying in {time_to_sleep}s); is the server online?")
                await asyncio.sleep(time_to_sleep)
                retry_count += 1
            else:
                raise e

async def run_lrr_connection_test(lrr_host: str, lrr_api_key: str=None, max_retries: int=3):
    """
    Test (write) connection to LANraragi server.

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
    bool
        True if connection is successful, False otherwise
        
    Raises
    ------
    ConnectionError
        Cannot reach LANraragi server, SSL certificate invalid, or general connection error.
    Timeout
    """
    client = LRRClient(lrr_host=lrr_host, lrr_api_key=lrr_api_key)
    retry_count = 0
    while True:
        try:
            response = await client.get_shinobu_status()
            return response.status_code == 200
        except aiohttp.client_exceptions.ClientConnectionError as e:
            if retry_count < max_retries or max_retries < 0:
                time_to_sleep = 2 ** (retry_count + 1)
                logger.error(f"Connection error occurred (retrying in {time_to_sleep}s); is the server online?")
                await asyncio.sleep(time_to_sleep)
                retry_count += 1
            else:
                raise e

@overload
async def async_validate_archive(archive: Path) -> ArchiveValidateResponse:
    ...

@overload
async def async_validate_archive(archive: str) -> ArchiveValidateResponse:
    ...

async def async_validate_archive(archive: Union[Path, str]) -> ArchiveValidateResponse:
    """
    Validates that an Archive can be uploaded.
    """
    if isinstance(archive, str):
        archive = Path(archive)
    if isinstance(archive, Path):
        validate_response = ArchiveValidateResponse()
        validate_response.archive_file_path = archive
        validate_response.message = ""

        # check if archive exists
        if not archive.exists:
            validate_response.status_code = ArchiveValidateUploadStatus.FILE_NOT_EXIST
            return validate_response

        # check if archive is file
        if not archive.is_file():
            validate_response.status_code = ArchiveValidateUploadStatus.NOT_A_FILE
            validate_response.message = f"Not a file: {archive.absolute()}"
            return validate_response

        # check if extension is exists and valid
        ext = archive.suffix
        if not ext:
            validate_response.status_code = ArchiveValidateUploadStatus.INVALID_EXTENSION
            validate_response.message = "No file extension."
            return validate_response
        if ext[1:] not in ALLOWED_LRR_EXTENSIONS:
            validate_response.status_code = ArchiveValidateUploadStatus.INVALID_EXTENSION
            validate_response.message = f"Invalid extension: \"{ext}\""
            return validate_response

        # check if file signature is valid.
        signature = get_signature_hex(archive)
        is_allowed_mime = is_valid_signature_hex(signature)
        if not is_allowed_mime:
            validate_response.status_code = ArchiveValidateUploadStatus.INVALID_MIME_TYPE
            validate_response.message = f"Invalid signature: {signature}"
            return validate_response

        # check if archive does not contain corrupted data
        if archive_contains_corrupted_image(archive):
            validate_response.status_code = ArchiveValidateUploadStatus.CONTAINS_CORRUPTED_IMAGE
            validate_response.message = "Archive contains corrupted image"
            return validate_response

        validate_response.status_code = ArchiveValidateUploadStatus.SUCCESS
        validate_response.message = "success"
        return validate_response
    else:
        raise TypeError(f"Unsupported file type: {type(archive)}")

async def async_upload_archive_to_server(
        archive_file_path: Path,
        metadata: ArchiveMetadata,
        lrr_host: str,
        archive_file_name: str=None,
        lrr_api_key: str=None,
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
    archive_file_path : Path
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
    """
    upload_response = ArchiveUploadResponse()
    upload_response.archive_file_path = archive_file_path.absolute()
    upload_response.message = ""
    archive_file_name = archive_file_name if archive_file_name else archive_file_path.name
    archive_md5 = hashlib.md5(str(archive_file_path).encode('utf-8')).hexdigest()
    archive_stat = archive_file_path.stat()
    archive_integrity_status = ArchiveIntegrityStatus.ARCHIVE_PENDING
    ctime = archive_stat.st_ctime
    mtime = archive_stat.st_mtime
    client = LRRClient(lrr_host=lrr_host, lrr_api_key=lrr_api_key)

    # check if archive exists
    if not archive_file_path.exists():
        upload_response.status_code = ArchiveValidateUploadStatus.FILE_NOT_EXIST
        return upload_response

    # check if extension is exists and valid
    ext = archive_file_path.suffix
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
        archive_cache_row = await get_archive(archive_md5)
        if archive_cache_row and cache.get_modify_time_seconds(archive_cache_row) == mtime:
            upload_response.status_code = ArchiveValidateUploadStatus.IS_DUPLICATE
            upload_response.message = "Duplicate in cache"
            logger.info(f"Duplicate in cache: {archive_file_name}")
            return upload_response

    # check if file signature is valid.
    signature = get_signature_hex(archive_file_path)
    is_allowed_mime = is_valid_signature_hex(signature)
    if not is_allowed_mime:
        upload_response.status_code = ArchiveValidateUploadStatus.INVALID_MIME_TYPE
        upload_response.message = f"Invalid signature: {signature}"
        return upload_response

    # check if archive is duplicate (remotely)
    archive_id = compute_archive_id(archive_file_path)
    archive_is_duplicate = await __archive_id_exists(archive_id, lrr_host, lrr_api_key=lrr_api_key)
    if archive_is_duplicate:
        upload_response.status_code = ArchiveValidateUploadStatus.IS_DUPLICATE
        upload_response.message = "Duplicate in server"
        logger.info(f"Duplicate in server: {archive_file_name}")
        return upload_response

    # TODO: check if archive is corrupted
    # this is probably something that is done better off on another machine or separate workload...

    # upload archive to server
    with open(archive_file_path, 'rb') as archive_br:
        archive_checksum = compute_sha1(archive_br)
        archive_br.seek(0)
        checksum_mismatch_retry_count = 0
        connection_error_retry_count = 0
        while True:
            try:
                response = await client.upload_archive(
                    archive_br, 
                    archive_file_name, 
                    archive_checksum=archive_checksum,
                    title=metadata.title,
                    tags=metadata.tags,
                    summary=metadata.summary,
                    category_id=metadata.category_id
                )
                status_code = response.status_code
                if status_code == 200:
                    upload_response.status_code = ArchiveValidateUploadStatus.SUCCESS
                    if use_cache:
                        await insert_archive(
                            archive_md5, str(upload_response.archive_file_path), archive_integrity_status.value, ctime, mtime
                        )
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
                    upload_response.message = response.error
                    return upload_response
                elif status_code == 417: # try several times for checksum mismatch.
                    if checksum_mismatch_retry_count < 3:
                        checksum_mismatch_retry_count += 1
                        continue
                    else:
                        upload_response.status_code = ArchiveValidateUploadStatus.CHECKSUM_MISMATCH
                        upload_response.message = response.error
                        return upload_response
                elif status_code == 422: # probably shouldn't happen.
                    upload_response.status_code = ArchiveValidateUploadStatus.UNPROCESSABLE_ENTITY
                    return upload_response
                elif status_code == 423: # will happen if upload design is bad.
                    upload_response.status_code = ArchiveValidateUploadStatus.LOCKED
                    return upload_response
                elif status_code == 500:
                    upload_response.status_code = ArchiveValidateUploadStatus.INTERNAL_SERVER_ERROR
                    try:
                        upload_response.message = response.error
                    except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                        logger.error("An unhandled internal server error has occurred!", content_type_error)
                        upload_response.message = await response.text()
                    return upload_response
                else:
                    logger.error(f"Unexpected error occurred with status {status_code}: {response.text}")
                    upload_response.status_code = ArchiveValidateUploadStatus.FAILURE
                    upload_response.message = response.error
                    return response
            except aiohttp.ClientConnectionError as e:
                if connection_error_retry_count < max_retries or max_retries == -1:
                    time_to_sleep = 2 ** (connection_error_retry_count + 1)
                    logger.error(f"Connection error occurred (retrying in {time_to_sleep}s); is the server online?")
                    await asyncio.sleep(time_to_sleep)
                else:
                    upload_response.status_code = ArchiveValidateUploadStatus.NETWORK_FAILURE
                    upload_response.message = str(e)
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
    async def __upload_archive_task(
            archive_file_path: Path, metadata: ArchiveMetadata, lrr_host: str, archive_file_name: str, lrr_api_key: str
    ):
        async with semaphore:
            return await async_upload_archive_to_server(archive_file_path, metadata, lrr_host, archive_file_name=archive_file_name, lrr_api_key=lrr_api_key)
    tasks = [
        asyncio.create_task(
            __upload_archive_task(upload_request.archive_file_path, upload_request.metadata, lrr_host, upload_request.archive_file_name, lrr_api_key=lrr_api_key)
        ) for upload_request in upload_requests
    ]
    upload_responses: List[ArchiveUploadResponse] = await asyncio.gather(*tasks)
    batch_response.upload_responses = upload_responses
    return batch_response

async def upload_archives_from_folders(
        folders: List[Path], lrr_host: str, lrr_api_key: str=None, use_cache: bool=True, metadata_client: MetadataClient=None,
):
    """
    Upload Archives found in a list of Folder Paths.

    Parameters
    ----------
    folders : List[Path]
        A list of folder Paths that contain Archives to upload.
    lrr_host : str
        Absolute URL of the LANraragi host (e.g. `http://localhost:3000` or `https://lanraragi`).
    lrr_api_key : str, optional
        API key for LANraragi server. Defaults to no key.
    use_cache : int, optional
        Use cache for Archive-to-server deduplication (Default: True).
    metadata_client : MetadataClient, optional
        Client/interface for a metadata/content downloader.
    """
    upload_requests = []
    for folder in folders:
        archives_from_folder = find_all_archives(folder)
        for archive_path in archives_from_folder:
            if metadata_client:
                archive_id = metadata_client.get_id_from_path(archive_path)
                metadata = await metadata_client.get_metadata_from_id(archive_id)
            else:
                metadata = ArchiveMetadata()
            upload_request = ArchiveUploadRequest(archive_path, archive_path.name, metadata)
            upload_requests.append(upload_request)
    batch_upload_response = await upload_multiple_archives_to_server(
        upload_requests, lrr_host, lrr_api_key=lrr_api_key, use_cache=use_cache
    )
    return batch_upload_response

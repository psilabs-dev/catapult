from asyncio import Semaphore
import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from time import perf_counter
from typing import List
from fastapi import BackgroundTasks, Depends, FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from aiolrr.client import LRRClient
from catapult import cache, controller
from catapult.configuration import config
from catapult.metadata import PixivUtil2MetadataClient
from catapult.models import ArchiveMetadata, ArchiveUploadRequest, ArchiveValidateUploadStatus
from catapult.utils.archive import find_all_leaf_folders

logger = logging.getLogger('uvicorn.info')

@asynccontextmanager
async def lifespan(_: FastAPI):
    await cache.create_cache_table()
    yield

header_scheme = APIKeyHeader(name="Authorization")
server_api_key = f"Bearer {config.satellite_api_key}" if config.satellite_api_key else None

app = FastAPI(
    lifespan=lifespan
)

def __check_api_key(key: str) -> bool:
    """
    Check if API key is valid.
    """
    return key == server_api_key

async def __upload_pixivutil2_archives(folders: List[Path], metadata_client: PixivUtil2MetadataClient):
    start_time = perf_counter()
    # gather all archive paths to upload.
    archive_paths = []
    for folder in folders:
        archives_from_folder = find_all_leaf_folders(folder)
        archive_paths += archives_from_folder

    # now upload each archive path individually.
    semaphore = Semaphore(value=8)
    async def __upload_archive_with_metadata_client(archive_path: Path):
        async with semaphore:
            archive_id = metadata_client.get_id_from_path(archive_path)
            if not archive_id:
                metadata = ArchiveMetadata()
            else:
                # do not upload if metadata is not present (might change)
                metadata = await metadata_client.get_metadata_from_id(archive_id)
            upload_request = ArchiveUploadRequest(archive_path, archive_path.name, metadata)
            response = await controller.async_upload_archive_to_server(
                archive_path, metadata, config.lrr_host, archive_file_name=upload_request.archive_file_name, lrr_api_key=config.lrr_api_key,
            )
            if response.status_code == ArchiveValidateUploadStatus.SUCCESS:
                logger.info(   f"[upload_pixivutil2_archives] OK        {archive_path.name}")
            elif response.status_code == ArchiveValidateUploadStatus.IS_DUPLICATE:
                logger.info(   f"[upload_pixivutil2_archives] DUPLICATE {archive_path.name}")
            else:
                logger.warning(f"[upload_pixivutil2_archives] NOT OK    {archive_path}")

    tasks = [asyncio.create_task(__upload_archive_with_metadata_client(archive_path)) for archive_path in archive_paths]
    await asyncio.gather(*tasks)
    duration = perf_counter() - start_time
    logger.info(f"[upload_pixivutil2_archives] finished upload. Time: {duration}s")

@app.post("/api/upload/pixivutil2")
async def upload_pixivutil2_archives(background_tasks: BackgroundTasks, key: str=Depends(header_scheme)):
    """
    Upload PixivUtil2 folder archives. To be used in conjunction with a cron job.
    """
    if not __check_api_key(key):
        return JSONResponse({
            "message": "Missing or invalid API key."
        }, status_code=status.HTTP_401_UNAUTHORIZED)

    # check for connectivity
    lrr_host = config.lrr_host
    lrr_api_key = config.lrr_api_key
    if not lrr_host:
        return JSONResponse({
            "message": "No LANraragi host configured."
        }, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not lrr_api_key:
        return JSONResponse({
            "message": "No LANraragi API key."
        }, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    lanraragi = LRRClient(lrr_host=config.lrr_host, lrr_api_key=config.lrr_api_key)
    shinobu_response = await lanraragi.get_shinobu_status()
    if shinobu_response.status_code != 200:
        return JSONResponse({
            "message": f"Error occurred while checking connection: {shinobu_response.error}"
        }, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # check for pixivutil2
    metadata_db = config.pixivutil2_db
    if not metadata_db:
        return JSONResponse({
            "message": "No metadata db configured"
        }, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    metadata_db = Path(metadata_db)
    if not metadata_db.exists():
        return JSONResponse({
            "message": f"PixivUtil2 database does not exist: \"{metadata_db}\""
        }, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not metadata_db.is_file():
        return JSONResponse({
            "message": f"PixivUtil2 database is not file: {metadata_db}"
        }, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    pixivutil2_metadata = PixivUtil2MetadataClient(metadata_db)
    folders = config.pixivutil2_folders
    if not folders:
        return JSONResponse({
            "message": "No folders to upload archives from."
        })
    folders = [Path(directory) for directory in folders.split(";")]
    for folder in folders:
        if not folder.exists():
            return JSONResponse({
                "message": f"Invalid folder: {folder}"
            }, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    background_tasks.add_task(__upload_pixivutil2_archives, folders, pixivutil2_metadata)
    return JSONResponse({
        "message": "Queued PixivUtil2 Archive uploads."
    })

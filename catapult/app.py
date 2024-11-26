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
    # TODO: this should have a more dedicated logic.
    start_time = perf_counter()
    await controller.upload_archives_from_folders(
        folders, config.lrr_host, lrr_api_key=config.lrr_api_key, metadata_client=metadata_client
    )
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

from asyncio import Semaphore
import asyncio
from contextlib import asynccontextmanager
import hashlib
import logging
from pathlib import Path
from time import perf_counter
from typing import Dict, List
import aiohttp
import aiohttp.client_exceptions
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

from aiolrr.client import LRRClient
from catapult import cache
from catapult.cache import ArchiveIntegrityStatus
from catapult.configuration import config
from catapult.metadata import NhentaiArchivistMetadataClient
from catapult.utils.archive import find_all_archives
from catapult.utils.image_processing import archive_contains_corrupted_image

logger = logging.getLogger('uvicorn.info')

@asynccontextmanager
async def lifespan(_: FastAPI):
    await cache.create_cache_table()
    yield

app = FastAPI(
    lifespan=lifespan
)

@app.post("/api/metadata/nhentai-archivist")
async def update_nhentai_archivist_metadata(background_tasks: BackgroundTasks):
    """
    Update all untagged archives in LANraragi with metadata found in the nhentai_archivist
    database. To be used in conjunction with a cron job.
    """
    # check for connectivity
    client = LRRClient.default_client()
    shinobu_response = await client.get_shinobu_status()
    if shinobu_response.status_code != 200:
        return JSONResponse({
            "message": f"Error occurred while checking connection: {shinobu_response.error}"
        }, status_code=shinobu_response.status_code)

    lanraragi = LRRClient.default_client()
    nhentai_archivist = NhentaiArchivistMetadataClient.default_client()

    # get all untagged archives from LRR.
    untagged_archives = (await lanraragi.get_untagged_archives()).data
    logger.info(f"Found {len(untagged_archives)} untagged archives.")

    semaphore = Semaphore(value=8)
    async def __handle_archive_id(archive_id: str):
        """
        Run a metadata update job for any given archive ID under a semaphore.
        """
        async with semaphore:
            archive_response = await lanraragi.get_archive_metadata(archive_id)
            title = archive_response.title
            nhentai_id = nhentai_archivist.get_id_from_path(title)
            nhentai_metadata = await nhentai_archivist.get_metadata_from_id(nhentai_id)

            retry_count = 0
            while True:
                try:
                    response = await lanraragi.update_archive(
                        archive_id, title=nhentai_metadata.title, tags=nhentai_metadata.tags, summary=nhentai_metadata.summary
                    )
                    if response.success:
                        logger.info(f"Updated archive metadata: {nhentai_metadata.title}")
                        return (archive_id, response.status_code)
                    else:
                        logger.error(f"Failed to update archive: {archive_id}")
                        return (archive_id, response.status_code)
                except aiohttp.client_exceptions.ClientConnectionError:
                    # retry indefinitely
                    time_to_sleep = 2 ** (retry_count + 1)
                    await asyncio.sleep(time_to_sleep)

    tasks = [asyncio.create_task(__handle_archive_id(archive_id)) for archive_id in untagged_archives]
    results = await asyncio.gather(*tasks)
    response:Dict[int, List[str]] = {}
    for result in results:
        archive_id, status_code = result
        if status_code not in response:
            response[status_code] = [archive_id]
        else:
            response[status_code].append(archive_id)
    return JSONResponse(response, status_code=200)

@app.get("/api/archives/integrity/{integrity_status}")
async def get_integrity_status(integrity_status: int):
    """
    Get archives from database based on integrity ID.
    """
    results = [cache.get_path(result) for result in (await cache.get_archives_by_integrity_status(integrity_status))]
    return JSONResponse(results, status_code=200)

async def __scan_archives_directory(contents_dir):
    integrity_status = ArchiveIntegrityStatus.ARCHIVE_PENDING.value
    all_archives = find_all_archives(contents_dir)
    archive_paths = []
    for archive in all_archives:
        archive_path = str(archive.absolute())
        archive_stat = archive.stat()
        archive_md5 = hashlib.md5(archive_path.encode('utf-8')).hexdigest()
        row = await cache.get_archive(archive_md5)
        if row and cache.get_modify_time_seconds(row) == archive_stat.st_mtime:
            logger.info(f"[scan_archives_directory] Already scanned: {archive.name}")
            continue
        await cache.insert_archive(archive_md5, archive_path, integrity_status, archive_stat.st_ctime, archive_stat.st_mtime)
        logger.info(f"[scan_archives_directory] Insert archive {archive.name}")
        archive_paths.append(archive_path)

@app.post("/api/archives/scan")
async def scan_archives_directory(background_tasks: BackgroundTasks):
    """
    Scan and add all archives from the LRR contents directory to the cache.
    """
    contents_dir = config.lrr_contents_dir
    if not contents_dir:
        return JSONResponse({"message": "LRR contents dir not configured"}, status_code=404)
    contents_dir = Path(contents_dir)
    if not contents_dir.exists():
        return JSONResponse({"message": f"Contents dir does not exist: {contents_dir}"}, status_code=404)
    if not contents_dir.is_dir():
        return JSONResponse({"message": f"Contents dir must be directory: {contents_dir}"}, status_code=400)
    background_tasks.add_task(__scan_archives_directory, contents_dir)
    return JSONResponse({"message": "Queued file scan of directory."}, status_code=200)

async def __update_integrity_status(rows):
    # run check
    logger.info("[update_integrity_status] classifying archive integrity...")
    start_time = perf_counter()
    semaphore = Semaphore(value=8)
    async def __handle_path(row):
        _path = Path(cache.get_path(row))
        if not _path.exists():
            logger.error(f"[update_integrity_status] Archive does not exist: {_path.name}")
            await cache.delete_archive(cache.get_md5(row))
        path = str(_path)
        archive_md5 = cache.get_md5(row)
        stat = _path.stat()
        async with semaphore:
            if archive_contains_corrupted_image(_path):
                logger.warning(f"[update_integrity_status] Archive NOT OK: {_path.name}")
                await cache.insert_archive(archive_md5, path, ArchiveIntegrityStatus.ARCHIVE_CORRUPTED.value, stat.st_ctime, stat.st_mtime)
            else:
                logger.info(f"[update_integrity_status] Archive OK:    {_path.name}")
                await cache.insert_archive(archive_md5, path, ArchiveIntegrityStatus.ARCHIVE_OK.value, stat.st_ctime, stat.st_mtime)
    tasks = [
        asyncio.create_task(__handle_path(row)) for row in rows
    ]
    await asyncio.gather(*tasks)
    duration = perf_counter() - start_time
    logger.info(f"[update_integrity_status] time: {duration}s")

@app.post("/api/archives/integrity")
async def update_integrity_status(background_tasks: BackgroundTasks):
    """
    Get all PENDING archives in cache and classify their integrity status.
    """
    integrity_status = ArchiveIntegrityStatus.ARCHIVE_PENDING.value
    rows = await cache.get_archives_by_integrity_status(integrity_status)
    background_tasks.add_task(__update_integrity_status, rows)
    # paths_to_analyze = [cache.get_path(row) for row in rows]
    num_paths_to_analyze = len([cache.get_path(row) for row in rows])
    return JSONResponse({"message": f"Queued integrity scan of {num_paths_to_analyze} archives."}, status_code=200)

async def __delete_corrupted_archives(rows):
    for row in rows:
        try:
            _path = Path(cache.get_path(row))
            _path.unlink()
        except FileNotFoundError:
            logger.info(f"[delete_corrupted_archives] Archive does not exist: {_path}")
        await cache.delete_archive(cache.get_md5(row))
        logger.info(f"[delete_corrupted_archives] DELETE {_path.name}")

@app.delete("/api/archives/corrupted")
async def delete_corrupted_archives(background_tasks: BackgroundTasks):
    """
    Run a background task that removes all CORRUPTED archives.

    WARNING: this is a DESTRUCTIVE action!
    """
    logger.info("[delete_corrupted_archives] Removing corrupted archives...")
    integrity_status = ArchiveIntegrityStatus.ARCHIVE_CORRUPTED.value
    rows = await cache.get_archives_by_integrity_status(integrity_status)
    paths_to_delete = [cache.get_path(row) for row in rows]
    num_paths_to_delete = len(paths_to_delete)
    background_tasks.add_task(__delete_corrupted_archives, rows)
    return JSONResponse({"message": f"Deleted {num_paths_to_delete} archives."}, status_code=200)
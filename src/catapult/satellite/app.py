from asyncio import Semaphore
import asyncio
import logging
from typing import Dict, List
import aiohttp
import aiohttp.client_exceptions
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

from catapult.lanraragi.client import LRRClient
from catapult.metadata import NhentaiArchivistMetadataClient

logger = logging.getLogger('uvicorn.info')
app = FastAPI()

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

@app.get("/api/archives/integrity")
async def get_integrity_status():
    """
    Get all corrupted archives currently identified in the catapult database.
    """
    raise NotImplementedError("get_integrity_status not implemented!")

@app.post("/api/archives/integrity")
async def update_integrity_status(background_tasks: BackgroundTasks):
    """
    Run a background task that updates the integrity status of archives from the database.

    This is a (potentially very) long-running task.
    """
    raise NotImplementedError("compute_integrity_status not implemented!")

@app.delete("/api/archives/corrupted")
async def remove_corrupted_archives(background_tasks: BackgroundTasks):
    """
    Run a background task that removes corrupted archives as defined in the database.
    """
    raise NotImplementedError("remove_corrupted_status not implemented!")
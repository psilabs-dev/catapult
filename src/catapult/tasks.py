from celery import Celery
import logging
from pathlib import Path

from catapult.configuration import config
from catapult.controller import run_lrr_connection_test, start_folder_upload_process, start_nhentai_archivist_upload_process

logger = logging.getLogger(__name__)
worker = Celery(broker=config.celery_broker_url)

@worker.task
def process_upload_task():
    """
    Runs an automated (potentially very long-running) background upload task.
    The task is determined completely by configuration file and environment variables
    checks which sub-tasks are available and executes them.

    While it may be possible to run concurrently, at the moment this is single-process.
    `check_for_corruption` is set to False (the worker should not be responsible for this).
    """

    # get application configuration
    lrr_host = config.lrr_host
    lrr_api_key = config.lrr_api_key

    # get multi-upload from-folder configuration
    mu_folder = config.multi_upload_folder_dir

    # get multi-upload from-nhentai-archivist configuration
    mu_nhentai_archivist_db = config.multi_upload_nhentai_archivist_db
    mu_nhentai_archivist_contents = config.multi_upload_nhentai_archivist_content_dir

    # run connection test.
    response = run_lrr_connection_test(lrr_host, lrr_api_key)
    if not response.status_code == 200:
        logger.error('Cannot reach LRR server!')
        return

    # check if multi-upload can be used.
    logger.info("Checking for folder-based multi-upload availability...")
    if mu_folder is not None:
        if Path(mu_folder).exists:
            logger.info("Folder-based multi-upload is available; running...")
            start_folder_upload_process(
                mu_folder, lrr_host, lrr_api_key, remove_duplicates=True, check_for_corruption=False,
                use_threading=True, use_multiprocessing=False, max_upload_workers=1,
                use_cache=True
            )
        else:
            logger.error(f"Cannot perform folder-based upload; {mu_folder} does not exist!")
    
    # check if nh-archivist can be used.
    if mu_nhentai_archivist_contents and mu_nhentai_archivist_db:
        if Path(mu_nhentai_archivist_contents).exists and Path(mu_nhentai_archivist_db).exists:
            logger.info("nhentai-archivist multi-upload is available; running...")
            start_nhentai_archivist_upload_process(
                mu_nhentai_archivist_db, mu_nhentai_archivist_contents,
                lrr_host, lrr_api_key, remove_duplicates=True, check_for_corruption=False,
                use_threading=True, use_multiprocessing=False, max_upload_workers=1,
                use_cache=True
            )
        else:
            logger.error(f"Cannot upload archives from nhentai-archivist; file does not exist!")
    
    return
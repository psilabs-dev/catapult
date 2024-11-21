import aiosqlite
import asyncio
import logging

from catapult.configuration import config

logger = logging.getLogger(__name__)

async def create_cache_table():
    """
    Create `archive_hash` table which stores the MD5 hashes of the filenames of all 
    Archives that are uploaded to the Server.
    """
    async with aiosqlite.connect(config.CATAPULT_CACHE_DB) as conn:
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS archive_hash (
        md5 VARCHAR(255) PRIMARY KEY
        )
        ''')
        await conn.commit()
    return

async def archive_hash_exists(archive_md5: str) -> bool:
    """
    Returns True if hash exists in cache, else False.
    """
    async with aiosqlite.connect(config.CATAPULT_CACHE_DB) as conn, conn.execute('SELECT * FROM archive_hash WHERE md5 = ?', (archive_md5,)) as cursor:
            return await cursor.fetchone() is not None

async def insert_archive_hash(archive_md5: str):
    """
    Creates a hash entry, saying the corresponding Archive upload is cached.
    This action is performed upon completion of an Archive upload.
    Retry several times with exponential backoff in order to guarantee a write.
    """
    retry_count = 0
    while True:
        try:
            async with aiosqlite.connect(config.CATAPULT_CACHE_DB) as conn:
                await conn.execute('INSERT OR IGNORE INTO archive_hash VALUES (?)', (archive_md5,))
                await conn.commit()
                return
        except aiosqlite.core.sqlite3.OperationalError:
            time_to_sleep = 2 ** (retry_count + 1)
            asyncio.sleep(time_to_sleep)
            continue

async def drop_cache_table():
    async with aiosqlite.connect(config.CATAPULT_CACHE_DB) as conn:
        await conn.execute('DROP TABLE IF EXISTS archive_hash')
        await conn.commit()
    return

asyncio.run(create_cache_table())

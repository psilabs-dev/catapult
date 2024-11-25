from enum import Enum
import aiosqlite
import asyncio
import logging

from catapult.configuration import config

logger = logging.getLogger(__name__)

class ArchiveIntegrityStatus(Enum):
    
    ARCHIVE_OK = 0
    ARCHIVE_CORRUPTED = 1 # archive is corrupted
    ARCHIVE_PENDING = 2 # archive status unknown

def get_md5(row: aiosqlite.Row):
    return row[0]

def get_path(row: aiosqlite.Row):
    return row[1]

def get_integrity_status(row: aiosqlite.Row):
    return row[2]

def get_create_time_seconds(row: aiosqlite.Row):
    return row[3]

def get_modify_time_seconds(row: aiosqlite.Row):
    return row[4]

async def create_cache_table():
    """
    Create `archive_hash` table which stores the MD5 hashes of the filenames of all 
    Archives that are uploaded to the Server.
    """
    async with aiosqlite.connect(config.CATAPULT_CACHE_DB) as conn:
        await conn.execute('''
                           CREATE TABLE IF NOT EXISTS archive_hash (
                           md5 VARCHAR(255) PRIMARY KEY,
                           path TEXT,
                           integrity_status INTEGER,
                           create_time_seconds INTEGER,
                           modify_time_seconds INTEGER
                           )''')
        await conn.commit()
    return

async def get_archive(archive_md5: str):
    """
    Get archive stat from archive filename hash.
    """
    async with aiosqlite.connect(config.CATAPULT_CACHE_DB) as conn, conn.execute('SELECT * FROM archive_hash WHERE md5 = ?', (archive_md5,)) as cursor:
        return await cursor.fetchone()

async def get_archives_by_integrity_status(integrity_status: int):
    """
    Get all archives with given integrity status.
    """
    async with aiosqlite.connect(config.CATAPULT_CACHE_DB) as conn, conn.execute('SELECT * FROM archive_hash WHERE integrity_status = ?', (integrity_status,)) as cursor:
        return await cursor.fetchall()

async def insert_archive(archive_md5: str, path: str, integrity_status: int, create_time_seconds: int, modify_time_seconds: int):
    """
    Creates a hash entry, saying the corresponding Archive upload is cached.
    This action is performed upon completion of an Archive upload.
    Retry several times with exponential backoff in order to guarantee a write.
    """
    retry_count = 0
    while True:
        try:
            async with aiosqlite.connect(config.CATAPULT_CACHE_DB) as conn:
                await conn.execute('''
                                   INSERT OR IGNORE INTO archive_hash
                                   (md5, path, integrity_status, create_time_seconds, modify_time_seconds)
                                   VALUES (?, ?, ?, ?, ?)
                                   ON CONFLICT(md5) DO UPDATE SET
                                   path = excluded.path,
                                   integrity_status = excluded.integrity_status,
                                   create_time_seconds = excluded.create_time_seconds,
                                   modify_time_seconds = excluded.modify_time_seconds
''', (archive_md5, path, integrity_status, create_time_seconds, modify_time_seconds))
                await conn.commit()
                return
        except aiosqlite.core.sqlite3.OperationalError:
            # this may happen if database is locked; in this case, wait and try again.
            time_to_sleep = 2 ** (retry_count + 1)
            await asyncio.sleep(time_to_sleep)
            continue

async def delete_archive(archive_md5: str):
    """
    Delete archive record in database.
    """
    retry_count = 0
    while True:
        try:
            async with aiosqlite.connect(config.CATAPULT_CACHE_DB) as conn:
                await conn.execute('DELETE FROM archive_hash WHERE md5 = ?', (archive_md5,))
                await conn.commit()
                return
        except aiosqlite.core.sqlite3.OperationalError:
            # this may happen if database is locked; in this case, wait and try again.
            time_to_sleep = 2 ** (retry_count + 1)
            await asyncio.sleep(time_to_sleep)
            continue

async def drop_cache_table():
    async with aiosqlite.connect(config.CATAPULT_CACHE_DB) as conn:
        await conn.execute('DROP TABLE IF EXISTS archive_hash')
        await conn.commit()
    return

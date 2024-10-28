from contextlib import closing
import hashlib
import logging
from pathlib import Path
import sqlite3

from catapult.configuration import config
from catapult.utils import lrr_compute_id

logger = logging.getLogger(__name__)

def __calculate_md5_from_filepath(archive_path: str) -> str:
    return hashlib.md5(archive_path.encode('utf-8')).hexdigest()

def create_cache_table():
    """
    Create archive_hash table, which maps the archive to its corresponding LRR ID.
    """
    with closing(sqlite3.connect(config.CATAPULT_CACHE_DB)) as conn:
        with closing(conn.cursor()) as c:
            c.execute(
                '''
        CREATE TABLE IF NOT EXISTS archive_hash (
        md5 VARCHAR(255) PRIMARY KEY,
        archive_id VARCHAR(255)
        )
        '''
            )
        conn.commit()
    return

def get_cached_archive_id_else_compute(archive_path: str) -> str:
    """
    Get archive ID from cache if it exists (quick), otherwise compute it (slow) and add it to cache.
    """
    md5 = __calculate_md5_from_filepath(archive_path)
    with closing(sqlite3.connect(config.CATAPULT_CACHE_DB)) as conn:
        with closing(conn.cursor()) as c:
            c.execute(
                '''
        SELECT archive_id FROM archive_hash WHERE md5 = ?
        ''', (md5, )
            )
            result = c.fetchone()

    if result:
        return result[0]
    else:
        return create_archive_entry(archive_path, md5)

def create_archive_entry(archive_path: str, md5: str):
    """
    Create an archive row in cache with corresponding md5.
    """
    archive_id = lrr_compute_id(archive_path)
    filename = Path(archive_path).name
    with closing(sqlite3.connect(config.CATAPULT_CACHE_DB)) as conn:
        with closing(conn.cursor()) as c:
            c.execute('''INSERT OR IGNORE INTO archive_hash VALUES (?, ?)''', (md5, archive_id))
        conn.commit()
    return archive_id

def clear_cache():
    with closing(sqlite3.connect(config.CATAPULT_CACHE_DB)) as conn:
        with closing(conn.cursor()) as c:
            c.execute('DELETE FROM archive_hash')
        conn.commit()
    return

create_cache_table()

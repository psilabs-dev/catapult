import abc
import os
from pathlib import Path
import sqlite3
from typing import List

from ..models import ArchiveMetadata, ArchiveUploadRequest
from ..utils import find_all_archives

def __nh_archivist_build_metadata(archive_id: str, conn: sqlite3.Connection) -> ArchiveMetadata:
    """
    Build archive metadata for an nh ID using an nh archivist database.
    """
    # nhentai database archive extraction
    title = conn.cursor().execute(f"SELECT title_pretty FROM Hentai WHERE id={archive_id}").fetchone()[0]

    groups = conn.cursor().execute('''
        WITH groups AS (SELECT * FROM tag WHERE type = ?)
        SELECT groups.name FROM hentai_tag JOIN groups ON hentai_tag.tag_id = groups.id
        WHERE hentai_tag.hentai_id = ?
    ''', ('group', archive_id)).fetchall()
    artists = conn.cursor().execute('''
        WITH artists AS (SELECT * FROM tag WHERE type = ?)
        SELECT artists.name FROM hentai_tag JOIN artists ON hentai_tag.tag_id = artists.id
        WHERE hentai_tag.hentai_id = ?
    ''', ('artist', archive_id)).fetchall()

    tags = conn.cursor().execute('''
        WITH true_tags AS (SELECT * FROM tag WHERE type = ?)
        SELECT true_tags.name FROM hentai_tag JOIN true_tags ON hentai_tag.tag_id = true_tags.id
        WHERE hentai_tag.hentai_id = ?
    ''', ('tag', archive_id)).fetchall()
    characters = conn.cursor().execute('''
        WITH characters AS (SELECT * FROM tag WHERE type = ?)
        SELECT characters.name FROM hentai_tag JOIN characters ON hentai_tag.tag_id = characters.id
        WHERE hentai_tag.hentai_id = ?
    ''', ('character', archive_id)).fetchall()
    parodies = conn.cursor().execute('''
        WITH parodies AS (SELECT * FROM tag WHERE type = ?)
        SELECT parodies.name FROM hentai_tag JOIN parodies ON hentai_tag.tag_id = parodies.id
        WHERE hentai_tag.hentai_id = ?
    ''', ('parody', archive_id)).fetchall()
    languages = conn.cursor().execute('''
        WITH languages AS (SELECT * FROM tag WHERE type = ?)
        SELECT languages.name FROM hentai_tag JOIN languages ON hentai_tag.tag_id = languages.id
        WHERE hentai_tag.hentai_id = ?
    ''', ('language', archive_id)).fetchall()
    categories = conn.cursor().execute('''
        WITH categories AS (SELECT * FROM tag WHERE type = ?)
        SELECT categories.name FROM hentai_tag JOIN categories ON hentai_tag.tag_id = categories.id
        WHERE hentai_tag.hentai_id = ?
    ''', ('category', archive_id)).fetchall()

    # assemble tags by adding them to the tags list.
    tag_list = list()
    for tag in tags:
        tag_list.append(tag[0])
    for character in characters:
        tag_list.append(f"character:{character[0]}")
    for parody in parodies:
        tag_list.append(f"parody:{parody[0]}")
    for language in languages:
        tag_list.append(f"language:{language[0]}")
    for category in categories:
        tag_list.append(f"category:{category[0]}")
    for artist in artists:
        tag_list.append(f"artist:{artist[0]}")
    for group in groups:
        tag_list.append(f"group:{group[0]}")

    # add source
    tag_list.append(f"source:nhentai.net/g/{archive_id}")

    # validate tag list
    for item in tag_list:
        assert ',' not in item, f'Item {item} contains comma.'

    final_tag_string = ",".join(tag_list)

    metadata = ArchiveMetadata(title=title, tags=final_tag_string)
    return metadata

def is_available(db: str, contents_directory: str) -> bool:
    """
    Check if nh archivist archives are available for upload.
    """
    if not Path(db).exists():
        return False
    if not Path(contents_directory).exists():
        return False
    try:
        conn = sqlite3.connect(db)
        conn.close()
        return True
    except:
        return False

def build_upload_requests(db: str, contents_directory: str) -> List[ArchiveUploadRequest]:
    """
    Build upload requests for nh archivist.
    """
    all_archive_paths = find_all_archives(contents_directory)
    upload_requests: List[ArchiveUploadRequest]=list()
    conn = sqlite3.connect(db)
    for archive_file_path in all_archive_paths:
        archive_file = os.path.split(archive_file_path)[1]
        archive_id = archive_file.split()[0]
        metadata = __nh_archivist_build_metadata(archive_id, conn)
        upload_request = ArchiveUploadRequest(archive_file_path, archive_file, metadata)
        upload_requests.append(upload_request)
    conn.close()
    return upload_requests

import abc
from pathlib import Path
import aiosqlite

from catapult.models import ArchiveMetadata

class MetadataClient(abc.ABC):
    """
    Metadata interface for a downloader or metadata server.
    """

    @abc.abstractmethod
    async def get_metadata_from_id(self, *args, **kwargs) -> ArchiveMetadata:
        ...

class NhentaiArchivistMetadataClient(MetadataClient):
    """
    Metadata client for [Nhentai Archivist](https://github.com/9-FS/nhentai_archivist.git)
    """

    def __init__(self, db: Path):
        self.db = db

    async def get_metadata_from_id(self, nhentai_id: str) -> ArchiveMetadata:
        """
        Get metadata from the nhentai_archivist database, given the nhentai ID.
        """
        metadata = ArchiveMetadata()
        async with aiosqlite.connect(self.db) as conn, conn.cursor() as cursor:
            titles = (await cursor.execute("SELECT title_pretty FROM Hentai WHERE id=?", (nhentai_id,))).fetchone()
            title = titles[0] if titles else None
            groups = (await cursor.execute('''
                WITH groups AS (SELECT * FROM tag WHERE type = ?)
                SELECT groups.name FROM hentai_tag JOIN groups ON hentai_tag.tag_id = groups.id
                WHERE hentai_tag.hentai_id = ?
            ''', ('group', nhentai_id))).fetchall()
            artists = (await cursor.execute('''
                WITH artists AS (SELECT * FROM tag WHERE type = ?)
                SELECT artists.name FROM hentai_tag JOIN artists ON hentai_tag.tag_id = artists.id
                WHERE hentai_tag.hentai_id = ?
            ''', ('artist', nhentai_id))).fetchall()
            tags = (await cursor.execute('''
                WITH true_tags AS (SELECT * FROM tag WHERE type = ?)
                SELECT true_tags.name FROM hentai_tag JOIN true_tags ON hentai_tag.tag_id = true_tags.id
                WHERE hentai_tag.hentai_id = ?
            ''', ('tag', nhentai_id))).fetchall()
            characters = (await cursor.execute('''
                WITH characters AS (SELECT * FROM tag WHERE type = ?)
                SELECT characters.name FROM hentai_tag JOIN characters ON hentai_tag.tag_id = characters.id
                WHERE hentai_tag.hentai_id = ?
            ''', ('character', nhentai_id))).fetchall()
            parodies = (await cursor.execute('''
                WITH parodies AS (SELECT * FROM tag WHERE type = ?)
                SELECT parodies.name FROM hentai_tag JOIN parodies ON hentai_tag.tag_id = parodies.id
                WHERE hentai_tag.hentai_id = ?
            ''', ('parody', nhentai_id))).fetchall()
            languages = (await cursor.execute('''
                WITH languages AS (SELECT * FROM tag WHERE type = ?)
                SELECT languages.name FROM hentai_tag JOIN languages ON hentai_tag.tag_id = languages.id
                WHERE hentai_tag.hentai_id = ?
            ''', ('language', nhentai_id))).fetchall()
            categories = (await cursor.execute('''
                WITH categories AS (SELECT * FROM tag WHERE type = ?)
                SELECT categories.name FROM hentai_tag JOIN categories ON hentai_tag.tag_id = categories.id
                WHERE hentai_tag.hentai_id = ?
            ''', ('category', nhentai_id))).fetchall()

        tag_list = []
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
        
        tag_list.append(f"source:nhentai.net/g/{nhentai_id}")
        # validate tag list
        for item in tag_list:
            assert ',' not in item, f'Item {item} contains comma.'

        final_tag_string = ",".join(tag_list)

        metadata = ArchiveMetadata(title=title, tags=final_tag_string)
        return metadata

class PixivUtil2MetadataClient(MetadataClient):
    """
    Metadata client for [PixivUtil2](https://github.com/Nandaka/PixivUtil2.git)
    """
    
    def __init__(self, db: Path) -> None:
        self.db = db

    async def get_metadata_from_id(self, pixiv_id: int) -> ArchiveMetadata:
        """
        TODO: Get metadata from PixivUtil2 database, given the Pixiv illust ID.
        """
        raise NotImplementedError("PixivUtil2 metadata fetcher is not implemented!")

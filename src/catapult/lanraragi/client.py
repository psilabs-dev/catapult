import io
import aiohttp
import aiohttp.client_exceptions
import logging
from pathlib import Path
from typing import overload, Union

from catapult.lanraragi.models import LanraragiResponse
from catapult.lanraragi.utils import build_auth_header

logger = logging.getLogger(__name__)

class LRRClient:
    """
    Basic, asynchronous LANraragi HTTP client.

    API documentation: https://sugoi.gitbook.io/lanraragi/api-documentation/getting-started
    """

    def __init__(
            self,
            lrr_host: str=None,
            lrr_api_key: str=None,
    ):
        if not lrr_host:
            lrr_host = "http://localhost:3000"
        self.lrr_host = lrr_host

        if not self.lrr_host:
            raise ValueError("LRR host cannot be empty.")

        lrr_headers = {}
        if lrr_api_key:
            lrr_headers["Authorization"] = build_auth_header(lrr_api_key)
        self.headers = lrr_headers

    @classmethod
    def default_client(cls) -> "LRRClient":
        """
        Return default LANraragi client based on catapult credentials.
        """
        from catapult.configuration import config
        return LRRClient(lrr_host=config.lrr_host, lrr_api_key=config.lrr_api_key)

    # ---- START ARCHIVE API ----
    # https://sugoi.gitbook.io/lanraragi/api-documentation/archive-api
    async def get_all_archives(self) -> LanraragiResponse:
        """
        `GET /api/archives`
        """
        url = f"{self.lrr_host}/api/archives"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.get(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            response.data = await async_response.json()
            return response

    async def get_untagged_archives(self) -> LanraragiResponse:
        """
        `GET /api/archives/untagged`
        """
        url = f"{self.lrr_host}/api/archives/untagged"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.get(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            response.data = await async_response.json()
            return response

    async def get_archive_metadata(self, archive_id: str) -> LanraragiResponse:
        """
        `GET /api/archives/:id/metadata`
        """
        url = f"{self.lrr_host}/api/archives/{archive_id}/metadata"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.get(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            data = await async_response.json()
            try:
                for key in data:
                    response.__setattr__(key, data[key])
            except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                logger.error("[get_archive_metadata] Failed to decode JSON response: ", content_type_error)
            return response

    async def download_archive(self, archive_id: str) -> LanraragiResponse:
        """
        `GET /api/archives/:id/download`
        """
        url = f"{self.lrr_host}/api/archives/{archive_id}/download"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.get(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            buffer = io.BytesIO()
            if response.success:
                while True:
                    chunk = await async_response.content.read(1024)
                    if not chunk:
                        break
                    buffer.write(chunk)
                buffer.seek(0)
                response.data = buffer
            else:
                try:
                    data = await async_response.json()
                    for key in data:
                        response.__setattr__(key, data[key])
                except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                    logger.error("[download_archive] Failed to decode JSON response: ", content_type_error)
            return response

    @overload
    async def upload_archive(
        self, archive_path: str, archive_filename: str, archive_checksum: str=None, 
        title: str=None, tags: str=None, summary: str=None, category_id: str=None
    ) -> LanraragiResponse:
        ...
    
    @overload
    async def upload_archive(
        self, archive_path: Path, archive_filename: str, archive_checksum: str=None, 
        title: str=None, tags: str=None, summary: str=None, category_id: str=None
    ) -> LanraragiResponse:
        ...

    @overload
    async def upload_archive(
        self, archive_io: io.IOBase, archive_filename: str, archive_checksum: str=None, 
        title: str=None, tags: str=None, summary: str=None, category_id: str=None
    ) -> LanraragiResponse:
        ...

    async def upload_archive(
            self, archive: Union[Path, str, io.IOBase], archive_filename: str, archive_checksum: str=None,
            title: str=None, tags: str=None, summary: str=None, category_id: str=None,
    ) -> LanraragiResponse:
        """
        `PUT /api/archives/upload`
        """
        if isinstance(archive, (Path, str)):
            with open(archive, 'rb') as archive_br:
                return self.upload_archive(
                    archive_br, archive_filename, archive_checksum=archive_checksum, 
                    title=title, tags=tags, summary=summary, category_id=category_id
                )
        elif isinstance(archive, io.IOBase):
            url = f"{self.lrr_host}/api/archives/upload"
            response = LanraragiResponse()
            form_data = aiohttp.FormData(quote_fields=False)
            form_data.add_field('file', archive, filename=archive_filename, content_type='application/octet-stream')
            if archive_checksum:
                form_data.add_field("file_checksum", archive_checksum)
            if title:
                form_data.add_field('title', title)
            if tags:
                form_data.add_field('tags', tags)
            if summary:
                form_data.add_field('summary', summary)
            if category_id:
                form_data.add_field('category_id', category_id)
            async with aiohttp.ClientSession() as session, session.put(url=url, data=form_data, headers=self.headers) as async_response:
                response.status_code = async_response.status
                response.success = 1 if async_response.status == 200 else 0
                try:
                    data = await async_response.json()
                    for key in data:
                        response.__setattr__(key, data[key])
                except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                    logger.error("[upload_archive] Failed to decode JSON response: ", content_type_error)
                    response.error = async_response.text
                return response
        else:
            raise TypeError(f"Unsupported upload content type (must be Path, str or IOBase): {type(archive)}")

    async def update_archive(self, archive_id: str, title: str=None, tags: str=None, summary: str=None):
        """
        `PUT /api/archives/:id/metadata`
        """
        if isinstance(tags, str):
            url = f"{self.lrr_host}/api/archives/{archive_id}/metadata"
            response = LanraragiResponse()
            form_data = aiohttp.FormData(quote_fields=False)
            if title:
                form_data.add_field('title', title)
            if tags:
                form_data.add_field('tags', tags)
            if summary:
                form_data.add_field('summary', summary)
            async with aiohttp.ClientSession() as session, session.put(url=url, headers=self.headers, data=form_data) as async_response:
                response.status_code = async_response.status
                response.success = 1 if async_response.status == 200 else 0
                try:
                    data = await async_response.json()
                    for key in data:
                        response.__setattr__(key, data[key])
                except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                    logger.error("[update_archive] Failed to update Archive: ", content_type_error)
                    response.error = async_response.text
                return response
        else:
            raise TypeError(f"Unsupported type for tags: {type(tags)}")

    async def delete_archive(self, archive_id: str) -> LanraragiResponse:
        """
        `DELETE /api/archives/:id`
        """
        url = f"{self.lrr_host}/api/archives/{archive_id}"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.delete(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            data = await async_response.json()
            try:
                data = await async_response.json()
                for key in data:
                    response.__setattr__(key, data[key])
            except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                logger.error("[delete_archive] Failed to decode JSON response: ", content_type_error)
            return response

    # ---- END ARCHIVE API ----

    # ---- START DATABASE API ----
    async def clean_database(self) -> LanraragiResponse:
        """
        `POST /api/database/clean`
        """
        url = f"{self.lrr_host}/api/database/clean"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.post(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            data = await async_response.json()
            try:
                for key in data:
                    response.__setattr__(key, data[key])
            except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                logger.error("[clean_database] Failed to clean database: ", content_type_error)
            return response

    async def drop_database(self) -> LanraragiResponse:
        """
        `POST /api/database/drop`
        """
        url = f"{self.lrr_host}/api/database/drop"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.post(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            data = await async_response.json()
            try:
                for key in data:
                    response.__setattr__(key, data[key])
            except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                logger.error("[drop_database] Failed to drop database: ", content_type_error)
            return response

    async def get_backup(self) -> LanraragiResponse:
        """
        `GET /api/database/backup`
        """
        url = f"{self.lrr_host}/api/database/backup"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.get(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            response.data = await async_response.json()
            return response

    async def clear_new_all(self) -> LanraragiResponse:
        """
        `DELETE /api/database/isnew`
        """
        url = f"{self.lrr_host}/api/database/isnew"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.delete(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            data = await async_response.json()
            try:
                for key in data:
                    response.__setattr__(key, data[key])
            except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                logger.error("[clear_new_all] Failed to clear new flag on Archives: ", content_type_error)
            return response

    # ---- END DATABASE API ----

    # ---- START SHINOBU API ----
    # https://sugoi.gitbook.io/lanraragi/api-documentation/shinobu-api
    async def get_shinobu_status(self) -> LanraragiResponse:
        """
        `GET /api/shinobu`
        """
        url = f"{self.lrr_host}/api/shinobu"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.get(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            try:
                data = await async_response.json()
                for key in data:
                    response.__setattr__(key, data[key])
            except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                logger.error("[get_shinobu_status] Failed to decode JSON response: ", content_type_error)
            return response

    async def stop_shinobu(self) -> LanraragiResponse:
        """
        `POST /api/shinobu/stop`
        """
        url = f"{self.lrr_host}/api/shinobu/stop"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.post(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            try:
                data = await async_response.json()
                for key in data:
                    response.__setattr__(key, data[key])
            except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                logger.error("[shinobu_stop] Failed to stop shinobu: ", content_type_error)
            return response

    async def restart_shinobu(self) -> LanraragiResponse:
        """
        `POST /api/shinobu/restart`
        """
        url = f"{self.lrr_host}/api/shinobu/restart"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.post(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            try:
                data = await async_response.json()
                for key in data:
                    response.__setattr__(key, data[key])
            except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                logger.error("[shinobu_restart] Failed to restart shinobu: ", content_type_error)
            return response

    # ---- END SHINOBU API ----

    # ---- START MISC API ----
    # https://sugoi.gitbook.io/lanraragi/api-documentation/miscellaneous-other-api
    async def get_server_info(self) -> LanraragiResponse:
        """
        `GET /api/info`
        """
        url = f"{self.lrr_host}/api/info"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session, session.get(url=url, headers=self.headers) as async_response:
            response.status_code = async_response.status
            response.success = 1 if async_response.status == 200 else 0
            try:
                data = await async_response.json()
                for key in data:
                    response.__setattr__(key, data[key])
            except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                logger.error("[get_server_info] Failed to decode JSON response: ", content_type_error)
            return response

    # ---- END MISC API ----

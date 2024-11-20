import io
import aiohttp
import aiohttp.client_exceptions
import logging
from pathlib import Path
from typing import overload

from catapult.lanraragi.models import LanraragiResponse
from catapult.lanraragi.utils import compute_sha1, build_auth_header

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

        lrr_headers = dict()
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
    async def get_archive_metadata(self, archive_id: str):
        """
        `GET /api/archives/:id/metadata`
        """
        url = f"{self.lrr_host}/api/archives/{archive_id}/metadata"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=self.headers) as async_response:
                response.status_code = async_response.status
                response.success = 1 if async_response.status == 200 else 0
                data = await async_response.json()
                try:
                    data = await async_response.json()
                    for key in data:
                        response.__setattr__(key, data[key])
                except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                    logger.error("[get_archive_metadata] Failed to decode JSON response: ", content_type_error)
                return response

    async def download_archive(self, archive_id: str):
        """
        `GET /api/archives/:id/download`
        """
        url = f"{self.lrr_host}/api/archives/{archive_id}/download"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=self.headers) as async_response:
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

    async def upload_archive(
            self,
            archive_br: io.IOBase,
            archive_filename: str,
            archive_checksum: str=None,
            title: str=None,
            tags: str=None,
            summary: str=None,
            category_id: str=None,
    ):
        """
        `PUT /api/archives/upload`
        """
        url = f"{self.lrr_host}/api/archives/upload"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session:
            files = {'file': (archive_filename, archive_br)}
            form_data = aiohttp.FormData(quote_fields=False)
            form_data.add_field('file', archive_br, filename=archive_filename, content_type='application/octet-stream')
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
            async with session.put(url=url, data=form_data, headers=self.headers) as async_response:
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

    async def delete_archive(self, archive_id: str):
        """
        `DELETE /api/archives/:id`
        """
        url = f"{self.lrr_host}/api/archives/{archive_id}"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session:
            async with session.delete(url=url, headers=self.headers) as async_response:
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

    # ---- START SHINOBU API ----
    # https://sugoi.gitbook.io/lanraragi/api-documentation/shinobu-api
    async def get_shinobu_status(self):
        """
        `GET /api/shinobu`
        """
        url = f"{self.lrr_host}/api/shinobu"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=self.headers) as async_response:
                response.status_code = async_response.status
                response.success = 1 if async_response.status == 200 else 0
                try:
                    data = await async_response.json()
                    for key in data:
                        response.__setattr__(key, data[key])
                except aiohttp.client_exceptions.ContentTypeError as content_type_error:
                    logger.error("[get_shinobu_status] Failed to decode JSON response: ", content_type_error)
                return response

    # ---- END SHINOBU API ----

    # ---- START MISC API ----
    # https://sugoi.gitbook.io/lanraragi/api-documentation/miscellaneous-other-api
    async def get_server_info(self):
        """
        `GET /api/info`
        """
        url = f"{self.lrr_host}/api/info"
        response = LanraragiResponse()
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=self.headers) as async_response:
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

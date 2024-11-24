# Catapult

An async LANraragi file upload toolkit.

## Quickstart
Install from source:
```sh
pip install .
```
Verify installation:
```sh
catapult version
```
Configure default settings, which are saved at `~/.config/catapult/catapult.toml`.
```sh
catapult configure
# LANraragi Host [http://lanraragi]: 
# LANraragi API key [a***y]: 
```
> You can overwrite these settings using `catapult configure`.

Confirm that `catapult` can reach the server:
```sh
catapult check
# success; otherwise throws some error
```
Upload an Archive to the LANraragi server:
```sh
catapult upload /path/to/Archive
# Uploaded /path/to/Archive to server.
```
You can add metadata or change/override the LANraragi url/API key.
```sh
catapult upload /path/to/Archive --title some-title --tags "key:value" --lrr-host http://lanraragi2
```
> See the [CLI](src/catapult/cli.py) for more details.

### Supporting Commands

Validate whether a file is a valid, uploadable Archive:
```sh
catapult validate Dockerfile
# INVALID_EXTENSION - No file extension.
catapult validate tests/resources/fake.cbz
# INVALID_MIME_TYPE - Invalid signature: 5468697320697320
```

### Multi-Archive Uploads

Upload all Archives from a folder.
```sh
catapult multi-upload from-folder --folders /path/to/archives
# starts uploading all archives found in /path/to/archives...
```

Upload all Archives downloaded from [nhentai_archivist](https://github.com/9-FS/nhentai_archivist.git).
```sh
catapult multi-upload from-nhentai-archivist --folders /path/to/nhentai-archives --db /path/to/db
```
With (environment) configuration, you can just run `catapult multi-upload from-folder` or `catapult multi-upload from-nhentai-archivist`.

## Configuration
There are several ways to configure `catapult`,

- file configuration through `~/.config/catapult/catapult.toml`,
- environment variable configuration,
- command line argument configuration.

Assuming configurations are nonempty; command line arguments will *always* override environment variables, which will *always* override file configurations.

### Environment Variables

Application-specific environment variables:

- `LRR_HOST`: absolute URL to the LANraragi server.
- `LRR_API_KEY`: API key for the LANraragi server.

Multi-upload from folder:
- `MULTI_UPLOAD_FOLDERS`: list of folders of Archives (joined by ";") that `catapult` should upload from.

Nhentai Archivist
- `MULTI_UPLOAD_NH_ARCHIVIST_DB`: path to the `nhentai_archivist` sqlite database.
- `MULTI_UPLOAD_NH_ARCHIVIST_FOLDERS`: list of folders of Archives (joined by ";") that `catapult` should upload from with metadata from corresponding database.

PixivUtil2
- `MULTI_UPLOAD_PIXIVUTIL2_DB`: path to the PixivUtil2 sqlite database.
- `MULTI_UPLOAD_PIXIVUTIL_FOLDERS`: list of folders of Archives/artworks (joined by ";") that `catapult` should upload from with metadata from corresponding database.

## Client Library
Example of uploading an Archive using `LRRClient`:
```python
import asyncio
from catapult.lanraragi import LRRClient

client = LRRClient.default_client()

archive_path = "archive-to-upload.zip"
archive_name = archive_path

response = asyncio.run(client.upload_archive(archive_path, archive_name))
print(response)
```

## Satellite Server
`satellite` is an HTTP server that attaches to the contents of LANraragi and performs two auxiliary tasks:

1. Identifying (and removing) corrupted archives;
1. Updating downloader-specific metadata using `catapult`.

Start a `satellite` with uvicorn:
```sh
pip install .[satellite]
uvicorn catapult.satellite:app --host 0.0.0.0 --port 8000
```

**Updating nhentai_archivist metadata**: Make a POST request to update nhentai_archivist metadata:
```sh
curl -X POST http://localhost:8000/api/metadata/nhentai-archivist
```

## Development

Run integration tests against a LANraragi docker instance. This setup script will create an LRR instance, inject it with an API key, and apply permissions.
```sh
./integration/setup.sh
```
> **Note**: This instance will have the API key `lanraragi`. 

Upload an Archive to this local instance:
```sh
catapult upload /path/to/Archive --lrr-host http://localhost:3000 --lrr-api-key lanraragi
```

Teardown instances when done:
```sh
./integration/teardown.sh
```
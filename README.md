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
catapult multi-upload from-folder --folder /path/to/archives
# starts uploading all archives found in /path/to/archives...
```

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
- `MULTI_UPLOAD_FOLDER`: path to the folder to upload Archives from.

## Client Library
Example of uploading an Archive using `LRRClient`:
```python
import asyncio
from catapult.lanraragi import LRRClient

client = LRRClient.default_client()

archive_path = "archive-to-upload.zip"
archive_name = archive_path
with open(archive_path, 'rb') as archive_br:
    response = asyncio.run(client.upload_archive(
        archive_br, 
        archive_name, 
    ))

print(response)
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
# Catapult

A LANraragi file upload toolkit.

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
Upload an Archive file to the LANraragi server:
```sh
catapult upload /path/to/Archive.zip
# Uploaded /path/to/Archive.zip to server as Archive.zip.
```
This extends to folders of images; `catapult` will create a zip file `ArchiveFolder.zip` and upload this to the server:
```sh
catapult upload /path/to/ArchiveFolder
# Uploaded ArchiveFolder.zip to server
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
# (False, 'cannot have no extension')
catapult validate tests/resources/fake.cbz
# (False, 'failed the MIME test')
```

### Multi-Archive Uploads

Upload all Archives from a folder.
```sh
catapult multi-upload from-folder --folder /path/to/archives
# starts uploading all archives found in /path/to/archives...
```
Upload all Archives from an nhentai_archivist instance.
```sh
catapult multi-upload from-nhentai-archivist --db /path/to/db --folder /path/to/downloads
# starts uploading downloaded archives found in /path/to/downloads with metadata from /path/to/db...
```
`catapult` supports multithreading for uploads and multiprocessing for compute-intensive hash checks.

## Worker Mode
"Worker mode" involves running `catapult` in the background as a Celery worker consuming requests from RabbitMQ. In order to run worker mode, a RabbitMQ instance is required.

Install worker mode with its dependencies:
```sh
pip install ".[worker]"
```
Run the worker.
```sh
celery -A catapult.tasks worker --loglevel=INFO
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

Worker-specific environment variables:
- `CELERY_BROKER_URL`: e.g. `amqp://localhost:5672`

Multi-upload from folder:
- `MULTI_UPLOAD_FOLDER`: path to the folder to upload Archives from.

Multi-upload from Nhentai Archivist:
- `MULTI_UPLOAD_NH_ARCHIVIST_DB`: path to the nhentai archivist database.
- `MULTI_UPLOAD_NH_ARCHIVIST_CONTENTS`: path to the nhentai archivist downloaded contents directory.

Multi-upload from PixivUtil2:
- `MULTI_UPLOAD_PIXIVUTIL_DB`: path to PixivUtil2 database.
- `MULTI_UPLOAD_PIXIVUTIL_CONTENT_DIR`: path to the PixivUtil2 downloads directory.

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
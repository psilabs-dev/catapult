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
# (False, 'cannot have no extension')
catapult validate tests/resources/fake.cbz
# (False, 'failed the MIME test')
```

### Multi-Archive Uploads

Upload all Archives from a folder.
```sh
catapult multi-upload from-folder /path/to/archives
# starts uploading all archives found in /path/to/archives...
```
Upload all Archives from an nhentai_archivist instance.
```sh
catapult multi-upload from-nhentai-archivist /path/to/db /path/to/downloads
# starts uploading downloaded archives found in /path/to/downloads with metadata from /path/to/db...
```
`catapult` supports multithreading for uploads and multiprocessing for compute-intensive hash checks.

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

Multi-upload from Nhentai Archivist:
- `MULTI_UPLOAD_NH_ARCHIVIST_DB`: path to the nhentai archivist database.
- `MULTI_UPLOAD_NH_ARCHIVIST_CONTENTS`: path to the nhentai archivist downloaded contents directory.

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
./integrations/teardown.sh
```
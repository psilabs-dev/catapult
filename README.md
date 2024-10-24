# Catapult

A LANraragi file upload toolkit.

## Installation guide

Build Docker image
```sh
docker build -t catapult .
```

Install from source:
```sh
pip install .
```
Verify installation:
```sh
catapult version
```
Test connection to a server:
```sh
catapult check
# success
```

## Usage
Configure `catapult` default settings, which are saved at `~/.config/catapult/catapult.toml`.
```sh
catapult configure
# LANraragi Host [http://lanraragi]: 
# LANraragi API key [a***1]: 
```

Validate whether a file is a valid, uploadable Archive:
```sh
catapult validate Dockerfile
# (False, 'cannot have no extension')
catapult validate tests/resources/fake.cbz
# (False, 'failed the MIME test')
```

Upload a file to the configured LANraragi server:
```sh
catapult upload /path/to/archive
```

Upload all Archives from a folder.
```sh
catapult plugin folder /path/to/archives
# starts uploading all archives found in /path/to/archives...
```
Upload all Archives from an nhentai_archivist instance.
```sh
catapult plugin nhentai-archivist /path/to/db /path/to/downloads
# starts uploading downloaded archives found in /path/to/downloads with metadata from /path/to/db...
```

## Configuration
There are several ways to configure `catapult`,

- file configuration through `~/.config/catapult/catapult.toml`,
- environment variable configuration,
- command line argument configuration.

Assuming configurations are nonempty; command line arguments will *always* override environment variables, which will *always* override file configurations.

### Environment Variables

`LRR_HOST`: absolute URL to the LANraragi server.

`LRR_API_KEY`: API key for the LANraragi server.

## Development

Run integration tests against a LANraragi docker instance. Setup instances, add API key and configure permissions with compose.
```sh
./integration/setup.sh
```
This instance will have the API key `lanraragi`.

Teardown instances:
```sh
./integrations/teardown.sh
```
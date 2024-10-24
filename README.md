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

Validate whether a file can be uploaded:
```sh
catapult validate Dockerfile
# (False, 'cannot have no extension')
```

Upload a file to the configured LANraragi server:
```sh
catapult upload ...
```

Upload archives from an nhentai_archivist instance.
```sh
catapult plugin nhentai-archivist path-to-db path-to-downloads
# starts uploading downloaded archives...
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

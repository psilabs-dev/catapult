import argparse
from collections import OrderedDict
import os
from pathlib import Path
import toml

from .controller import upload_archive_to_server, validate_archive_file
from .models import ArchiveMetadata
from .utils import get_version, mask_string

def main():
    parser = argparse.ArgumentParser("catapult command line")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # version subparser
    version_subparser = subparsers.add_parser("version", help="Get version.")

    # configure subparser
    configure_subparser = subparsers.add_parser("configure", help="Configure catapult settings.")

    # validate subparser
    validate_subparser = subparsers.add_parser("validate", help="Validate a file.")
    validate_subparser.add_argument("filepath", help="Path to file to validate.")

    # upload subparser
    upload_subparser = subparsers.add_parser("upload", help="Upload a file to the server.")
    upload_subparser.add_argument("filepath", help="Path to file to upload.")
    upload_subparser.add_argument('--title', type=str, help='Title of the archive.')
    upload_subparser.add_argument('--tags', type=str, help='Tags of the archive.')
    upload_subparser.add_argument('--summary', type=str, help='Summary of the archive.')
    upload_subparser.add_argument('--category_id', type=int, help='Category ID of the archive.')
    upload_subparser.add_argument('--lrr-host', type=str, help='URL of the server.')
    upload_subparser.add_argument('--lrr-api-key', type=str, help='API key of the server.')

    args = parser.parse_args()
    command = args.command

    if command == "version":
        print(get_version())
    elif command == "configure":
        # create configuration directory.
        from getpass import getpass
        import stat

        home = Path.home()
        config_dir = home / ".config" / "catapult"
        config_file = config_dir / "catapult.toml"
        config_dir.mkdir(parents=True, exist_ok=True)

        if config_file.exists():
            with open(config_file, 'r') as reader:
                curr_configuration = toml.load(reader)
                curr_lrr_host = curr_configuration['default']['lrr_host']
                curr_api_key = curr_configuration['default']['lrr_api_key']

            lrr_host = input(f"LANraragi Host [{curr_lrr_host}]: ")
            lrr_api_key = getpass(f"LANraragi API key [{mask_string(curr_api_key)}]: ")
            if not lrr_host:
                lrr_host = curr_lrr_host
            if not lrr_api_key:
                lrr_api_key = curr_api_key
        else:
            lrr_host = input(f"LANraragi Host: ")
            lrr_api_key = getpass(f"LANraragi API key: ")

        if lrr_host or lrr_api_key:
            configuration = OrderedDict([
                ('default', OrderedDict([
                    ('lrr_host', lrr_host),
                    ('lrr_api_key', lrr_api_key),
                ]))
            ])
            with open(config_file, 'w') as writer:
                toml.dump(configuration, writer)
            config_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
            return 0
        else:
            return 0

    elif command == "validate":
        file_path = args.filepath
        print(validate_archive_file(file_path))
    elif command == "upload":
        file_path = args.filepath
        title = args.title
        tags = args.tags
        summary = args.summary
        category_id = args.category_id
        arg_lrr_host = args.lrr_host
        arg_lrr_api_key = args.lrr_api_key

        metadata = ArchiveMetadata(
            title=title,
            tags=tags,
            summary=summary,
            category_id=category_id
        )

        file_is_valid, message = validate_archive_file(file_path)
        if not file_is_valid:
            print(f"File {file_path} is not valid. Reason: {message}.")
            return 1

        # get configurations
        lrr_host: str
        lrr_api_key: str

        # get default configuration if available
        home = Path.home()
        config_dir = home / ".config" / "catapult"
        config_file = config_dir / "catapult.toml"
        if config_file.exists():
            with open(config_file, 'r') as reader:
                configuration = toml.load(reader)
                lrr_host = configuration['default']['lrr_host']
                lrr_api_key = configuration['default']['lrr_api_key']

        # override with environment variables
        lrr_host = os.getenv('LRR_HOST', lrr_host)
        lrr_api_key = os.getenv('LRR_API_KEY', lrr_api_key)

        # override with command arguments if applicable
        if arg_lrr_host:
            lrr_host = arg_lrr_host
        if arg_lrr_api_key:
            lrr_api_key = arg_lrr_api_key

        # validation
        if not lrr_host:
            print("No LANraragi host!")
            return 1
        if not lrr_host.startswith('http://') and not lrr_host.startswith('https://'):
            print("No connection adapters found!")
            return 1
        if not Path(file_path).exists():
            print(f"File {file_path} does not exist!")
            return 1

        response = upload_archive_to_server(file_path, metadata, lrr_host, lrr_api_key=lrr_api_key)
        status_code = response.status_code
        if status_code == 200:
            print(f"Uploaded {file_path} to server.")
            return 0
        else:
            error_message = response.json()['error']
            print(f"Failed to upload file (status code {status_code}): {error_message}")
            return 1

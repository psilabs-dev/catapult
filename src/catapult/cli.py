import argparse
from collections import OrderedDict
import logging
import os
from pathlib import Path
import toml

from .constants import CATAPULT_HOME, CATAPULT_CONFIG_FILE
from .controller import start_folder_upload_process, start_nhentai_archivist_upload_process, test_connection, upload_archive_to_server, validate_archive_file
from .models import ArchiveMetadata
from .utils import get_version, mask_string

def main():

    global CATAPULT_CONFIG_FILE, CATAPULT_HOME

    parser = argparse.ArgumentParser("catapult command line")
    log_level = parser.add_argument('--log-level', type=str, default='warning', help='Set log level.')

    subparsers = parser.add_subparsers(dest="command", required=True)

    # version subparser
    version_subparser = subparsers.add_parser("version", help="Get version.")

    # configure subparser
    configure_subparser = subparsers.add_parser("configure", help="Configure catapult settings.")

    # check subparser
    check_subparser = subparsers.add_parser("check", help="Check connection to server instance.")
    check_subparser.add_argument('--lrr-host', type=str, help='URL of the server.')
    check_subparser.add_argument('--lrr-api-key', type=str, help='API key of the server.')

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

    # jobs subparser
    plugins_subparser = subparsers.add_parser("plugin", help="Plugins command")
    plugins_subparsers = plugins_subparser.add_subparsers(dest='plugin_command')
    folder_parser = plugins_subparsers.add_parser('folder', help="Upload archives from folder.")
    folder_parser.add_argument('folder', type=str, help='Path to nhentai archivist contents folder.')
    folder_parser.add_argument('--lrr-host', type=str, help='URL of the server.')
    folder_parser.add_argument('--lrr-api-key', type=str, help='API key of the server.')
    folder_parser.add_argument('--threading', action='store_true', help='Use multithreading.')
    folder_parser.add_argument('--multiprocessing', action='store_true', help='Use multiprocessing.')
    folder_parser.add_argument('--remove-duplicates', action='store_true', help='Remove duplicates before uploading.')
    nh_parser = plugins_subparsers.add_parser('nhentai-archivist', help="Nhentai archivist upload jobs.")
    nh_parser.add_argument('db', type=str, help='Path to nhentai archivist database.')
    nh_parser.add_argument('folder', type=str, help='Path to nhentai archivist contents folder.')
    nh_parser.add_argument('--lrr-host', type=str, help='URL of the server.')
    nh_parser.add_argument('--lrr-api-key', type=str, help='API key of the server.')
    nh_parser.add_argument('--threading', action='store_true', help='Use multithreading.')
    nh_parser.add_argument('--multiprocessing', action='store_true', help='Use multiprocessing.')
    nh_parser.add_argument('--remove-duplicates', action='store_true', help='Remove duplicates before uploading.')

    args = parser.parse_args()
    command = args.command

    logging.basicConfig(level=args.log_level.upper())

    if command == "version":
        print(get_version())
    elif command == "configure":
        # create configuration directory.
        from getpass import getpass
        import stat

        CATAPULT_HOME.mkdir(parents=True, exist_ok=True)

        if CATAPULT_CONFIG_FILE.exists():
            with open(CATAPULT_CONFIG_FILE, 'r') as reader:
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
            with open(CATAPULT_CONFIG_FILE, 'w') as writer:
                toml.dump(configuration, writer)
            CATAPULT_CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
            return 0
        else:
            return 0

    elif command == "check":
        arg_lrr_host = args.lrr_host
        arg_lrr_api_key = args.lrr_api_key

        # get configurations
        lrr_host: str = None
        lrr_api_key: str = None

        # get default configuration if available
        if CATAPULT_CONFIG_FILE.exists():
            with open(CATAPULT_CONFIG_FILE, 'r') as reader:
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
        
        response = test_connection(lrr_host, lrr_api_key=lrr_api_key)
        status_code = response.status_code
        if status_code == 200:
            print('success')
            return 0
        else:
            error_message = response.json()['error']
            print(f"Failed to connect (status code {status_code}): {error_message}")
            return 1

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
        lrr_host: str = None
        lrr_api_key: str = None

        # get default configuration if available
        CATAPULT_CONFIG_FILE = CATAPULT_HOME / "catapult.toml"
        if CATAPULT_CONFIG_FILE.exists():
            with open(CATAPULT_CONFIG_FILE, 'r') as reader:
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

    elif command == 'plugin':
        plugin_command = args.plugin_command
        if plugin_command == 'folder':
            contents_directory = args.folder
            arg_lrr_host = args.lrr_host
            arg_lrr_api_key = args.lrr_api_key
            remove_duplicates = args.remove_duplicates
            use_threading = args.threading
            use_multiprocessing = args.multiprocessing

            # get configurations
            lrr_host: str = None
            lrr_api_key: str = None

            # get default configuration if available
            CATAPULT_CONFIG_FILE = CATAPULT_HOME / "catapult.toml"
            if CATAPULT_CONFIG_FILE.exists():
                with open(CATAPULT_CONFIG_FILE, 'r') as reader:
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

            start_folder_upload_process(
                contents_directory, lrr_host, lrr_api_key=lrr_api_key, remove_duplicates=remove_duplicates,
                use_threading=use_threading, use_multiprocessing=use_multiprocessing
            )
        elif plugin_command == 'nhentai-archivist':
            db = args.db
            contents_directory = args.folder
            arg_lrr_host = args.lrr_host
            arg_lrr_api_key = args.lrr_api_key
            remove_duplicates = args.remove_duplicates
            use_threading = args.threading
            use_multiprocessing = args.multiprocessing

            # get configurations
            lrr_host: str = None
            lrr_api_key: str = None

            # get default configuration if available
            CATAPULT_CONFIG_FILE = CATAPULT_HOME / "catapult.toml"
            if CATAPULT_CONFIG_FILE.exists():
                with open(CATAPULT_CONFIG_FILE, 'r') as reader:
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

            start_nhentai_archivist_upload_process(
                db, contents_directory, lrr_host, lrr_api_key=lrr_api_key, remove_duplicates=remove_duplicates,
                use_threading=use_threading, use_multiprocessing=use_multiprocessing
            )

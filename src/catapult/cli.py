import argparse
import logging
from pathlib import Path

from .configuration import config
from .controller import start_folder_upload_process, start_nhentai_archivist_upload_process, run_lrr_connection_test, upload_archive_to_server, validate_archive_file
from .models import ArchiveMetadata
from .utils import get_version, mask_string

def __configure(args):
    # create configuration directory.
    from getpass import getpass

    if config.lrr_api_key is not None and config.lrr_host is not None:
        lrr_host = input(f"LANraragi Host [{config.lrr_host}]: ")
        lrr_api_key = getpass(f"LANraragi API key [{mask_string(config.lrr_api_key)}]: ")
        if not lrr_host and not lrr_api_key:
            print("No changes to configuration.")
            return 0
    else:
        lrr_host = input(f"LANraragi Host: ")
        lrr_api_key = getpass(f"LANraragi API key: ")

    if lrr_host:
        config.lrr_host = lrr_host
    if lrr_api_key:
        config.lrr_api_key = lrr_api_key

    config.save()
    return 0

def __check(args):
    arg_lrr_host = args.lrr_host
    arg_lrr_api_key = args.lrr_api_key
    
    response = run_lrr_connection_test(config.lrr_host, lrr_api_key=config.lrr_api_key)
    status_code = response.status_code
    if status_code == 200:
        print('success')
        return 0
    else:
        error_message = response.json()['error']
        print(f"Failed to connect (status code {status_code}): {error_message}")
        return 1

def __validate(args):
    file_path = args.filepath
    is_check_corruption = not args.no_check_corruption
    print(validate_archive_file(file_path, check_for_corruption=is_check_corruption))

def __upload(args):
    file_path = args.filepath
    title = args.title
    tags = args.tags
    summary = args.summary
    category_id = args.category_id
    is_check_corruption = not args.no_check_corruption

    lrr_host = config.lrr_host
    lrr_api_key = config.lrr_api_key

    metadata = ArchiveMetadata(
        title=title,
        tags=tags,
        summary=summary,
        category_id=category_id
    )

    file_is_valid, message = validate_archive_file(file_path, check_for_corruption=is_check_corruption)
    if not file_is_valid:
        print(f"File {file_path} is not valid. Reason: {message}.")
        return 1

    # validation
    config_is_valid, validation_err = config.is_valid()
    if not config_is_valid:
        print(validation_err)
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

def __multi_upload(args):
    plugin_command = args.plugin_command

    lrr_host = config.lrr_host
    lrr_api_key = config.lrr_api_key

    remove_duplicates = args.remove_duplicates
    use_threading = args.threading
    use_multiprocessing = args.multiprocessing
    upload_workers = args.upload_workers
    use_cache = not args.no_cache

    if plugin_command == 'from-folder':
        contents_directory = args.folder

        if not contents_directory:
            contents_directory = config.multi_upload_folder_dir

        start_folder_upload_process(
            contents_directory, lrr_host, lrr_api_key=lrr_api_key, remove_duplicates=remove_duplicates,
            use_threading=use_threading, use_multiprocessing=use_multiprocessing, max_upload_workers=upload_workers, use_cache=use_cache
        )
    elif plugin_command == 'from-nhentai-archivist':
        db = args.db
        contents_directory = args.folder

        if not db:
            db = config.multi_upload_nhentai_archivist_db
        if not contents_directory:
            contents_directory = config.multi_upload_nhentai_archivist_content_dir

        start_nhentai_archivist_upload_process(
            db, contents_directory, lrr_host, lrr_api_key=lrr_api_key, remove_duplicates=remove_duplicates,
            use_threading=use_threading, use_multiprocessing=use_multiprocessing, max_upload_workers=upload_workers, use_cache=use_cache
        )

def main():

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
    validate_subparser.add_argument('--no-check-corruption', action='store_true', help='Do not check if a (zip) archive contains corrupted images.')

    # upload subparser
    upload_subparser = subparsers.add_parser("upload", help="Upload a file to the server.")
    upload_subparser.add_argument("filepath", help="Path to file to upload.")
    upload_subparser.add_argument('--title', type=str, help='Title of the archive.')
    upload_subparser.add_argument('--tags', type=str, help='Tags of the archive.')
    upload_subparser.add_argument('--summary', type=str, help='Summary of the archive.')
    upload_subparser.add_argument('--category_id', type=int, help='Category ID of the archive.')
    upload_subparser.add_argument('--lrr-host', type=str, help='URL of the server.')
    upload_subparser.add_argument('--lrr-api-key', type=str, help='API key of the server.')
    upload_subparser.add_argument('--no-check-corruption', action='store_true', help='Do not check if a (zip) archive contains corrupted images.')

    # jobs subparser
    multiupload_subparser = subparsers.add_parser("multi-upload", help="Plugins command")
    mu_subparsers = multiupload_subparser.add_subparsers(dest='plugin_command')
    mu_folder_parser = mu_subparsers.add_parser('from-folder', help="Upload archives from folder.")
    mu_folder_parser.add_argument('--folder', type=str, help='Path to nhentai archivist contents folder.')
    mu_nh_parser = mu_subparsers.add_parser('from-nhentai-archivist', help="Nhentai archivist upload jobs.")
    mu_nh_parser.add_argument('--db', type=str, help='Path to nhentai archivist database.')
    mu_nh_parser.add_argument('--folder', type=str, help='Path to nhentai archivist contents folder.')

    for plugin_parser in [mu_folder_parser, mu_nh_parser]:
        plugin_parser.add_argument('--lrr-host', type=str, help='URL of the server.')
        plugin_parser.add_argument('--lrr-api-key', type=str, help='API key of the server.')
        plugin_parser.add_argument('--threading', action='store_true', help='Use multithreading.')
        plugin_parser.add_argument('--multiprocessing', action='store_true', help='Use multiprocessing.')
        plugin_parser.add_argument('--remove-duplicates', action='store_true', help='Remove duplicates before uploading.')
        plugin_parser.add_argument('--upload-workers', type=int, default=1, help='Number of upload workers in a multithreaded job (default 1).')
        plugin_parser.add_argument('--no-cache', action='store_true', help='Disable cache when remove duplicates.')

    args = parser.parse_args()
    command = args.command

    logging.basicConfig(level=args.log_level.upper())

    if command == "version":
        print(get_version())

    elif command == "configure":
        return __configure(args)

    elif command == "check":
        return __check(args)

    elif command == "validate":
        return __validate(args)

    elif command == "upload":
        return __upload(args)

    elif command == 'multi-upload':
        return __multi_upload(args)

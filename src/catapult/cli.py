import argparse
import asyncio
import logging
from pathlib import Path
from time import perf_counter

from .cache import drop_cache_table
from .configuration import config
from .controller import start_folder_upload_process, run_lrr_connection_test, async_upload_archive_to_server, async_validate_archive
from .models import ArchiveMetadata, ArchiveValidateUploadStatus, MultiArchiveUploadResponse
from .utils import get_version, mask_string, lrr_build_auth

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

def __reset_cache():
    asyncio.run(drop_cache_table())
    print("Cache dropped.")

def __check(args):
    arg_lrr_host = args.lrr_host
    arg_lrr_api_key = args.lrr_api_key
    
    headers = dict()
    response = asyncio.run(run_lrr_connection_test(config.lrr_host, lrr_api_key=config.lrr_api_key))
    status_code = response.status
    if status_code == 200:
        print('success')
        return 0
    else:
        print("fail")
        return 1

def __validate(args):
    file_path = args.filepath
    # print(validate_archive_file(file_path, check_for_corruption=is_check_corruption))
    response = asyncio.run(async_validate_archive(file_path))
    print(f"{response.status_code.name} - {response.message}")

def __upload(args):
    file_path = args.filepath
    title = args.title
    tags = args.tags
    summary = args.summary
    category_id = args.category_id

    lrr_host = config.lrr_host
    lrr_api_key = config.lrr_api_key

    metadata = ArchiveMetadata(
        title=title,
        tags=tags,
        summary=summary,
        category_id=category_id
    )
    headers = dict()
    if lrr_api_key:
        headers["Authorization"] = lrr_build_auth(lrr_api_key)
    response = asyncio.run(async_upload_archive_to_server(file_path, metadata, lrr_host, headers=headers))
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

    use_cache = not args.no_cache
    response = None

    start_time = perf_counter()
    if plugin_command == 'from-folder':
        contents_directory = args.folder

        if not contents_directory:
            contents_directory = config.multi_upload_folder_dir

        assert contents_directory, "no contents directory"

        response = start_folder_upload_process(
            contents_directory, lrr_host, lrr_api_key=lrr_api_key, use_cache=use_cache
        )

    total_time = perf_counter() - start_time
    if response:
        upload_responses = response.upload_responses
        stats_by_status_code = dict()
        for upload_response in upload_responses:
            status_code = upload_response.status_code.name
            if status_code in stats_by_status_code:
                stats_by_status_code[status_code] += 1
            else:
                stats_by_status_code[status_code] = 1
        print(f"\n --".join([f"{key}: {stats_by_status_code[key]}" for key in stats_by_status_code]))
        print(f"Time taken: {total_time}s")

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

    # reset cache subparser
    reset_cache_subparser = subparsers.add_parser("reset-cache", help="Reset cache.")

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
    multiupload_subparser = subparsers.add_parser("multi-upload", help="Plugins command")
    mu_subparsers = multiupload_subparser.add_subparsers(dest='plugin_command')
    mu_folder_parser = mu_subparsers.add_parser('from-folder', help="Upload archives from folder.")
    mu_folder_parser.add_argument('--folder', type=str, help='Path to nhentai archivist contents folder.')

    for plugin_parser in [mu_folder_parser]:
        plugin_parser.add_argument('--lrr-host', type=str, help='URL of the server.')
        plugin_parser.add_argument('--lrr-api-key', type=str, help='API key of the server.')
        plugin_parser.add_argument('--no-cache', action='store_true', help='Disable cache when remove duplicates.')

    args = parser.parse_args()
    command = args.command

    logging.basicConfig(level=args.log_level.upper())

    if command == "version":
        print(get_version())

    elif command == "configure":
        return __configure(args)

    elif command == "reset-cache":
        return __reset_cache()

    elif command == "check":
        return __check(args)

    elif command == "validate":
        return __validate(args)

    elif command == "upload":
        return __upload(args)

    elif command == 'multi-upload':
        return __multi_upload(args)

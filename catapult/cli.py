import argparse
import asyncio
import logging
from pathlib import Path
from time import perf_counter

from catapult.metadata import NhentaiArchivistMetadataClient, PixivUtil2MetadataClient

from .cache import create_cache_table, drop_cache_table
from .configuration import config
from .controller import upload_archives_from_folders, run_lrr_connection_test, async_upload_archive_to_server, async_validate_archive
from .models import ArchiveMetadata, ArchiveValidateUploadStatus
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
        lrr_host = input("LANraragi Host: ")
        lrr_api_key = getpass("LANraragi API key: ")

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
    if arg_lrr_host:
        config.lrr_host = arg_lrr_host
    if arg_lrr_api_key:
        config.lrr_api_key = arg_lrr_api_key
    is_connected = asyncio.run(run_lrr_connection_test(config.lrr_host, lrr_api_key=config.lrr_api_key))
    print(is_connected)

def __validate(args):
    file_path = args.filepath
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
    response = asyncio.run(async_upload_archive_to_server(file_path, metadata, lrr_host, lrr_api_key=lrr_api_key))
    status_code = response.status_code
    if status_code == ArchiveValidateUploadStatus.SUCCESS:
        print(f"Uploaded {file_path} to server.")
        return 0
    else:
        error_message = response.message
        print(f"Failed to upload file (status code {status_code.name}): {error_message}")
        return 1

def __multi_upload(args):
    plugin_command = args.plugin_command

    lrr_host = config.lrr_host
    lrr_api_key = config.lrr_api_key

    use_cache = not args.no_cache
    response = None

    start_time = perf_counter()
    if plugin_command == 'from-folder':
        folders = args.folders

        if not folders:
            folders = config.multi_upload_folder_dir
        if not folders:
            raise TypeError("Multi upload folder config cannot be empty (set MULTI_UPLOAD_FOLDER environment).")
        folders = [Path(directory) for directory in folders.split(";")]
        for folder in folders:
            if not folder.exists():
                raise FileNotFoundError(f"Folder not found: {folder}")
        response = asyncio.run(upload_archives_from_folders(folders, lrr_host, lrr_api_key=lrr_api_key, use_cache=use_cache))
    elif plugin_command == 'from-nhentai-archivist':
        db = args.db
        folders = args.folders
        if not db:
            db = config.nhentai_archivist_db
            if not db:
                raise TypeError("Nhentai Archivist database config cannot be empty (MULTI_UPLOAD_NH_ARCHIVIST_DB)")
        if not folders:
            folders = config.nhentai_archivist_folders
            if not folders:
                raise TypeError("Nhentai Archivist folder config cannot be empty (MULTI_UPLOAD_NH_ARCHIVIST_CONTENTS)")

        db = Path(db)
        if not db.exists():
            raise FileNotFoundError(f"Nhentai Archivist database not found: {db}")
        folders = [Path(directory) for directory in folders.split(";")]
        for folder in folders:
            if not folder.exists():
                raise FileNotFoundError(f"Folder not found: {folder}")
        nhentai_archivist_client = NhentaiArchivistMetadataClient(db)
        response = asyncio.run(upload_archives_from_folders(
            folders, lrr_host, lrr_api_key=lrr_api_key, use_cache=use_cache, metadata_client=nhentai_archivist_client
        ))
    elif plugin_command == 'from-pixivutil2':
        db = args.db
        folders = args.folders
        if not db:
            db = config.pixivutil2_db
            if not db:
                raise TypeError("PixivUtil2 database config cannot be empty (MULTI_UPLOAD_NH_ARCHIVIST_DB)")
        if not folders:
            folders = config.pixivutil2_folders
            if not folders:
                raise TypeError("PixivUtil2 download folder config cannot be empty (MULTI_UPLOAD_NH_ARCHIVIST_CONTENTS)")

        db = Path(db)
        if not db.exists():
            raise FileNotFoundError(f"PixivUtil2 database not found: {db}")
        folders = [Path(directory) for directory in folders.split(";")]
        for folder in folders:
            if not folder.exists():
                raise FileNotFoundError(f"Folder not found: {folder}")
        pixivutil2_client = PixivUtil2MetadataClient(db, allowed_translation_types=["en"])
        response = asyncio.run(upload_archives_from_folders(
            folders, lrr_host, lrr_api_key=lrr_api_key, use_cache=use_cache, metadata_client=pixivutil2_client
        ))
    else:
        raise NotImplementedError(f"Unsupported plugin: {plugin_command}")

    total_time = perf_counter() - start_time
    if response:
        upload_responses = response.upload_responses
        stats_by_status_code = {}
        for upload_response in upload_responses:
            status_code = upload_response.status_code.name
            if status_code in stats_by_status_code:
                stats_by_status_code[status_code] += 1
            else:
                stats_by_status_code[status_code] = 1
        print("\n --".join([f"{key}: {stats_by_status_code[key]}" for key in stats_by_status_code]))
        print(f"Time taken: {total_time}s")

def main():

    parser = argparse.ArgumentParser("catapult command line")
    parser.add_argument('--log-level', type=str, default='warning', help='Set log level.')

    subparsers = parser.add_subparsers(dest="command", required=True)

    # version subparser
    subparsers.add_parser("version", help="Get version.")

    # configure subparser
    subparsers.add_parser("configure", help="Configure catapult settings.")

    # check subparser
    check_subparser = subparsers.add_parser("check", help="Check connection to server instance.")
    check_subparser.add_argument('--lrr-host', type=str, help='URL of the server.')
    check_subparser.add_argument('--lrr-api-key', type=str, help='API key of the server.')

    # reset cache subparser
    subparsers.add_parser("reset-cache", help="Reset cache.")

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
    mu_folder_parser.add_argument('--folders', type=str, help='Path to nhentai archivist contents folder.')
    mu_nh_parser = mu_subparsers.add_parser('from-nhentai-archivist', help="Nhentai archivist upload jobs.")
    mu_nh_parser.add_argument('--db', type=str, help='Path to nhentai archivist database.')
    mu_nh_parser.add_argument('--folders', type=str, help='Path to nhentai archivist contents folder.')
    mu_nh_parser = mu_subparsers.add_parser('from-pixivutil2', help="PixivUtil2 upload jobs.")
    mu_nh_parser.add_argument('--db', type=str, help='Path to PixivUtil2 database.')
    mu_nh_parser.add_argument('--folders', type=str, help='Path to PixivUtil2 contents folder.')

    for plugin_parser in [mu_folder_parser, mu_nh_parser]:
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
        asyncio.run(create_cache_table())
        return __upload(args)

    elif command == 'multi-upload':
        asyncio.run(create_cache_table())
        return __multi_upload(args)

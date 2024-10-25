
class ArchiveMetadata:

    def __init__(self, title: str=None, tags: str=None, summary: str=None, category_id: int=None):
        self.title = title
        self.tags = tags
        self.summary = summary
        self.category_id = category_id

class ArchiveUploadRequest:

    def __init__(self, archive_file_path: str, archive_file_name: str, metadata: ArchiveMetadata):
        self.archive_file_path = archive_file_path
        self.archive_file_name = archive_file_name
        self.metadata = metadata

class MultiArchiveUploadResponse:
    """
    Response object for multiple archive uploads.
    """
    uploaded_files: int
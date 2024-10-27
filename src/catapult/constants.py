from pathlib import Path

ALLOWED_LRR_EXTENSIONS = {"zip", "rar", "targz", "lzma", "7z", "xz", "cbz", "cbr", "pdf"}

JPG_SIGNATURES = [
    "FF D8 FF E0 00 10 4A 46 49 46 00 01",
    "FF D8 FF EE",
    "FF D8 FF E1 ?? ?? 45 78 69 66 00 00"
]

PNG_SIGNATURES = [
    "89 50 4E 47 0D 0A 1A 0A",
]

ZIP_SIGNATURES = [
    # zip, cbz
    "50 4b 03 04",
    "50 4b 05 06",
    "50 4b 07 08",
]

RAR_SIGNATURES = [
    # rar, cbr
    "52 61 72 21 1A 07 00",
    "52 61 72 21 1A 07 01 00",
]

ALLOWED_SIGNATURES = ZIP_SIGNATURES + RAR_SIGNATURES + [

    # tar.gz file
    "1F 8B",

    # lzma
    "FD 37 7A 58 5A 00",

    # 7z
    "37 7A BC AF 27 1C",

    # xz
    "FD 37 7A 58 5A 00",

    # pdf
    "25 50 44 46 2D",

]

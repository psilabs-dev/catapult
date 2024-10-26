from pathlib import Path

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

for i in range(len(ZIP_SIGNATURES)):
    ZIP_SIGNATURES[i] = ZIP_SIGNATURES[i].lower().replace(' ', '')
for i in range(len(RAR_SIGNATURES)):
    RAR_SIGNATURES[i] = RAR_SIGNATURES[i].lower().replace(' ', '')
for i in range(len(ALLOWED_SIGNATURES)):
    ALLOWED_SIGNATURES[i] = ALLOWED_SIGNATURES[i].lower().replace(' ', '')
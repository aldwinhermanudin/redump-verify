# Redump Verify

## AI-Generated Disclaimer
This script is AI-generated. It has not been formally reviewed by a human developer, but it has been verified that it works as intended.

## Description
`redump-verify.py` is a Python command-line tool designed to verify ROM and ISO files against official Redump XML DAT databases. It calculates CRC32, MD5, and SHA-1 hashes of your local files and cross-references them with the DAT file to ensure you have perfect, unmodified dumps.

## Features
* **Multiple Hashing Algorithms:** Calculates CRC32, MD5, and SHA-1 simultaneously.
* **Memory Efficient:** Reads files (and ZIP contents) in 4MB chunks, allowing it to process large ISOs without consuming excessive RAM.
* **Batch Processing:** Scan a single file or an entire directory of `.iso`, `.bin`, and `.zip` files.
* **ZIP Archive Support:** Verifies ROMs directly inside ZIP archives without extracting them.
* **Redump DAT Support:** Parses official Redump XML databases to verify matches.
* **No External Dependencies:** Built entirely with Python's standard library.

## Requirements
* Python 3.6 or higher (uses standard library only)
* Tested in Python 3.12.3

## Usage

### Verify a single file
```bash
python redump-verify.py --file path/to/game.iso --dat path/to/redump.dat
```

### Verify a directory of files
```bash
python redump-verify.py --directory path/to/roms/ --dat path/to/redump.dat
```

### Additional Options
* `--log-file <path>`: Save the console output to a log file.
* `--zipped-rom`: Treat ZIP files as archives and verify the `.iso` or `.bin` ROMs inside them directly.
* `--result <path>`: Output a JSON file mapping verified and failed filenames to their SHA-1 hashes.
* `--log-level <LEVEL>`: Set the logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Default is `INFO`.

### Example
```bash
python redump-verify.py --directory ./ps1_games --dat ./Sony_PlayStation.dat --log-file verification_results.txt
```
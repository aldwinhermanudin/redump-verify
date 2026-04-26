#!/usr/bin/env python3
import os
import sys
import zlib
import hashlib
import argparse
import logging
import json
import xml.etree.ElementTree as ET
import zipfile

__version__ = "0.1.0"

def calculate_hashes_from_stream(f, file_size: int, filename: str):
    """Calculates CRC32, MD5, and SHA-1 hashes for a given file stream."""
    md5_hash = hashlib.md5()
    sha1_hash = hashlib.sha1()
    crc32_hash = 0
    
    processed = 0
    
    logging.info(f"Calculating hashes for: {filename}")
    logging.info(f"File size: {file_size / (1024 * 1024):.2f} MB")
    
    # Read in 4MB chunks to keep memory usage low
    for chunk in iter(lambda: f.read(4096 * 1024), b""):
        md5_hash.update(chunk)
        sha1_hash.update(chunk)
        crc32_hash = zlib.crc32(chunk, crc32_hash)
        
        processed += len(chunk)
        if file_size > 0:
            percent = (processed / file_size) * 100
            sys.stdout.write(f"\rProgress: [{percent:.1f}%] {processed/(1024*1024):.1f}MB")
            sys.stdout.flush()
            
    logging.info("\nHash calculation complete!\n")
    
    return {
        "crc32": format(crc32_hash & 0xFFFFFFFF, '08x'),
        "md5": md5_hash.hexdigest(),
        "sha1": sha1_hash.hexdigest(),
        "size": str(file_size)
    }

def calculate_hashes(filepath: str):
    """Calculates CRC32, MD5, and SHA-1 hashes for a given file."""
    file_size = os.path.getsize(filepath)
    with open(filepath, "rb") as f:
        return calculate_hashes_from_stream(f, file_size, os.path.basename(filepath))

def check_redump_dat(dat_root, file_hashes: dict) -> dict:
    """Searches for matching hashes in the parsed Redump XML DAT root."""
    for game in dat_root.findall('game'):
        for rom in game.findall('rom'):
            rom_sha1 = rom.get('sha1', '').lower()
            rom_md5 = rom.get('md5', '').lower()
            
            # SHA-1 is standard for checking against collisions, but checking both is safest
            if rom_sha1 == file_hashes['sha1'] or rom_md5 == file_hashes['md5']:
                return {
                    "game_name": game.get('name', 'Unknown'),
                    "rom_name": rom.get('name', 'Unknown'),
                    "status": "Match"
                }
                
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify a ROM/ISO against a Redump DAT file.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a single file (.iso/.bin/.zip) to verify")
    group.add_argument("--directory", help="Path to a directory containing files to verify")
    parser.add_argument("--dat", help="Path to the Redump .dat (XML) file", required=False)
    parser.add_argument("--result", help="Path to output a JSON file containing verified and failed filenames with their SHA-1 hashes", required=False)
    parser.add_argument("--zipped-rom", action="store_true", help="Treat files as ZIP archives and verify their contents", required=False)
    parser.add_argument("--log-file", help="Path to a log file to save the output", required=False)
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level.")
    
    args = parser.parse_args()
    
    log_handlers = [logging.StreamHandler(sys.stdout)]
    if args.log_file:
        log_handlers.append(logging.FileHandler(args.log_file, encoding='utf-8'))
        
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(message)s',
        handlers=log_handlers
    )

    files_to_verify = []
    if args.file:
        if not os.path.isfile(args.file):
            logging.error(f"Error: File not found -> {args.file}")
            sys.exit(1)
        files_to_verify.append(args.file)
    elif args.directory:
        if not os.path.isdir(args.directory):
            logging.error(f"Error: Directory not found -> {args.directory}")
            sys.exit(1)
        for root_dir, _, files in os.walk(args.directory):
            for f in files:
                if f.lower().endswith(('.iso', '.zip', '.bin')):
                    files_to_verify.append(os.path.join(root_dir, f))
                    
    if not files_to_verify:
        logging.info("No valid files (.iso, .zip, .bin) found to verify.")
        sys.exit(0)
        
    dat_root = None
    if args.dat:
        logging.info(f"Loading Redump database: {args.dat}...")
        try:
            tree = ET.parse(args.dat)
            dat_root = tree.getroot()
        except ET.ParseError as e:
            logging.error(f"Error parsing DAT file: {e}")
            sys.exit(1)
            
    results = {"matched": [], "failed": [], "unverified": []}

    def process_match(filepath_display, file_hashes):
        logging.info(f"CRC32: {file_hashes['crc32']}")
        logging.info(f"MD5:   {file_hashes['md5']}")
        logging.info(f"SHA-1: {file_hashes['sha1']}")
        logging.info("-" * 40)
        
        if dat_root is not None:
            match = check_redump_dat(dat_root, file_hashes)
            if match:
                logging.info("[✓] VERIFIED: Perfect match found in Redump database!")
                logging.info(f"Game: {match['game_name']}")
                logging.info(f"ROM:  {match['rom_name']}")
                results["matched"].append({"file": filepath_display, "sha1": file_hashes['sha1']})
            else:
                logging.info("[x] FAILED: No match found in the provided DAT file. This might be a bad dump.")
                results["failed"].append({"file": filepath_display, "sha1": file_hashes['sha1'], "reason": "NO_MATCH"})
        else:
            results["unverified"].append(filepath_display)

    for filepath in files_to_verify:
        if args.zipped_rom and filepath.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(filepath, 'r') as zf:
                    for zinfo in zf.infolist():
                        if zinfo.is_dir() or not zinfo.filename.lower().endswith(('.iso', '.bin')):
                            continue
                        logging.info(f"\n--- Verifying inside ZIP: {filepath} -> {zinfo.filename} ---")
                        with zf.open(zinfo) as f:
                            hashes = calculate_hashes_from_stream(f, zinfo.file_size, zinfo.filename)
                        process_match(f"{filepath}/{zinfo.filename}", hashes)
            except zipfile.BadZipFile:
                logging.error(f"[x] FAILED: Invalid ZIP file -> {filepath}")
                results["failed"].append({"file": filepath, "sha1": "", "reason": "INVALID_ZIP"})
        else:
            logging.info(f"\n--- Verifying: {filepath} ---")
            hashes = calculate_hashes(filepath)
            process_match(filepath, hashes)

    if args.directory:
        logging.info("\n" + "=" * 40)
        logging.info("VERIFICATION OVERVIEW")
        logging.info("=" * 40)
        logging.info(f"Total files processed: {len(files_to_verify)}")
        if dat_root is not None:
            logging.info(f"Successfully verified: {len(results['matched'])}")
            logging.info(f"Failed verification:   {len(results['failed'])}")
            if results['failed']:
                logging.info("\nFailed Files:")
                for f in results['failed']:
                    logging.info(f"  - {f['file']}")

    if args.result:
        json_output = {
            "matched": {os.path.basename(item["file"]): item["sha1"] for item in results["matched"]},
            "failed": {
                os.path.basename(item["file"]): {"sha1": item["sha1"], "reason": item["reason"]} for item in results["failed"]
            }
        }
        try:
            with open(args.result, "w", encoding="utf-8") as f:
                json.dump(json_output, f, indent=4)
            logging.info(f"\nSaved verified results to JSON: {args.result}")
        except Exception as e:
            logging.error(f"\nFailed to save results to JSON: {e}")

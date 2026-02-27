#!/usr/bin/env python3
"""
Simple HBCD Conversion Script

Downloads RDA file from NBDCtoolsData and calls convert.py.
Replaces the complex convert.yml workflow with a single simple script.
"""
import argparse
import subprocess
import sys
from pathlib import Path
import requests

NBDC_REPO = "nbdc-datahub/NBDCtoolsData"
RDA_FILENAME = "lst_dds.rda"
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"


def download_rda_file():
    """Download lst_dds.rda from NBDCtoolsData repository.

    Uses GitHub raw content URL.
    """
    # Build URL directly - no f-string formatting
    raw_url = f"https://raw.githubusercontent.com/{NBDC_REPO}/main/data/{RDA_FILENAME}"

    print(f"Downloading {RDA_FILENAME} from {NBDC_REPO}...")
    try:
        response = requests.get(raw_url, timeout=60)
        response.raise_for_status()

        # Save to data directory
        DATA_DIR.mkdir(exist_ok=True)
        rda_path = DATA_DIR / RDA_FILENAME
        with open(rda_path, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded {rda_path}")
        return rda_path
    except requests.RequestException as e:
        print(f"Error downloading {RDA_FILENAME}: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Simple HBCD conversion: download RDA and convert"
    )
    parser.add_argument(
        "--release",
        required=False,
        help="HBCD release version (if empty, auto-detect from RDA)",
    )
    parser.add_argument(
        "--create-tag",
        action="store_true",
        default=False,
        help="Create git tag for this release",
    )
    args = parser.parse_args()

    # Download RDA file
    rda_path = download_rda_file()
    if not rda_path:
        sys.exit(1)

    # Build convert.py command
    # If release specified, use that. If empty, convert.py will auto-detect from RDA.
    convert_args = ["python", "scripts/convert.py", "--release", args.release]

    print(f"\n=== Running conversion ===")
    print(f"Command: {' '.join(convert_args)}")

    try:
        result = subprocess.run(convert_args, capture_output=True, text=True)

        # Parse output to get version
        output_lines = result.stdout.strip().split('\n')
        version = None
        status = "success"

        for line in output_lines:
            if "Converting HBCD" in line:
                # Extract version from line like "Converting HBCD 1.0"
                import re
                match = re.search(r'Converting HBCD\s+([\d.]+)', line)
                if match:
                    version = match.group(1)
            elif "Error during conversion" in line:
                status = "failed"
            elif "Conversion complete" in line:
                status = "complete"

        # Set GitHub outputs
        with open(Path(System.getenv("GITHUB_OUTPUT", "/tmp/outputs")), 'a') as f:
            f.write(f"version={version or ''}\n")
            f.write(f"status={status}\n")

        print(f"\n=== Conversion {status} ===")
        if version:
            print(f"Version: {version}")

        # Commit and tag if requested
        if args.create_tag and status == "complete":
            print(f"\n=== Creating tag {version} ===")
            tag_result = subprocess.run(
                ["git", "tag", "-a", f"v{version}", "-m", f"HBCD Release {version}"],
                capture_output=True,
                text=True
            )
            if tag_result.returncode == 0:
                print(f"Tag v{version} created")
            else:
                print(f"Failed to create tag: {tag_result.stderr}")

        sys.exit(0 if status == "complete" else 1)

    except subprocess.CalledProcessError as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
HBCD ReproSchema Conversion Script - Version from RDA

This script extracts HBCD data dictionary from NBDCtoolsData and converts
it to ReproSchema JSON-LD format using reproschema-py.

VERSION IS NOW EXTRACTED FROM THE DOWNLOADED RDA FILE ITSELF!
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import requests

NBDC_REPO = "nbdc-datahub/NBDCtoolsData"
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = Path("data")
RDA_FILENAME = "lst_dds.rda"


def download_rda_file():
    """Download lst_dds.rda from NBDCtoolsData repository.

    Uses GitHub API to fetch just the file we need.
    Returns the path to the downloaded RDA file.
    """
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
        return None


def extract_version_from_rda(rda_path, release_version=None):
    """Extract release version from the RDA file structure.

    The RDA file contains lst_dds$hbcd which is a list/structure.
    We can parse the file to find all available release versions.

    If release_version is specified, use that. Otherwise, return all versions.
    """
    print(f"Extracting version information from {rda_path}...")

    # Use R to parse the RDA and extract version information
    r_script = """
# Load the RDA file
load(file)

# Get the hbcd structure
if (exists("lst_dds") && !is.null(lst_dds$hbcd)) {
  hbcd <- lst_dds$hbcd

  # Get all release versions
  releases <- names(hbcd)

  # Print all available versions
  cat("ALL_VERSIONS:", paste(releases, collapse=","), "\\n")
  flush.console()

} else {
  cat("ERROR: lst_dds$hbcd not found in RDA")
  quit(status=1)
}
"""

    result = subprocess.run(
        ["Rscript", "-e", r_script],
        input=str(rda_path),
        capture_output=True,
        text=True,
        cwd=SCRIPT_DIR
    )

    if result.returncode != 0:
        print(f"Error extracting versions from RDA: {result.stderr}")
        sys.exit(1)

    # Parse the output to get versions
    versions_output = result.stdout.strip()

    # Extract versions list (format: "ALL_VERSIONS: 1.0,2.0,3.0")
    if versions_output.startswith("ALL_VERSIONS:"):
        all_versions = [v.strip() for v in versions_output.split(":", 1)[1].split(",") if v.strip()]
    else:
        print(f"Unexpected output format: {versions_output}")
        all_versions = []

    print(f"All available releases in RDA: {all_versions}")

    # If specific version requested, validate it exists
    if release_version:
        if release_version not in all_versions:
            print(f"Error: Version '{release_version}' not found in RDA")
            print(f"Available versions: {', '.join(all_versions)}")
            sys.exit(1)
        return [release_version]
    else:
        return all_versions


def main():
    parser = argparse.ArgumentParser(
        description="Convert HBCD data dictionary to ReproSchema format"
    )
    parser.add_argument(
        "--release",
        required=True,
        help="HBCD release version (e.g., 1.0)",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip R extraction step (use existing CSV)",
    )
    parser.add_argument(
        "--keep-data",
        action="store_true",
        default=False,
        help="Keep downloaded data and extracted CSV after conversion",
    )
    args = parser.parse_args()

    # Paths
    repo_root = SCRIPT_DIR.parent
    csv_path = DATA_DIR / f"hbcd_{args.release}.csv"
    yaml_path = repo_root / "hbcd_nbdc2rs.yaml"
    # reproschema-py creates a subfolder named after protocol_name (HBCD)
    output_dir = repo_root / "HBCD"  # Must match protocol_name in hbcd_nbdc2rs.yaml
    old_output_dir = repo_root / "HBCD2reproschema"  # Legacy folder name to clean up

    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)

    # Download RDA file and extract version
    rda_path = download_rda_file()
    if not rda_path:
        print("Error: Failed to download RDA file")
        sys.exit(1)

    # Validate and get version from RDA
    versions = extract_version_from_rda(rda_path, args.release)
    if not versions:
        print("Error: No versions found in RDA")
        sys.exit(1)

    # We now have the version from RDA - use args.release (which was validated)
    version = versions[0]  # First (and only) version in the list
    print(f"=== Converting HBCD release {version} ===")

    try:
        # Step 1: Extract data dictionary using R script
        if not args.skip_extract:
            print(f"Extracting HBCD {version} data dictionary...")
            r_script = SCRIPT_DIR / "extract_release.R"

            cmd = ["Rscript", str(r_script), str(rda_path), version, str(csv_path)]
            print(f"Running: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True)
            print(result.stdout)
            if result.returncode != 0:
                print(f"Error extracting data dictionary:\\n{result.stderr}")
                sys.exit(1)

        # Step 2: Convert to ReproSchema using reproschema-py
        print(f"Converting to ReproSchema format...")

        # Update yaml config with source_version from RDA-extracted version
        import yaml
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        config['source_version'] = version
        with open(yaml_path, 'w') as f:
            yaml.dump(config, f)
        print(f"Set source_version to {version} (extracted from RDA)")

        # Remove existing output directories to avoid conflicts
        if output_dir.exists():
            shutil.rmtree(output_dir)
        if old_output_dir.exists():
            shutil.rmtree(old_output_dir)

        try:
            subprocess.run(
                [
                    "reproschema",
                    "nbdc2reproschema",
                    "--output-path", str(repo_root),
                    str(csv_path),
                    str(yaml_path),
                ],
                check=True,
            )

            if output_dir.exists():
                print(f"Conversion complete. Output in {output_dir}/")
            else:
                print(f"Error: Expected output directory {output_dir} not found")
                sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"Error during conversion: {e}")
            sys.exit(1)
        except FileNotFoundError:
            print("Error: reproschema command not found. Please install reproschema-py.")
            sys.exit(1)

        # Step 3: Validate output
        print("Validating ReproSchema output...")
        try:
            result = subprocess.run(
                ["reproschema", "validate", str(output_dir)],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print("Validation passed!")
            else:
                print(f"Validation warnings/errors:\\n{result.stdout}\\n{result.stderr}")
        except FileNotFoundError:
            print("Warning: Could not run validation (reproschema command not found)")

        print("Done!")

    finally:
        # Cleanup
        if not args.keep_data:
            if rda_path and rda_path.exists():
                print(f"Removing {rda_path}")
                rda_path.unlink()
            if csv_path.exists():
                print(f"Removing temporary CSV: {csv_path}")
                csv_path.unlink()


if __name__ == "__main__":
    main()

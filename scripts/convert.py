#!/usr/bin/env python3
"""
HBCD ReproSchema Conversion Script

This script extracts HBCD data dictionary from NBDCtoolsData and converts
it to ReproSchema JSON-LD format using reproschema-py.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

NBDC_REPO_URL = "https://github.com/nbdc-datahub/NBDCtoolsData.git"
NBDC_DATA_DIR = "NBDCtoolsData"
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = Path("data")


def clone_nbdc_data():
    """Clone NBDCtoolsData repository if not present."""
    if os.path.exists(NBDC_DATA_DIR):
        print(f"Data directory '{NBDC_DATA_DIR}' already exists")
        return True

    print(f"Cloning {NBDC_REPO_URL}...")
    result = subprocess.run(
        ["git", "clone", "--depth", "1", NBDC_REPO_URL],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Failed to clone repository: {result.stderr}")
        return False
    print("Clone complete")
    return True


def find_rda_path():
    """Find lst_dds.rda in either cloned or local dev location."""
    # Cloned location (inside repo)
    cloned_path = Path(NBDC_DATA_DIR) / "data" / "lst_dds.rda"
    if cloned_path.exists():
        return cloned_path

    # Local dev location (sibling directory)
    local_path = Path(__file__).parent.parent.parent / "NBDCtoolsData" / "data" / "lst_dds.rda"
    if local_path.exists():
        return local_path

    return None


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
        help="Keep cloned data and extracted CSV after conversion",
    )
    args = parser.parse_args()

    # Paths
    repo_root = SCRIPT_DIR.parent
    csv_path = repo_root / f"hbcd_{args.release}.csv"
    yaml_path = repo_root / "hbcd_nbdc2rs.yaml"
    # reproschema-py creates a subfolder named after protocol_name (HBCD)
    # So we output to repo_root, then rename HBCD -> HBCD2reproschema
    temp_output_dir = repo_root
    final_output_dir = repo_root / "HBCD2reproschema"
    protocol_name = "HBCD"  # Must match protocol_name in hbcd_nbdc2rs.yaml

    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)

    # Find or clone the RDA file
    rda_path = find_rda_path()
    cloned = False

    if rda_path is None:
        if not clone_nbdc_data():
            sys.exit(1)
        cloned = True
        rda_path = Path(NBDC_DATA_DIR) / "data" / "lst_dds.rda"

    # Move CSV to data directory
    csv_path = DATA_DIR / f"hbcd_{args.release}.csv"

    try:
        # Step 1: Extract data dictionary using R script
        if not args.skip_extract:
            print(f"Extracting HBCD {args.release} data dictionary...")
            r_script = SCRIPT_DIR / "extract_release.R"

            cmd = ["Rscript", str(r_script), str(rda_path), args.release, str(csv_path)]
            print(f"Running: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True)
            print(result.stdout)
            if result.returncode != 0:
                print(f"Error extracting data dictionary:\n{result.stderr}")
                sys.exit(1)

        # Step 2: Convert to ReproSchema using reproschema-py
        print(f"Converting to ReproSchema format...")

        # Remove existing output directories to avoid conflicts
        if final_output_dir.exists():
            shutil.rmtree(final_output_dir)
        if (temp_output_dir / protocol_name).exists():
            shutil.rmtree(temp_output_dir / protocol_name)

        try:
            subprocess.run(
                [
                    "reproschema",
                    "nbdc2reproschema",
                    "--output-path", str(temp_output_dir),
                    str(csv_path),
                    str(yaml_path),
                ],
                check=True,
            )

            # Rename HBCD -> HBCD2reproschema to avoid redundant nesting
            generated_dir = temp_output_dir / protocol_name
            if generated_dir.exists():
                shutil.move(str(generated_dir), str(final_output_dir))
                print(f"Conversion complete. Output in {final_output_dir}/")
            else:
                print(f"Error: Expected output directory {generated_dir} not found")
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
                ["reproschema", "validate", str(final_output_dir)],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print("Validation passed!")
            else:
                print(f"Validation warnings/errors:\n{result.stdout}\n{result.stderr}")
        except FileNotFoundError:
            print("Warning: Could not run validation (reproschema command not found)")

        print("Done!")

    finally:
        # Cleanup
        if not args.keep_data:
            if cloned:
                if os.path.exists(NBDC_DATA_DIR):
                    print(f"Cleaning up '{NBDC_DATA_DIR}'...")
                    shutil.rmtree(NBDC_DATA_DIR)
            if csv_path.exists():
                print(f"Removing temporary CSV: {csv_path}")
                csv_path.unlink()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
HBCD ReproSchema Conversion Script - Simplified

Downloads RDA file, detects version, and converts to ReproSchema.
No external config needed - version detected from RDA file itself.

REQUIRES: R (base R is sufficient, no extra packages needed)
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import requests

NBDC_REPO = "nbdc-datahub/NBDCtoolsData"
RDA_FILENAME = "lst_dds.rda"
RDA_URL = f"https://raw.githubusercontent.com/{NBDC_REPO}/main/data/{RDA_FILENAME}"


def download_rda():
    """Download RDA file from NBDCtoolsData (single file, not clone)."""
    print(f"Downloading {RDA_FILENAME} from {NBDC_REPO}...")
    try:
        response = requests.get(RDA_URL, timeout=60)
        response.raise_for_status()

        Path("data").mkdir(exist_ok=True)
        rda_path = Path("data") / RDA_FILENAME
        with open(rda_path, 'wb') as f:
            f.write(response.content)

        print(f"Downloaded to {rda_path}")
        return rda_path
    except requests.RequestException as e:
        print(f"Error downloading {RDA_FILENAME}: {e}")
        sys.exit(1)


def check_r_available():
    """Check if Rscript is available."""
    result = subprocess.run(["which", "Rscript"], capture_output=True)
    return result.returncode == 0


def extract_versions_from_rda(rda_path):
    """Extract available HBCD versions from RDA file using R."""
    print(f"Extracting versions from {rda_path}...")

    r_script = f"""
load("{rda_path}")
if (exists("lst_dds") && !is.null(lst_dds$hbcd)) {{
  versions <- names(lst_dds$hbcd)
  cat(paste(versions, collapse="\\n"))
}} else {{
  stop("No HBCD data found in RDA file")
}}
"""

    result = subprocess.run(
        ["Rscript", "-e", r_script],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error extracting versions: {result.stderr}")
        sys.exit(1)

    versions = [v.strip() for v in result.stdout.strip().split('\n') if v.strip()]
    print(f"Available versions in RDA: {', '.join(versions)}")
    return versions


def get_existing_tags():
    """Get existing git tags."""
    result = subprocess.run(
        ["git", "tag", "-l"],
        capture_output=True,
        text=True
    )
    return [t.strip() for t in result.stdout.strip().split('\n') if t.strip()]


def find_new_versions(all_versions, existing_tags):
    """Find versions that haven't been converted yet."""
    new_versions = [v for v in all_versions if v not in existing_tags]
    print(f"New versions to convert: {', '.join(new_versions) if new_versions else 'None'}")
    return new_versions


def extract_csv_from_rda(rda_path, version):
    """Extract CSV for a specific version from RDA file."""
    csv_path = Path("data") / f"hbcd_{version}.csv"
    print(f"Extracting version {version} to CSV...")

    r_script = f"""
load("{rda_path}")
if (!exists("lst_dds") || is.null(lst_dds$hbcd)) {{
  stop("No HBCD data found")
}}

hbcd <- lst_dds$hbcd
if (!"{version}" %in% names(hbcd)) {{
  stop("Version {version} not found in HBCD data")
}}

data <- hbcd[["{version}"]]
write.csv(data, "{csv_path}", row.names=FALSE)
cat("CSV created: {csv_path}\\n")
"""

    result = subprocess.run(
        ["Rscript", "-e", r_script],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error creating CSV: {result.stderr}")
        return None

    print(result.stdout)
    return csv_path


def convert_to_reproschema(csv_path, version):
    """Convert CSV to ReproSchema using reproschema-py."""
    print(f"Converting CSV to ReproSchema...")

    # Remove old output if exists
    output_dir = Path("HBCD")
    if output_dir.exists():
        shutil.rmtree(output_dir)

    yaml_path = Path("hbcd_nbdc2rs.yaml")

    result = subprocess.run(
        [
            "reproschema",
            "nbdc2reproschema",
            "--output-path", ".",
            str(csv_path),
            str(yaml_path)
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error during conversion: {result.stderr}")
        return False

    print(result.stdout)
    print(f"✓ Conversion complete for version {version}")
    return True


def commit_and_tag(version):
    """Commit changes and create git tag."""
    print(f"\n=== Committing and tagging version {version} ===")

    subprocess.run(["git", "config", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True
    )

    if not result.stdout.strip():
        print("No changes to commit")
        return

    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Convert HBCD release {version}"],
        check=True
    )
    subprocess.run(
        ["git", "tag", "-a", version, "-m", f"HBCD Release {version}"],
        check=True
    )
    subprocess.run(
        ["git", "push", "origin", "main", "--follow-tags"],
        check=True
    )

    print(f"✓ Committed and tagged version {version}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert HBCD data to ReproSchema (simplified)"
    )
    parser.add_argument(
        "--release",
        help="Specific version to convert (if not specified, converts all new versions)"
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Don't commit and tag (for testing)"
    )
    args = parser.parse_args()

    # Check R is available
    if not check_r_available():
        print("Error: Rscript not found. Please install R.")
        print("  Ubuntu/Debian: sudo apt-get install r-base")
        print("  macOS: brew install r")
        sys.exit(1)

    # Download RDA file (single file, fast)
    rda_path = download_rda()

    # Extract available versions
    all_versions = extract_versions_from_rda(rda_path)

    # Determine which versions to convert
    if args.release:
        if args.release not in all_versions:
            print(f"Error: Version {args.release} not found in RDA file")
            sys.exit(1)
        versions_to_convert = [args.release]
    else:
        existing_tags = get_existing_tags()
        versions_to_convert = find_new_versions(all_versions, existing_tags)

    if not versions_to_convert:
        print("No versions to convert")
        sys.exit(0)

    # Convert each version
    for version in versions_to_convert:
        csv_path = extract_csv_from_rda(rda_path, version)
        if not csv_path:
            continue

        success = convert_to_reproschema(csv_path, version)

        if success and not args.no_commit:
            commit_and_tag(version)

    print("\n✓ All conversions complete!")


if __name__ == "__main__":
    main()

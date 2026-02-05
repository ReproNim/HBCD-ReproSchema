# HBCD-ReproSchema

ReproSchema conversion for the **Healthy Brain and Child Development (HBCD)** Study data dictionary.

This repository converts HBCD data dictionaries from [NBDCtoolsData](https://github.com/nbdc-datahub/NBDCtoolsData) into [ReproSchema](https://github.com/ReproNim/reproschema) JSON-LD format.

## Overview

The HBCD Study is a large-scale longitudinal study examining brain and child development. This repository provides:

- Automated extraction of HBCD data dictionaries from NBDC format
- Conversion to standardized ReproSchema JSON-LD format
- Validation of generated schemas

## Usage

### Prerequisites

- Python 3.11+
- R 4.x
- Conda (recommended)

### Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_ORG/HBCD-ReproSchema.git
   cd HBCD-ReproSchema
   ```

2. Create the conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate nbdc-reproschema
   ```

3. Clone NBDCtoolsData:
   ```bash
   git clone https://github.com/nbdc-datahub/NBDCtoolsData.git
   ```

### Run Conversion

```bash
python scripts/convert.py --release <version>
```

Replace `<version>` with the HBCD release version (e.g., `1.0`).

### Validate Output

```bash
reproschema validate HBCD/
```

## Directory Structure

```
HBCD-ReproSchema/
├── HBCD/                           # Generated ReproSchema output
│   ├── HBCD/
│   │   └── HBCD_schema             # Protocol schema
│   └── activities/                 # Activity directories
│       └── [activity_name]/
│           ├── [activity]_schema
│           └── items/
├── scripts/
│   ├── convert.py                  # Main conversion wrapper
│   └── extract_release.R           # R extraction script
├── hbcd_nbdc2rs.yaml               # Protocol metadata
├── environment.yml                 # Conda environment
├── .github/workflows/
│   └── convert.yml                 # CI/CD workflow
├── .gitignore
├── LICENSE
└── README.md
```

## GitHub Actions

This repository includes a GitHub Actions workflow that can be manually triggered to convert a specific HBCD release:

1. Go to **Actions** tab
2. Select **Convert HBCD Releases**
3. Click **Run workflow**
4. Enter the release version
5. The workflow will extract, convert, validate, and commit the changes

## Related Projects

- [ABCD-ReproSchema](https://github.com/ReproNim/ABCD-ReproSchema) - Similar conversion for ABCD Study
- [reproschema-py](https://github.com/ReproNim/reproschema-py) - Python library for ReproSchema
- [NBDCtoolsData](https://github.com/nbdc-datahub/NBDCtoolsData) - Source data dictionaries

## License

See [LICENSE](LICENSE) file.

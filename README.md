# HBCD-ReproSchema

ReproSchema conversion of the **Healthy Brain and Child Development (HBCD)** Study data dictionary from [NBDC - NIH Brain Development Cohorts](https://github.com/nbdc-datahub/NBDCtoolsData).

## What is ReproSchema?

[ReproSchema](https://github.com/ReproNim/reproschema) is an open standard for creating machine-readable, reproducible assessments and data dictionaries. It uses JSON-LD format to describe surveys, questionnaires, and data collection instruments in a way that enables interoperability across studies and platforms.

> Chen Y, Jarecka D, Abraham S, Gau R, Ng E, Low D, Bevers I, Johnson A, Keshavan A, Klein A, Clucas J, Rosli Z, Hodge S, Linkersdorfer J, Bartsch H, Das S, Fair D, Kennedy D, Ghosh S. Standardizing Survey Data Collection to Enhance Reproducibility: Development and Comparative Evaluation of the ReproSchema Ecosystem. J Med Internet Res 2025;27:e63343. URL: https://www.jmir.org/2025/1/e63343. DOI: 10.2196/63343

## Repository Structure

```
HBCD-ReproSchema/
├── HBCD/                      # ReproSchema output
│   ├── HBCD_schema            # Protocol schema
│   └── activities/            # Activity directories
│       └── [activity_name]/
│           ├── [activity]_schema
│           └── items/
├── scripts/
│   ├── convert.py             # Conversion wrapper
│   └── extract_release.R      # Extraction script
├── hbcd_nbdc2rs.yaml          # Protocol metadata
├── .github/workflows/
│   └── convert.yml            # CI/CD workflow
└── README.md
```

## Related Projects

- [ABCD-ReproSchema](https://github.com/ReproNim/ABCD-ReproSchema) - ReproSchema conversion for ABCD Study
- [reproschema-py](https://github.com/ReproNim/reproschema-py) - Python library for ReproSchema
- [NBDCtoolsData](https://github.com/nbdc-datahub/NBDCtoolsData) - Source data dictionaries

## License

See [LICENSE](LICENSE) file.

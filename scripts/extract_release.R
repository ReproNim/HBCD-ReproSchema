#!/usr/bin/env Rscript
# Extract a specific HBCD release from lst_dds.rda to CSV
#
# Usage: Rscript extract_release.R <rda_path> <release_version> <output_csv>
# Example: Rscript extract_release.R NBDCtoolsData/data/lst_dds.rda 1.0 hbcd_1.0.csv

args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 3) {
  cat("Usage: Rscript extract_release.R <rda_path> <release_version> <output_csv>\n")
  quit(status = 1)
}

rda_path <- args[1]
release_version <- args[2]
output_csv <- args[3]

# Load required packages BEFORE loading the RDA file
# This is required for proper reconstruction of tibble objects from serialized format
if (requireNamespace("tibble", quietly = TRUE)) {
  library(tibble)
  cat("Loaded tibble package\n")
} else {
  cat("WARNING: tibble package not available - tibble columns may not load correctly\n")
}

# Load vctrs if available (needed for some tibble unpacking operations)
if (requireNamespace("vctrs", quietly = TRUE)) {
  library(vctrs)
  cat("Loaded vctrs package\n")
}

# Load dplyr if available (for collect() to materialize lazy tibbles)
if (requireNamespace("dplyr", quietly = TRUE)) {
  library(dplyr)
  cat("Loaded dplyr package\n")
}

cat(sprintf("R version: %s\n", R.version.string))
cat(sprintf("Loading: %s\n", rda_path))
load(rda_path)

cat(sprintf("Top-level objects: %s\n", paste(names(lst_dds), collapse = ", ")))

# Get HBCD data
if (!"hbcd" %in% names(lst_dds)) {
  cat("Available datasets in lst_dds:\n")
  print(names(lst_dds))
  stop("HBCD data not found in lst_dds")
}

hbcd_data <- lst_dds[["hbcd"]]
cat(sprintf("HBCD releases available: %s\n", paste(names(hbcd_data), collapse = ", ")))

# Find the release
release_key <- release_version
if (!release_key %in% names(hbcd_data)) {
  release_key <- paste0("hbcd_", release_version)
}
if (!release_key %in% names(hbcd_data)) {
  cat(sprintf("Error: Release '%s' not found\n", release_version))
  quit(status = 1)
}

cat(sprintf("Extracting release: %s\n", release_key))
release_data <- hbcd_data[[release_key]]

# Get dimensions before conversion
n_rows <- nrow(release_data)
n_cols <- ncol(release_data)
col_names <- names(release_data)
cat(sprintf("Original dimensions: %d rows x %d cols\n", n_rows, n_cols))

# Check if columns have 0 length (ALTREP/lazy column issue)
first_col_len <- length(release_data[[1]])
cat(sprintf("First column length: %d (expected: %d)\n", first_col_len, n_rows))

# Create output directory
output_dir <- dirname(output_csv)
if (output_dir != "." && !dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE)
}

# Try different materialization approaches
if (first_col_len == 0 && n_rows > 0) {
  cat("Detected 0-length columns - trying as.data.frame() conversion first...\n")

  # Approach 0: Try as.data.frame() FIRST - this is the most reliable
  # method for forcing ALTREP/lazy column materialization
  release_data <- tryCatch({
    converted <- as.data.frame(release_data, stringsAsFactors = FALSE)
    if (length(converted[[1]]) > 0) {
      cat(sprintf("as.data.frame() succeeded: %d x %d\n", nrow(converted), ncol(converted)))
      converted
    } else {
      stop("as.data.frame() did not materialize columns")
    }
  }, error = function(e) {
    cat(sprintf("as.data.frame() failed: %s\n", e$message))
    cat("Trying alternative extraction methods...\n")

    # Alternative: Extract column by column directly
    result_list <- lapply(col_names, function(cn) {
      cat(sprintf("  Extracting column: %s\n", cn))
      val <- release_data[[cn]]
      if (is.list(val)) {
        sapply(val, function(x) {
          if (is.null(x) || length(x) == 0) NA_character_
          else paste(as.character(x), collapse = "; ")
        })
      } else {
        as.character(val)
      }
    })
    names(result_list) <- col_names
    as.data.frame(result_list, stringsAsFactors = FALSE)
  })

  # Re-check length
  first_col_len <- length(release_data[[1]])
  if (first_col_len == 0) {
    stop("Failed to materialize columns - all extraction methods returned 0-length data")
  }
} else {
  # Standard conversion for normal tibbles
  cat("Converting tibble to data.frame...\n")
  release_data <- tryCatch({
    as.data.frame(release_data, stringsAsFactors = FALSE)
  }, error = function(e) {
    cat(sprintf("Standard conversion failed: %s\n", e$message))
    cat("Attempting column-by-column extraction...\n")

    result_list <- lapply(col_names, function(cn) {
      val <- release_data[[cn]]
      if (is.list(val)) {
        sapply(val, function(x) {
          if (is.null(x) || length(x) == 0) NA_character_
          else paste(as.character(x), collapse = "; ")
        })
      } else {
        as.character(val)
      }
    })
    names(result_list) <- col_names
    as.data.frame(result_list, stringsAsFactors = FALSE)
  })
}

# Handle any list columns
for (col in names(release_data)) {
  if (is.list(release_data[[col]])) {
    cat(sprintf("Converting list column: %s\n", col))
    release_data[[col]] <- sapply(release_data[[col]], function(x) {
      if (is.null(x) || length(x) == 0) NA_character_
      else paste(as.character(x), collapse = "; ")
    })
  }
}

# Diagnose structure
cat(sprintf("Dimensions: %d rows x %d cols\n", nrow(release_data), ncol(release_data)))

# Write to CSV
write.csv(release_data, output_csv, row.names = FALSE)

# Verify output
cat(sprintf("Verifying output: %s\n", output_csv))
final_data <- read.csv(output_csv, nrows = 10)
cat(sprintf("Output dimensions: %d+ rows x %d cols\n", nrow(final_data), ncol(final_data)))
cat(sprintf("Sample columns: %s\n", paste(head(names(final_data), 5), collapse = ", ")))

if ("name" %in% names(final_data)) {
  sample_names <- head(final_data$name[!is.na(final_data$name)], 3)
  cat(sprintf("Sample names: %s\n", paste(sample_names, collapse = ", ")))
}

cat("Done!\n")

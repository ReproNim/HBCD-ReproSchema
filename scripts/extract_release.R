#!/usr/bin/env Rscript
# Extract a specific HBCD release from lst_dds.rda to CSV
#
# Usage: Rscript extract_release.R <rda_path> <release_version> <output_csv>
# Example: Rscript extract_release.R NBDCtoolsData/data/lst_dds.rda 1.0 data/hbcd_1.0.csv

args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 3) {
  cat("Usage: Rscript extract_release.R <rda_path> <release_version> <output_csv>\n")
  quit(status = 1)
}

rda_path <- args[1]
release_version <- args[2]
output_csv <- args[3]

# Load tibble BEFORE loading RDA - required for proper deserialization
if (requireNamespace("tibble", quietly = TRUE)) {
  library(tibble)
  cat("Loaded tibble package\n")
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

# Get expected dimensions from row.names attribute
n_rows <- nrow(release_data)
n_cols <- ncol(release_data)
col_names <- names(release_data)
cat(sprintf("Dimensions: %d x %d\n", n_rows, n_cols))

# Check if columns have data
first_col_len <- length(release_data[[1]])
cat(sprintf("First column length: %d (expected: %d)\n", first_col_len, n_rows))

# Create output directory
output_dir <- dirname(output_csv)
if (output_dir != "." && !dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE)
}

# If columns are empty (GA Ubuntu issue), try alternative extraction methods
if (first_col_len == 0 && n_rows > 0) {
  cat("Columns appear empty - trying alternative extraction methods\n")

  # Method 1: Try direct write.csv on tibble (uses format.data.frame internally)
  cat("Method 1: Trying direct write.csv...\n")
  success <- tryCatch({
    write.csv(release_data, output_csv, row.names = FALSE)
    # Verify it wrote data
    test_read <- read.csv(output_csv, nrows = 5)
    if (nrow(test_read) > 0 && ncol(test_read) == n_cols) {
      cat("Direct write.csv succeeded!\n")
      TRUE
    } else {
      FALSE
    }
  }, error = function(e) {
    cat(sprintf("Direct write.csv failed: %s\n", e$message))
    FALSE
  })

  if (!success) {
    # Method 2: Use .subset2 to access raw list elements
    cat("Method 2: Trying .subset2 access...\n")
    success <- tryCatch({
      raw_list <- lapply(seq_len(n_cols), function(i) .subset2(release_data, i))
      names(raw_list) <- col_names
      first_len <- length(raw_list[[1]])
      cat(sprintf("  .subset2 first column length: %d\n", first_len))

      if (first_len > 0) {
        df <- as.data.frame(raw_list, stringsAsFactors = FALSE)
        write.csv(df, output_csv, row.names = FALSE)
        cat(".subset2 method succeeded!\n")
        TRUE
      } else {
        FALSE
      }
    }, error = function(e) {
      cat(sprintf(".subset2 method failed: %s\n", e$message))
      FALSE
    })
  }

  if (!success) {
    # Method 3: Unclass to raw list and rebuild
    cat("Method 3: Trying unclass...\n")
    success <- tryCatch({
      raw <- unclass(release_data)
      cat(sprintf("  Unclassed type: %s, length: %d\n", typeof(raw), length(raw)))
      first_len <- length(raw[[1]])
      cat(sprintf("  Unclassed first element length: %d\n", first_len))

      if (first_len > 0) {
        # Build data frame from raw list
        df <- data.frame(raw, stringsAsFactors = FALSE, check.names = FALSE)
        write.csv(df, output_csv, row.names = FALSE)
        cat("Unclass method succeeded!\n")
        TRUE
      } else {
        FALSE
      }
    }, error = function(e) {
      cat(sprintf("Unclass method failed: %s\n", e$message))
      FALSE
    })
  }

  if (!success) {
    # Method 4: format() each column and rebuild
    cat("Method 4: Trying format()...\n")
    success <- tryCatch({
      # format.data.frame accesses data differently
      formatted <- format(release_data)
      cat(sprintf("  Formatted dim: %d x %d\n", nrow(formatted), ncol(formatted)))
      if (nrow(formatted) > 0) {
        write.csv(formatted, output_csv, row.names = FALSE)
        cat("Format method succeeded!\n")
        TRUE
      } else {
        FALSE
      }
    }, error = function(e) {
      cat(sprintf("Format method failed: %s\n", e$message))
      FALSE
    })
  }

  if (!success) {
    # Method 5: Print to text and parse (last resort)
    cat("Method 5: Trying print capture...\n")
    success <- tryCatch({
      tmp_file <- tempfile(fileext = ".txt")
      sink(tmp_file)
      print(release_data, n = Inf, width = Inf)
      sink()

      # Read and parse the printed output
      lines <- readLines(tmp_file)
      unlink(tmp_file)

      cat(sprintf("  Captured %d lines\n", length(lines)))

      # This is fragile but might work as last resort
      if (length(lines) > 10) {
        cat("Print capture got data, but parsing not implemented\n")
      }
      FALSE
    }, error = function(e) {
      cat(sprintf("Print capture failed: %s\n", e$message))
      FALSE
    })
  }

  if (!success) {
    cat("ERROR: All extraction methods failed!\n")
    cat("This appears to be a tibble serialization incompatibility issue.\n")
    cat("The RDA file may need to be re-saved with a compatible R version.\n")
    quit(status = 1)
  }
} else {
  # Normal case - columns have data
  cat("Columns have data, using standard conversion\n")

  # Convert to plain data.frame, handling list columns
  result <- as.data.frame(release_data, stringsAsFactors = FALSE)

  # Handle any list columns
  for (col in names(result)) {
    if (is.list(result[[col]])) {
      cat(sprintf("Converting list column: %s\n", col))
      result[[col]] <- sapply(result[[col]], function(x) {
        if (is.null(x) || length(x) == 0) NA_character_
        else paste(as.character(x), collapse = "; ")
      })
    }
  }

  write.csv(result, output_csv, row.names = FALSE)
}

# Verify output
cat(sprintf("Verifying output: %s\n", output_csv))
final_data <- read.csv(output_csv, nrows = 10)
cat(sprintf("Output dimensions: %d+ rows x %d cols\n", nrow(final_data), ncol(final_data)))
cat(sprintf("Sample columns: %s\n", paste(head(names(final_data), 5), collapse = ", ")))

if ("name" %in% names(final_data)) {
  sample_names <- head(final_data$name[!is.na(final_data$name)], 3)
  cat(sprintf("Sample names: %s\n", paste(sample_names), collapse = ", "))
}

cat("Done!\n")

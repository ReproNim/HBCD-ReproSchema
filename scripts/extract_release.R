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
  cat("Detected 0-length columns - trying materialization approaches...\n")

  # Approach 1: Try dplyr::collect() to materialize lazy tibble
  if (requireNamespace("dplyr", quietly = TRUE)) {
    cat("Trying dplyr::collect()...\n")
    release_data <- tryCatch({
      collected <- dplyr::collect(release_data)
      if (length(collected[[1]]) > 0) {
        cat("dplyr::collect() succeeded\n")
        collected
      } else {
        stop("collect() did not materialize columns")
      }
    }, error = function(e) {
      cat(sprintf("dplyr::collect() failed: %s\n", e$message))
      release_data
    })
    first_col_len <- length(release_data[[1]])
  }

  # Approach 2: Try writing to tempfile and reading back
  if (first_col_len == 0 && n_rows > 0) {
    cat("Trying tempfile round-trip...\n")
    release_data <- tryCatch({
      tmp_file <- tempfile(fileext = ".rds")
      saveRDS(release_data, tmp_file)
      reloaded <- readRDS(tmp_file)
      unlink(tmp_file)
      if (length(reloaded[[1]]) > 0) {
        cat("Tempfile round-trip succeeded\n")
        reloaded
      } else {
        stop("Round-trip did not materialize columns")
      }
    }, error = function(e) {
      cat(sprintf("Tempfile round-trip failed: %s\n", e$message))
      release_data
    })
    first_col_len <- length(release_data[[1]])
  }

  # Approach 3: Force copy by modifying then reverting
  if (first_col_len == 0 && n_rows > 0) {
    cat("Trying force copy via modification...\n")
    release_data <- tryCatch({
      # Adding and removing a column forces a copy
      release_data[["__temp__"]] <- seq_len(n_rows)
      release_data[["__temp__"]] <- NULL
      if (length(release_data[[1]]) > 0) {
        cat("Force copy succeeded\n")
      }
      release_data
    }, error = function(e) {
      cat(sprintf("Force copy failed: %s\n", e$message))
      release_data
    })
    first_col_len <- length(release_data[[1]])
  }
}

# Re-check after materialization attempts
first_col_len <- length(release_data[[1]])
if (first_col_len == 0 && n_rows > 0) {
  cat("Detected 0-length columns in tibble - using row-by-row extraction\n")

  # Extract data row by row using tibble's [ indexing
  # This forces materialization of lazy columns
  result_list <- vector("list", n_cols)
  names(result_list) <- col_names

  # Initialize each column as the correct type
  for (j in seq_len(n_cols)) {
    result_list[[j]] <- vector("character", n_rows)
  }

  # Extract in chunks to avoid memory issues
  chunk_size <- 10000
  n_chunks <- ceiling(n_rows / chunk_size)

  for (chunk in seq_len(n_chunks)) {
    start_row <- (chunk - 1) * chunk_size + 1
    end_row <- min(chunk * chunk_size, n_rows)
    cat(sprintf("Processing rows %d-%d of %d...\n", start_row, end_row, n_rows))

    # Extract this chunk of rows - this forces materialization
    chunk_data <- release_data[start_row:end_row, , drop = FALSE]

    # Convert chunk to data.frame (should work on smaller subsets)
    chunk_df <- tryCatch({
      as.data.frame(chunk_data, stringsAsFactors = FALSE)
    }, error = function(e) {
      # If that fails, extract column by column from the chunk
      temp_list <- lapply(col_names, function(cn) {
        val <- chunk_data[[cn]]
        if (is.list(val)) {
          sapply(val, function(x) {
            if (is.null(x) || length(x) == 0) NA_character_
            else paste(as.character(x), collapse = "; ")
          })
        } else {
          as.character(val)
        }
      })
      names(temp_list) <- col_names
      as.data.frame(temp_list, stringsAsFactors = FALSE)
    })

    # Store in result
    for (j in seq_len(n_cols)) {
      result_list[[j]][start_row:end_row] <- as.character(chunk_df[[j]])
    }
  }

  release_data <- as.data.frame(result_list, stringsAsFactors = FALSE)
  cat(sprintf("Row-by-row extraction complete: %d x %d\n",
              nrow(release_data), ncol(release_data)))
} else {
  # Standard conversion
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

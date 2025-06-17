#!/usr/bin/env Rscript

# Install R dependencies for cross-validation testing

# Function to install packages if not already installed
install_if_missing <- function(packages) {
  new_packages <- packages[!(packages %in% installed.packages()[,"Package"])]
  if(length(new_packages)) {
    install.packages(new_packages, repos = "https://cloud.r-project.org/")
  }
}

# List of required packages
required_packages <- c(
  "cancensus",      # Main package to test against
  "testthat",       # Testing framework
  "jsonlite",       # JSON handling
  "httr",           # HTTP requests
  "sf",             # Spatial data
  "dplyr",          # Data manipulation
  "tidyr",          # Data tidying
  "purrr",          # Functional programming
  "readr",          # Data reading
  "tibble",         # Modern data frames
  "microbenchmark", # Performance testing
  "ggplot2",        # Visualization
  "here"            # Path management
)

# Install packages
cat("Installing R dependencies for cross-validation testing...\n")
install_if_missing(required_packages)

# Verify installation
for (pkg in required_packages) {
  if (pkg %in% installed.packages()[,"Package"]) {
    cat(sprintf("✓ %s installed successfully\n", pkg))
  } else {
    cat(sprintf("✗ Failed to install %s\n", pkg))
  }
}

cat("\nR dependency installation complete!\n")
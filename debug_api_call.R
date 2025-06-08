#!/usr/bin/env Rscript

# Debug script to show exact API call parameters from R cancensus package
library(cancensus)
library(httr)
library(jsonlite)

# Set API key (replace with your key)
Sys.setenv(CM_API_KEY = "CensusMapper_7cb8d0ee55b67305388e0a7e8ba9c725")

cat("=== R Package API Call Debug ===\n\n")

# Test parameters
dataset <- "CA16"
regions <- list(CMA="59933")
vectors <- c("v_CA16_408", "v_CA16_409", "v_CA16_410")
level <- "CSD"
api_key <- Sys.getenv("CM_API_KEY")

cat("Input parameters:\n")
cat("dataset:", dataset, "\n")
cat("regions:", capture.output(dput(regions)), "\n")
cat("vectors:", capture.output(dput(vectors)), "\n")
cat("level:", level, "\n")
cat("api_key:", substr(api_key, 1, 8), "...\n\n")

# Show how cancensus processes these parameters
cat("Parameter processing:\n")

# Convert regions like cancensus does
regions_json <- jsonlite::toJSON(lapply(regions, as.character))
cat("regions (JSON):", regions_json, "\n")

# Convert vectors like cancensus does  
vectors_json <- jsonlite::toJSON(vectors)
cat("vectors (JSON):", vectors_json, "\n\n")

# Build the exact params list that cancensus would send
params <- list(
  regions = as.character(regions_json),
  vectors = as.character(vectors_json),
  level = level,
  dataset = dataset,
  api_key = api_key
)

cat("Final params list for POST body:\n")
for(name in names(params)) {
  cat(name, "=", params[[name]], "\n")
}

cat("\nBase URL: https://censusmapper.ca/api/v1/\n")
cat("Endpoint: data.csv\n")
cat("Method: POST\n\n")

# Enable verbose HTTP output to see actual request
cat("Making actual API call with verbose output...\n")
cat("==========================================\n")

# Set verbose mode to see HTTP traffic
httr::set_config(httr::verbose())

# Make the actual call
tryCatch({
  data <- get_census(
    dataset = dataset,
    regions = regions,
    vectors = vectors,
    level = level,
    quiet = FALSE
  )
  cat("\n==========================================\n")
  cat("SUCCESS! Retrieved", nrow(data), "rows\n")
  cat("Columns:", paste(colnames(data), collapse=", "), "\n")
}, error = function(e) {
  cat("\n==========================================\n")
  cat("ERROR:", e$message, "\n")
})
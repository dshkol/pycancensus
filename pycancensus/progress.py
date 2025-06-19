"""
Progress indicators and download monitoring for pycancensus.

Provides visual feedback for long-running operations like large data downloads.
"""

import time
import sys
from typing import Optional, Union


class ProgressIndicator:
    """Simple progress indicator for console output."""

    def __init__(self, description: str = "Processing", show_spinner: bool = True):
        self.description = description
        self.show_spinner = show_spinner
        self.start_time = None
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.spinner_idx = 0

    def start(self):
        """Start the progress indicator."""
        self.start_time = time.time()
        if self.show_spinner:
            print(f"{self.description}...", end=" ", flush=True)

    def update(self, status: Optional[str] = None):
        """Update the progress indicator."""
        if not self.show_spinner or self.start_time is None:
            return

        # Update spinner
        spinner = self.spinner_chars[self.spinner_idx % len(self.spinner_chars)]
        self.spinner_idx += 1

        # Show elapsed time
        elapsed = time.time() - self.start_time

        if status:
            print(
                f"\r{spinner} {self.description} - {status} ({elapsed:.1f}s)",
                end="",
                flush=True,
            )
        else:
            print(
                f"\r{spinner} {self.description}... ({elapsed:.1f}s)",
                end="",
                flush=True,
            )

    def finish(self, final_message: Optional[str] = None):
        """Finish the progress indicator."""
        if self.start_time is None:
            return

        elapsed = time.time() - self.start_time

        if final_message:
            print(f"\r✅ {final_message} ({elapsed:.1f}s)")
        else:
            print(f"\r✅ {self.description} complete ({elapsed:.1f}s)")


class DataSizeEstimator:
    """Estimate download time and size based on request parameters."""

    @staticmethod
    def estimate_request_size(
        num_regions: int, num_vectors: int, level: str, geo_format: Optional[str] = None
    ) -> dict:
        """
        Estimate the size and complexity of a data request.

        Parameters
        ----------
        num_regions : int
            Number of regions being requested
        num_vectors : int
            Number of vectors (variables) being requested
        level : str
            Geographic level (affects number of result rows)
        geo_format : str, optional
            Whether geography is included

        Returns
        -------
        dict
            Estimation details including size category and expected time
        """
        # Rough estimates based on level complexity
        level_multipliers = {
            "PR": 1,  # Provinces/Territories (13-14 rows typically)
            "CMA": 5,  # Census Metropolitan Areas (~40 CMAs)
            "CD": 20,  # Census Divisions (~300 CDs)
            "CSD": 100,  # Census Subdivisions (~5000 CSDs)
            "CT": 200,  # Census Tracts (~5500 CTs)
            "DA": 1000,  # Dissemination Areas (~57000 DAs)
            "DB": 5000,  # Dissemination Blocks (~500000 DBs)
        }

        base_rows = level_multipliers.get(level, 100) * num_regions
        total_data_points = base_rows * max(num_vectors, 1)

        # Size categories
        if total_data_points < 1000:
            size_category = "small"
            expected_time = "< 5 seconds"
        elif total_data_points < 10000:
            size_category = "medium"
            expected_time = "5-15 seconds"
        elif total_data_points < 100000:
            size_category = "large"
            expected_time = "15-60 seconds"
        else:
            size_category = "very_large"
            expected_time = "> 1 minute"

        # Geography adds complexity
        if geo_format == "geopandas":
            if size_category == "small":
                size_category = "medium"
                expected_time = "5-15 seconds"
            elif size_category == "medium":
                size_category = "large"
                expected_time = "15-60 seconds"
            elif size_category == "large":
                expected_time = "> 1 minute"

        return {
            "size_category": size_category,
            "expected_time": expected_time,
            "estimated_rows": base_rows,
            "estimated_data_points": total_data_points,
            "includes_geography": geo_format == "geopandas",
        }


def show_request_preview(
    regions: dict,
    vectors: list,
    level: str,
    dataset: str,
    geo_format: Optional[str] = None,
    quiet: bool = False,
):
    """
    Show a preview of what will be downloaded before making the request.

    Parameters
    ----------
    regions : dict
        Region specification
    vectors : list
        List of vector codes
    level : str
        Geographic level
    dataset : str
        Dataset identifier
    geo_format : str, optional
        Geographic format
    quiet : bool
        Whether to suppress output
    """
    if quiet:
        return

    # Count regions
    total_regions = sum(len(v) if isinstance(v, list) else 1 for v in regions.values())

    # Estimate request
    estimate = DataSizeEstimator.estimate_request_size(
        num_regions=total_regions,
        num_vectors=len(vectors) if vectors else 0,
        level=level,
        geo_format=geo_format,
    )

    print(f"📋 Request Preview:")
    print(f"   Dataset: {dataset}")
    print(f"   Level: {level}")
    print(f"   Regions: {total_regions} region(s)")
    if vectors:
        print(f"   Variables: {len(vectors)} vector(s)")
    if geo_format:
        print(f"   Geography: {geo_format}")

    print(
        f"🔍 Estimated Size: {estimate['size_category']} ({estimate['estimated_rows']:,} rows)"
    )
    print(f"⏱️  Expected Time: {estimate['expected_time']}")

    if estimate["size_category"] in ["large", "very_large"]:
        print(f"⚠️  Large request detected - please be patient...")


def create_progress_for_request(
    regions: dict, vectors: list, level: str, geo_format: Optional[str] = None
) -> Optional[ProgressIndicator]:
    """
    Create an appropriate progress indicator for a data request.

    Parameters
    ----------
    regions : dict
        Region specification
    vectors : list
        Vector list
    level : str
        Geographic level
    geo_format : str, optional
        Geographic format

    Returns
    -------
    ProgressIndicator or None
        Progress indicator for large requests, None for small ones
    """
    total_regions = sum(len(v) if isinstance(v, list) else 1 for v in regions.values())

    estimate = DataSizeEstimator.estimate_request_size(
        num_regions=total_regions,
        num_vectors=len(vectors) if vectors else 0,
        level=level,
        geo_format=geo_format,
    )

    # Only show progress for medium+ requests
    if estimate["size_category"] in ["medium", "large", "very_large"]:
        if geo_format == "geopandas":
            description = (
                f"Downloading {estimate['estimated_rows']:,} regions with geography"
            )
        else:
            description = f"Downloading {estimate['estimated_rows']:,} regions"
        return ProgressIndicator(description, show_spinner=True)

    return None


# Convenience function for backwards compatibility
def show_download_progress(
    description: str = "Downloading data", show_spinner: bool = True
) -> ProgressIndicator:
    """Create a simple progress indicator."""
    return ProgressIndicator(description, show_spinner)

"""
Utility functions for pycancensus.
"""

from typing import Dict, List, Union


def validate_dataset(dataset: str) -> str:
    """
    Validate and normalize dataset identifier.

    Parameters
    ----------
    dataset : str
        Dataset identifier like 'CA16', 'CA21', etc.

    Returns
    -------
    str
        Validated dataset identifier.

    Raises
    ------
    ValueError
        If dataset format is invalid.
    """
    if not isinstance(dataset, str):
        raise ValueError("Dataset must be a string")

    dataset = dataset.upper().strip()

    # Basic validation - should be like CA16, CA21, etc.
    if not dataset.startswith("CA") or len(dataset) != 4:
        raise ValueError(
            f"Invalid dataset format: {dataset}. "
            "Expected format like 'CA16', 'CA21', etc."
        )

    return dataset


def validate_level(level: str) -> str:
    """
    Validate census aggregation level.

    Parameters
    ----------
    level : str
        Census aggregation level.

    Returns
    -------
    str
        Validated level.

    Raises
    ------
    ValueError
        If level is invalid.
    """
    valid_levels = ["C", "Regions", "PR", "CMA", "CD", "CSD", "CT", "DA", "EA", "DB"]

    if level not in valid_levels:
        raise ValueError(
            f"Invalid level: {level}. " f"Valid levels are: {', '.join(valid_levels)}"
        )

    return level


def process_regions(
    regions: Dict[str, Union[str, List[str]]],
) -> Dict[str, Union[str, List[str]]]:
    """
    Process and validate regions dictionary.

    Parameters
    ----------
    regions : dict
        Dictionary mapping region levels to region IDs.

    Returns
    -------
    dict
        Processed regions dictionary.

    Raises
    ------
    ValueError
        If regions format is invalid.
    """
    if not isinstance(regions, dict):
        raise ValueError("Regions must be a dictionary")

    if not regions:
        raise ValueError("At least one region must be specified")

    valid_region_levels = ["C", "PR", "CMA", "CD", "CSD", "CT", "DA", "EA", "DB"]

    processed = {}
    for level, ids in regions.items():
        if level not in valid_region_levels:
            raise ValueError(
                f"Invalid region level: {level}. "
                f"Valid levels are: {', '.join(valid_region_levels)}"
            )

        # Ensure IDs are strings
        if isinstance(ids, (int, str)):
            processed[level] = str(ids)
        elif isinstance(ids, list):
            processed[level] = [str(id_) for id_ in ids]
        else:
            raise ValueError(f"Invalid region IDs format for {level}")

    return processed


def format_vector_labels(
    vectors_data: List[Dict], labels: str = "detailed"
) -> Dict[str, str]:
    """
    Format vector labels based on the labels parameter.

    Parameters
    ----------
    vectors_data : list of dict
        Vector metadata from API.
    labels : str
        Label format - 'detailed' or 'short'.

    Returns
    -------
    dict
        Mapping of vector IDs to formatted labels.
    """
    label_map = {}

    for vector in vectors_data:
        vector_id = vector.get("vector")
        if not vector_id:
            continue

        if labels == "short":
            label = vector.get("label", vector_id)
        else:  # detailed
            label = vector.get("details", vector.get("label", vector_id))

        label_map[vector_id] = label

    return label_map

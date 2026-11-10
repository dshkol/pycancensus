"""
Utility functions for pycancensus.
"""

import re
from typing import Dict, List, Union


# Census years accepted in place of dataset IDs, as in R cancensus
_DATASET_YEAR_ALIASES = {
    "1996": "CA1996",
    "2001": "CA01",
    "2006": "CA06",
    "2011": "CA11",
    "2016": "CA16",
    "2021": "CA21",
}

# CensusMapper dataset IDs: censuses (CA16, CA1996), cross-tabulations
# (CA16xSD) and taxfiler data (TX2018)
_DATASET_PATTERN = re.compile(r"(CA|TX)(\d{2}|\d{4})(XSD)?", re.IGNORECASE)


def validate_dataset(dataset: Union[str, int]) -> str:
    """
    Validate and normalize dataset identifier.

    Parameters
    ----------
    dataset : str or int
        Dataset identifier like 'CA21', 'CA1996', 'CA16xSD' or 'TX2018'
        (see list_census_datasets()). Matching ignores case. A census year
        such as 2021 or '2021' is translated to its dataset ID, like R
        cancensus does.

    Returns
    -------
    str
        Dataset identifier as CensusMapper spells it.

    Raises
    ------
    ValueError
        If dataset format is invalid.
    """
    if isinstance(dataset, int) and not isinstance(dataset, bool):
        dataset = str(dataset)
    if not isinstance(dataset, str):
        raise ValueError("Dataset must be a string")

    dataset = dataset.strip()
    if dataset in _DATASET_YEAR_ALIASES:
        return _DATASET_YEAR_ALIASES[dataset]

    match = _DATASET_PATTERN.fullmatch(dataset)
    if not match:
        raise ValueError(
            f"Invalid dataset format: {dataset}. Expected an ID like 'CA21', "
            "'CA1996', 'CA16xSD' or 'TX2018'; see list_census_datasets()."
        )
    prefix, digits, cross_tab = match.groups()
    return prefix.upper() + digits + ("xSD" if cross_tab else "")


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
    valid_levels = [
        "C",
        "Regions",
        "PR",
        "CMA",
        "CA",
        "CMACA",
        "CD",
        "CSD",
        "CT",
        "DA",
        "EA",
        "DB",
    ]

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

    # "CMA", "CA" and "CMACA" all name the same level, which holds both census
    # metropolitan areas and census agglomerations (as in R cancensus 0.6.2)
    valid_region_levels = [
        "C",
        "PR",
        "CMA",
        "CA",
        "CMACA",
        "CD",
        "CSD",
        "CT",
        "DA",
        "EA",
        "DB",
    ]

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

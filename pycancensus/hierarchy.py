"""Vector hierarchy navigation functions for pycancensus."""

import pandas as pd
import requests
from typing import List, Dict, Optional, Union
import warnings

from .settings import get_api_key
from .utils import validate_dataset
from .cache import get_cached_data, cache_data


def parent_census_vectors(
    vectors: Union[str, List[str]],
    dataset: Optional[str] = None,
    use_cache: bool = True,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get parent vectors for given child vectors.

    Parameters
    ----------
    vectors : str or list of str
        Vector IDs to find parents for
    dataset : str, optional
        Dataset to search in. If None, inferred from vectors
    use_cache : bool, default True
        Whether to use cached data if available
    api_key : str, optional
        API key for CensusMapper API

    Returns
    -------
    pd.DataFrame
        DataFrame with parent vector information
    """
    # Ensure vectors is a list
    if isinstance(vectors, str):
        vectors = [vectors]

    if not vectors:
        return pd.DataFrame()

    # Infer dataset if not provided
    if dataset is None:
        try:
            dataset = vectors[0].split("_")[1]
        except (IndexError, AttributeError):
            raise ValueError("Dataset must be specified or inferable from vectors")

    dataset = validate_dataset(dataset)

    if api_key is None:
        api_key = get_api_key()
        if api_key is None:
            raise ValueError(
                "API key required. Set with set_api_key() or CANCENSUS_API_KEY "
                "environment variable."
            )

    # Check cache first
    cache_key = f"parent_vectors_{dataset}_{'-'.join(sorted(vectors))}"
    if use_cache:
        cached_data = get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data

    # Get all vectors for the dataset to build hierarchy
    from .vectors import list_census_vectors

    try:
        all_vectors = list_census_vectors(dataset, use_cache=use_cache, api_key=api_key)
    except Exception as e:
        warnings.warn(f"Could not retrieve vector list for hierarchy: {e}")
        return pd.DataFrame()

    # Filter for parent vectors
    parent_vectors = []

    for vector in vectors:
        if "parent_vector" in all_vectors.columns:
            # Find direct parents
            matches = all_vectors[all_vectors["vector"] == vector]
            if not matches.empty and pd.notna(matches.iloc[0]["parent_vector"]):
                parent_id = matches.iloc[0]["parent_vector"]
                parent_info = all_vectors[all_vectors["vector"] == parent_id]
                if not parent_info.empty:
                    parent_vectors.append(parent_info.iloc[0].to_dict())
        else:
            # Fallback: try to infer parent from vector naming patterns
            parent_candidate = _infer_parent_vector(vector, all_vectors)
            if parent_candidate is not None:
                parent_vectors.append(parent_candidate)

    result = pd.DataFrame(parent_vectors).drop_duplicates()

    # Cache the result
    if use_cache and not result.empty:
        cache_data(cache_key, result)

    return result


def child_census_vectors(
    vectors: Union[str, List[str]],
    dataset: Optional[str] = None,
    use_cache: bool = True,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get child vectors for given parent vectors.

    Parameters
    ----------
    vectors : str or list of str
        Parent vector IDs
    dataset : str, optional
        Dataset to search in
    use_cache : bool, default True
        Whether to use cached data if available
    api_key : str, optional
        API key for CensusMapper API

    Returns
    -------
    pd.DataFrame
        DataFrame with child vector information
    """
    # Ensure vectors is a list
    if isinstance(vectors, str):
        vectors = [vectors]

    if not vectors:
        return pd.DataFrame()

    # Infer dataset if not provided
    if dataset is None:
        try:
            dataset = vectors[0].split("_")[1]
        except (IndexError, AttributeError):
            raise ValueError("Dataset must be specified or inferable from vectors")

    dataset = validate_dataset(dataset)

    if api_key is None:
        api_key = get_api_key()
        if api_key is None:
            raise ValueError(
                "API key required. Set with set_api_key() or CANCENSUS_API_KEY "
                "environment variable."
            )

    # Check cache first
    cache_key = f"child_vectors_{dataset}_{'-'.join(sorted(vectors))}"
    if use_cache:
        cached_data = get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data

    # Get all vectors for the dataset to build hierarchy
    from .vectors import list_census_vectors

    try:
        all_vectors = list_census_vectors(dataset, use_cache=use_cache, api_key=api_key)
    except Exception as e:
        warnings.warn(f"Could not retrieve vector list for hierarchy: {e}")
        return pd.DataFrame()

    # Filter for child vectors
    child_vectors = []

    for vector in vectors:
        if "parent_vector" in all_vectors.columns:
            # Find direct children
            children = all_vectors[all_vectors["parent_vector"] == vector]
            for _, child in children.iterrows():
                child_vectors.append(child.to_dict())
        else:
            # Fallback: try to infer children from vector naming patterns
            children_candidates = _infer_child_vectors(vector, all_vectors)
            child_vectors.extend(children_candidates)

    result = pd.DataFrame(child_vectors).drop_duplicates()

    # Cache the result
    if use_cache and not result.empty:
        cache_data(cache_key, result)

    return result


def find_census_vectors(
    dataset: str,
    query: str,
    search_type: str = "keyword",
    use_cache: bool = True,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Enhanced vector search with multiple search types.

    Parameters
    ----------
    dataset : str
        Dataset to search in
    query : str
        Search query
    search_type : str, default "keyword"
        Type of search: "keyword", "exact", "regex"
    use_cache : bool, default True
        Whether to use cached data if available
    api_key : str, optional
        API key for CensusMapper API

    Returns
    -------
    pd.DataFrame
        Matching vectors with relevance information
    """
    dataset = validate_dataset(dataset)

    # Get all vectors for the dataset
    from .vectors import list_census_vectors

    try:
        all_vectors = list_census_vectors(dataset, use_cache=use_cache, api_key=api_key)
    except Exception as e:
        warnings.warn(f"Could not retrieve vector list for search: {e}")
        return pd.DataFrame()

    if all_vectors.empty:
        return pd.DataFrame()

    # Perform search based on type
    query_lower = query.lower()

    if search_type == "exact":
        # Exact match in label or vector ID
        mask = (all_vectors["vector"].str.lower() == query_lower) | (
            all_vectors["label"].str.lower() == query_lower
        )
    elif search_type == "regex":
        # Regex search
        import re

        try:
            pattern = re.compile(query, re.IGNORECASE)
            mask = all_vectors["label"].str.contains(pattern, na=False) | all_vectors[
                "vector"
            ].str.contains(pattern, na=False)
            if "details" in all_vectors.columns:
                mask |= all_vectors["details"].str.contains(pattern, na=False)
        except re.error:
            warnings.warn(f"Invalid regex pattern: {query}")
            return pd.DataFrame()
    else:  # keyword search (default)
        # Keyword search in label and details
        mask = all_vectors["label"].str.contains(query, case=False, na=False)
        if "details" in all_vectors.columns:
            mask |= all_vectors["details"].str.contains(query, case=False, na=False)

    result = all_vectors[mask].copy()

    if not result.empty:
        # Add relevance scoring
        result["relevance_score"] = 0.0

        # Higher score for matches in vector ID
        vector_match = result["vector"].str.contains(query, case=False, na=False)
        result.loc[vector_match, "relevance_score"] += 10

        # Higher score for matches in label
        label_match = result["label"].str.contains(query, case=False, na=False)
        result.loc[label_match, "relevance_score"] += 5

        # Sort by relevance score
        result = result.sort_values("relevance_score", ascending=False)

    return result


def _infer_parent_vector(vector: str, all_vectors: pd.DataFrame) -> Optional[Dict]:
    """
    Infer parent vector from naming patterns.

    This is a fallback when explicit parent_vector column is not available.
    """
    # Extract the numeric part of the vector ID
    import re

    match = re.match(r"(v_[A-Z0-9]+_)(\d+)", vector)
    if not match:
        return None

    prefix, number = match.groups()
    vector_num = int(number)

    # Look for parent patterns (shorter vector numbers often indicate parents)
    for potential_parent_num in range(1, vector_num):
        potential_parent = f"{prefix}{potential_parent_num}"
        parent_match = all_vectors[all_vectors["vector"] == potential_parent]

        if not parent_match.empty:
            # Check if this could be a reasonable parent based on naming
            parent_label = parent_match.iloc[0].get("label", "").lower()
            current_label = (
                all_vectors[all_vectors["vector"] == vector]["label"].iloc[0].lower()
            )

            # Simple heuristic: if parent label is contained in current label
            if parent_label and parent_label in current_label:
                return parent_match.iloc[0].to_dict()

    return None


def _infer_child_vectors(vector: str, all_vectors: pd.DataFrame) -> List[Dict]:
    """
    Infer child vectors from naming patterns.

    This is a fallback when explicit parent_vector column is not available.
    """
    import re

    match = re.match(r"(v_[A-Z0-9]+_)(\d+)", vector)
    if not match:
        return []

    prefix, number = match.groups()
    vector_num = int(number)

    # Get current vector label for comparison
    current_match = all_vectors[all_vectors["vector"] == vector]
    if current_match.empty:
        return []

    current_label = current_match.iloc[0].get("label", "").lower()
    children = []

    # Look for child patterns (higher vector numbers that might be children)
    max_search = min(
        vector_num + 1000,
        all_vectors["vector"].str.extract(r"v_[A-Z0-9]+_(\d+)")[0].astype(int).max(),
    )

    for potential_child_num in range(vector_num + 1, max_search + 1):
        potential_child = f"{prefix}{potential_child_num}"
        child_match = all_vectors[all_vectors["vector"] == potential_child]

        if not child_match.empty:
            child_label = child_match.iloc[0].get("label", "").lower()

            # Simple heuristic: if current label is contained in child label
            if current_label and current_label in child_label:
                children.append(child_match.iloc[0].to_dict())

                # Limit to reasonable number of children
                if len(children) >= 50:
                    break

    return children

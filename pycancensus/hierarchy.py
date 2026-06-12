"""Vector hierarchy navigation functions for pycancensus."""

import re
import warnings
from typing import Dict, List, Optional, Union

import pandas as pd

from .utils import validate_dataset


def _clean_vector_input(vectors: Union[str, List[str], pd.DataFrame]) -> List[str]:
    """Normalize vector input (string, list, or DataFrame) to a list of IDs."""
    if isinstance(vectors, pd.DataFrame):
        if "vector" not in vectors.columns:
            raise ValueError("DataFrame input must have a 'vector' column")
        return vectors["vector"].tolist()
    if isinstance(vectors, str):
        return [vectors]
    return list(vectors)


def _dataset_from_vectors(vector_ids: List[str]) -> str:
    """Infer the dataset from vector IDs, requiring all to agree."""
    try:
        datasets = {v.split("_")[1] for v in vector_ids}
    except (IndexError, AttributeError):
        raise ValueError("Unable to determine dataset")
    if len(datasets) != 1:
        raise ValueError("Unable to determine dataset")
    return datasets.pop()


def _get_all_vectors(dataset, use_cache, api_key) -> Optional[pd.DataFrame]:
    """Fetch the full vector list for a dataset, warning on failure."""
    from .vectors import list_census_vectors

    try:
        all_vectors = list_census_vectors(
            dataset, use_cache=use_cache, quiet=True, api_key=api_key
        )
    except ValueError:
        # Configuration problems (e.g. missing API key) should surface
        raise
    except Exception as e:
        warnings.warn(f"Could not retrieve vector list for hierarchy: {e}")
        return None
    if "parent_vector" not in all_vectors.columns:
        warnings.warn("Vector list has no parent_vector column; cannot traverse")
        return None
    return all_vectors


def parent_census_vectors(
    vectors: Union[str, List[str], pd.DataFrame],
    dataset: Optional[str] = None,
    use_cache: bool = True,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get all parent vectors up the hierarchy for given vectors.

    Traverses the full vector hierarchy upward (matching R cancensus),
    returning every ancestor of the input vectors, not just direct parents.

    Parameters
    ----------
    vectors : str, list of str, or pd.DataFrame
        Vector IDs to find parents for, or a DataFrame as returned by
        list_census_vectors() with a 'vector' column
    dataset : str, optional
        Dataset to search in. If None, inferred from vectors; all input
        vectors must then belong to the same dataset
    use_cache : bool, default True
        Whether to use cached data if available
    api_key : str, optional
        API key for CensusMapper API

    Returns
    -------
    pd.DataFrame
        DataFrame with ancestor vector information, in discovery order
        (direct parents first, then grandparents, and so on)
    """
    vector_ids = _clean_vector_input(vectors)
    if not vector_ids:
        return pd.DataFrame()

    if dataset is None:
        dataset = _dataset_from_vectors(vector_ids)
    dataset = validate_dataset(dataset)

    all_vectors = _get_all_vectors(dataset, use_cache, api_key)
    if all_vectors is None:
        return pd.DataFrame()

    # Hash-based BFS upward over plain dicts/sets, matching the R package's
    # traversal: `seen` accumulates ancestors in discovery order.
    parent_of = dict(zip(all_vectors["vector"], all_vectors["parent_vector"]))
    known = set(parent_of)

    seen: List[str] = []
    seen_set = set()
    frontier = vector_ids
    while frontier:
        new_vecs = []
        for v in frontier:
            parent = parent_of.get(v)
            if pd.notna(parent) and parent in known and parent not in seen_set:
                seen_set.add(parent)
                new_vecs.append(parent)
        seen.extend(new_vecs)
        frontier = new_vecs

    if not seen:
        return pd.DataFrame(columns=all_vectors.columns)

    return all_vectors.set_index("vector").loc[seen].reset_index()[all_vectors.columns]


def child_census_vectors(
    vectors: Union[str, List[str], pd.DataFrame],
    dataset: Optional[str] = None,
    use_cache: bool = True,
    api_key: Optional[str] = None,
    leaves_only: bool = False,
    max_level: Optional[int] = None,
    keep_parent: bool = False,
) -> pd.DataFrame:
    """
    Get all child vectors down the hierarchy for given vectors.

    Traverses the full vector hierarchy downward (matching R cancensus),
    returning every descendant of the input vectors, not just direct
    children.

    Parameters
    ----------
    vectors : str, list of str, or pd.DataFrame
        Parent vector IDs, or a DataFrame as returned by
        list_census_vectors() with a 'vector' column
    dataset : str, optional
        Dataset to search in. If None, inferred from vectors; all input
        vectors must then belong to the same dataset
    use_cache : bool, default True
        Whether to use cached data if available
    api_key : str, optional
        API key for CensusMapper API
    leaves_only : bool, default False
        Only return terminal vectors that themselves have no children
    max_level : int, optional
        Maximum depth to traverse. Default traverses the full hierarchy;
        max_level=1 returns only direct children
    keep_parent : bool, default False
        Also include the input vectors in the result

    Returns
    -------
    pd.DataFrame
        DataFrame with descendant vector information, in discovery order
        (direct children first, then grandchildren, and so on)
    """
    vector_ids = _clean_vector_input(vectors)
    if not vector_ids:
        return pd.DataFrame()

    if dataset is None:
        dataset = _dataset_from_vectors(vector_ids)
    dataset = validate_dataset(dataset)

    all_vectors = _get_all_vectors(dataset, use_cache, api_key)
    if all_vectors is None:
        return pd.DataFrame()

    # Hash-based BFS downward, matching the R package's traversal.
    children_of: Dict[str, List[str]] = {}
    for child, parent in zip(all_vectors["vector"], all_vectors["parent_vector"]):
        if pd.notna(parent):
            children_of.setdefault(parent, []).append(child)

    seen: List[str] = []
    seen_set = set()
    frontier = vector_ids
    level = 0
    while frontier and (max_level is None or level < max_level):
        level += 1
        new_vecs = []
        for v in frontier:
            for child in children_of.get(v, []):
                if child not in seen_set:
                    seen_set.add(child)
                    new_vecs.append(child)
        if not new_vecs:
            break
        seen.extend(new_vecs)
        frontier = new_vecs

    if leaves_only:
        seen = [v for v in seen if v not in children_of]

    if keep_parent:
        valid_inputs = set(all_vectors["vector"])
        seen = [v for v in vector_ids if v in valid_inputs] + seen

    if not seen:
        return pd.DataFrame(columns=all_vectors.columns)

    return all_vectors.set_index("vector").loc[seen].reset_index()[all_vectors.columns]


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

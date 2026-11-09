"""Vector hierarchy navigation functions for pycancensus."""

import warnings
from typing import Dict, List, Optional, Union

import pandas as pd

from .settings import get_language, validate_language
from .utils import validate_dataset


def _with_attrs(df: pd.DataFrame, dataset: str, language: str) -> pd.DataFrame:
    """Record the dataset and language of a vector list, like R."""
    df.attrs["dataset"] = dataset
    df.attrs["language"] = language
    return df


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


def _vector_list_language(vectors, language: Optional[str] = None) -> str:
    """
    Language of a list of vectors: the explicitly requested language if
    there is one, otherwise the language a vector list was retrieved in,
    otherwise the session default (R cancensus vector_list_language()).
    """
    if language is None and isinstance(vectors, pd.DataFrame):
        language = vectors.attrs.get("language")
    if language is None:
        return get_language()
    return validate_language(language)


def _get_all_vectors(dataset, use_cache, api_key, language) -> Optional[pd.DataFrame]:
    """Fetch the full vector list for a dataset, warning on failure."""
    from .vectors import list_census_vectors

    try:
        all_vectors = list_census_vectors(
            dataset,
            use_cache=use_cache,
            quiet=True,
            api_key=api_key,
            language=language,
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
    language: Optional[str] = None,
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
    language : str, optional
        Language of the labels, ``"en"`` or ``"fr"``. By default the language
        ``vectors`` was retrieved in if it is a DataFrame from
        :func:`list_census_vectors`, otherwise :func:`get_language`. See
        :func:`list_census_vectors`.

    Returns
    -------
    pd.DataFrame
        DataFrame with ancestor vector information, in discovery order
        (direct parents first, then grandparents, and so on)
    """
    language = _vector_list_language(vectors, language)
    vector_ids = _clean_vector_input(vectors)
    if not vector_ids:
        return pd.DataFrame()

    if dataset is None:
        dataset = _dataset_from_vectors(vector_ids)
    dataset = validate_dataset(dataset)

    all_vectors = _get_all_vectors(dataset, use_cache, api_key, language)
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
        return _with_attrs(pd.DataFrame(columns=all_vectors.columns), dataset, language)

    result = all_vectors.set_index("vector").loc[seen].reset_index()
    return _with_attrs(result[all_vectors.columns], dataset, language)


def child_census_vectors(
    vectors: Union[str, List[str], pd.DataFrame],
    dataset: Optional[str] = None,
    use_cache: bool = True,
    api_key: Optional[str] = None,
    leaves_only: bool = False,
    max_level: Optional[int] = None,
    keep_parent: bool = False,
    language: Optional[str] = None,
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
    language : str, optional
        Language of the labels, ``"en"`` or ``"fr"``. By default the language
        ``vectors`` was retrieved in if it is a DataFrame from
        :func:`list_census_vectors`, otherwise :func:`get_language`. See
        :func:`list_census_vectors`.

    Returns
    -------
    pd.DataFrame
        DataFrame with descendant vector information, in discovery order
        (direct children first, then grandchildren, and so on)
    """
    language = _vector_list_language(vectors, language)
    vector_ids = _clean_vector_input(vectors)
    if not vector_ids:
        return pd.DataFrame()

    if dataset is None:
        dataset = _dataset_from_vectors(vector_ids)
    dataset = validate_dataset(dataset)

    all_vectors = _get_all_vectors(dataset, use_cache, api_key, language)
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
        return _with_attrs(pd.DataFrame(columns=all_vectors.columns), dataset, language)

    result = all_vectors.set_index("vector").loc[seen].reset_index()
    return _with_attrs(result[all_vectors.columns], dataset, language)

"""ASCII tree visualization of census vector hierarchies."""

from typing import Optional, Union

import pandas as pd

from .hierarchy import (
    _clean_vector_input,
    _dataset_from_vectors,
    child_census_vectors,
)
from .utils import validate_dataset


def visualize_vector_hierarchy(
    vector: Union[str, pd.DataFrame],
    dataset: Optional[str] = None,
    max_depth: Optional[int] = None,
    show_type: bool = False,
    quiet: bool = False,
    use_cache: bool = True,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Visualize a census vector hierarchy as an ASCII tree.

    Displays the hierarchical structure of census vectors, helping users
    understand parent/child relationships when selecting variables.
    Mirrors R cancensus's visualize_vector_hierarchy().

    Parameters
    ----------
    vector : str or pd.DataFrame
        A census vector code (e.g., "v_CA16_2510") or a filtered DataFrame
        as returned by list_census_vectors().
    dataset : str, optional
        The dataset to query. Only required if it cannot be inferred from
        the vector code.
    max_depth : int, optional
        Maximum depth of the tree to display. Default shows the entire
        hierarchy. Nodes truncated by max_depth are marked with "..."
        rather than "(leaf)".
    show_type : bool, default False
        Show the type (Total/Male/Female) next to each vector.
    quiet : bool, default False
        Suppress messages.
    use_cache : bool, default True
        Whether to use cached data if available.
    api_key : str, optional
        API key for CensusMapper API.

    Returns
    -------
    pd.DataFrame
        The vectors displayed in the tree. The tree itself is printed to
        the console as a side effect.

    Examples
    --------
    >>> import pycancensus as pc
    >>> pc.visualize_vector_hierarchy("v_CA16_2510")
    >>> pc.visualize_vector_hierarchy("v_CA16_2510", max_depth=2, show_type=True)
    """
    from .vectors import list_census_vectors

    vector_ids = _clean_vector_input(vector)
    if not vector_ids:
        raise ValueError("Empty vector input provided.")

    if dataset is None:
        try:
            dataset = _dataset_from_vectors(vector_ids)
        except ValueError:
            raise ValueError(
                "Cannot determine dataset from vector code. "
                "Please provide the 'dataset' parameter."
            )
    dataset = validate_dataset(dataset)

    all_vectors = list_census_vectors(
        dataset, use_cache=use_cache, quiet=True, api_key=api_key
    )
    root_info = all_vectors[all_vectors["vector"].isin(vector_ids)]
    if root_info.empty:
        raise ValueError(
            f"Vector '{', '.join(vector_ids)}' not found in dataset '{dataset}'."
        )

    if len(root_info) > 1:
        if not quiet:
            print(
                f"Multiple vectors provided. Using first vector: "
                f"{root_info['vector'].iloc[0]}"
            )
        root_info = root_info.iloc[[0]]

    root_vector = root_info["vector"].iloc[0]

    children = child_census_vectors(
        root_vector,
        dataset=dataset,
        use_cache=use_cache,
        api_key=api_key,
        max_level=max_depth,
    )
    tree_vectors = pd.concat([root_info, children], ignore_index=True)

    if not quiet:
        print(f"Vector hierarchy for {root_vector} ({dataset}):\n")

    root_label = root_info["label"].iloc[0]
    if show_type:
        root_label = f"{root_label} [{root_info['type'].iloc[0]}]"
    print(f"{root_vector}: {root_label}")

    # Parent sets for leaf detection: consult the full vector list so that
    # nodes truncated by max_depth are not falsely labeled as leaves
    tree_parents = set(tree_vectors["parent_vector"].dropna())
    dataset_parents = set(all_vectors["parent_vector"].dropna())

    _print_children(
        root_vector,
        tree_vectors,
        tree_parents,
        dataset_parents,
        prefix="",
        show_type=show_type,
        current_depth=1,
        max_depth=max_depth,
    )

    return tree_vectors


def _print_children(
    parent_vector: str,
    tree_vectors: pd.DataFrame,
    tree_parents: set,
    dataset_parents: set,
    prefix: str,
    show_type: bool,
    current_depth: int,
    max_depth: Optional[int],
) -> None:
    """Recursively print the children of a vector as tree branches."""
    if max_depth is not None and current_depth > max_depth:
        return

    direct_children = tree_vectors[tree_vectors["parent_vector"] == parent_vector]
    n_children = len(direct_children)
    if n_children == 0:
        return

    for i, (_, child) in enumerate(direct_children.iterrows()):
        is_last = i == n_children - 1
        connector = "└── " if is_last else "├── "
        child_prefix = "    " if is_last else "│   "

        label = child["label"]
        if show_type:
            label = f"{label} [{child['type']}]"

        if child["vector"] not in dataset_parents:
            leaf_indicator = " (leaf)"
        elif child["vector"] not in tree_parents:
            leaf_indicator = " ..."
        else:
            leaf_indicator = ""

        print(f"{prefix}{connector}{child['vector']}: {label}{leaf_indicator}")

        _print_children(
            child["vector"],
            tree_vectors,
            tree_parents,
            dataset_parents,
            prefix=prefix + child_prefix,
            show_type=show_type,
            current_depth=current_depth + 1,
            max_depth=max_depth,
        )

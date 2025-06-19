#!/usr/bin/env python3
"""
Command-line interface for pycancensus.
"""

import argparse
import sys
import json
from typing import Optional

import pycancensus as pc


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Access Canadian Census data through the CensusMapper API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pycancensus datasets                    # List available datasets
  pycancensus regions CA16                # List regions for 2016 Census
  pycancensus vectors CA16                # List vectors for 2016 Census
  pycancensus search-regions Vancouver CA16  # Search for Vancouver regions
  pycancensus search-vectors income CA16     # Search for income vectors
  
Set API key with environment variable: export CANCENSUS_API_KEY=your_key_here
Or get a free key at: https://censusmapper.ca/users/sign_up
        """,
    )

    parser.add_argument(
        "--api-key",
        help="CensusMapper API key (or set CANCENSUS_API_KEY environment variable)",
    )
    parser.add_argument("--cache-path", help="Path for caching downloaded data")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--quiet", action="store_true", help="Suppress output messages")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Datasets command
    datasets_parser = subparsers.add_parser("datasets", help="List available datasets")

    # Regions command
    regions_parser = subparsers.add_parser("regions", help="List regions for a dataset")
    regions_parser.add_argument("dataset", help="Dataset identifier (e.g., CA16)")

    # Vectors command
    vectors_parser = subparsers.add_parser("vectors", help="List vectors for a dataset")
    vectors_parser.add_argument("dataset", help="Dataset identifier (e.g., CA16)")

    # Search regions command
    search_regions_parser = subparsers.add_parser(
        "search-regions", help="Search for regions"
    )
    search_regions_parser.add_argument("term", help="Search term")
    search_regions_parser.add_argument(
        "dataset", help="Dataset identifier (e.g., CA16)"
    )
    search_regions_parser.add_argument("--level", help="Filter by aggregation level")

    # Search vectors command
    search_vectors_parser = subparsers.add_parser(
        "search-vectors", help="Search for vectors"
    )
    search_vectors_parser.add_argument("term", help="Search term")
    search_vectors_parser.add_argument(
        "dataset", help="Dataset identifier (e.g., CA16)"
    )
    search_vectors_parser.add_argument("--type", help="Filter by vector type")

    # Get data command
    get_data_parser = subparsers.add_parser("get-data", help="Get census data")
    get_data_parser.add_argument("dataset", help="Dataset identifier (e.g., CA16)")
    get_data_parser.add_argument(
        "--regions", required=True, help='Regions as JSON (e.g., \'{"CMA": "59933"}\')'
    )
    get_data_parser.add_argument("--vectors", help="Comma-separated list of vector IDs")
    get_data_parser.add_argument("--level", default="Regions", help="Aggregation level")
    get_data_parser.add_argument("--geo", action="store_true", help="Include geometry")
    get_data_parser.add_argument("--output", help="Output file path (CSV or GeoJSON)")

    args = parser.parse_args()

    # Set up configuration
    if args.api_key:
        pc.set_api_key(args.api_key)

    if args.cache_path:
        pc.set_cache_path(args.cache_path)

    use_cache = not args.no_cache
    quiet = args.quiet

    try:
        if args.command == "datasets":
            df = pc.list_census_datasets(use_cache=use_cache, quiet=quiet)
            print(df.to_string(index=False))

        elif args.command == "regions":
            df = pc.list_census_regions(args.dataset, use_cache=use_cache, quiet=quiet)
            print(df.to_string(index=False))

        elif args.command == "vectors":
            df = pc.list_census_vectors(args.dataset, use_cache=use_cache, quiet=quiet)
            print(df.to_string(index=False))

        elif args.command == "search-regions":
            df = pc.search_census_regions(
                args.term,
                args.dataset,
                level=args.level,
                use_cache=use_cache,
                quiet=quiet,
            )
            print(df.to_string(index=False))

        elif args.command == "search-vectors":
            df = pc.search_census_vectors(
                args.term,
                args.dataset,
                type_filter=args.type,
                use_cache=use_cache,
                quiet=quiet,
            )
            print(df.to_string(index=False))

        elif args.command == "get-data":
            # Parse regions JSON
            try:
                regions = json.loads(args.regions)
            except json.JSONDecodeError:
                print("Error: Invalid JSON format for regions", file=sys.stderr)
                return 1

            # Parse vectors
            vectors = None
            if args.vectors:
                vectors = [v.strip() for v in args.vectors.split(",")]

            # Get data
            geo_format = "geopandas" if args.geo else None

            df = pc.get_census(
                dataset=args.dataset,
                regions=regions,
                vectors=vectors,
                level=args.level,
                geo_format=geo_format,
                use_cache=use_cache,
                quiet=quiet,
            )

            # Output data
            if args.output:
                if args.output.endswith(".geojson") and hasattr(df, "to_file"):
                    df.to_file(args.output, driver="GeoJSON")
                    if not quiet:
                        print(f"Data saved to {args.output}")
                else:
                    df.to_csv(args.output, index=False)
                    if not quiet:
                        print(f"Data saved to {args.output}")
            else:
                print(df.to_string(index=False))

        else:
            parser.print_help()
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if not quiet:
            import traceback

            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

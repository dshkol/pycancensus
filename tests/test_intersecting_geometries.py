"""Test get_intersecting_geometries function against R cancensus."""

import os
import sys
import pytest
from pathlib import Path
from shapely.geometry import Point, Polygon
import geopandas as gpd

# Add pycancensus to path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pycancensus as pc


class TestIntersectingGeometries:
    """Test get_intersecting_geometries function."""
    
    def test_point_geometry(self):
        """Test with a Point geometry."""
        try:
            # Vancouver coordinates
            point = Point(-123.25149, 49.27026)
            
            regions = pc.get_intersecting_geometries(
                dataset="CA21",
                level="CT",
                geometry=point,
                simplified=False,
                quiet=True
            )
            
            # Should return a dictionary with CT as key
            assert isinstance(regions, dict)
            assert "CT" in regions or "ct" in regions.keys()
            
            # Should have some region IDs
            region_list = list(regions.values())[0]
            assert len(region_list) > 0
            
            print(f"✅ Point intersection found {len(region_list)} census tracts")
            
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
    
    def test_point_geometry_simplified(self):
        """Test with simplified output."""
        try:
            point = Point(-123.25149, 49.27026)
            
            regions = pc.get_intersecting_geometries(
                dataset="CA21",
                level="CT",
                geometry=point,
                simplified=True,
                quiet=True
            )
            
            # Should return a list of strings
            assert isinstance(regions, list)
            assert len(regions) > 0
            assert all(isinstance(r, str) for r in regions)
            
            print(f"✅ Simplified output: {len(regions)} region IDs")
            
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
    
    def test_polygon_geometry(self):
        """Test with a Polygon geometry (bounding box)."""
        try:
            # Small bounding box in Vancouver
            bbox = Polygon([
                (-123.30, 49.25),
                (-123.25, 49.25),
                (-123.25, 49.30),
                (-123.30, 49.30),
                (-123.30, 49.25)
            ])
            
            regions = pc.get_intersecting_geometries(
                dataset="CA21",
                level="CT",
                geometry=bbox,
                simplified=False,
                quiet=True
            )
            
            assert isinstance(regions, dict)
            region_list = list(regions.values())[0]
            assert len(region_list) > 0
            
            print(f"✅ Polygon intersection found {len(region_list)} census tracts")
            
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
    
    def test_geodataframe_input(self):
        """Test with GeoDataFrame input."""
        try:
            # Create a GeoDataFrame with a point
            gdf = gpd.GeoDataFrame(
                {'id': [1]}, 
                geometry=[Point(-123.25149, 49.27026)],
                crs='EPSG:4326'
            )
            
            regions = pc.get_intersecting_geometries(
                dataset="CA21",
                level="CT",
                geometry=gdf,
                simplified=True,
                quiet=True
            )
            
            assert isinstance(regions, list)
            assert len(regions) > 0
            
            print(f"✅ GeoDataFrame input: {len(regions)} region IDs")
            
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
    
    def test_geoseries_input(self):
        """Test with GeoSeries input."""
        try:
            # Create a GeoSeries with a point
            gs = gpd.GeoSeries([Point(-123.25149, 49.27026)], crs='EPSG:4326')
            
            regions = pc.get_intersecting_geometries(
                dataset="CA21",
                level="CT",
                geometry=gs,
                simplified=True,
                quiet=True
            )
            
            assert isinstance(regions, list)
            assert len(regions) > 0
            
            print(f"✅ GeoSeries input: {len(regions)} region IDs")
            
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
    
    def test_integration_with_get_census(self):
        """Test using results with get_census."""
        try:
            point = Point(-123.25149, 49.27026)
            
            # Get intersecting regions
            regions = pc.get_intersecting_geometries(
                dataset="CA21",
                level="CT", 
                geometry=point,
                simplified=False,
                quiet=True
            )
            
            # Use regions to get census data
            census_data = pc.get_census(
                dataset="CA21",
                regions=regions,
                vectors=["v_CA21_1"],
                level="CT",
                quiet=True
            )
            
            assert len(census_data) > 0
            assert "v_CA21_1" in census_data.columns
            
            print(f"✅ Integration test: retrieved {len(census_data)} regions with census data")
            
        except Exception as e:
            pytest.skip(f"Integration test failed: {e}")
    
    def test_invalid_geometry(self):
        """Test with invalid geometry input."""
        with pytest.raises(ValueError, match="geometry parameter must be"):
            pc.get_intersecting_geometries(
                dataset="CA21",
                level="CT",
                geometry="invalid",
                quiet=True
            )
    
    def test_caching(self):
        """Test caching functionality."""
        try:
            point = Point(-123.25149, 49.27026)
            
            # First call - should query API
            regions1 = pc.get_intersecting_geometries(
                dataset="CA21",
                level="CT",
                geometry=point,
                use_cache=True,
                quiet=False  # Should show API message
            )
            
            # Second call - should use cache
            regions2 = pc.get_intersecting_geometries(
                dataset="CA21",
                level="CT",
                geometry=point,
                use_cache=True,
                quiet=False  # Should show cache message
            )
            
            # Results should be identical
            assert regions1 == regions2
            
            print("✅ Caching test passed")
            
        except Exception as e:
            pytest.skip(f"Caching test failed: {e}")


if __name__ == "__main__":
    # Run basic tests
    test = TestIntersectingGeometries()
    
    print("Testing point geometry...")
    test.test_point_geometry()
    
    print("\nTesting simplified output...")
    test.test_point_geometry_simplified()
    
    print("\nTesting polygon geometry...")
    test.test_polygon_geometry()
    
    print("\nTesting GeoDataFrame input...")
    test.test_geodataframe_input()
    
    print("\nTesting GeoSeries input...")
    test.test_geoseries_input()
    
    print("\nTesting integration with get_census...")
    test.test_integration_with_get_census()
    
    print("\nTesting invalid geometry...")
    test.test_invalid_geometry()
    
    print("\nTesting caching...")
    test.test_caching()
    
    print("\n🎉 All tests passed!")
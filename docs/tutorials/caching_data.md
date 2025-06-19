---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.14.1
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Data Caching and Performance

This tutorial explains how pycancensus caches data to improve performance and how to manage the cache effectively.

## Why Caching Matters

Census data requests can be slow due to:
- Large datasets (millions of records)
- Complex geographic boundaries
- API rate limits
- Network latency

pycancensus automatically caches responses to make subsequent requests much faster.

```{code-cell} python
import pycancensus as pc
import pandas as pd
import os
from pathlib import Path
import time

print("pycancensus caching tutorial")
```

## How Caching Works

pycancensus uses intelligent caching that considers:

```{code-cell} python
# Cache system overview
print("pycancensus Cache System:")
print("="*30)
print("• Automatic caching of all API responses")
print("• Unique cache keys based on request parameters")
print("• Persistent storage between sessions")
print("• Configurable cache location")
print("• Cache management tools")
```

## Cache Configuration

### Viewing Current Cache Settings

```{code-cell} python
try:
    # Check current cache settings
    cache_path = pc.get_cache_path()
    print(f"Current cache path: {cache_path}")
    
    # Check if cache directory exists
    if os.path.exists(cache_path):
        print(f"Cache directory exists: ✓")
        
        # List cache contents
        cache_files = list(Path(cache_path).glob("*"))
        print(f"Cache contains {len(cache_files)} files")
    else:
        print("Cache directory doesn't exist yet")
        
except Exception as e:
    print(f"Error checking cache: {e}")
```

### Setting Custom Cache Location

```{code-cell} python
try:
    # Set custom cache location
    custom_cache = os.path.expanduser("~/my_census_cache")
    pc.set_cache_path(custom_cache)
    
    print(f"Cache path set to: {pc.get_cache_path()}")
    
    # Create directory if it doesn't exist
    os.makedirs(custom_cache, exist_ok=True)
    print("Custom cache directory created")
    
except Exception as e:
    print(f"Error setting cache path: {e}")
```

## Cache in Action

Let's see caching performance improvements:

```{code-cell} python
try:
    # First request (uncached) - will be slower
    print("Making first request (will be cached)...")
    start_time = time.time()
    
    data1 = pc.get_census(
        dataset="CA21",
        regions={"CMA": "59933"},  # Vancouver
        vectors=["v_CA21_1", "v_CA21_434"],
        level="CSD"
    )
    
    first_time = time.time() - start_time
    print(f"First request: {first_time:.2f} seconds")
    print(f"Retrieved {len(data1)} records")
    
    # Second identical request (cached) - will be faster
    print("\nMaking identical request (will use cache)...")
    start_time = time.time()
    
    data2 = pc.get_census(
        dataset="CA21", 
        regions={"CMA": "59933"},
        vectors=["v_CA21_1", "v_CA21_434"],
        level="CSD"
    )
    
    second_time = time.time() - start_time
    print(f"Second request: {second_time:.2f} seconds")
    
    # Compare performance
    if first_time > 0 and second_time > 0:
        speedup = first_time / second_time
        print(f"\nSpeedup: {speedup:.1f}x faster!")
    
    # Verify data is identical
    print(f"Data identical: {data1.equals(data2)}")
    
except Exception as e:
    print(f"Error demonstrating cache: {e}")
    print("This requires API access to demonstrate fully")
```

## Cache Management

### Listing Cached Data

```{code-cell} python
try:
    # List what's in the cache
    cached_data = pc.list_cached_data()
    
    if len(cached_data) > 0:
        print(f"Found {len(cached_data)} cached datasets:")
        print("\nCache contents:")
        for i, cache_info in enumerate(cached_data[:5]):  # Show first 5
            print(f"{i+1}. Dataset: {cache_info.get('dataset', 'Unknown')}")
            print(f"   Regions: {cache_info.get('regions', 'Unknown')}")
            print(f"   Vectors: {len(cache_info.get('vectors', []))} vectors")
            print(f"   Size: {cache_info.get('size', 'Unknown')}")
            print()
    else:
        print("No cached data found")
        
except Exception as e:
    print(f"Error listing cache: {e}")
    print("Cache listing requires cached data to exist")
```

### Cache Statistics

```{code-cell} python
try:
    cache_path = pc.get_cache_path()
    
    if os.path.exists(cache_path):
        # Calculate cache size
        total_size = 0
        file_count = 0
        
        for file_path in Path(cache_path).rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1
        
        # Convert to readable format
        if total_size > 1024**3:  # GB
            size_str = f"{total_size / 1024**3:.2f} GB"
        elif total_size > 1024**2:  # MB
            size_str = f"{total_size / 1024**2:.2f} MB"
        elif total_size > 1024:  # KB
            size_str = f"{total_size / 1024:.2f} KB"
        else:
            size_str = f"{total_size} bytes"
        
        print("Cache Statistics:")
        print("="*20)
        print(f"Location: {cache_path}")
        print(f"Files: {file_count}")
        print(f"Total size: {size_str}")
        
    else:
        print("Cache directory doesn't exist")
        
except Exception as e:
    print(f"Error calculating cache stats: {e}")
```

## Controlling Cache Behavior

### Bypassing Cache

```{code-cell} python
try:
    # Force fresh data (bypass cache)
    print("Forcing fresh data download...")
    
    fresh_data = pc.get_census(
        dataset="CA21",
        regions={"PR": "59"},  # British Columbia
        vectors=["v_CA21_1"],
        level="PR",
        use_cache=False  # Force fresh download
    )
    
    print(f"Fresh data retrieved: {len(fresh_data)} records")
    
except Exception as e:
    print(f"Error bypassing cache: {e}")
    print("This requires API access")
```

### Cache Expiration

```{code-cell} python
# pycancensus cache behavior
print("Cache Expiration Policy:")
print("="*25)
print("• Census data rarely changes, so cache persists indefinitely")
print("• Vector lists and region lists are cached for performance")
print("• Geographic boundaries are cached (they don't change)")
print("• API responses include timestamps for freshness checking")
print("\nTo force refresh:")
print("• Use use_cache=False parameter")
print("• Clear specific cache entries")
print("• Clear entire cache")
```

## Cache Maintenance

### Selective Cache Removal

```{code-cell} python
try:
    # Remove specific cached data
    print("Cache removal options:")
    
    # Option 1: Remove by dataset
    # pc.remove_cached_data(dataset="CA16")
    print("• Remove by dataset: pc.remove_cached_data(dataset='CA16')")
    
    # Option 2: Remove by region
    # pc.remove_cached_data(regions={"CMA": "59933"})
    print("• Remove by region: pc.remove_cached_data(regions={'CMA': '59933'})")
    
    # Option 3: Remove old data
    # pc.remove_cached_data(older_than_days=30)
    print("• Remove old data: pc.remove_cached_data(older_than_days=30)")
    
    print("\n(Commands shown for reference - not executed)")
    
except Exception as e:
    print(f"Cache removal info: {e}")
```

### Complete Cache Reset

```{code-cell} python
try:
    # Clear entire cache
    print("Complete cache reset:")
    print("="*20)
    
    # Get cache size before
    cache_path = pc.get_cache_path()
    if os.path.exists(cache_path):
        before_files = len(list(Path(cache_path).rglob("*")))
        print(f"Files before reset: {before_files}")
        
        # Clear cache (commented out to avoid actually clearing)
        # pc.clear_cache()
        print("To clear entire cache: pc.clear_cache()")
        
        print("⚠️  Warning: This removes all cached data!")
        print("   Use with caution as it will slow down future requests")
    else:
        print("No cache to clear")
        
except Exception as e:
    print(f"Error with cache reset: {e}")
```

## Advanced Cache Strategies

### Preloading Common Data

```{code-cell} python
# Strategy for preloading frequently used data
common_datasets = ["CA21", "CA16"]
major_cmas = {
    "Toronto": "535", 
    "Montreal": "462",
    "Vancouver": "59933",
    "Calgary": "825",
    "Ottawa": "505"
}

print("Preloading Strategy:")
print("="*20)
print("For applications that frequently access certain data:")
print()

for city, cma_code in major_cmas.items():
    print(f"# Preload {city} data")
    print(f"""data_{city.lower()} = pc.get_census(
    dataset="CA21",
    regions={{"CMA": "{cma_code}"}},
    vectors=["v_CA21_1", "v_CA21_434"],  # Common vectors
    level="CSD"
)""")
    print()

print("This ensures fast access to commonly requested data.")
```

### Cache-Aware Application Design

```{code-cell} python
def efficient_census_analysis(regions_list, vectors_list):
    """
    Example of cache-aware function design
    """
    print("Cache-Aware Function Design:")
    print("="*30)
    
    # Check what's already cached
    try:
        cached = pc.list_cached_data()
        print(f"Found {len(cached)} cached datasets")
    except:
        print("Cache check not available")
    
    # Batch similar requests
    print("\nBest practices:")
    print("• Group requests by dataset and geography level")
    print("• Request multiple vectors in single call")
    print("• Reuse data objects when possible")
    print("• Check cache before making requests")
    
    return "Design pattern demonstrated"

# Example usage
result = efficient_census_analysis(
    regions_list=["535", "462", "59933"],  # Toronto, Montreal, Vancouver
    vectors_list=["v_CA21_1", "v_CA21_434"]
)
```

## Troubleshooting Cache Issues

### Common Problems and Solutions

```{code-cell} python
print("Common Cache Issues and Solutions:")
print("="*35)
print()

print("1. Cache Directory Permissions:")
print("   Problem: Can't write to cache directory")
print("   Solution: Check directory permissions or set new cache path")
print("   pc.set_cache_path('/path/with/write/access')")
print()

print("2. Disk Space:")
print("   Problem: Cache grows too large")
print("   Solution: Regular cache cleanup")
print("   pc.remove_cached_data(older_than_days=30)")
print()

print("3. Stale Data:")
print("   Problem: Using old cached data")
print("   Solution: Force fresh download")
print("   pc.get_census(..., use_cache=False)")
print()

print("4. Cache Corruption:")
print("   Problem: Corrupted cache files")
print("   Solution: Clear cache and start fresh")
print("   pc.clear_cache()")
```

### Cache Diagnostics

```{code-cell} python
def diagnose_cache_health():
    """Diagnostic function for cache health"""
    
    print("Cache Health Diagnostic:")
    print("="*25)
    
    try:
        cache_path = pc.get_cache_path()
        print(f"✓ Cache path accessible: {cache_path}")
        
        # Check if writable
        test_file = os.path.join(cache_path, ".test_write")
        try:
            os.makedirs(cache_path, exist_ok=True)
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print("✓ Cache directory is writable")
        except:
            print("✗ Cache directory is not writable")
        
        # Check space usage
        if os.path.exists(cache_path):
            file_count = len(list(Path(cache_path).rglob("*")))
            print(f"✓ Cache contains {file_count} files")
        else:
            print("! Cache directory doesn't exist yet")
            
    except Exception as e:
        print(f"✗ Cache diagnostic error: {e}")

# Run diagnostics
diagnose_cache_health()
```

## Performance Monitoring

### Measuring Cache Effectiveness

```{code-cell} python
class CacheMonitor:
    """Simple cache performance monitor"""
    
    def __init__(self):
        self.requests = []
    
    def log_request(self, request_type, duration, cached=False):
        self.requests.append({
            'type': request_type,
            'duration': duration,
            'cached': cached,
            'timestamp': time.time()
        })
    
    def get_stats(self):
        if not self.requests:
            return "No requests logged"
        
        cached_requests = [r for r in self.requests if r['cached']]
        uncached_requests = [r for r in self.requests if not r['cached']]
        
        print("Cache Performance Stats:")
        print("="*25)
        print(f"Total requests: {len(self.requests)}")
        print(f"Cache hits: {len(cached_requests)}")
        print(f"Cache misses: {len(uncached_requests)}")
        
        if cached_requests and uncached_requests:
            avg_cached = sum(r['duration'] for r in cached_requests) / len(cached_requests)
            avg_uncached = sum(r['duration'] for r in uncached_requests) / len(uncached_requests)
            speedup = avg_uncached / avg_cached if avg_cached > 0 else 0
            print(f"Average speedup: {speedup:.1f}x")

# Example usage
monitor = CacheMonitor()
monitor.log_request("get_census", 2.5, cached=False)
monitor.log_request("get_census", 0.1, cached=True)
monitor.get_stats()
```

## Summary

This tutorial covered comprehensive cache management for pycancensus:

✅ **Key Concepts Learned:**
- How pycancensus caching works automatically 
- Configuring cache location and settings
- Measuring cache performance improvements
- Managing and maintaining the cache
- Troubleshooting common cache issues
- Cache-aware application design patterns

### Best Practices Summary:
1. **Let cache work automatically** - Default behavior is optimized
2. **Monitor cache size** - Clean up old data periodically  
3. **Use consistent requests** - Same parameters = cache hits
4. **Batch requests** - Request multiple vectors together
5. **Handle cache errors** - Have fallbacks for cache issues

### Next Steps:
- Implement cache monitoring in your applications
- Set up automated cache maintenance schedules
- Experiment with preloading strategies for your use cases
- Combine caching with other performance optimizations

The cache system makes pycancensus much more responsive for interactive analysis and production applications!
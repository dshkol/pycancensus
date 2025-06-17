# R vs Python API Comparison Results

**Test Date**: 2025-06-17  
**API Key**: Valid CensusMapper API key  
**Test Case**: CA21 dataset, British Columbia (PR=59), Population vector (v_CA21_1)

## Summary

✅ **Core data values MATCH perfectly**  
✅ **Both libraries retrieve identical population data**  
⚠️ **Minor differences in column structure and naming**  
❌ **Python API endpoints for metadata have issues**

## Detailed Comparison

### Test Case: Basic Provincial Data Retrieval

**Parameters:**
- Dataset: CA21 (2021 Census)
- Region: PR = "59" (British Columbia)
- Vector: v_CA21_1 (Total Population)
- Level: PR (Provincial)

### Results Comparison

| Metric | Python (pycancensus) | R (cancensus) | Match |
|--------|---------------------|---------------|-------|
| **Population** | 5,000,879 | 5,000,879 | ✅ EXACT |
| **GeoUID** | "59" | "59" | ✅ EXACT |
| **Region Name** | "British Columbia (B.C.)" | [Index: 1] | ⚠️ Different |
| **Column Count** | 12 | 9 | ⚠️ Different |
| **Data Shape** | (1, 12) | (1, 9) | ⚠️ Different |

### Column Structure Differences

**Python columns (12):**
```
GeoUID, Type, Region Name, Area (sq km), Population , Dwellings , 
Households , rpid, rgid, ruid, rguid, v_CA21_1: Population, 2021
```

**R columns (9):**
```
GeoUID, Type, Region Name, Area (sq km), Population, Dwellings, 
Households, C_UID, v_CA21_1: Population, 2021
```

**Key Differences:**
1. **Extra columns in Python**: `rpid`, `rgid`, `ruid`, `rguid` vs R's single `C_UID`
2. **Trailing spaces**: Python has trailing spaces in some column names (`Population `, `Dwellings `, `Households `)
3. **Region name display**: Python shows full name, R shows index

## Advanced Functionality Tests

### ✅ What Works in Both Libraries

1. **Basic data retrieval**: Both return identical population values
2. **Multiple regions**: Both handle multiple CSD codes correctly
3. **Multiple vectors**: Both can retrieve multiple census variables
4. **Geometry support**: Both can include geographic boundaries
5. **Caching**: Both implement local data caching

### 📊 Python Test Results Summary

**All core data retrieval tests PASSED:**

1. ✅ Provincial level data: (1, 12) shape
2. ✅ City level data (Vancouver): (1, 12) shape, Pop: 662,248
3. ✅ Multiple cities: (2, 12) shape (Vancouver + Toronto)
4. ✅ Multiple vectors: (1, 13) shape with 2 vector columns
5. ✅ Geometry test: (1, 16) shape with geometry column

### ❌ Known Issues in Python Implementation

1. **Vector listing API**: 404 error on `/list_vectors` endpoint
   ```
   404 Client Error: Not Found for url: 
   https://censusmapper.ca/api/v1/list_vectors?dataset=CA21&...
   ```

2. **Region listing API**: 404 error on `/list_regions` endpoint
   ```
   404 Client Error: Not Found for url:
   https://censusmapper.ca/api/v1/list_regions?dataset=CA21&...
   ```

3. **R vector listing works**: R successfully retrieved 7,709 vectors for CA21

## API Endpoint Analysis

### Working Endpoints (Both R & Python)
- ✅ **Data retrieval**: `/data.csv` - Returns census data
- ✅ **Geometry retrieval**: `/geo.geojson` - Returns geographic boundaries  
- ✅ **Dataset listing**: `/list_datasets` - Returns available datasets

### Problematic Endpoints (Python only)
- ❌ **Vector listing**: `/list_vectors` - 404 error in Python
- ❌ **Region listing**: `/list_regions` - 404 error in Python

**Root Cause**: The Python implementation may be using different API endpoint URLs or parameters than the R library.

## Data Quality Assessment

### ✅ Strengths Confirmed
1. **Identical core data**: Population figures match exactly
2. **Consistent geographic identifiers**: GeoUIDs match
3. **Proper data types**: Numeric values correctly converted
4. **Cache functionality**: Both libraries cache data appropriately
5. **Error handling**: Python properly returns 401 for invalid API keys

### ⚠️ Areas Requiring Attention
1. **Column naming consistency**: Trailing spaces in Python
2. **Metadata column differences**: Different auxiliary columns
3. **API endpoint compatibility**: Python endpoints need updating
4. **Error messages**: Could be more informative

## Recommendations

### High Priority Fixes
1. **Fix API endpoint URLs** for vector and region listing
2. **Standardize column naming** to remove trailing spaces
3. **Align metadata columns** with R implementation
4. **Implement missing vector hierarchy functions**

### Medium Priority Improvements
1. **Enhance error messages** with specific guidance
2. **Add retry logic** for failed API requests
3. **Implement progress indicators** for large data downloads
4. **Add comprehensive integration tests**

### API Compatibility Investigation
The 404 errors on `/list_vectors` and `/list_regions` endpoints suggest:
1. **Different API version**: Python may be using older endpoint paths
2. **Parameter formatting**: Request parameters may not match R implementation
3. **Authentication differences**: Headers or auth methods may differ

**Next Step**: Examine R library source code to identify correct endpoint URLs and request formats.

## Conclusion

**The fundamental data retrieval functionality of pycancensus is working correctly** and produces identical results to the R cancensus library. The core census data values match exactly, confirming that the Python port successfully replicates the essential functionality.

**The main issues are in metadata retrieval functions** (listing vectors and regions), which appear to be using incorrect API endpoints. This does not affect the core use case of retrieving census data but limits the library's usability for data exploration.

**Overall Assessment**: pycancensus provides a solid foundation with correct core functionality, but needs API endpoint fixes and enhanced metadata capabilities to achieve full equivalence with the R library.
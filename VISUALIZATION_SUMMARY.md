# Dependency Graph Visualization Summary

## Current State Analysis

The dependency graph visualization (`tools/dependency_graph_current_state.png`) shows the current state of the CICS GenApp system with **26 nodes and 39 dependency relationships**.

### Graph Statistics

- **Total Components:** 26
- **Total Dependencies:** 39
- **Component Types:**
  - COBOL Programs: 12
  - DB2 Tables: 5  
  - Copybooks: 1
  - SQL Includes: 1
  - VSAM Files: 1
  - Undefined/Incomplete: 6

### Key Foundation Components

**Critical Shared Infrastructure:**
1. **LGCMAREA** (copybook): 11 dependents
   - The shared commarea layout used by all transaction programs
   - Single point of change for communication structure
   
2. **LGSTSQ** (cobol): 11 dependents  
   - Central TDQ logging facility used throughout the system
   - Critical for diagnostics and error tracking

### Complex Integration Points

**Backend Service Orchestrators:**
1. **LGAPDB01** (cobol): 9 dependencies
   - DB2-backed policy add service
   - Integrates with multiple DB2 tables and VSAM
   - Most complex component in the system

2. **LGACDB01** (cobol): 4 dependencies
   - Add customer DB2 backend service
   - Key integration point for customer domain

### Documentation Priority Recommendations

Based on the dependency analysis, the recommended documentation order is:

#### Phase 1: Foundation (Parallel-safe)
- **LGCMAREA** - Document commarea structure first as it affects all programs
- **LGSTSQ** - Document logging facility as it's used by all programs

#### Phase 2: Core Integrators (Serial)
- **LGAPDB01** - Most complex component, orchestrates policy creation
- **LGACDB01** - Customer domain leader

#### Phase 3: Transaction Front-ends (Parallel)
- All front-end programs can be documented in parallel once their backends are understood
- Pattern-based documentation since they follow consistent structures

### Visualization Legend

The visualization uses color coding and shapes to distinguish component types:
- **Green Circles:** COBOL Programs
- **Blue Squares:** Copybooks  
- **Purple Triangles:** SQL Includes
- **Orange Diamonds:** DB2 Tables
- **Red Hexagons:** VSAM Files

### Generated Artifacts

- **Visualization Tool:** `tools/visualize_dependencies.py`
- **Current State Image:** `tools/dependency_graph_current_state.png` (4770x3574 PNG)
- **Graph Data:** `dependency_graph.json` (maintained by `tools/dep_graph.py`)

## Usage Instructions

To regenerate the visualization:
```bash
python3 tools/visualize_dependencies.py --stats --suggestions
```

To analyze specific components:
```bash  
python3 tools/dep_graph.py show LGCMAREA --include-dependents
```

This analysis provides a data-driven foundation for organizing the documentation effort and understanding the system's architecture.
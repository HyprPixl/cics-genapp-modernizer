# Dependency Graph Visualization

The CICS GenApp dependency graph tool includes comprehensive visualization capabilities for understanding the relationships between system components.

## Quick Start

Generate a complete system overview:
```bash
./tools/dep_graph.py visualize --output system_overview.png
```

## Available Commands

### Basic Visualization
```bash
# Full system graph
./tools/dep_graph.py visualize

# Custom output file
./tools/dep_graph.py visualize --output my_graph.png
```

### Filtered Views
```bash
# Show only COBOL programs
./tools/dep_graph.py visualize --filter-type cobol --show-labels

# Database tables only
./tools/dep_graph.py visualize --filter-type db2-table --show-labels

# VSAM files
./tools/dep_graph.py visualize --filter-type vsam-file --show-labels

# Copybooks and includes
./tools/dep_graph.py visualize --filter-type copybook --show-labels
```

### Layout and Sizing Options
```bash
# Large detailed view
./tools/dep_graph.py visualize --width 20 --height 16

# Hierarchical layout (requires graphviz)
./tools/dep_graph.py visualize --layout hierarchical

# Force labels on large graphs
./tools/dep_graph.py visualize --show-labels
```

## Component Types and Colors

The visualization uses color coding to distinguish different component types:

| Type | Color | Description |
|------|-------|-------------|
| `cobol` | Green | COBOL programs |
| `copybook` | Blue | Copybook definitions |
| `sql-include` | Indigo | SQL include files |
| `db2-table` | Orange | Database tables |
| `vsam-file` | Purple | VSAM datasets |
| `jcl` | Brown | JCL procedures |
| `rexx` | Blue Grey | REXX scripts |
| `shell` | Dark Grey | Shell scripts |
| `bms-map` | Pink | BMS mapsets |
| `dataset` | Amber | Data files |
| `wsim-script` | Light Green | WSIM scenarios |
| `event-binding` | Deep Orange | CICS event bindings |
| `cics-counter` | Cyan | CICS counters |

## Current System Statistics

Based on the complete dependency graph:

- **Total Components:** 43 nodes
- **Total Dependencies:** 89 directed relationships
- **Component Types:** 14 different categories

### Component Distribution
- COBOL programs: 19 (44%)
- DB2 tables: 7 (16%)
- Copybooks: 3 (7%)
- VSAM files: 2 (5%)
- REXX scripts: 2 (5%)
- Other components: 10 (23%)

### Key Insights
- **Most Referenced Component:** `LGCMAREA` copybook (referenced by 19 components)
- **Most Complex Component:** `LGAPDB01` (depends on 9 different components)
- **Central Logger:** `LGSTSQ` (used by 18 COBOL programs)

## Generated Visualizations

The repository includes several pre-generated visualizations:

### System Overview
- `full_system.png` - Complete dependency graph with all components
- Shows the full complexity and interconnections of the GenApp system

### Component-Specific Views
- `cobol_programs.png` - COBOL program relationships and dependencies
- `database_schema.png` - DB2 table structure (note: tables are independent)
- `vsam_files.png` - VSAM dataset relationships
- `copybooks.png` - Shared copybook structures

### Operational Views
- `jcl_components.png` - JCL procedures
- `rexx_components.png` - REXX script relationships
- `shell_components.png` - Shell script dependencies

## Batch Generation

Use the provided script to generate all visualizations at once:

```bash
./tools/generate_all_visualizations.sh
```

This creates organized visualizations in the `./visualizations/` directory.

## Understanding the Graphs

### Node Relationships
- **Arrows point FROM dependents TO dependencies**
- Example: `LGAPOL01 → LGAPDB01` means LGAPOL01 depends on LGAPDB01

### Graph Layouts
- **Spring Layout:** Automatic positioning based on relationships (default)
- **Hierarchical Layout:** Top-down organization (requires graphviz installation)

### Reading Dependencies
- **Thick clusters:** Highly interconnected components
- **Isolated nodes:** Independent components with no dependencies
- **Star patterns:** Central components used by many others (like `LGCMAREA`)

## Advanced Usage

### Finding Critical Dependencies
```bash
# Show components with most dependencies
./tools/dep_graph.py show LGAPDB01 --include-dependents

# List all dependents of a shared component
./tools/dep_graph.py dependents LGCMAREA
```

### Analyzing Component Types
```bash
# List all components of a specific type
./tools/dep_graph.py list --type cobol

# Count components by type
./tools/dep_graph.py list | cut -d: -f1 | xargs -I {} ./tools/dep_graph.py show {} | grep "Type:" | sort | uniq -c
```

## Technical Requirements

The visualization feature requires:
- Python 3.7+
- matplotlib
- networkx

Install dependencies:
```bash
pip install matplotlib networkx
```

Optional for hierarchical layouts:
```bash
pip install graphviz
```

## Output Formats

All visualizations are generated as PNG files with:
- High resolution (300 DPI)
- Transparent backgrounds where appropriate
- Optimized for both screen viewing and printing

## Integration with Documentation

The visualizations complement the textual documentation in:
- `README.md` - Component descriptions and purposes
- `AGENTS.md` - Development progress and dependency notes
- `REPORT.md` - Executive summary with visual context

Use the visualizations to:
1. **Understand system architecture** at a glance
2. **Identify modernization targets** (highly connected components)
3. **Plan development phases** (components with fewer dependencies first)
4. **Communicate system structure** to stakeholders
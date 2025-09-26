#!/bin/bash
# Generate all dependency graph visualizations

echo "Generating dependency graph visualizations..."

# Create output directory if it doesn't exist
mkdir -p visualizations

# Generate complete system overview
echo "1. Complete system overview..."
./tools/dep_graph.py visualize --output visualizations/full_system.png --width 20 --height 16

# COBOL programs with relationships
echo "2. COBOL programs..."
./tools/dep_graph.py visualize --filter-type cobol --output visualizations/cobol_programs.png --show-labels --width 16 --height 12

# Database schema
echo "3. Database tables..."
./tools/dep_graph.py visualize --filter-type db2-table --output visualizations/database_schema.png --show-labels --width 12 --height 10

# VSAM files
echo "4. VSAM files..."
./tools/dep_graph.py visualize --filter-type vsam-file --output visualizations/vsam_files.png --show-labels --width 10 --height 8

# Copybooks and includes
echo "5. Copybooks..."
./tools/dep_graph.py visualize --filter-type copybook --output visualizations/copybooks.png --show-labels --width 10 --height 8

# Operational components (JCL, REXX, shell)
echo "6. Operational components..."
for type in jcl rexx shell; do
    ./tools/dep_graph.py visualize --filter-type $type --output visualizations/${type}_components.png --show-labels --width 10 --height 8 2>/dev/null || true
done

echo "All visualizations generated in ./visualizations/"
echo ""
echo "Quick statistics:"
./tools/dep_graph.py visualize --output /tmp/stats_only.png 2>&1 | grep -A 10 "Graph Statistics:"
rm -f /tmp/stats_only.png

"""Open Energy Database Compliance Manager

Validate measurement data from HSRM with logging.
Comprehensive dataset analysis and transformation planning.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from oedbcm import DataPackage
from oedbcm.analyzer import ColumnAnalyzer, FileNameAnalyzer
from oedbcm.planner import TransformationPlanner

# Your dataset
dataset_path = Path("data/raw/HSRM_Messdaten_Brennstoffzelle")
package = DataPackage(dataset_path)

# 1. Column Analysis
print("\n" + "="*70)
print("STEP 1: COLUMN ANALYSIS")
print("="*70)
col_analyzer = ColumnAnalyzer(package)
col_analyzer.print_analysis()

# 2. Filename Analysis
print("\n" + "="*70)
print("STEP 2: FILENAME ANALYSIS")
print("="*70)
file_analyzer = FileNameAnalyzer(package)
file_analyzer.print_analysis()

# 3. Transformation Planning
print("\n" + "="*70)
print("STEP 3: TRANSFORMATION PLANNING")
print("="*70)
planner = TransformationPlanner(package)
planner.print_plan()
planner.save_plan()

# 4. Structure Planning
print("\n" + "="*70)
print("STEP 4: STRUCTURE PLANNING")
print("="*70)

# Assign groups based on structure
groups = planner.assign_groups_by_structure()

# Create and save structure plan
plan = planner.create_structure_plan(
    version="0.1.0",
    description="Initial analysis of HSRM fuel cell measurement data"
)

output_files = planner.save_complete_plan(plan)

print("\n" + "="*70)
print("STRUCTURE PLAN CREATED")
print("="*70)
print(f"YAML Plan: {output_files['yaml']}")
print(f"Visualization: {output_files['visualization']}")
print("\n📝 Next: Edit the YAML file to define your planned structure!")
print("="*70 + "\n")

print("\n✅ Complete analysis finished! Check data/reports/, data/plans/, and data/plots/")

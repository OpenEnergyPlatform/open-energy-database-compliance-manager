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

print("\n✅ Analysis complete! Check data/reports/ for detailed plan.")

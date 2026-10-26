<!--
SPDX-FileCopyrightText: 2026 Ludwig Hülk https://github.com/Ludee © Reiner Lemoine Institut
SPDX-FileCopyrightText: 2026 Tomi Nguyen https://github.com/tomi-rli © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
-->
# Open Energy Database Compliance Manager - Planning Guide

**3-Phase Workflow for OEP Dataset Preparation**

---

## 🎯 Overview

### Phase 0: Raw Data 📦

`data/0_raw/(dataset)/` - Original files, never modified

### Phase 1+2: Analysis & Planning 🔍

`data/2_planning/(dataset)/` - Classification, structure plans, metadata

### Phase 3: Results ✅  

`data/3_results/(dataset)/` - Transformed OEP-compliant tables

---

## 📁 Complete Folder Structure

```
data/
├── 0_raw/HSRM_Messdaten_Brennstoffzelle/     # Original data
│   ├── measurements_*.csv                     # 18 Data files
│   ├── device_info.csv                        # 2 Additional Data
│   ├── readme.csv                             # 3 Metadata
│   └── *.pdf, *.png                          # Ignored
│
├── 2_planning/HSRM_Messdaten_Brennstoffzelle/
│   ├── catalogs/
│   │   ├── *_draft.csv                       # Auto-generated
│   │   └── *_catalog.csv                     # Manual-edited ✏️
│   ├── structure/
│   │   ├── structure_current_*_v0.1.0.yaml  # As-is
│   │   ├── structure_plan_*_v0.1.0.yaml     # To-be
│   │   └── structure_merged_*_v0.1.0.yaml   # Final (DATA only)
│   ├── metadata/
│   │   ├── oemetadata_general_keys_draft.yaml
│   │   ├── oemetadata_context_draft.yaml
│   │   ├── oemetadata_spatial_temporal_draft.yaml
│   │   ├── oemetadata_contributors_draft.yaml
│   │   ├── oemetadata_sources_draft.yaml
│   │   └── oemetadata_licenses_draft.yaml
│   ├── plots/
│   │   └── structure_comparison_v0.1.0.png
│   └── reports/
│       └── 2026-02-18_150530_*.log
│
└── 3_results/HSRM_Messdaten_Brennstoffzelle/
    └── hsrm_fuel_cell_measurements.csv       # Final table
```

---

## 🔄 Complete Workflow

### 1️⃣ Load & Classify

```python
from pathlib import Path
from oedbcm import DataPackage
from oedbcm.planner import TransformationPlanner

# Load dataset
dataset_path = Path("data/0_raw/HSRM_Messdaten_Brennstoffzelle")
package = DataPackage(dataset_path)
planner = TransformationPlanner(package)

# Create classification draft
result = planner.create_catalog_draft()
# Output: data/2_planning/(dataset)/catalogs/*_draft.csv
```

**📝 Manual Step:** Edit `*_draft.csv` → Save as `*_catalog.csv`

**Classification Types:**

- `Data` - Tables to upload (18 files)
- `Metadata` - Descriptive info (3 files)
- `Additional Data` - Supporting info (2 files)
- `Ignore` - Binary files, PDFs
- `Not Supported Yet` - XLSX, JSON

### 2️⃣ Load Catalog & Analyze

```python
# Load finalized catalog
planner.load_catalog()

# Analyze only DATA + ADDITIONAL_DATA
package.analyze_all(filter_by_classification=True)

# Group by identical structure
groups = planner.assign_groups_by_structure()
```

### 3️⃣ Extract OEMetadata

```python
# Create structure plan with auto-extracted metadata
plan = planner.create_structure_plan(
    version="0.1.0",
    description="Initial OEMetadata extraction"
)
```

**Auto-extracted fields:**

```yaml
fields:
  - name: temperature              # ✅ Standardized
    type: number                   # ✅ Inferred
    description: Temperature [°C]  # ✅ Original name
    nullable: true
    unit: °C                      # ✅ Extracted from [°C]
    isAbout: []                   # Fill manually
    valueReference: []            # Fill manually
```

**Extraction patterns:**

- `Temperature [°C]` → unit: `°C`
- `Pressure (bar)` → unit: `bar`
- `voltage_V` → unit: `V`
- `Power_in_kW` → unit: `kW`

### 4️⃣ Create Merged Structure

```python
# Merge all DATA tables into final structure
merged_plan = planner.create_merged_structure_plan(
    version="0.1.0",
    target_table_name="hsrm_fuel_cell_measurements"
)
# Output: structure_merged_*_v0.1.0.yaml
```

This combines 18 DATA tables → 1 final table structure

### 5️⃣ Generate OEMetadata Sections

```python
from oedbcm.metadata_builder import OEMetadataBuilder

builder = OEMetadataBuilder(package.dataset_name)
drafts = builder.create_all_drafts(
    title="HSRM Fuel Cell Measurements",
    description="Test bench measurements",
    contributor_name="Your Name",
    contributor_email="email@example.com"
)
```

**Output:** 6 YAML drafts in `metadata/`

**📝 Manual Step:** Edit drafts → Remove `_draft` suffix

### 6️⃣ Visualize

```python
# Save with visualization
output_files = planner.save_complete_plan(
    plan, 
    create_visualization=True
)
```

**Output:** `plots/structure_comparison_v0.1.0.png`

### 7️⃣ Transform (TODO)

```python
# Future: Transform to final structure
# Output: data/3_results/(dataset)/*.csv
```

---

## 🔑 Key Features

### OEMetadata Auto-Extraction

**Input column:** `Temperature [°C]`

**Output:**

```yaml
name: temperature
type: number
description: Temperature [°C]
unit: °C
```

**Supported patterns:**

- `[unit]` - Square brackets
- `(unit)` - Parentheses
- `_in_unit` - Underscore notation
- `_unit` - Suffix

### Structure Grouping

Identical structures → Same group:

```yaml
- name: measurements_Q1.csv
  group_number: 1
  fields: [timestamp, temp, pressure]

- name: measurements_Q2.csv
  group_number: 1  # Same structure!
```

### Versioning

```python
plan.increment_version('minor')  # 0.1.0 → 0.2.0
plan.save_yaml()
```

- **Patch** (0.1.1): Typos, small edits
- **Minor** (0.2.0): Structure changes
- **Major** (1.0.0): Complete redesign

---

## 🐛 Known Issues & Fixes

### ✅ Fixed Issues

1. **Duplicate catalogs folder**  
   ❌ Was: `data/catalogs/` AND `data/2_planning/(dataset)/catalogs/`  
   ✅ Now: Only `data/2_planning/(dataset)/catalogs/`

2. **Reports subfolder**  
   ❌ Was: `data/2_planning/(dataset)/reports/(dataset)/`  
   ✅ Now: `data/2_planning/(dataset)/reports/`

3. **Missing merged structure**  
   ✅ Now: Use `create_merged_structure_plan()`

### ⏳ TODO

1. **Reports visualization** - Improve readability
2. **Data transformation** - Phase 3 implementation
3. **OEMetadata validation** - Schema compliance check

---

## 📖 Example: Complete Run

```python
from pathlib import Path
from oedbcm.package import DataPackage
from oedbcm.planner import TransformationPlanner
from oedbcm.metadata_builder import OEMetadataBuilder

# 1. Load
dataset_path = Path("data/0_raw/HSRM_Messdaten_Brennstoffzelle")
package = DataPackage(dataset_path)
planner = TransformationPlanner(package)

# 2. Classify → Edit catalog manually → Reload
planner.create_catalog_draft()
planner.load_catalog()

# 3. Analyze
package.analyze_all(filter_by_classification=True)
planner.assign_groups_by_structure()

# 4. Extract OEMetadata
plan = planner.create_structure_plan(version="0.1.0")
planner.save_complete_plan(plan)

# 5. Merge
merged = planner.create_merged_structure_plan(
    version="0.1.0",
    target_table_name="hsrm_measurements"
)

# 6. OEMetadata sections
builder = OEMetadataBuilder(package.dataset_name)
builder.create_all_drafts(
    title="HSRM Fuel Cell Data",
    description="Measurements from test bench"
)
```

---

## 💡 Tips

1. **Always classify first** - Catalog drives everything
2. **Check OEMetadata extraction** - Verify units extracted correctly
3. **Use merged structure** - Final structure for upload
4. **Version frequently** - Each major edit = new version
5. **Edit drafts carefully** - YAML syntax matters

---

## 🆘 Troubleshooting

**Missing fields in YAML:**

```
fields:
  - name: temperature
    type: unknown  # ❌ Bad
```

**Fix:** Ensure `analyze_all()` called before `create_structure_plan()`

**No merged structure:**  
**Fix:** Call `create_merged_structure_plan()` separately

**Wrong folder structure:**  
**Fix:** Delete old folders, re-run with latest code

---

## 📚 References

- **OEMetadata Spec:** <https://github.com/OpenEnergyPlatform/oemetadata>
- **OEP Upload Guide:** <https://openenergy-platform.org/>
- **Project Repo:** <https://github.com/ludee/open-energy-database-compliance-manager>

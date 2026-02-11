# Structure Planning Guide

This guide explains how to use the structure planning feature to visualize and optimize your dataset structure.

## Overview

The structure planning workflow helps you:

1. **Analyze** current data structure (as-is)
2. **Plan** optimized structure (to-be)
3. **Visualize** the comparison
4. **Version** your planning iterations
5. **Export** plans as editable YAML files

## Quick Start

### Step 1: Run Initial Analysis
```python
from pathlib import Path
from oedbcm import DataPackage
from oedbcm.planner import TransformationPlanner

# Load your dataset
dataset_path = Path("data/raw/your_dataset")
package = DataPackage(dataset_path)

# Create planner
planner = TransformationPlanner(package)

# Auto-assign groups based on structure similarity
groups = planner.assign_groups_by_structure()

# Create initial structure plan
plan = planner.create_structure_plan(
    version="0.1.0",
    description="Initial structure analysis"
)

# Save YAML + visualization
output_files = planner.save_complete_plan(plan)
```

This creates:
- `data/plans/structure_plan_<dataset>_v0.1.0.yaml` - Editable plan
- `data/visualizations/structure_comparison_v0.1.0.png` - Visual comparison

### Step 2: Edit YAML Plan

Open the YAML file and modify the `planned_structure` section:
```yaml
metadata:
  dataset_name: my_dataset
  version: 0.1.0
  description: Initial structure analysis

current_structure:
  name: my_dataset
  resources:
    - name: measurements_2023.csv
      fields:
        - name: timestamp
        - name: Temperature
        - name: Pressure (bar)

planned_structure:  # ← Edit this!
  name: my_dataset
  resources:
    - name: timeseries_measurements
      fields:
        - name: timestamp
        - name: temperature  # ← Standardized
        - name: pressure     # ← Standardized
        - name: unit         # ← New field
```

### Step 3: Update Version and Visualize
```python
from oedbcm.structure_schema import StructurePlan

# Load edited plan
plan = StructurePlan.load_yaml("data/plans/structure_plan_my_dataset_v0.1.0.yaml")

# Increment version
plan.increment_version('minor')  # 0.1.0 → 0.2.0

# Save updated plan
plan.save_yaml()

# Create new visualization
from oedbcm.visualizer import StructureVisualizer
viz = StructureVisualizer()
viz.visualize_comparison(
    current_structure=plan.current_structure,
    planned_structure=plan.planned_structure,
    title="My Dataset - Structure Planning",
    version=plan.version
)
```

## Main Script Usage

Use the provided `plan_structure.py` script:
```bash
python plan_structure.py
```

Edit the script to configure your dataset path.

## Key Concepts

### Group Numbers

Resources with identical structure get the same `group_number`:
```yaml
resources:
  - name: measurements_jan.csv
    group_number: 1
    fields: [timestamp, value]
  
  - name: measurements_feb.csv
    group_number: 1  # ← Same structure
    fields: [timestamp, value]
  
  - name: metadata.csv
    group_number: 2  # ← Different structure
    fields: [id, description]
```

### Resource Mapping

Track transformations between current and planned:
```yaml
resource_mapping:
  - current_resource: measurements_2023.csv
    planned_resource: timeseries_measurements
    group_number: 1
    transformation_notes: "Renamed, standardized columns, added unit field"
```

### Semantic Versioning

- **Patch** (0.1.0 → 0.1.1): Minor edits
- **Minor** (0.1.0 → 0.2.0): Structural changes
- **Major** (0.1.0 → 1.0.0): Complete redesign

## Workflow Tips

1. **Start broad** - Create initial plan with `version="0.1.0"`
2. **Iterate quickly** - Make small changes, increment patch version
3. **Visualize often** - Generate PNG after each significant change
4. **Document changes** - Use `transformation_notes` in mappings
5. **Version milestones** - Increment minor/major for big decisions

## Integration with OEMetadata

The planned structure follows OEMetadata 2.0 schema:
```yaml
planned_structure:
  resources:
    - name: table_name
      type: table
      schema:
        fields:
          - name: column_name
            type: integer
            description: "..."
            unit: MW
            isAbout:
              - name: concept_name
                "@id": ontology_uri
```

See `oemetadata_table_resource.yaml` for full template.

## Troubleshooting

**Issue**: `No plan available` error  
**Solution**: Call `create_structure_plan()` before `save_complete_plan()`

**Issue**: YAML syntax errors  
**Solution**: Use a YAML validator, check indentation (2 spaces)

**Issue**: Visualization shows wrong data  
**Solution**: Reload plan from YAML before visualizing

## Next Steps

After planning:
1. Review visualization with team
2. Finalize planned structure in YAML
3. Use plan as blueprint for data transformation
4. Implement transformations in code
5. Validate against OEMetadata schema
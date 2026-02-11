"""Open Energy Database Compliance Manager

Main script for structure planning workflow.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from oedbcm import DataPackage
from oedbcm.planner import TransformationPlanner
from oedbcm.structure_schema import StructurePlan
import sys


def main_planning_workflow(
        dataset_path: Path,
        version: str = "0.2.0",
        description: str = "Initial structure planning"
):
    """
    Complete structure planning workflow.

    Args:
        dataset_path: Path to dataset directory
        version: Version string for this plan
        description: Description of planning iteration
    """
    print("\n" + "=" * 80)
    print("STRUCTURE PLANNING WORKFLOW")
    print("=" * 80 + "\n")

    # Step 1: Load and analyze dataset
    print("📦 Step 1: Loading dataset...")
    package = DataPackage(dataset_path)
    print(f"   Found {len(package.resources)} resources\n")

    # Step 2: Create planner
    print("🔍 Step 2: Analyzing structure...")
    planner = TransformationPlanner(package)

    # Assign groups automatically based on structure similarity
    groups = planner.assign_groups_by_structure()
    print()

    # Step 3: Create structure plan
    print("📋 Step 3: Creating structure plan...")
    plan = planner.create_structure_plan(
        version = version,
        description = description
    )
    print(f"   Plan version: {plan.version}")
    print(f"   Current resources: {len(plan.current_structure['resources'])}\n")

    # Step 4: Save plan (YAML + visualization)
    print("💾 Step 4: Saving plan...")
    output_files = planner.save_complete_plan(
        plan = plan,
        create_visualization = True
    )

    print("\n✅ Planning workflow complete!")
    print("-" * 80)
    print("Generated files:")
    for file_type, file_path in output_files.items():
        print(f"   {file_type}: {file_path}")

    print("\n📝 Next steps:")
    print("   1. Review the visualization PNG")
    print("   2. Edit the YAML file to define your planned structure")
    print("   3. Update resource mappings and group assignments")
    print("   4. Increment version and regenerate visualization")
    print("\n" + "=" * 80 + "\n")

    return plan, output_files


def load_and_update_plan(
        yaml_path: Path,
        increment_version: str = None
):
    """
    Load existing plan and optionally increment version.

    Args:
        yaml_path: Path to existing YAML plan
        increment_version: 'major', 'minor', or 'patch' to increment version

    Returns:
        Updated StructurePlan
    """
    print(f"\n📂 Loading plan from: {yaml_path}")
    plan = StructurePlan.load_yaml(yaml_path)

    print(f"   Current version: {plan.version}")
    print(f"   Dataset: {plan.dataset_name}")
    print(f"   Last updated: {plan.updated_at}\n")

    if increment_version:
        old_version = plan.version
        plan.increment_version(increment_version)
        print(f"✨ Version incremented: {old_version} → {plan.version}\n")

    return plan


def visualize_existing_plan(yaml_path: Path):
    """
    Create visualization from existing YAML plan.

    Args:
        yaml_path: Path to YAML plan file
    """
    from oedbcm.visualizer import StructureVisualizer

    print(f"\n🎨 Creating visualization from: {yaml_path}")
    plan = StructurePlan.load_yaml(yaml_path)

    visualizer = StructureVisualizer()
    output_path = visualizer.visualize_comparison(
        current_structure = plan.current_structure,
        planned_structure = plan.planned_structure,
        title = f"{plan.dataset_name} - Structure Planning",
        version = plan.version
    )

    print(f"✅ Visualization saved: {output_path}\n")
    return output_path


if __name__ == "__main__":
    # Example usage - adjust paths as needed

    # Configuration
    dataset_path = Path("data/raw/HSRM_Messdaten_Brennstoffzelle")

    # Check if dataset exists
    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        print("   Please update the dataset_path in this script.")
        sys.exit(1)

    # Run main workflow
    plan, files = main_planning_workflow(
        dataset_path = dataset_path,
        version = "0.1.0",
        description = "Initial structure analysis for HSRM fuel cell measurements"
    )

    # Example: Load and update existing plan
    # plan = load_and_update_plan(
    #     yaml_path=Path("data/plans/structure_plan_HSRM_Messdaten_Brennstoffzelle_v0.1.0.yaml"),
    #     increment_version='minor'  # Will become 0.2.0
    # )
    # plan.save_yaml()

    # Example: Just visualize existing plan
    # visualize_existing_plan(
    #     yaml_path=Path("data/plans/structure_plan_HSRM_Messdaten_Brennstoffzelle_v0.1.0.yaml")
    # )
"""
SPDX-FileCopyrightText: 2026 Vismaya Jochem <https://github.com/vismayajochem> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from oedbcm.planner import TransformationPlanner
from oedbcm.file_classifier import ResourceType
from oedbcm.structure_schema import StructurePlan
from oedbcm.logger import ValidationLogger
from oedbcm.package import DataPackage
import sys


def ask_user_confirmation(question: str, default: str = 'y') -> bool:
    """
    Ask user for yes/no confirmation.

    Args:
        question: Question to ask
        default: Default answer ('y' or 'n')

    Returns:
        True if yes, False if no
    """
    valid_responses = {'y': True, 'yes': True, 'n': False, 'no': False}

    prompt = f"{question} [y/n, default={default}]: "

    while True:
        response = input(prompt).strip().lower()

        if not response:
            response = default

        if response in valid_responses:
            return valid_responses[response]

        print("   Please answer 'y' or 'n'")

def main_planning_workflow(
        dataset_path: Path,
        version: str = "0.1.0",
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
    logger = ValidationLogger(dataset_name = package.dataset_name)
    logger.log_start(dataset_path, len(package.resources))
    print(f"   Found {len(package.resources)} resources\n")

    # 🔴 USER INPUT 1: Start planning?
    print("📊 ANALYSIS COMPLETE")
    print()

    if not ask_user_confirmation("⏸️  Start planning phase?", default = 'y'):
        print("\n⏹️  Planning aborted by user")
        print("   Re-run script when ready to continue")
        print("=" * 80 + "\n")
        return None, {}
    print()

    # Step 2: Create planner
    print("🔍 Step 2: Analyzing structure...")
    planner = TransformationPlanner(package)

    # Step 2a: Create classification catalog
    print("📋 Step 2a: Creating resource classification catalog...")
    classification_result = planner.create_catalog_draft(
        version=version,
        auto_assign_groups=False)

    # Show classification summary
    print(f"\n   Classification breakdown:")
    for type_name, count in sorted(classification_result['type_counts'].items()):
        print(f"     • {type_name:<25} {count:>2} resources")

    print(f"\n   Catalog files:")
    print(f"     Draft:  {classification_result['draft_path']}")
    print(
        f"     Catalog: {classification_result['catalog_path']} ({classification_result['catalog_status']})")

    # 🔴 USER INPUT 2: Classifications correct?
    print()
    print("📝 REVIEW CATALOG (DATATYPES)")
    print("-" * 80)
    print(f"   Please review: {classification_result['catalog_path']}")
    print(f"   - Check 'type' column (Data, Metadata, Additional Data, etc.)")
    print()

    if not ask_user_confirmation("⏸️  All datatypes correct?", default = 'n'):
        print("\n⏸️  Please edit the catalog file and re-run the script")
        print(f"   File: {classification_result['catalog_path']}")
        print("=" * 80 + "\n")
        return None, {}
    print()

    # Load catalog
    print(f"   ℹ️  Loading catalog...")
    planner.load_catalog(classification_result['catalog_path'])
    print()

    # Step 2b: Analyze only DATA resources
    print("🔍 Step 2b: Analyzing DATA resources...")
    package.analyze_all(filter_by_classification = True)
    print()

    # Step 2c: Verify group assignments
    print("🔍 Step 2c: Structure groups assigned")
    print()

    # Assign groups based on structure
    groups = planner.assign_groups_by_structure()

    # Update catalog file with target_group assignments
    import csv
    print(f"   Updating catalog with target_group assignments...")
    try:
        updated_rows = []
        with open(classification_result['catalog_path'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                filename = row['filename']
                assigned_group = ""
                for g_id, files in groups.items():
                    if filename in files:
                        assigned_group = f"group_{g_id}"
                        break
                row['target_group'] = assigned_group
                updated_rows.append(row)
                
        with open(classification_result['catalog_path'], 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)
    except Exception as e:
        print(f"   ⚠️ Could not update catalog with target_group: {e}")

    # Show group details
    print("   Group assignments:")
    for group_id, files in groups.items():
        print(f"     Group {group_id}: {len(files)} files")
        for filename in files[:3]:
            print(f"       - {filename}")
        if len(files) > 3:
            print(f"       ... +{len(files) - 3} more")
    print()

    # 🔴 USER INPUT 3: Groups correct?
    print("📊 REVIEW GROUPS IN CATALOG")
    print("-" * 80)
    print(f"   {len(groups)} groups with identical column structures")
    print(f"   Please review 'target_group' column in: {classification_result['catalog_path']}")
    print()

    if not ask_user_confirmation("⏸️  All group assignments correct?", default = 'y'):
        print("\n⏸️  Group assignment needs manual review")
        print("   Consider:")
        print("   - Editing catalog 'target_group' column manually")
        print("   - Re-running with corrected catalog")
        print("=" * 80 + "\n")
        return None, {}
    print()

    # Reload the catalog in case user changed 'target_group' manually
    print(f"   ℹ️  Reloading catalog group assignments...")
    planner.load_catalog(classification_result['catalog_path'])
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
    print("   1. Review catalog and set 'target_group' for DATA files:")
    print(f"      {classification_result['catalog_path']}")
    print("   2. Review and edit grouped structures:")
    print(
        f"      data/2_planning/{package.dataset_name}/structure/structure_group*_target.yaml")
    print("   3. Review and edit OEMetadata sections:")
    print(f"      data/2_planning/{package.dataset_name}/metadata/oemetadata_*.yaml")
    print("   4. Review visualization:")
    print(f"      {output_files.get('visualization', 'N/A')}")

    # Step 5: Save grouped structures
    print("📊 Step 5: Saving grouped structures...")
    grouped_files = planner.save_grouped_structures(
        version = version,
        description = "Structure groups for HSRM measurements"
    )
    print()

    # Step 6: Create OEMetadata drafts
    print("📄 Step 6: Creating OEMetadata section drafts...")
    from oedbcm.metadata_builder import OEMetadataBuilder

    builder = OEMetadataBuilder(package.dataset_name)
    metadata_drafts = builder.create_all_drafts(
        title = f"HSRM Fuel Cell Measurements",
        description = description,
        contributor_name = "HSRM",
        contributor_email = "contact@example.com"
    )
    print()

    # Step 7: Create overview tables
    print("📊 Step 7: Creating overview tables...")

    # Table overview (matrix)
    table_overview_path = planner.create_table_overview(version = version)

    # Group overview (matrix)
    group_overview_path = planner.create_group_overview(version = version)

    # Column details (list)
    column_detail_path = planner.create_column_detail_list(version = version)

    print()

    print("\n✅ Planning workflow complete!")
    print("-" * 80)
    print("Generated files:")
    print(f"\n📋 Catalog:")
    print(f"   {classification_result['catalog_path']}")

    print(f"\n📊 Overviews (in reports/):")
    print(f"   - Table overview:  {table_overview_path}")
    print(f"   - Group overview:  {group_overview_path}")
    print(f"   - Column details:  {column_detail_path}")

    print(f"\n📁 Structure plans:")
    for file_type, file_path in output_files.items():
        print(f"   {file_type}: {file_path}")

    print(f"\n🗂️  Grouped structures: {len(grouped_files)} groups")
    for group_num, paths in grouped_files.items():
        print(
            f"     Group {group_num}: {paths['file_count']} files, {paths['column_count']} columns")

    print(f"\n📄 OEMetadata sections: {len(metadata_drafts)}")

    builder = OEMetadataBuilder(package.dataset_name)
    metadata_drafts = builder.create_all_drafts(
        title = f"Dataset: {package.dataset_name}",
        description = description,
        contributor_name = "Your Name",
        contributor_email = "email@example.com"
    )
    print()

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

    visualizer = StructureVisualizer(dataset_name = plan.dataset_name)
    output_path = visualizer.visualize_comparison(
        current_structure = plan.current_structure,
        planned_structure = plan.planned_structure,
        title = f"{plan.dataset_name} - Structure Planning",
        version = plan.version
    )

    print(f"✅ Visualization saved: {output_path}\n")
    return output_path
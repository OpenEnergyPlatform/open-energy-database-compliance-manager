"""Open Energy Database Compliance Manager

Generic structure planning script - easily adaptable for any dataset.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
import sys

from oedbcm.config import WorkflowConfig, ask_user_confirmation, print_section_header
from oedbcm.package import DataPackage
from oedbcm.planner import TransformationPlanner
from oedbcm.logger import ValidationLogger
from oedbcm.metadata_builder import OEMetadataBuilder


def run_planning_workflow(config: WorkflowConfig) -> bool:
    """
    Execute complete planning workflow.

    Args:
        config: Workflow configuration

    Returns:
        True if successful, False if aborted
    """
    # Initialize
    package = DataPackage(config.dataset_path)
    logger = ValidationLogger(package.dataset_name)
    planner = TransformationPlanner(package)

    logger.log_start(config.dataset_path, len(package.resources))

    # USER INPUT 1: Start planning?
    print_section_header("STEP 1: ANALYSIS")
    logger.logger.info(f"Found {len(package.resources)} resources")

    if not ask_user_confirmation("▶️  Start planning phase?", default = 'y'):
        logger.logger.info("Planning aborted by user")
        return False

    # CREATE CATALOG
    print_section_header("STEP 2: CLASSIFICATION")
    logger.logger.info("Creating classification catalog...")

    result = planner.create_catalog_draft(
        version = config.version,
        auto_assign_groups = config.auto_assign_groups
    )

    logger.logger.info(
        f"Catalog: {result['catalog_path']} ({result['catalog_status']})")
    for type_name, count in result['type_counts'].items():
        logger.logger.info(f"  {type_name}: {count} resources")

    # USER INPUT 2: Catalog correct?
    print(f"\n📝 Review catalog: {result['catalog_path']}")
    print("   - Verify 'type' classifications")
    print("   - Check 'target_group' assignments\n")

    if not ask_user_confirmation("▶️  Catalog correct?", default = 'n'):
        logger.logger.info("Waiting for catalog edits - please re-run after editing")
        return False

    # Load catalog
    planner.load_catalog(result['catalog_path'])

    # ANALYZE DATA
    print_section_header("STEP 3: STRUCTURE ANALYSIS")
    logger.logger.info("Analyzing DATA and ADDITIONAL_DATA resources...")

    package.analyze_all(filter_by_classification = True)
    groups = planner.assign_groups_by_structure()

    logger.logger.info(f"Identified {len(groups)} structure groups")
    for group_id, files in groups.items():
        logger.logger.info(f"  Group {group_id}: {len(files)} files")

    # USER INPUT 3: Groups correct?
    print(f"\n📊 {len(groups)} groups identified")

    if not ask_user_confirmation("▶️  Group assignments correct?", default = 'y'):
        logger.logger.info("Group assignment needs review - edit catalog manually")
        return False

    # CREATE PLANNING OUTPUTS
    print_section_header("STEP 4: GENERATING OUTPUTS")

    # Structure plan
    logger.logger.info("Creating structure plan...")
    plan = planner.create_structure_plan(
        version = config.version,
        description = config.description
    )

    output_files = planner.save_complete_plan(
        plan = plan,
        create_visualization = config.create_visualization
    )

    # Grouped structures
    logger.logger.info("Saving grouped structures...")
    grouped_files = planner.save_grouped_structures(
        version = config.version,
        description = config.description
    )

    # Overview tables
    if config.create_overview_tables:
        logger.logger.info("Creating overview tables...")
        planner.create_table_overview(version = config.version)
        planner.create_group_overview(version = config.version)
        planner.create_column_detail_list(version = config.version)

    # OEMetadata
    if config.create_metadata_drafts:
        logger.logger.info("Creating OEMetadata drafts...")
        builder = OEMetadataBuilder(package.dataset_name)
        builder.create_all_drafts(
            title = config.title,
            description = config.description,
            contributor_name = config.contributor_name,
            contributor_email = config.contributor_email
        )

    # SUMMARY
    print_section_header("✅ WORKFLOW COMPLETE")

    logger.logger.info(f"Structure plans: {len(output_files)} files")
    logger.logger.info(f"Grouped structures: {len(grouped_files)} groups")
    logger.logger.info(f"Catalog: {result['catalog_path']}")

    print("\n📁 Output locations:")
    print(f"   Plans:    data/1_planning/{package.dataset_name}/structure/")
    print(f"   Metadata: data/1_planning/{package.dataset_name}/metadata/")
    print(f"   Reports:  data/1_planning/{package.dataset_name}/reports/")

    return True


if __name__ == "__main__":
    # Messdaten HSRM

    config = WorkflowConfig(
        # Required
        dataset_path = "data/0_raw/HSRM_Messdaten_Brennstoffzelle",
        version = "0.11.0",
        description = "Planning structure for HSRM fuel cell measurements",

        # Optional metadata
        title = "HSRM Fuel Cell Measurements",
        contributor_name = "HSRM",

        # Optional workflow flags
        auto_assign_groups = True,
        create_visualization = True,
        create_metadata_drafts = True,
        create_overview_tables = True
    )

    # RUN WORKFLOW

    if not config.dataset_path.exists():
        print(f"❌ Dataset not found: {config.dataset_path}")
        sys.exit(1)

    success = run_planning_workflow(config)

    sys.exit(0 if success else 1)

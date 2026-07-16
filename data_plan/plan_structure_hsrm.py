"""Open Energy Database Compliance Manager

Main script for structure planning workflow.
DataPackage HSRM.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
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
from oedbcm.planner_structure import ask_user_confirmation, main_planning_workflow, load_and_update_plan, visualize_existing_plan



if __name__ == "__main__":
    # Example usage - adjust paths as needed

    # Configuration
    dataset_path = Path("data/0_raw/HSRM_Messdaten_Brennstoffzelle_v0.1")

    # Check if dataset exists
    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        print("   Please update the dataset_path in this script.")
        sys.exit(1)

    # Run main workflow
    result  = main_planning_workflow(
        dataset_path = dataset_path,
        version = "0.9.0",
        description = "Planning structure for HSRM fuel cell measurements"
    )

    # Check if user aborted
    if result[0] is None:
        print("Workflow was aborted. Exiting.")
        sys.exit(0)

    plan, files = result

    print("\n🎉 All steps completed successfully!")
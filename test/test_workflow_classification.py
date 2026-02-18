"""Open Energy Database Compliance Manager

Workflow example: Resource classification.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from oedbcm import DataPackage
from oedbcm.planner import TransformationPlanner
from oedbcm.file_classifier import ResourceType


def workflow_classification(dataset_path: Path):
    """
    Complete classification workflow.

    Steps:
    1. Create draft catalog
    2. User edits draft → saves as _catalog.csv
    3. Load catalog and apply to resources
    4. Filter resources by type
    """

    print("\n" + "=" * 80)
    print("RESOURCE CLASSIFICATION WORKFLOW")
    print("=" * 80 + "\n")

    # Load package
    package = DataPackage(dataset_path)
    planner = TransformationPlanner(package)

    # Step 1: Create draft catalog
    print("📋 Step 1: Creating classification draft...")
    result = planner.create_catalog_draft()

    planner.classifier.print_classification_summary(result)

    print(f"\n📝 MANUAL STEP REQUIRED:")
    print(f"   1. Open: {result['draft_path']}")
    print(f"   2. Review and edit 'type' column if needed")
    print(f"   3. Save as: data/catalogs/{package.dataset_name}_catalog.csv")
    print(f"\n   Press Enter when done...")

    # Wait for user (comment out for automated testing)
    # input()

    # Step 2: Load finalized catalog
    print("\n📂 Step 2: Loading finalized catalog...")
    catalog_path = Path("data/catalogs") / f"{package.dataset_name}_catalog.csv"

    if not catalog_path.exists():
        print(f"⚠️  Catalog not found. Using draft for demonstration.")
        # For demo: copy draft to catalog
        import shutil
        shutil.copy(result['draft_path'], catalog_path)

    classified_count = planner.load_catalog(catalog_path)

    # Step 3: Filter resources by type
    print("\n🔍 Step 3: Filtering resources by type...")

    data_resources = planner.get_resources_by_type(ResourceType.DATA)
    metadata_resources = planner.get_resources_by_type(ResourceType.METADATA)

    print(f"\n   DATA resources ({len(data_resources)}):")
    for res in data_resources[:5]:
        print(f"     • {res.path.name}")
    if len(data_resources) > 5:
        print(f"     ... +{len(data_resources) - 5} more")

    print(f"\n   METADATA resources ({len(metadata_resources)}):")
    for res in metadata_resources[:5]:
        print(f"     • {res.path.name}")
    if len(metadata_resources) > 5:
        print(f"     ... +{len(metadata_resources) - 5} more")

    # Step 4: Verify classifications on resources
    print("\n✅ Step 4: Verification - Resource objects updated:")
    for resource in package.resources[:3]:
        class_val = resource.classification.value if resource.classification else "Not classified"
        print(f"   • {resource.path.name:<40} → {class_val}")

    print("\n" + "=" * 80)
    print("CLASSIFICATION COMPLETE")
    print("=" * 80 + "\n")

    return planner


if __name__ == "__main__":
    dataset_path = Path("data/0_raw/HSRM_Messdaten_Brennstoffzelle")

    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        exit(1)

    planner = workflow_classification(dataset_path)

"""Open Energy Database Compliance Manager
Main script for merging data tables.
"""
import sys
from pathlib import Path

# Import the workflow from the src module
from oedbcm.table_merger import main_merging_workflow

if __name__ == "__main__":
    # Configuration
    dataset_path = Path("data/0_raw/HSRM_Messdaten_Brennstoffzelle")

    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        print("   Please update the dataset_path in this script.")
        sys.exit(1)

    # Run main merging workflow
    main_merging_workflow(
        dataset_path = dataset_path,
        catalog_path = Path("data/1_planning/HSRM..._catalog.csv")
    )

    print("\n🎉 All merging steps finished!")
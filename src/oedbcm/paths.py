"""Open Energy Database Compliance Manager

Centralized path management for consistent directory structure.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from typing import Optional


class ProjectPaths:
    """
    Centralized path management for the project.

    data/
      0_raw/                    # Raw input data
      2_planning/                  # Planning artifacts per dataset
        [DataPackageName]/
          catalogs/             # Resource classification catalogs
          plots/                # Visualizations
          reports/              # Analysis reports
          structure/            # Structure plans (YAML)
          metadata/             # OEMetadata drafts
      3_results/                # Final transformed data
        [DataPackageName]/
    """

    # Base directories
    BASE_DATA = Path("data")
    RAW = BASE_DATA / "0_raw"
    PLANS = BASE_DATA / "1_planning"
    RESULTS = BASE_DATA / "2_results"

    def __init__(self, dataset_name: str):
        """
        Initialize paths for a specific dataset.

        Args:
            dataset_name: Name of the dataset
        """
        self.dataset_name = dataset_name

        # Dataset-specific directories
        self.dataset_plans = self.PLANS / dataset_name

        self.catalogs = self.dataset_plans / "catalogs"
        self.plots = self.dataset_plans / "plots"
        self.reports = self.dataset_plans / "reports"
        self.structure = self.dataset_plans / "structure"
        self.metadata = self.dataset_plans / "metadata"

        # Results directory
        self.dataset_results = self.RESULTS / dataset_name
        self.config = self.dataset_results / "config"

    def ensure_all(self):
        """Create all directories if they don't exist."""
        for dir_path in [
            self.RAW,
            self.catalogs,
            self.plots,
            self.reports,
            self.structure,
            self.metadata,
            self.dataset_results
        ]:
            dir_path.mkdir(parents = True, exist_ok = True)

    def get_catalog_draft_path(self, version: str = None) -> Path:
        """Get path for catalog draft CSV."""
        if version:
            return self.catalogs / f"{self.dataset_name}_v{version}_catalog_draft.csv"
        return self.catalogs / f"{self.dataset_name}_catalog_draft.csv"

    def get_catalog_path(self, version: str = None) -> Path:
        """Get path for finalized catalog CSV."""
        if version:
            return self.catalogs / f"{self.dataset_name}_v{version}_catalog.csv"
        return self.catalogs / f"{self.dataset_name}_catalog.csv"

    def get_latest_catalog(self) -> Path:
        """
        Get path to latest catalog version.

        Returns:
            Path to latest *_catalog.csv file, or None if not found.
        """
        catalog_files = list(self.catalogs.glob(f"{self.dataset_name}_v*_catalog.csv"))
        if catalog_files:
            return sorted(catalog_files)[-1]

        # Fallback to unversioned
        unversioned = self.get_catalog_path()
        if unversioned.exists():
            return unversioned

        return None

    def get_structure_current_path(self, version: str) -> Path:
        """Get path for current structure YAML."""
        return self.structure / f"{self.dataset_name}_v{version}_structure_dataset_current.yaml"

    def get_structure_plan_path(self, version: str) -> Path:
        """Get path for planned structure YAML."""
        return self.structure / f"{self.dataset_name}_v{version}_structure_dataset_plan.yaml"

    def get_visualization_path(self, version: str) -> Path:
        """Get path for structure visualization PNG."""
        return self.plots / f"{self.dataset_name}_v{version}_structure_comparison.png"

    def get_metadata_draft_path(self, section: str) -> Path:
        """
        Get path for OEMetadata section draft.

        Args:
            section: Section name (general, context, spatial, contributors, sources, licenses)
        """
        return self.metadata / f"oemetadata_{section}_draft.yaml"

    def get_metadata_path(self, section: str) -> Path:
        """Get path for finalized OEMetadata section."""
        return self.metadata / f"oemetadata_{section}.yaml"


def get_project_paths(dataset_name: str) -> ProjectPaths:
    """
    Convenience function to get ProjectPaths instance.

    Args:
        dataset_name: Name of the dataset

    Returns:
        ProjectPaths instance
    """
    paths = ProjectPaths(dataset_name)
    paths.ensure_all()
    return paths

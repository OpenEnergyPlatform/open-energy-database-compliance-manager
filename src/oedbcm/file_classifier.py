"""Open Energy Database Compliance Manager

Resource classification for data package cataloging.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from typing import Dict, List, Any, Literal
from enum import Enum
import csv
import re


class ResourceType(Enum):
    """Resource classification types."""
    DATA = "Data"
    METADATA = "Metadata"
    ADDITIONAL_DATA = "Additional Data"
    NOT_SUPPORTED = "Not Supported Yet"
    IGNORE = "Ignore"


class ResourceClassifier:
    """Classify resources in a data package."""

    # Keywords für Metadata-Erkennung
    METADATA_KEYWORDS = [
        'metadata', 'description', 'info', 'readme',
        'documentation', 'legend', 'codebook'
    ]

    # Keywords für Additional Data
    ADDITIONAL_KEYWORDS = [
        'sensor', 'device', 'equipment', 'model',
        'calibration', 'setup', 'configuration'
    ]

    # Unterstützte Datenformate
    SUPPORTED_DATA_FORMATS = ['.csv', '.txt', '.tsv']

    # Nicht unterstützte aber datenhaltige Formate
    DATA_FORMATS_NOT_SUPPORTED = ['.xlsx', '.xls', '.sqlite', '.db', '.json']

    # Zu ignorierende Formate
    IGNORE_FORMATS = [
        '.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg',
        '.gif', '.bmp', '.zip', '.rar', '.7z'
    ]

    def __init__(self):
        """Initialize classifier."""
        pass

    def classify_resource(
            self,
            resource_path: Path,
            n_rows: int = None,
            n_columns: int = None,
            column_names: List[str] = None
    ) -> ResourceType:
        """
        Classify a single resource.

        Args:
            resource_path: Path to the resource file
            n_rows: Number of rows (if analyzed)
            n_columns: Number of columns (if analyzed)
            column_names: Column names (if analyzed)

        Returns:
            ResourceType classification
        """
        filename = resource_path.stem.lower()
        file_ext = resource_path.suffix.lower()

        # 1. Check IGNORE formats
        if file_ext in self.IGNORE_FORMATS:
            return ResourceType.IGNORE

        # 2. Check NOT_SUPPORTED formats
        if file_ext in self.DATA_FORMATS_NOT_SUPPORTED:
            return ResourceType.NOT_SUPPORTED

        # 3. Check if supported format
        if file_ext not in self.SUPPORTED_DATA_FORMATS:
            return ResourceType.IGNORE

        # 4. Classify by filename patterns

        # Metadata detection
        if any(kw in filename for kw in self.METADATA_KEYWORDS):
            return ResourceType.METADATA

        # Additional Data detection
        if any(kw in filename for kw in self.ADDITIONAL_KEYWORDS):
            return ResourceType.ADDITIONAL_DATA

        # 5. Classify by structure (if available)
        if n_rows is not None and n_columns is not None:
            # Very small files are likely metadata
            if n_rows < 20 and n_columns < 5:
                return ResourceType.METADATA

            # Files with many descriptive columns might be metadata
            if column_names:
                descriptive_cols = sum(
                    1 for col in column_names
                    if any(kw in col.lower() for kw in ['description', 'name', 'info'])
                )
                if descriptive_cols >= n_columns / 2:
                    return ResourceType.METADATA

        # 6. Default: DATA
        return ResourceType.DATA

    def classify_package(
            self,
            package,
            output_dir: Path = None
    ) -> Dict[str, Any]:
        """
        Classify all resources in a package and create catalog draft.

        Args:
            package: DataPackage instance
            output_dir: Output directory for catalog (default: data/catalogs/)

        Returns:
            Dict with classification results
        """
        if output_dir is None:
            output_dir = Path("data/catalogs")
        output_dir.mkdir(parents = True, exist_ok = True)

        # Analyze package if not done yet
        if not all(r.column_names is not None for r in package.resources):
            package.analyze_all()

        # Classify each resource
        classifications = []

        for resource in package.resources:
            classification = self.classify_resource(
                resource.path,
                resource.n_rows,
                resource.n_columns,
                resource.column_names
            )

            classifications.append({
                'filename': resource.path.name,
                'path': str(resource.path),
                'type': classification.value,
                'rows': resource.n_rows or 0,
                'columns': resource.n_columns or 0,
                'size_mb': round(resource.file_size / (1024 * 1024), 3),
                'format': resource.file_type.upper(),
                'encoding': getattr(resource, 'detected_encoding', 'utf-8'),
                'notes': ''  # For manual editing
            })

        # Create draft catalog
        draft_path = output_dir / f"{package.dataset_name}_draft.csv"
        self._save_catalog_csv(classifications, draft_path)

        print(f"✅ Draft catalog created: {draft_path}")
        print(f"   📝 Edit and save as '{package.dataset_name}_catalog.csv' to use")

        # Statistics
        type_counts = {}
        for c in classifications:
            type_val = c['type']
            type_counts[type_val] = type_counts.get(type_val, 0) + 1

        return {
            'draft_path': draft_path,
            'total_resources': len(classifications),
            'classifications': classifications,
            'type_counts': type_counts
        }

    def _save_catalog_csv(self, classifications: List[Dict], output_path: Path):
        """Save classifications to CSV."""
        fieldnames = [
            'filename', 'type', 'rows', 'columns',
            'size_mb', 'format', 'encoding', 'notes'
        ]

        with open(output_path, 'w', newline = '', encoding = 'utf-8') as f:
            writer = csv.DictWriter(f, fieldnames = fieldnames)
            writer.writeheader()

            for item in classifications:
                # Write only necessary fields
                row = {k: item[k] for k in fieldnames}
                writer.writerow(row)

    def load_catalog(self, catalog_path: Path) -> Dict[str, ResourceType]:
        """
        Load finalized catalog CSV.

        Args:
            catalog_path: Path to catalog CSV

        Returns:
            Dict mapping filename to ResourceType
        """
        catalog = {}

        with open(catalog_path, 'r', encoding = 'utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                filename = row['filename']
                type_str = row['type']

                # Map string back to Enum
                try:
                    resource_type = ResourceType(type_str)
                except ValueError:
                    resource_type = ResourceType.DATA  # Fallback

                catalog[filename] = resource_type

        return catalog

    def print_classification_summary(self, result: Dict[str, Any]):
        """Print classification summary."""
        print("\n" + "=" * 70)
        print("RESOURCE CLASSIFICATION SUMMARY")
        print("=" * 70)

        print(f"\nTotal Resources: {result['total_resources']}")
        print("\nClassification Breakdown:")
        print("-" * 70)

        for type_name, count in sorted(result['type_counts'].items()):
            print(f"  {type_name:<25} {count:>3} resources")

        print("\n" + "=" * 70)

    def apply_catalog_to_package(
            self,
            package,
            catalog_path: Path = None
    ) -> int:
        """
        Load catalog and apply classifications to package resources.

        Args:
            package: DataPackage instance
            catalog_path: Path to catalog CSV. If None, auto-detect.

        Returns:
            Number of resources classified
        """
        if catalog_path is None:
            # Try to find catalog in standard location
            catalog_dir = Path("data/catalogs")
            catalog_path = catalog_dir / f"{package.dataset_name}_catalog.csv"

            if not catalog_path.exists():
                print(f"⚠️  No catalog found at {catalog_path}")
                print(f"   Create draft with: classifier.classify_package()")
                return 0

        # Load catalog
        catalog = self.load_catalog(catalog_path)

        # Apply to resources
        classified_count = 0
        for resource in package.resources:
            if resource.path.name in catalog:
                resource.classification = catalog[resource.path.name]
                classified_count += 1

        print(f"✅ Applied catalog classifications to {classified_count} resources")
        return classified_count

"""Open Energy Database Compliance Manager

Metadata digesting module - Extract OEMetadata using OMI and standardizers.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import csv
import re
from dataclasses import dataclass, field

try:
    from omi import inspection
except ImportError:
    print("Warning: 'omi' library not found. Please install via pip.")
    inspection = None


@dataclass
class DigestConfig:
    """Configuration for metadata extraction."""

    # Unit extraction patterns
    unit_patterns: List[str] = field(default_factory=lambda: [
        r'\[([^\]]+)\]',  # [unit]
        r'\(([^\)]+)\)',  # (unit)
        r'_in_(\w+)',     # column_in_MW
        r'_(\w+)$',       # column_kW (at end)
    ])

    # Description cleanup
    description_cleanup_patterns: List[str] = field(default_factory=lambda: [
        r'\s*\[.*?\]\s*',  # Remove [units]
        r'\s*\(.*?\)\s*',  # Remove (units)
        r'_in_\w+$',       # Remove _in_unit suffix
    ])

    # Column name standardization
    standardize_column_names: bool = True

    custom_extractors: Dict[str, Callable[[str, List[Any]], Any]] = field(
        default_factory = dict
    )

class MetadataDigester:
    """
    Extract and generate OEMetadata using OMI inspection and custom cleaning.
    """

    def __init__(self, config: DigestConfig = None):
        self.config = config or DigestConfig()

    def _ensure_dataset_dir(self, base_path: Path, dataset_name: str) -> Path:
        """Create dataset specific subdirectory."""
        target_dir = base_path / dataset_name
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def extract_unit(self, column_name: str) -> Optional[str]:
        """Extract unit from column name using configured patterns."""
        for pattern in self.config.unit_patterns:
            match = re.search(pattern, column_name)
            if match:
                unit = match.group(1).strip()
                # Einfache Plausibilitätsprüfung: Einheiten sind meist kurz
                if len(unit) < 10:
                    return unit
        return None

    def create_description(self, original_name: str) -> str:
        """Create clean description from original column name."""
        description = original_name
        for pattern in self.config.description_cleanup_patterns:
            description = re.sub(pattern, '', description)
        return ' '.join(description.split()).strip()

    def standardize_column_name(self, original_name: str) -> str:
        """Convert column name to OEMetadata/database-compliant format."""
        if not self.config.standardize_column_names:
            return original_name

        # Extract base name (remove units)
        name = original_name
        for pattern in self.config.description_cleanup_patterns:
            name = re.sub(pattern, '', name)

        # Convert to lowercase and replace special chars
        name = name.lower()
        name = re.sub(r'[^a-z0-9_]', '_', name)
        name = re.sub(r'_+', '_', name).strip('_')

        # Ensure starts with letter
        if name and name[0].isdigit():
            name = 'col_' + name

        return name

    def infer_datatype(
            self,
            column_name: str,
            sample_values: List[Any] = None
    ) -> str:
        """
        Infer basic frictionless-compatible datatype.
        """

        if not sample_values:
            return "string"

        has_float = False
        has_int = False
        has_bool = False

        for value in sample_values:
            if value is None or value == "":
                continue

            if isinstance(value, bool):
                has_bool = True
                continue

            if isinstance(value, int):
                has_int = True
                continue

            if isinstance(value, float):
                has_float = True
                continue

            return "string"

        if has_float:
            return "number"

        if has_int:
            return "integer"

        if has_bool:
            return "boolean"

        return "string"

    def digest_resource(self, resource_path: Path, dataset_name: str = None) -> Dict[str, Any]:
        """
        Analyze a resource using OMI and apply standardization.

        Args:
            resource_path: Path to the CSV file.
            dataset_name: Name of the dataset (optional, for logging context).

        Returns:
            OEMetadata resource definition.
        """
        if inspection is None:
            raise ImportError("OMI library is required for digestion.")

        # 1. Use OMI to inspect the file
        with open(resource_path, "r", encoding='utf-8', errors='replace') as f:
            # OMI returns a full datapackage descriptor dict
            try:
                omi_metadata = inspection.infer_metadata(f, "OEP")
            except Exception as e:
                print(f"Error inspecting {resource_path.name}: {e}")
                # Fallback minimal structure if OMI fails
                omi_metadata = {"resources": [{"schema": {"fields": []}}]}

        # Extract the schema from the first resource detected by OMI
        omi_fields = []
        if omi_metadata.get("resources"):
            omi_fields = omi_metadata["resources"][0].get("schema", {}).get("fields", [])

        # 2. Refine OMI results with our standardization logic
        processed_fields = []

        # If OMI found no fields (empty file?), try to read header manually for names
        if not omi_fields:
            with open(resource_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                try:
                    header = next(reader)
                    omi_fields = [{'name': h, 'type': 'string'} for h in header]
                except StopIteration:
                    pass

        for field_def in omi_fields:
            original_name = field_def.get("name", "unknown")
            original_type = field_def.get("type", "string")

            # Standardize Name
            std_name = self.standardize_column_name(original_name)

            # Extract Unit (if not detected by OMI or to override)
            unit = field_def.get("unit") or self.extract_unit(original_name)

            # Create Description
            description = field_def.get("description") or self.create_description(original_name)

            new_field = {
                "name": std_name,
                "type": original_type,  # Keep OMI inferred type
                "description": description,
                "original_name": original_name, # Keep track of source
                "unit": unit,
                "nullable": True
            }
            processed_fields.append(new_field)

        # 3. Build Resource Definition
        resource_def = {
            "name": self.standardize_column_name(resource_path.stem),
            "path": resource_path.name,
            "profile": "tabular-data-resource",
            "schema": {
                "fields": processed_fields,
                "primaryKey": []
            }
        }

        return resource_def

    def digest_field(
            self,
            original_name: str,
            sample_values: List[Any] = None,
            custom_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create OEMetadata 2.0 field definition from column information.

        Args:
            original_name: Original column name
            sample_values: Optional sample values for type inference
            custom_metadata: Optional custom metadata to merge

        Returns:
            Complete OEMetadata 2.0 field definition
        """
        # Standardize name
        standardized_name = self.standardize_column_name(original_name)

        # Extract unit
        unit = self.extract_unit(original_name)

        # Infer datatype
        datatype = self.infer_datatype(original_name, sample_values)

        # Create description (use original name as description)
        description = self.create_description(original_name)

        # Build complete OEMetadata 2.0 field definition
        field_def = {
            'name': standardized_name,
            'type': datatype,
            'description': description,
            'nullable': True,  # Conservative default
            'unit': unit,
            'isAbout': [
                # Empty list - to be filled manually or by ontology matching
                # Example: {'name': 'temperature', '@id': 'http://...'}
            ],
            'valueReference': [
                # Empty list - to be filled manually
                # Example: {'value': 'active', 'name': 'active state', '@id': 'http://...'}
            ]
        }

        # Apply custom metadata if provided
        if custom_metadata:
            field_def.update(custom_metadata)

        # Apply custom extractors
        for extractor_name, extractor_func in self.config.custom_extractors.items():
            try:
                result = extractor_func(original_name, sample_values)
                if result:
                    field_def[extractor_name] = result
            except Exception as e:
                print(f"Warning: Custom extractor '{extractor_name}' failed: {e}")

        return field_def

    def create_empty_template(self,
                            resource_def: Dict[str, Any],
                            dataset_name: str,
                            output_base_dir: Path = Path("data/processed")) -> Path:
        """
        Generate an empty CSV file with the new standardized structure.

        Args:
            resource_def: The digested resource definition containing the schema.
            dataset_name: Name of the dataset (defines the subfolder).
            output_base_dir: Base directory for output.

        Returns:
            Path to the created template file.
        """
        # Ensure subdirectory exists: data/processed/DatasetName/
        target_dir = output_base_dir / dataset_name
        target_dir.mkdir(parents = True, exist_ok = True)

        file_path = target_dir / f"{resource_def['name']}.csv"

        headers = [field['name'] for field in
                   resource_def.get('schema', {}).get('fields', [])]

        with open(file_path, 'w', newline = '', encoding = 'utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

        return file_path

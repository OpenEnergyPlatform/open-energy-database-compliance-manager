"""Open Energy Database Compliance Manager

Metadata digesting module - Extract OEMetadata using OMI and standardizers.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
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

    class OEMetadataBuilder:
        """
        Build complete OEMetadata sections from templates and user input.

        Generates draft YAML files for each OEMetadata section that can be
        manually edited before final compilation.
        """

        def __init__(self, dataset_name: str):
            """
            Initialize OEMetadata builder.

            Args:
                dataset_name: Name of the dataset
            """
            self.dataset_name = dataset_name
            from .paths import get_project_paths
            self.paths = get_project_paths(dataset_name)

        def create_general_keys_draft(
                self,
                title: str = None,
                description: str = None,
                language: List[str] = None
        ) -> Path:
            """
            Create draft for general OEMetadata keys.

            Args:
                title: Dataset title (auto-generated if None)
                description: Dataset description
                language: List of language codes (default: ['en'])

            Returns:
                Path to created draft file
            """
            import yaml
            from datetime import datetime

            draft = {
                'name': self.dataset_name,
                'title': title or f"Dataset: {self.dataset_name}",
                'id': f"https://openenergy-platform.org/dataedit/view/{self.dataset_name}",
                'description': description or "Please provide dataset description",
                'language': language or ['en'],
                'keywords': [],  # To be filled manually
                'publicationDate': datetime.now().strftime("%Y-%m-%d"),
                'context': {
                    'homepage': None,
                    'documentation': None,
                    'sourceCode': None,
                    'contact': None,
                    'grantNo': None,
                    'fundingAgency': None,
                    'fundingAgencyLogo': None,
                    'publisherLogo': None
                }
            }

            output_path = self.paths.get_metadata_draft_path('general_keys')
            with open(output_path, 'w', encoding = 'utf-8') as f:
                yaml.dump(draft, f, default_flow_style = False, allow_unicode = True,
                          sort_keys = False)

            print(f"✅ General keys draft: {output_path}")
            return output_path

        def create_context_draft(
                self,
                homepage: str = None,
                documentation: str = None
        ) -> Path:
            """Create draft for context section."""
            import yaml

            draft = {
                'homepage': homepage,
                'documentation': documentation,
                'sourceCode': None,
                'contact': None,
                'grantNo': None,
                'fundingAgency': None,
                'fundingAgencyLogo': None,
                'publisherLogo': None
            }

            output_path = self.paths.get_metadata_draft_path('context')
            with open(output_path, 'w', encoding = 'utf-8') as f:
                yaml.dump(draft, f, default_flow_style = False, allow_unicode = True,
                          sort_keys = False)

            print(f"✅ Context draft: {output_path}")
            return output_path

        def create_spatial_temporal_draft(
                self,
                location: str = None,
                extent_name: str = None,
                reference_date: str = None
        ) -> Path:
            """Create draft for spatial and temporal metadata."""
            import yaml
            from datetime import datetime

            draft = {
                'spatial': {
                    'location': location,
                    'extent': extent_name,
                    'resolution': None
                },
                'temporal': {
                    'referenceDate': reference_date or datetime.now().strftime(
                        "%Y-%m-%d"),
                    'timeseries': []
                }
            }

            output_path = self.paths.get_metadata_draft_path('spatial_temporal')
            with open(output_path, 'w', encoding = 'utf-8') as f:
                yaml.dump(draft, f, default_flow_style = False, allow_unicode = True,
                          sort_keys = False)

            print(f"✅ Spatial/Temporal draft: {output_path}")
            return output_path

        def create_contributors_draft(
                self,
                default_contributor: Dict[str, str] = None
        ) -> Path:
            """Create draft for contributors section."""
            import yaml
            from datetime import datetime

            # Default contributor template
            contributor_template = {
                'title': default_contributor.get(
                    'name') if default_contributor else 'Your Name',
                'email': default_contributor.get(
                    'email') if default_contributor else 'email@example.com',
                'date': datetime.now().strftime("%Y-%m-%d"),
                'object': 'data',
                'comment': 'Data collection and preparation'
            }

            draft = {
                'contributors': [contributor_template]
            }

            output_path = self.paths.get_metadata_draft_path('contributors')
            with open(output_path, 'w', encoding = 'utf-8') as f:
                yaml.dump(draft, f, default_flow_style = False, allow_unicode = True,
                          sort_keys = False)

            print(f"✅ Contributors draft: {output_path}")
            return output_path

        def create_sources_draft(
                self,
                primary_source: Dict[str, str] = None
        ) -> Path:
            """Create draft for sources section."""
            import yaml

            source_template = {
                'title': primary_source.get(
                    'title') if primary_source else 'Source Title',
                'description': primary_source.get(
                    'description') if primary_source else 'Source description',
                'path': primary_source.get(
                    'url') if primary_source else 'https://example.com',
                'licenses': []
            }

            draft = {
                'sources': [source_template]
            }

            output_path = self.paths.get_metadata_draft_path('sources')
            with open(output_path, 'w', encoding = 'utf-8') as f:
                yaml.dump(draft, f, default_flow_style = False, allow_unicode = True,
                          sort_keys = False)

            print(f"✅ Sources draft: {output_path}")
            return output_path

        def create_licenses_draft(
                self,
                default_license: str = 'CC-BY-4.0'
        ) -> Path:
            """Create draft for licenses section."""
            import yaml

            license_templates = {
                'CC-BY-4.0': {
                    'name': 'CC-BY-4.0',
                    'title': 'Creative Commons Attribution 4.0 International',
                    'path': 'https://creativecommons.org/licenses/by/4.0/legalcode',
                    'instruction': 'You are free to share and adapt, but you must give appropriate credit.',
                    'attribution': '© Copyright Owner'
                },
                'ODbL-1.0': {
                    'name': 'ODbL-1.0',
                    'title': 'Open Data Commons Open Database License 1.0',
                    'path': 'https://opendatacommons.org/licenses/odbl/1.0/',
                    'instruction': 'You are free to share and adapt, but you must attribute and share-alike.',
                    'attribution': '© Copyright Owner'
                }
            }

            draft = {
                'licenses': [license_templates.get(default_license,
                                                   license_templates['CC-BY-4.0'])]
            }

            output_path = self.paths.get_metadata_draft_path('licenses')
            with open(output_path, 'w', encoding = 'utf-8') as f:
                yaml.dump(draft, f, default_flow_style = False, allow_unicode = True,
                          sort_keys = False)

            print(f"✅ Licenses draft: {output_path}")
            return output_path

        def create_all_drafts(
                self,
                title: str = None,
                description: str = None,
                contributor_name: str = None,
                contributor_email: str = None
        ) -> Dict[str, Path]:
            """
            Create all OEMetadata section drafts at once.

            Args:
                title: Dataset title
                description: Dataset description
                contributor_name: Default contributor name
                contributor_email: Default contributor email

            Returns:
                Dict mapping section name to draft file path
            """
            print("\n" + "=" * 70)
            print("CREATING OEMETADATA DRAFTS")
            print("=" * 70 + "\n")

            drafts = {}

            drafts['general_keys'] = self.create_general_keys_draft(
                title = title,
                description = description
            )

            drafts['context'] = self.create_context_draft()

            drafts['spatial_temporal'] = self.create_spatial_temporal_draft()

            contributor_info = {}
            if contributor_name:
                contributor_info['name'] = contributor_name
            if contributor_email:
                contributor_info['email'] = contributor_email

            drafts['contributors'] = self.create_contributors_draft(
                default_contributor = contributor_info if contributor_info else None
            )

            drafts['sources'] = self.create_sources_draft()

            drafts['licenses'] = self.create_licenses_draft()

            print("\n" + "=" * 70)
            print("DRAFTS CREATED - Please review and edit:")
            print("=" * 70)
            for section, path in drafts.items():
                print(f"  {section:<20} {path}")
            print("\nAfter editing, save with same name without '_draft' suffix")
            print("=" * 70 + "\n")

            return drafts

        def load_metadata_section(self, section: str) -> Dict[str, Any]:
            """
            Load finalized metadata section.

            Args:
                section: Section name (general_keys, context, etc.)

            Returns:
                Loaded metadata dict
            """
            import yaml

            # Try finalized version first
            path = self.paths.get_metadata_path(section)
            if not path.exists():
                # Fall back to draft
                path = self.paths.get_metadata_draft_path(section)
                if not path.exists():
                    print(f"⚠️  No metadata found for section '{section}'")
                    return {}

            with open(path, 'r', encoding = 'utf-8') as f:
                return yaml.safe_load(f) or {}

        def compile_complete_metadata(self) -> Dict[str, Any]:
            """
            Compile complete OEMetadata from all sections.

            Returns:
                Complete OEMetadata dict
            """
            metadata = {}

            # Load all sections
            sections = [
                'general_keys',
                'context',
                'spatial_temporal',
                'contributors',
                'sources',
                'licenses'
            ]

            for section in sections:
                section_data = self.load_metadata_section(section)
                metadata.update(section_data)

            return metadata

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

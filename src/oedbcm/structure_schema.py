"""Open Energy Database Compliance Manager

Schema definitions for structure planning and YAML export.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import yaml
import json


class StructurePlan:
    """
    Container for a versioned structure plan.

    Manages both current (as-is) and planned (to-be) data structures
    with SemVer versioning.
    """

    def __init__(
            self,
            dataset_name: str,
            version: str = "0.1.0",
            description: str = ""
    ):
        """
        Initialize a structure plan.

        Args:
            dataset_name: Name of the dataset
            version: Semantic version string (e.g., "0.1.0")
            description: Description of this plan version
        """
        self.dataset_name = dataset_name
        self.version = version
        self.description = description
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

        # Structures
        self.current_structure: Dict[str, Any] = {}
        self.planned_structure: Dict[str, Any] = {}

        # Mapping between current and planned resources
        self.resource_mapping: List[Dict[str, Any]] = []

    def set_current_structure(
            self,
            package_name: str,
            resources: List[Dict[str, Any]]
    ):
        """
        Set the current (as-is) structure.

        Args:
            package_name: Name of the data package
            resources: List of resource definitions
        """
        self.current_structure = {
            'name': package_name,
            'resources': resources
        }
        self.updated_at = datetime.now().isoformat()

    def set_planned_structure(
            self,
            package_name: str,
            resources: List[Dict[str, Any]]
    ):
        """
        Set the planned (to-be) structure.

        Args:
            package_name: Name of the data package
            resources: List of planned resource definitions
        """
        self.planned_structure = {
            'name': package_name,
            'resources': resources
        }
        self.updated_at = datetime.now().isoformat()

    def add_resource_mapping(
            self,
            current_resource_name: str,
            planned_resource_name: str,
            group_number: int,
            transformation_notes: str = ""
    ):
        """
        Add mapping between current and planned resource.

        Args:
            current_resource_name: Name of current resource
            planned_resource_name: Name of planned resource
            group_number: Group ID for this mapping
            transformation_notes: Notes about the transformation
        """
        self.resource_mapping.append({
            'current_resource': current_resource_name,
            'planned_resource': planned_resource_name,
            'group_number': group_number,
            'transformation_notes': transformation_notes
        })
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary for YAML export."""
        return {
            'metadata': {
                'dataset_name': self.dataset_name,
                'version': self.version,
                'description': self.description,
                'created_at': self.created_at,
                'updated_at': self.updated_at
            },
            'current_structure': self.current_structure,
            'planned_structure': self.planned_structure,
            'resource_mapping': self.resource_mapping
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructurePlan':
        """Load plan from dictionary."""
        metadata = data.get('metadata', {})
        plan = cls(
            dataset_name = metadata.get('dataset_name', 'unknown'),
            version = metadata.get('version', '0.1.0'),
            description = metadata.get('description', '')
        )
        plan.created_at = metadata.get('created_at', plan.created_at)
        plan.updated_at = metadata.get('updated_at', plan.updated_at)
        plan.current_structure = data.get('current_structure', {})
        plan.planned_structure = data.get('planned_structure', {})
        plan.resource_mapping = data.get('resource_mapping', [])
        return plan

    def save_yaml(self, output_dir: Path = None) -> Dict[str, Path]:
        """
        Save current and planned structures to YAML.

        Args:
            output_dir: Directory for YAML files (default: data/plans/)

        Returns:
            Dict with paths to saved files
        """
        from .paths import get_project_paths

        if output_dir is None:
            paths = get_project_paths(self.dataset_name)
            current_path = paths.get_structure_current_path(self.version)
            planned_path = paths.get_structure_plan_path(self.version)
        else:
            base_dir = Path(output_dir)
            target_dir = base_dir / self.dataset_name
            target_dir.mkdir(parents = True, exist_ok = True)
            current_path = target_dir / f"{self.dataset_name}_v{self.version}_structure_current.yaml"
            planned_path = target_dir / f"{self.dataset_name}_v{self.version}_structure_plan.yaml"

        # Speichern unter Verwendung der vorhandenen Datenstruktur
        # (Da _prepare_for_export fehlt, nutzen wir direkt die dicts)
        with open(current_path, 'w', encoding = 'utf-8') as f:
            yaml.dump(
                self.current_structure,
                f,
                default_flow_style = False,
                allow_unicode = True,
                sort_keys = False
            )

        with open(planned_path, 'w', encoding = 'utf-8') as f:
            yaml.dump(
                self.planned_structure,
                f,
                default_flow_style = False,
                allow_unicode = True,
                sort_keys = False
            )

        print(f"✅ Current structure saved: {current_path}")
        print(f"✅ Planned structure saved: {planned_path}")

        return {
            'current': current_path,
            'planned': planned_path
        }

    def save_split_yaml(self, output_dir: Path = None) -> Dict[str, Path]:
        """
        Save current and planned structures to separate YAML files.

        This allows opening both files side-by-side for comparison.

        Args:
            output_dir: Directory for output files. If None, uses data/plans/

        Returns:
            Dict with paths to 'current' and 'planned' YAML files
        """
        if output_dir is None:
            output_dir = Path("data/plans")
        output_dir.mkdir(parents = True, exist_ok = True)

        base_name = f"{self.dataset_name}_v{self.version}"

        # Save current structure
        current_path = output_dir / f"current_{base_name}.yaml"
        current_data = {
            'metadata': self.to_dict()['metadata'],
            'structure': self.current_structure
        }

        # Clean data to avoid YAML anchors
        current_clean = json.loads(json.dumps(current_data))

        with open(current_path, 'w', encoding = 'utf-8') as f:
            yaml.dump(
                current_clean,
                f,
                default_flow_style = False,
                allow_unicode = True,
                sort_keys = False
            )

        # Save planned structure
        planned_path = output_dir / f"planned_{base_name}.yaml"
        planned_data = {
            'metadata': self.to_dict()['metadata'],
            'structure': self.planned_structure,
            'resource_mapping': self.resource_mapping
        }

        # Clean data to avoid YAML anchors
        planned_clean = json.loads(json.dumps(planned_data))

        with open(planned_path, 'w', encoding = 'utf-8') as f:
            yaml.dump(
                planned_clean,
                f,
                default_flow_style = False,
                allow_unicode = True,
                sort_keys = False
            )

        print(f"✅ Current structure saved: {current_path}")
        print(f"✅ Planned structure saved: {planned_path}")

        return {
            'current': current_path,
            'planned': planned_path
        }

    @classmethod
    def load_yaml(cls, yaml_path: Path) -> 'StructurePlan':
        """
        Load plan from YAML file.

        Args:
            yaml_path: Path to YAML file

        Returns:
            StructurePlan instance
        """
        with open(yaml_path, 'r', encoding = 'utf-8') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    def increment_version(self, part: str = 'patch'):
        """
        Increment version number.

        Args:
            part: Which part to increment ('major', 'minor', 'patch')
        """
        parts = self.version.split('.')
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if part == 'major':
            major += 1
            minor = 0
            patch = 0
        elif part == 'minor':
            minor += 1
            patch = 0
        else:  # patch
            patch += 1

        self.version = f"{major}.{minor}.{patch}"
        self.updated_at = datetime.now().isoformat()

"""Open Energy Database Compliance Manager

Tests for structure planning functionality.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from oedbcm.structure_schema import StructurePlan
from oedbcm.visualizer import StructureVisualizer


class TestStructurePlan:
    """Test StructurePlan class."""

    def test_create_plan(self):
        """Test creating a new structure plan."""
        plan = StructurePlan(
            dataset_name = "test_dataset",
            version = "0.1.0",
            description = "Test plan"
        )

        assert plan.dataset_name == "test_dataset"
        assert plan.version == "0.1.0"
        assert plan.description == "Test plan"
        assert plan.created_at is not None

    def test_set_structures(self):
        """Test setting current and planned structures."""
        plan = StructurePlan("test_dataset")

        current = {
            'name': 'TestPackage',
            'resources': [
                {'name': 'file1.csv', 'fields': [{'name': 'col1'}]}
            ]
        }

        planned = {
            'name': 'TestPackage',
            'resources': [
                {'name': 'optimized_file.csv', 'fields': [{'name': 'column1'}]}
            ]
        }

        plan.set_current_structure('TestPackage', current['resources'])
        plan.set_planned_structure('TestPackage', planned['resources'])

        assert plan.current_structure['name'] == 'TestPackage'
        assert len(plan.current_structure['resources']) == 1
        assert plan.planned_structure['name'] == 'TestPackage'

    def test_version_increment(self):
        """Test version incrementing."""
        plan = StructurePlan("test", version = "0.1.5")

        # Patch increment
        plan.increment_version('patch')
        assert plan.version == "0.1.6"

        # Minor increment
        plan.increment_version('minor')
        assert plan.version == "0.2.0"

        # Major increment
        plan.increment_version('major')
        assert plan.version == "1.0.0"

    def test_resource_mapping(self):
        """Test adding resource mappings."""
        plan = StructurePlan("test")

        plan.add_resource_mapping(
            current_resource_name = "old_file.csv",
            planned_resource_name = "new_file.csv",
            group_number = 1,
            transformation_notes = "Renamed and restructured"
        )

        assert len(plan.resource_mapping) == 1
        assert plan.resource_mapping[0]['group_number'] == 1
        assert plan.resource_mapping[0]['current_resource'] == "old_file.csv"

    def test_yaml_save_load(self):
        """Test saving and loading YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = StructurePlan("test_dataset", version = "0.2.0")
            plan.set_current_structure('Test', [{'name': 'file.csv', 'fields': []}])
            print(plan.to_dict())
            # Save
            yaml_path = Path(tmpdir) / "test_plan.yaml"
            # Fehler: Es wird kein kein einzelnen path-Objekt, sondern ein Dictionary zurückgegeben: 
            saved_path = plan.save_yaml(yaml_path)
            assert saved_path["current"].exists()
            assert saved_path["planned"].exists()

            # Load
            loaded_plan = StructurePlan.load_yaml(saved_path["current"])
            print(loaded_plan.to_dict())
            print(saved_path["current"].read_text())
            assert loaded_plan.dataset_name == "test_dataset"
            assert loaded_plan.version == "0.2.0"
            assert loaded_plan.current_structure['name'] == 'Test'

    def test_to_dict_from_dict(self):
        """Test dictionary conversion."""
        plan = StructurePlan("test", version = "1.0.0", description = "Test")
        plan.set_current_structure('Pkg', [])

        # Convert to dict
        data = plan.to_dict()

        assert data['metadata']['dataset_name'] == "test"
        assert data['metadata']['version'] == "1.0.0"
        assert 'current_structure' in data

        # Convert back
        new_plan = StructurePlan.from_dict(data)

        assert new_plan.dataset_name == "test"
        assert new_plan.version == "1.0.0"


class TestStructureVisualizer:
    """Test StructureVisualizer class."""

    def test_visualizer_init(self):
        """Test visualizer initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = StructureVisualizer(output_dir = Path(tmpdir), 
            dataset_name="test_dataset")
            assert viz.output_dir.exists()

    def test_create_visualization(self):
        """Test creating a visualization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = StructureVisualizer(output_dir = Path(tmpdir), dataset_name="test_dataset")

            current = {
                'name': 'Dataset',
                'resources': [
                    {
                        'name': 'file1.csv',
                        'fields': [
                            {'name': 'col1'},
                            {'name': 'col2'}
                        ]
                    }
                ]
            }

            planned = {
                'name': 'Dataset',
                'resources': [
                    {
                        'name': 'optimized.csv',
                        'fields': [
                            {'name': 'column_1'},
                            {'name': 'column_2'},
                            {'name': 'metadata'}
                        ]
                    }
                ]
            }

            output_path = viz.visualize_comparison(
                current_structure = current,
                planned_structure = planned,
                title = "Test Comparison",
                version = "0.1.0"
            )

            assert output_path.exists()
            assert output_path.suffix == '.png'
            assert 'v0.1.0' in output_path.name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

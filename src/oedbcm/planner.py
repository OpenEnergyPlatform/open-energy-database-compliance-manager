"""Open Energy Database Compliance Manager

Transformation planning and recommendation engine.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""


from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from .paths import get_project_paths
from .package import DataPackage
from .analyzer import ColumnAnalyzer, FileNameAnalyzer
from .visualizer import StructureVisualizer
from .structure_schema import StructurePlan
from .file_classifier import ResourceClassifier, ResourceType
from .digester import MetadataDigester, DigestConfig
from .logger import ValidationLogger
import json


class TransformationPlanner:
    """Plan and suggest transformations for datasets."""

    def __init__(self, package: DataPackage):
        self.package = package
        self.paths = get_project_paths(package.dataset_name)
        self.col_analyzer = ColumnAnalyzer(package)
        self.file_analyzer = FileNameAnalyzer(package)
        self.visualizer = StructureVisualizer(dataset_name=package.dataset_name)
        self.logger = ValidationLogger(dataset_name = package.dataset_name)
        self.current_plan: StructurePlan = None
        self.classifier = ResourceClassifier()
        self.catalog = None
        self.digester = MetadataDigester()


    def analyze_and_plan(self) -> Dict[str, Any]:
        """
        Perform full analysis and generate transformation plan.

        Returns dict with:
        - analysis: Current state analysis
        - options: List of transformation options
        - recommendations: Prioritized recommendations
        """
        structure_groups = self.col_analyzer.get_column_structure_groups()
        filename_metadata = self.file_analyzer.extract_metadata_patterns()
        resource_stats = self.col_analyzer.get_resource_statistics()

        options = []

        # Option 1: Standardize column names
        invalid_cols = set()
        for resource in self.package.resources:
            invalid_cols.update(resource.invalid_column_names())

        if invalid_cols:
            options.append({
                'id': 'standardize_columns',
                'title': 'Standardize Column Names',
                'description': 'Convert all column names to DB-compliant format',
                'impact': f'{len(invalid_cols)} columns affected',
                'details': {
                    'invalid_columns': list(invalid_cols)[:10],
                    'example_mappings': self._suggest_column_renames(
                        list(invalid_cols)[:5])
                }
            })

        # Option 2: Extract metadata from filenames
        files_with_extractable_metadata = sum(
            1 for m in filename_metadata.values()
            if m['years'] or m['dates'] or len(m['parts']) > 1
        )

        if files_with_extractable_metadata > 0:
            options.append({
                'id': 'extract_filename_metadata',
                'title': 'Extract Metadata from Filenames',
                'description': 'Add columns based on information in filenames',
                'impact': f'{files_with_extractable_metadata} files can be enhanced',
                'details': {
                    'example_extractions': self._example_metadata_extractions(
                        filename_metadata)
                }
            })

        # Option 3: Harmonize structure groups
        multi_file_groups = {
            k: v for k, v in structure_groups.items()
            if v['count'] > 1
        }

        if multi_file_groups:
            options.append({
                'id': 'harmonize_groups',
                'title': 'Harmonize File Groups',
                'description': 'Process groups of files with identical structure together',
                'impact': f'{len(multi_file_groups)} groups identified',
                'details': {
                    'groups': {k: v['count'] for k, v in multi_file_groups.items()}
                }
            })

        # Option 4: Split by structure
        if len(structure_groups) > 1:
            options.append({
                'id': 'split_by_structure',
                'title': 'Split Dataset by Structure',
                'description': 'Create sub-packages for each unique file structure',
                'impact': f'{len(structure_groups)} distinct structures found',
                'details': {
                    'structures': [
                        {
                            'columns': v['columns'][:5],
                            'file_count': v['count']
                        }
                        for v in structure_groups.values()
                    ]
                }
            })

        return {
            'dataset': self.package.dataset_name,
            'current_state': {
                'total_files': len(self.package.resources),
                'unique_structures': len(structure_groups),
                'invalid_columns': len(invalid_cols),
                'total_size_mb': resource_stats['total_size_mb'],
                'total_rows': resource_stats['total_rows'],
                'avg_rows_per_file': resource_stats['avg_rows_per_file'],
            },
            'options': options,
            'recommendations': self._prioritize_options(options),
            'resource_details': resource_stats
        }

    def _suggest_column_renames(self, columns: List[str]) -> Dict[str, str]:
        """Suggest DB-compliant renames for columns."""
        import re
        mappings = {}
        for col in columns:
            # Simple conversion: lowercase, replace spaces/special chars with underscore
            suggested = re.sub(r'[^a-z0-9_]', '_', col.lower())
            suggested = re.sub(r'_+', '_', suggested).strip('_')
            # Ensure starts with letter
            if suggested and suggested[0].isdigit():
                suggested = 'col_' + suggested
            mappings[col] = suggested
        return mappings

    def _example_metadata_extractions(self, metadata: Dict) -> List[Dict]:
        """Show example metadata extractions."""
        examples = []
        for filename, info in list(metadata.items())[:3]:
            if info['suggested_columns']:
                examples.append({
                    'file': filename,
                    'extractable': info['suggested_columns'],
                    'values': {
                        'years': info['years'],
                        'dates': info['dates']
                    }
                })
        return examples

    def _prioritize_options(self, options: List[Dict]) -> List[str]:
        """Prioritize transformation options."""
        # Simple priority: standardize → extract → harmonize → split
        priority_order = [
            'standardize_columns',
            'extract_filename_metadata',
            'harmonize_groups',
            'split_by_structure'
        ]

        recommendations = []
        for opt_id in priority_order:
            if any(o['id'] == opt_id for o in options):
                recommendations.append(opt_id)

        return recommendations

    def extract_current_structure(
            self,
            include_metadata: bool = False
    ) -> Dict[str, Any]:
        """
        Extract current structure from analyzed package.

        Only includes DATA and ADDITIONAL_DATA resources by default.
        Uses MetadataDigester to extract OEMetadata fields.

        Args:
            include_metadata: If True, also include METADATA resources

        Returns:
            Dictionary representing current data structure
        """
        resources = []

        for idx, resource in enumerate(self.package.resources):
            # Filter by classification
            if resource.classification:
                from .file_classifier import ResourceType
                # Skip ignored types
                if resource.classification in [
                    ResourceType.NOT_SUPPORTED,
                    ResourceType.IGNORE
                ]:
                    continue

                # Skip metadata unless requested
                if not include_metadata and resource.classification == ResourceType.METADATA:
                    continue

            # Extract OEMetadata fields using digester
            fields = []
            if resource.column_names:
                for col_name in resource.column_names:
                    # ✅ Use digester.digest_field() for complete OEMetadata
                    if hasattr(self, 'digester') and self.digester:
                        field = self.digester.digest_field(col_name)
                    else:
                        # Fallback if digester not available
                        field = {
                            'name': col_name,
                            'type': 'string',
                            'description': col_name,
                            'nullable': True,
                            'unit': None,
                            'isAbout': [],
                            'valueReference': []
                        }
                    fields.append(field)

            resource_dict = {
                'name': resource.path.name,
                'path': str(resource.path),
                'format': resource.file_type.upper(),
                'encoding': getattr(resource, 'detected_encoding',
                                    resource.encoding) if hasattr(resource,
                                                                  'encoding') else 'utf-8',
                'rows': resource.n_rows or 0,
                'columns': resource.n_columns or 0,
                'schema': {
                    'fields': fields,
                    'primaryKey': [],
                    'foreignKeys': []
                },
                'group_number': resource.group_number,
                'classification': resource.classification.value if resource.classification else None
            }
            resources.append(resource_dict)

        return {
            'name': self.package.dataset_name,
            'resources': resources
        }

    def create_structure_plan(
            self,
            version: str = "0.1.0",
            description: str = "Initial structure planning"
    ) -> StructurePlan:
        """
        Create a new structure plan with current state.

        Args:
            version: Semantic version for this plan
            description: Description of the planning iteration

        Returns:
            StructurePlan instance
        """
        plan = StructurePlan(
            dataset_name = self.package.dataset_name,
            version = version,
            description = description
        )

        # Extract and set current structure
        current_struct = self.extract_current_structure()
        plan.set_current_structure(
            package_name = self.package.dataset_name,
            resources = current_struct['resources']
        )

        # Initialize planned structure as copy of current
        # User will modify this manually in YAML
        plan.set_planned_structure(
            package_name = self.package.dataset_name,
            resources = current_struct['resources'].copy()
        )

        self.current_plan = plan
        return plan

    def visualize_plan(
            self,
            plan: StructurePlan = None,
            output_path: Path = None
    ) -> Path:
        """
        Create visualization for a structure plan.

        Args:
            plan: StructurePlan to visualize (uses self.current_plan if None)
            output_path: Custom output path for PNG

        Returns:
            Path to generated visualization
        """
        if plan is None:
            if self.current_plan is None:
                raise ValueError(
                    "No plan available. Call create_structure_plan() first.")
            plan = self.current_plan

        return self.visualizer.visualize_comparison(
            current_structure = plan.current_structure,
            planned_structure = plan.planned_structure,
            title = f"{plan.dataset_name} - Structure Planning",
            version = plan.version
        )

    def save_complete_plan(
            self,
            plan: StructurePlan = None,
            yaml_path: Path = None,
            create_visualization: bool = True
    ) -> Dict[str, Path]:
        """
        Save complete planning package (YAML + visualization).

        Args:
            plan: StructurePlan to save (uses self.current_plan if None)
            yaml_path: Custom path for YAML file
            create_visualization: Whether to create PNG visualization

        Returns:
            Dict with paths to created files
        """
        if plan is None:
            if self.current_plan is None:
                raise ValueError(
                    "No plan available. Call create_structure_plan() first.")
            plan = self.current_plan

        output_files = {}

        # Save YAML
        yaml_file = plan.save_yaml(yaml_path)
        output_files['yaml'] = yaml_file

        # Create visualization
        if create_visualization:
            viz_file = self.visualize_plan(plan)
            output_files['visualization'] = viz_file

        return output_files

    def create_merged_structure_plan(
            self,
            version: str = "0.1.0",
            target_table_name: str = None,
            description: str = "Merged structure for planning"
    ) -> StructurePlan:
        """
        Create merged structure plan containing only DATA resources.

        Combines all DATA tables into single target structure.

        Args:
            version: Version for merged plan
            target_table_name: Name for final merged table
            description: Description of merged structure

        Returns:
            StructurePlan with merged DATA resources
        """
        from .file_classifier import ResourceType

        # Filter DATA resources only
        data_resources = []
        for resource in self.package.resources:
            if resource.classification == ResourceType.DATA:
                data_resources.append(resource)

        if not data_resources:
            print("⚠️  No DATA resources found in catalog")
            return None

        print(f"📊 Merging {len(data_resources)} DATA resources into single structure")

        # Collect all unique fields from DATA resources
        all_fields_dict = {}  # name -> field_def

        for resource in data_resources:
            if hasattr(self, 'digester') and self.digester and resource.column_names:
                for col_name in resource.column_names:
                    field = self.digester.digest_field(col_name)
                    field_name = field['name']

                    # Keep first occurrence or merge if needed
                    if field_name not in all_fields_dict:
                        all_fields_dict[field_name] = field

        # Create merged resource definition
        merged_fields = list(all_fields_dict.values())

        target_name = target_table_name or f"{self.package.dataset_name}_merged"

        merged_resource = {
            'name': f"{target_name}.csv",
            'path': f"data/3_results/{self.package.dataset_name}/{target_name}.csv",
            'type': 'table',
            'format': 'CSV',
            'encoding': 'utf-8',
            'rows': sum(r.n_rows or 0 for r in data_resources),
            'columns': len(merged_fields),
            'schema': {
                'fields': merged_fields,
                'primaryKey': [],
                'foreignKeys': []
            },
            'classification': 'Data',
            'source_files': [r.path.name for r in data_resources],
            'source_count': len(data_resources)
        }

        # Create plan
        plan = StructurePlan(
            dataset_name = self.package.dataset_name,
            version = version,
            description = description
        )

        plan.set_current_structure(
            package_name = self.package.dataset_name,
            resources = [merged_resource]
        )

        # Planned is same as current for merged structure
        import json
        plan.set_planned_structure(
            package_name = self.package.dataset_name,
            resources = json.loads(json.dumps([merged_resource]))
        )

        # Save merged structure
        merged_path = self.paths.structure / f"structure_merged_{self.package.dataset_name}_v{version}.yaml"

        import yaml
        with open(merged_path, 'w', encoding = 'utf-8') as f:
            yaml.dump(
                {
                    'metadata': plan.to_dict()['metadata'],
                    'merged_structure': plan.current_structure
                },
                f,
                default_flow_style = False,
                allow_unicode = True,
                sort_keys = False
            )

        print(f"✅ Merged structure saved: {merged_path}")
        print(f"   Target table: {target_name}.csv")
        print(f"   Total fields: {len(merged_fields)}")
        print(f"   Source files: {len(data_resources)}")

        return plan

    def save_grouped_structures(
            self,
            version: str = "0.1.0",
            description: str = "Grouped structure plans"
    ) -> Dict[int, Dict[str, Path]]:
        """
        Save each structure group as separate YAML files.

        Creates draft and target files for each group.

        Args:
            version: Version string
            description: Description for the plans

        Returns:
            Dict mapping group_number to dict of file paths
        """
        from .file_classifier import ResourceType
        import yaml
        import json

        # Get structure groups
        structure_groups = self.col_analyzer.get_column_structure_groups()

        # Filter only DATA and ADDITIONAL_DATA resources
        filtered_groups = {}

        for group_name, group_info in structure_groups.items():
            # Check if any file in this group is DATA or ADDITIONAL_DATA
            group_resources = []
            for filename in group_info['files']:
                for resource in self.package.resources:
                    if resource.path.name == filename:
                        if resource.classification in [ResourceType.DATA,
                                                       ResourceType.ADDITIONAL_DATA]:
                            group_resources.append(resource)
                        break

            if group_resources:
                filtered_groups[group_name] = {
                    'info': group_info,
                    'resources': group_resources
                }

        if not filtered_groups:
            print("⚠️  No DATA/ADDITIONAL_DATA groups found")
            return {}

        print(f"\n📊 Saving {len(filtered_groups)} structure groups...")

        output_files = {}

        for group_idx, (group_name, group_data) in enumerate(filtered_groups.items(),
                                                             1):
            group_info = group_data['info']
            resources_list = group_data['resources']

            # Extract structure for this group
            group_structure = {
                'group_number': group_idx,
                'group_name': group_name,
                'file_count': len(group_info['files']),
                'columns': group_info['columns'],
                'resources': []
            }

            # Add resources with OEMetadata fields
            for resource in resources_list:
                fields = []
                if resource.column_names:
                    for col_name in resource.column_names:
                        if self.digester:
                            field = self.digester.digest_field(col_name)
                        else:
                            field = {
                                'name': col_name,
                                'type': 'string',
                                'description': col_name
                            }
                        fields.append(field)

                resource_dict = {
                    'name': resource.path.name,
                    'path': str(resource.path),
                    'format': resource.file_type.upper(),
                    'encoding': getattr(resource, 'detected_encoding', 'utf-8'),
                    'rows': resource.n_rows or 0,
                    'columns': resource.n_columns or 0,
                    'schema': {
                        'fields': fields,
                        'primaryKey': [],
                        'foreignKeys': []
                    },
                    'classification': resource.classification.value if resource.classification else None,
                    'target_table': getattr(resource, 'target_table', '')
                }
                group_structure['resources'].append(resource_dict)

            # Metadata for this group
            metadata = {
                'dataset_name': self.package.dataset_name,
                'version': version,
                'description': f"{description} - Group {group_idx}",
                'created_at': datetime.now().isoformat(),
                'group_number': group_idx
            }

            # Create draft data
            draft_data = {
                'metadata': metadata,
                'structure': group_structure
            }

            # Clean data (avoid YAML anchors)
            draft_clean = json.loads(json.dumps(draft_data))

            # Save draft file
            draft_path = self.paths.structure / f"{self.package.dataset_name}_v{version}_structure_group{group_idx}_draft.yaml"
            with open(draft_path, 'w', encoding = 'utf-8') as f:
                yaml.dump(draft_clean, f, default_flow_style = False,
                          allow_unicode = True, sort_keys = False)

            # Save target file (only if doesn't exist)
            target_path = self.paths.structure / f"{self.package.dataset_name}_v{version}_structure_group{group_idx}_target.yaml"

            if not target_path.exists():
                with open(target_path, 'w', encoding = 'utf-8') as f:
                    yaml.dump(draft_clean, f, default_flow_style = False,
                              allow_unicode = True, sort_keys = False)
                status = "(created)"
            else:
                status = "(exists, not overwritten)"

            print(
                f"  Group {group_idx}: {len(group_info['files'])} files, {len(group_info['columns'])} columns")
            print(f"    - Draft:  {draft_path}")
            print(f"    - Target: {target_path} {status}")

            output_files[group_idx] = {
                'draft': draft_path,
                'target': target_path,
                'file_count': len(group_info['files']),
                'column_count': len(group_info['columns'])
            }

        print(f"\n✅ Saved {len(output_files)} grouped structures")
        return output_files

    def create_table_overview(
            self,
            version: str = "0.1.0",
            include_all: bool = False
    ) -> Path:
        """
        Create CSV overview of all tables and their standardized column names.

        Args:
            version: Version string
            include_all: If True, include all resources. If False, only DATA/ADDITIONAL_DATA

        Returns:
            Path to created CSV file
        """
        import csv
        from .file_classifier import ResourceType

        # Filter resources
        resources_to_process = []
        for resource in self.package.resources:
            if include_all:
                resources_to_process.append(resource)
            else:
                if resource.classification in [ResourceType.DATA,
                                               ResourceType.ADDITIONAL_DATA]:
                    resources_to_process.append(resource)

        if not resources_to_process:
            print("⚠️  No resources to process")
            return None

        # Collect all unique standardized column names
        all_columns = set()
        table_columns = {}

        for resource in resources_to_process:
            if not resource.column_names:
                continue

            standardized_cols = []
            for col_name in resource.column_names:
                if self.digester:
                    std_name = self.digester.standardize_column_name(col_name)
                else:
                    std_name = col_name.lower().replace(' ', '_')
                standardized_cols.append(std_name)
                all_columns.add(std_name)

            table_columns[resource.path.name] = {
                'columns': standardized_cols,
                'rows': resource.n_rows or 0,
                'classification': resource.classification.value if resource.classification else 'Unknown',
                'target_table': getattr(resource, 'target_table', ''),
                'group_number': resource.group_number
            }

        # Sort columns alphabetically
        sorted_columns = sorted(all_columns)

        # Create CSV with matrix: rows=tables, cols=column names
        output_path = self.paths.catalogs / f"{self.package.dataset_name}_v{version}_detail_table.csv"

        with open(output_path, 'w', newline = '', encoding = 'utf-8') as f:
            writer = csv.writer(f)

            # Header row
            header = ['Table', 'Rows', 'Classification', 'Target_Table', 'Group',
                      'Column_Count'] + sorted_columns
            writer.writerow(header)

            # Data rows
            for table_name in sorted(table_columns.keys()):
                info = table_columns[table_name]
                row = [
                    table_name,
                    info['rows'],
                    info['classification'],
                    info['target_table'] or '',
                    info['group_number'] or '',
                    len(info['columns'])
                ]

                # Mark columns that exist in this table
                for col in sorted_columns:
                    if col in info['columns']:
                        row.append('X')
                    else:
                        row.append('')

                writer.writerow(row)

        print(f"✅ Table overview: {output_path}")
        print(f"   Tables: {len(table_columns)}")
        print(f"   Unique columns: {len(all_columns)}")

        return output_path

    def create_group_overview(
            self,
            version: str = "0.1.0"
    ) -> Path:
        """
        Create CSV overview of structure groups and their columns.

        Shows which columns appear in each group.

        Args:
            version: Version string

        Returns:
            Path to created CSV file
        """
        import csv
        from .file_classifier import ResourceType

        # Get structure groups
        structure_groups = self.col_analyzer.get_column_structure_groups()

        # Filter only DATA and ADDITIONAL_DATA resources
        filtered_groups = {}

        for group_name, group_info in structure_groups.items():
            # Check if any file in this group is DATA or ADDITIONAL_DATA
            group_resources = []
            for filename in group_info['files']:
                for resource in self.package.resources:
                    if resource.path.name == filename:
                        if resource.classification in [ResourceType.DATA,
                                                       ResourceType.ADDITIONAL_DATA]:
                            group_resources.append(resource)
                        break

            if group_resources:
                filtered_groups[group_name] = {
                    'info': group_info,
                    'resources': group_resources
                }

        if not filtered_groups:
            print("⚠️  No DATA/ADDITIONAL_DATA groups found")
            return None

        # Collect all unique columns across all groups
        all_columns = set()
        group_columns = {}

        for group_idx, (group_name, group_data) in enumerate(filtered_groups.items(),
                                                             1):
            group_info = group_data['info']
            resources_list = group_data['resources']

            # Standardize column names for this group
            standardized_cols = []
            for col_name in group_info['columns']:
                if self.digester:
                    std_name = self.digester.standardize_column_name(col_name)
                else:
                    std_name = col_name.lower().replace(' ', '_')
                standardized_cols.append(std_name)
                all_columns.add(std_name)

            # Get target tables from resources
            target_tables = set()
            for res in resources_list:
                if hasattr(res, 'target_table') and res.target_table:
                    target_tables.add(res.target_table)

            group_columns[group_idx] = {
                'group_name': group_name,
                'columns': standardized_cols,
                'file_count': len(group_info['files']),
                'files': group_info['files'],
                'target_tables': ', '.join(
                    sorted(target_tables)) if target_tables else ''
            }

        # Sort columns alphabetically
        sorted_columns = sorted(all_columns)

        # Create CSV with matrix: rows=groups, cols=column names
        output_path = self.paths.catalogs / f"{self.package.dataset_name}_v{version}_detail_group.csv"

        with open(output_path, 'w', newline = '', encoding = 'utf-8') as f:
            writer = csv.writer(f)

            # Header row
            header = ['Group', 'Files', 'Target_Tables',
                      'Column_Count'] + sorted_columns
            writer.writerow(header)

            # Data rows
            for group_num in sorted(group_columns.keys()):
                info = group_columns[group_num]
                row = [
                    f"Group {group_num}",
                    info['file_count'],
                    info['target_tables'],
                    len(info['columns'])
                ]

                # Mark columns that exist in this group
                for col in sorted_columns:
                    if col in info['columns']:
                        row.append('X')
                    else:
                        row.append('')

                writer.writerow(row)

            # Add separator row
            writer.writerow([])

            # Add detailed file listing per group
            writer.writerow(['Group Details'])
            writer.writerow(['Group', 'Files in Group'])

            for group_num in sorted(group_columns.keys()):
                info = group_columns[group_num]
                for idx, filename in enumerate(info['files']):
                    if idx == 0:
                        writer.writerow([f"Group {group_num}", filename])
                    else:
                        writer.writerow(['', filename])

        print(f"✅ Group overview: {output_path}")
        print(f"   Groups: {len(group_columns)}")
        print(f"   Unique columns: {len(all_columns)}")

        return output_path

    def create_column_detail_list(
            self,
            version: str = "0.1.0"
    ) -> Path:
        """
        Create detailed list of all columns with their metadata.

        Shows original name, standardized name, type, unit, description.

        Args:
            version: Version string

        Returns:
            Path to created CSV file
        """
        import csv
        from .file_classifier import ResourceType

        # Collect all unique columns with their metadata
        columns_detail = {}

        for resource in self.package.resources:
            if not resource.column_names:
                continue

            # Only process DATA and ADDITIONAL_DATA
            if resource.classification not in [ResourceType.DATA,
                                               ResourceType.ADDITIONAL_DATA]:
                continue

            for col_name in resource.column_names:
                if self.digester:
                    field = self.digester.digest_field(col_name)
                    std_name = field['name']

                    # Only add if not already present (use first occurrence)
                    if std_name not in columns_detail:
                        columns_detail[std_name] = {
                            'original_name': col_name,
                            'standardized_name': std_name,
                            'type': field.get('type', 'unknown'),
                            'unit': field.get('unit', ''),
                            'description': field.get('description', col_name),
                            'appears_in': []
                        }

                    # Track which tables use this column
                    columns_detail[std_name]['appears_in'].append(resource.path.name)
                else:
                    std_name = col_name.lower().replace(' ', '_')
                    if std_name not in columns_detail:
                        columns_detail[std_name] = {
                            'original_name': col_name,
                            'standardized_name': std_name,
                            'type': 'unknown',
                            'unit': '',
                            'description': col_name,
                            'appears_in': [resource.path.name]
                        }

        # Create CSV
        output_path = self.paths.catalogs / f"{self.package.dataset_name}_v{version}_detail_column.csv"

        with open(output_path, 'w', newline = '', encoding = 'utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Standardized_Name',
                'Original_Name',
                'Type',
                'Unit',
                'Description',
                'Table_Count',
                'Appears_In'
            ])

            # Data rows (sorted by standardized name)
            for std_name in sorted(columns_detail.keys()):
                info = columns_detail[std_name]
                writer.writerow([
                    info['standardized_name'],
                    info['original_name'],
                    info['type'],
                    info['unit'] or '',
                    info['description'],
                    len(info['appears_in']),
                    '; '.join(info['appears_in'][:3]) + (
                        '...' if len(info['appears_in']) > 3 else '')
                ])

        print(f"✅ Column details: {output_path}")
        print(f"   Unique columns: {len(columns_detail)}")

        return output_path

    def assign_groups_by_structure(
            self,
            filter_by_classification: bool = True
    ) -> Dict[int, List[str]]:
        """
        Automatically assign group_number to resources with identical structure.
        Only processes DATA and ADDITIONAL_DATA resources by default.
        """
        # Filter resources first if classification is enabled
        if filter_by_classification:
            from .file_classifier import ResourceType
            filtered_resources = [
                r for r in self.package.resources
                if r.classification in [ResourceType.DATA]
            ]
            if filtered_resources:
                print(
                    f"   Grouping {len(filtered_resources)}/{len(self.package.resources)} resources (DATA + ADDITIONAL_DATA only)")
        structure_groups = self.col_analyzer.get_column_structure_groups()
        groups = {}
        # Assign group numbers based on structure similarity
        for group_idx, (group_name, group_info) in enumerate(structure_groups.items(),
                                                             1):
            group_files = []
            for filename in group_info['files']:
                for resource in self.package.resources:
                    if resource.path.name == filename:
                        # Apply filter if enabled
                        if filter_by_classification:
                            if resource.classification not in [
                                ResourceType.DATA
                            ]:
                                continue
                        resource.group_number = group_idx
                        group_files.append(resource.path.name)
                        break
            if group_files:
                groups[group_idx] = group_files
        return groups

    def create_catalog_draft(
            self,
            output_dir: Path = None,
            version: str = "0.1.0",
            auto_assign_groups: bool = True
    ) -> Dict[str, Any]:
        """
        Create classification catalog with optional group assignment.

        Args:
            output_dir: Output directory
            version: Version string
            auto_assign_groups: If True, assign groups before creating catalog

        Returns:
            Classification results with paths
        """
        # Assign groups first if requested
        group_mapping = {}
        if auto_assign_groups:
            print("   Assigning structure groups for catalog...")
            groups = self.assign_groups_by_structure()

            # Create mapping filename -> group_number
            for resource in self.package.resources:
                if hasattr(resource, 'group_number') and resource.group_number:
                    group_mapping[resource.path.name] = resource.group_number

        return self.classifier.classify_package(
            self.package,
            output_dir,
            version,
            group_mapping
        )

    def load_catalog(self, catalog_path: Path = None) -> int:
        """
        Load finalized catalog and apply to resources.

        Args:
            catalog_path: Path to catalog CSV. If None, auto-detect.

        Returns:
            Number of resources classified
        """
        if catalog_path is None:
            # Use new path structure - try to find latest version
            catalog_files = list(
                self.paths.catalogs.glob(f"{self.package.dataset_name}_v*_catalog.csv"))

            if not catalog_files:
                print(f"⚠️  No catalog found at {self.paths.catalogs}")
                print(f"   Create one with: planner.create_catalog_draft()")
                return 0

            # Use latest version (sort by name)
            catalog_path = sorted(catalog_files)[-1]

        # Load catalog
        catalog = self.classifier.load_catalog(catalog_path)

        # Apply classifications AND target_table to resources
        classified_count = 0
        for resource in self.package.resources:
            if resource.path.name in catalog:
                catalog_entry = catalog[resource.path.name]
                resource.classification = catalog_entry['type']
                resource.target_table = catalog_entry.get('target_table', '')
                classified_count += 1

        print(f"✅ Loaded catalog: {catalog_path}")
        print(
            f"   Applied classifications to {classified_count}/{len(self.package.resources)} resources")

        # Print breakdown
        type_counts = {}
        target_tables = set()

        for resource in self.package.resources:
            if resource.classification:
                type_val = resource.classification.value
                type_counts[type_val] = type_counts.get(type_val, 0) + 1

                # Collect target tables
                if hasattr(resource, 'target_table') and resource.target_table:
                    target_tables.add(resource.target_table)

        if type_counts:
            print("\n   Classification breakdown:")
            for type_name, count in sorted(type_counts.items()):
                print(f"     • {type_name:<25} {count:>2} resources")

        if target_tables:
            print(f"\n   Target tables: {len(target_tables)}")
            for table in sorted(target_tables):
                data_files = [
                    r.path.name for r in self.package.resources
                    if hasattr(r, 'target_table') and r.target_table == table
                ]
                print(f"     • {table:<30} {len(data_files)} files")

        return classified_count

    def get_resources_by_type(
            self,
            resource_type: ResourceType
    ) -> List:
        """
        Get resources filtered by classification type.

        Args:
            resource_type: ResourceType to filter by

        Returns:
            List of resources matching the type
        """
        if self.catalog is None:
            print("⚠️  No catalog loaded. Call load_catalog() first.")
            return []

        filtered = []
        for resource in self.package.resources:
            classified_type = self.catalog.get(resource.path.name)
            if classified_type == resource_type:
                filtered.append(resource)

        return filtered

    def save_plan(self, output_path: Path = None):
        """Save transformation plan to JSON."""
        if output_path is None:
            output_path = Path(
                f"data/reports/transformation_plan_{self.package.dataset_name}.json")

        plan = self.analyze_and_plan()

        with open(output_path, 'w', encoding = 'utf-8') as f:
            json.dump(plan, f, indent = 2, ensure_ascii = False)

        print(f"Transformation plan saved: {output_path}")
        return output_path

    def print_plan(self):
        """Print transformation plan in readable format."""
        plan = self.analyze_and_plan()

        print(f"\n{'=' * 70}")
        print(f"TRANSFORMATION PLAN: {plan['dataset']}")
        print(f"{'=' * 70}\n")

        print("📊 CURRENT STATE:")
        print("-" * 70)
        state = plan['current_state']
        print(f"  Total files: {state['total_files']}")
        print(f"  Total size: {state['total_size_mb']} MB")
        print(f"  Total rows: {state['total_rows']:,}")
        print(f"  Average rows/file: {state['avg_rows_per_file']:,}")
        print(f"  Unique structures: {state['unique_structures']}")
        print(f"  Invalid columns: {state['invalid_columns']}")
        print()

        print("💡 TRANSFORMATION OPTIONS:")
        print("-" * 70)
        for idx, option in enumerate(plan['options'], 1):
            print(f"\n  [{idx}] {option['title']}")
            print(f"      {option['description']}")
            print(f"      Impact: {option['impact']}")
        print()

        print("🎯 RECOMMENDED SEQUENCE:")
        print("-" * 70)
        for idx, rec_id in enumerate(plan['recommendations'], 1):
            option = next(o for o in plan['options'] if o['id'] == rec_id)
            print(f"  {idx}. {option['title']}")

        print(f"\n{'=' * 70}\n")

        print("💡 TIP: Create a structure plan with:")
        print("   planner.create_structure_plan()")
        print("   planner.save_complete_plan()")
        print()
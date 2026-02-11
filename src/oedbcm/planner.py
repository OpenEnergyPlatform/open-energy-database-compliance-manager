"""Open Energy Database Compliance Manager

Transformation planning and recommendation engine.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""


from pathlib import Path
from typing import Dict, List, Any
from .package import DataPackage
from .analyzer import ColumnAnalyzer, FileNameAnalyzer
import json


class TransformationPlanner:
    """Plan and suggest transformations for datasets."""

    def __init__(self, package: DataPackage):
        self.package = package
        self.col_analyzer = ColumnAnalyzer(package)
        self.file_analyzer = FileNameAnalyzer(package)

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

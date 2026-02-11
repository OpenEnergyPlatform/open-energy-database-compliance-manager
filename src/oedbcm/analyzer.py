"""Open Energy Database Compliance Manager

Analysis utilities for exploring dataset structures.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""


from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import Counter, defaultdict
from .package import DataPackage
from .resource import CSVResource
from .resource import Resource


class ColumnAnalyzer:
    """Analyze column names and patterns across a dataset."""

    def __init__(self, package: DataPackage):
        self.package = package
        self.package.analyze_all()

    def get_all_column_names(self) -> List[str]:
        """Get all unique column names across all files."""
        all_columns = []
        for resource in self.package.resources:
            if resource.column_names:
                all_columns.extend(resource.column_names)
        return all_columns

    def column_frequency(self) -> Dict[str, int]:
        """Count how often each column name appears."""
        columns = self.get_all_column_names()
        return dict(Counter(columns).most_common())

    def column_patterns(self) -> Dict[str, List[str]]:
        """
        Group similar column names by patterns.

        Returns dict with pattern types:
        - timestamps: time-related columns
        - measurements: numeric measurement columns
        - identifiers: ID columns
        - metadata: descriptive columns
        """
        patterns = {
            'timestamps': [],
            'measurements': [],
            'identifiers': [],
            'metadata': [],
            'unknown': []
        }

        timestamp_keywords = ['time', 'date', 'timestamp', 'datetime', 'zeit', 'datum']
        measurement_keywords = ['value', 'wert', 'power', 'leistung', 'energy',
                                'energie', 'voltage', 'spannung', 'current', 'strom',
                                'temperature', 'temperatur', 'pressure', 'druck']
        id_keywords = ['id', 'identifier', 'index', 'nummer', 'number']

        for col in set(self.get_all_column_names()):
            col_lower = col.lower()

            if any(kw in col_lower for kw in timestamp_keywords):
                patterns['timestamps'].append(col)
            elif any(kw in col_lower for kw in id_keywords):
                patterns['identifiers'].append(col)
            elif any(kw in col_lower for kw in measurement_keywords):
                patterns['measurements'].append(col)
            elif any(kw in col_lower for kw in ['name', 'description', 'type', 'unit', 'einheit']):
                patterns['metadata'].append(col)
            else:
                patterns['unknown'].append(col)

        return patterns

    def files_by_column_count(self) -> Dict[int, List[str]]:
        """Group files by number of columns."""
        groups = defaultdict(list)
        for resource in self.package.resources:
            if resource.n_columns:
                groups[resource.n_columns].append(resource.path.name)
        return dict(sorted(groups.items()))

    def files_with_column(self, column_name: str) -> List[str]:
        """Find all files containing a specific column."""
        files = []
        for resource in self.package.resources:
            if resource.column_names and column_name in resource.column_names:
                files.append(resource.path.name)
        return files

    def get_column_structure_groups(self) -> Dict[str, List[str]]:
        """
        Group files by identical column structure.

        Returns dict where key is tuple of column names, value is list of files.
        """
        groups = defaultdict(list)
        for resource in self.package.resources:
            if resource.column_names:
                # Use sorted tuple as key for grouping
                col_signature = tuple(sorted(resource.column_names))
                groups[col_signature].append(resource.path.name)

        # Convert to readable format
        result = {}
        for idx, (cols, files) in enumerate(groups.items(), 1):
            result[f"Group_{idx}"] = {
                'columns': list(cols),
                'files': files,
                'count': len(files)
            }
        return result

    def get_resource_statistics(self) -> Dict[str, any]:
        """Get statistics about all resources."""
        stats = {
            'total_size_bytes': 0,
            'total_rows': 0,
            'files': []
        }

        for resource in self.package.resources:
            file_info = {
                'name': resource.path.name,
                'size_bytes': resource.file_size,
                'size_mb': round(resource.file_size / (1024 * 1024), 2),
                'rows': resource.n_rows or 0,
                'columns': resource.n_columns or 0,
                'encoding': getattr(resource, 'detected_encoding', resource.encoding),
            }
            stats['files'].append(file_info)
            stats['total_size_bytes'] += resource.file_size
            stats['total_rows'] += file_info['rows']

        stats['total_size_mb'] = round(stats['total_size_bytes'] / (1024 * 1024), 2)
        stats['avg_rows_per_file'] = round(stats['total_rows'] / len(stats['files']),
                                           1) if stats['files'] else 0

        return stats

    def print_analysis(self):
        """Print comprehensive column analysis."""
        print(f"\n{'=' * 70}")
        print(f"COLUMN ANALYSIS: {self.package.dataset_name}")
        print(f"{'=' * 70}\n")

        # RESOURCE STATISTICS (NEU!)
        print("📦 RESOURCE STATISTICS:")
        print("-" * 70)
        stats = self.get_resource_statistics()
        print(f"  Total files: {len(stats['files'])}")
        print(f"  Total size: {stats['total_size_mb']} MB")
        print(f"  Total rows: {stats['total_rows']:,}")
        print(f"  Average rows/file: {stats['avg_rows_per_file']:,}")
        print()

        print("  File Details:")
        # Sort by size descending
        sorted_files = sorted(stats['files'], key = lambda x: x['size_bytes'],
                              reverse = True)
        for file_info in sorted_files[:10]:  # Show top 10
            print(f"    • {file_info['name']:<45} "
                  f"{file_info['size_mb']:>6.2f} MB | "
                  f"{file_info['rows']:>7,} rows | "
                  f"{file_info['columns']:>3} cols | "
                  f"{file_info['encoding']}")

        if len(sorted_files) > 10:
            print(f"    ... (+{len(sorted_files) - 10} more files)")
        print()

        # Frequency analysis
        print("📊 MOST COMMON COLUMN NAMES:")
        print("-" * 70)
        from .resource import Resource
        freq = self.column_frequency()
        for col, count in list(freq.items())[:15]:
            valid = "✓" if Resource.DB_COLUMN_PATTERN.match(col) else "✗"
            print(f"  {valid} {col:<40} ({count} files)")
        print()

        # Pattern analysis
        print("🔍 COLUMN PATTERNS:")
        print("-" * 70)
        patterns = self.column_patterns()
        for pattern_type, columns in patterns.items():
            if columns:
                print(f"  {pattern_type.upper()}: {len(columns)} columns")
                for col in sorted(columns)[:5]:
                    print(f"    • {col}")
                if len(columns) > 5:
                    print(f"    ... (+{len(columns) - 5} more)")
        print()

        # Column count distribution
        print("📁 FILES BY COLUMN COUNT:")
        print("-" * 70)
        col_groups = self.files_by_column_count()
        for n_cols, files in col_groups.items():
            print(f"  {n_cols} columns: {len(files)} files")
            if len(files) <= 3:
                for f in files:
                    print(f"    • {f}")
        print()

        # Structure groups
        print("🗂️  FILES WITH IDENTICAL STRUCTURE:")
        print("-" * 70)
        structure_groups = self.get_column_structure_groups()
        for group_name, info in structure_groups.items():
            if info['count'] > 1:  # Only show groups with multiple files
                print(f"  {group_name}: {info['count']} files")
                print(
                    f"    Columns ({len(info['columns'])}): {', '.join(info['columns'][:3])}",
                    end = '')
                if len(info['columns']) > 3:
                    print(f" ... (+{len(info['columns']) - 3} more)")
                else:
                    print()
                print(f"    Files: {', '.join(info['files'][:2])}", end = '')
                if len(info['files']) > 2:
                    print(f" ... (+{len(info['files']) - 2} more)")
                else:
                    print()
                print()

        print(f"{'=' * 70}\n")


class FileNameAnalyzer:
    """Analyze filename patterns and extract metadata."""

    def __init__(self, package: DataPackage):
        self.package = package

    def extract_metadata_patterns(self) -> Dict[str, Dict]:
        """
        Extract common patterns from filenames.

        Looks for:
        - Years (4 digits)
        - Dates (various formats)
        - Common separators (_, -, space)
        - File naming patterns
        """
        metadata = {}

        for resource in self.package.resources:
            filename = resource.path.stem

            info = {
                'original': filename,
                'parts': filename.split('_'),
                'years': self._extract_years(filename),
                'dates': self._extract_dates(filename),
                'numeric_parts': self._extract_numbers(filename),
                'suggested_columns': []
            }

            # Suggest columns based on patterns
            if info['years']:
                info['suggested_columns'].append('year')
            if info['dates']:
                info['suggested_columns'].append('date')
            if len(info['parts']) > 1:
                info['suggested_columns'].extend([
                    f'metadata_{i}' for i in range(len(info['parts']))
                ])

            metadata[resource.path.name] = info

        return metadata

    def _extract_years(self, filename: str) -> List[str]:
        """Extract 4-digit years from filename."""
        import re
        return re.findall(r'\b(19\d{2}|20\d{2})\b', filename)

    def _extract_dates(self, filename: str) -> List[str]:
        """Extract date patterns from filename."""
        import re
        # Look for common date formats
        patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}\.\d{2}\.\d{4}',  # DD.MM.YYYY
            r'\d{8}',  # YYYYMMDD
        ]
        dates = []
        for pattern in patterns:
            dates.extend(re.findall(pattern, filename))
        return dates

    def _extract_numbers(self, filename: str) -> List[str]:
        """Extract all numeric parts from filename."""
        import re
        return re.findall(r'\d+', filename)

    def group_by_pattern(self) -> Dict[str, List[str]]:
        """Group files by similar naming patterns."""
        groups = defaultdict(list)

        for resource in self.package.resources:
            filename = resource.path.stem
            # Create pattern signature
            pattern_parts = []
            for part in filename.split('_'):
                if part.isdigit():
                    pattern_parts.append('NUM')
                elif any(char.isdigit() for char in part):
                    pattern_parts.append('MIXED')
                else:
                    pattern_parts.append('TEXT')

            pattern = '_'.join(pattern_parts)
            groups[pattern].append(resource.path.name)

        return dict(groups)

    def print_analysis(self):
        """Print filename pattern analysis."""
        print(f"\n{'= ' *70}")
        print(f"FILENAME ANALYSIS: {self.package.dataset_name}")
        print(f"{'= ' *70}\n")

        # Pattern groups
        print("📋 FILENAME PATTERNS:")
        print("- " *70)
        groups = self.group_by_pattern()
        for pattern, files in groups.items():
            print(f"  Pattern '{pattern}': {len(files)} files")
            for f in files[:3]:
                print(f"    • {f}")
            if len(files) > 3:
                print(f"    ... (+{len(files ) -3} more)")
            print()

        # Metadata extraction
        print("🏷️  EXTRACTABLE METADATA:")
        print("- " *70)
        metadata = self.extract_metadata_patterns()

        files_with_years = [f for f, m in metadata.items() if m['years']]
        files_with_dates = [f for f, m in metadata.items() if m['dates']]

        print(f"  Files with years: {len(files_with_years)}")
        if files_with_years:
            example = metadata[files_with_years[0]]
            print(f"    Example: {files_with_years[0]}")
            print(f"    Years found: {example['years']}")
            print(f"    → Could add column 'year' with value: {example['years'][0]}")
        print()

        print(f"  Files with dates: {len(files_with_dates)}")
        if files_with_dates:
            example = metadata[files_with_dates[0]]
            print(f"    Example: {files_with_dates[0]}")
            print(f"    Dates found: {example['dates']}")
        print()

        print(f"{'= ' *70}\n")

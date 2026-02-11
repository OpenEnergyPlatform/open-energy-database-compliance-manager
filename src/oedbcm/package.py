"""Open Energy Database Compliance Manager

DataPackage container for managing multiple CSV resources.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from .resource import CSVResource
from .logger import ValidationLogger


class DataPackage:
    """Container for a collection of CSV files in a directory."""

    def __init__(self, directory: Path, dataset_name: Optional[str] = None):
        self.directory = Path(directory)
        if not self.directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.directory}")

        # Use directory name as dataset name if not provided
        self.dataset_name = dataset_name or self.directory.name

        self.resources: List[CSVResource] = []
        self.logger: Optional[ValidationLogger] = None

        self._discover_csvs()

    def _discover_csvs(self) -> None:
        """Find all CSV files in directory."""
        for csv_file in sorted(self.directory.glob("*.csv")):
            self.resources.append(CSVResource(csv_file))

    def analyze_all(self, enable_logging: bool = False) -> None:
        """
        Analyze all CSV files.

        Args:
            enable_logging: If True, create log files for this run
        """
        if enable_logging:
            self.logger = ValidationLogger(self.dataset_name)
            self.logger.log_start(self.directory, len(self.resources))

        for resource in self.resources:
            resource.analyze_structure()

            if self.logger:
                self.logger.log_file_analysis(
                    resource.path.name,
                    resource.n_rows or 0,
                    resource.n_columns or 0
                )

    def validate_all(self, enable_logging: bool = False) -> Dict[str, Any]:
        """
        Validate all resources and return issues.

        Args:
            enable_logging: If True, create log files for this run

        Returns dict with:
        - filename_issues: Files with invalid names
        - column_issues: Files with invalid column names
        """
        self.analyze_all(enable_logging = enable_logging)

        filename_issues = []
        column_issues = []

        for resource in self.resources:
            # Check filename
            if not resource.is_valid_filename():
                issue = {
                    'file': resource.path.name,
                    'reason': 'Contains uppercase, spaces, or special characters'
                }
                filename_issues.append(issue)

                if self.logger:
                    self.logger.log_validation_issue(
                        'ERROR',
                        f"Invalid filename: {resource.path.name}"
                    )

            # Check column names
            invalid_cols = resource.invalid_column_names()
            if invalid_cols:
                issue = {
                    'file': resource.path.name,
                    'invalid_columns': invalid_cols
                }
                column_issues.append(issue)

                if self.logger:
                    self.logger.log_validation_issue(
                        'WARNING',
                        f"Invalid columns in {resource.path.name}: {', '.join(invalid_cols)}"
                    )

        results = {
            'total_files': len(self.resources),
            'filename_issues': filename_issues,
            'column_issues': column_issues,
            'passed': len(filename_issues) == 0 and len(column_issues) == 0
        }

        if self.logger:
            total_issues = len(filename_issues) + len(column_issues)
            self.logger.log_summary(
                results['total_files'],
                total_issues,
                results['passed']
            )
            self.logger.save_json_report(results)
            self.logger.append_to_history()

        return results

    def print_report(self) -> None:
        """Print validation report to console."""
        results = self.validate_all(enable_logging = False)

        print(f"\n{'=' * 60}")
        print(f"Data Package Validation: {self.dataset_name}")
        print(f"{'=' * 60}\n")
        print(f"Total files: {results['total_files']}\n")

        # Filename issues
        if results['filename_issues']:
            print(f"❌ FILENAME ISSUES ({len(results['filename_issues'])}):")
            for issue in results['filename_issues']:
                print(f"  • {issue['file']}")
                print(f"    → {issue['reason']}")
            print()

        # Column name issues
        if results['column_issues']:
            print(f"⚠️  COLUMN NAME ISSUES ({len(results['column_issues'])}):")
            for issue in results['column_issues']:
                print(f"  • {issue['file']}")
                print(f"    → Invalid: {', '.join(issue['invalid_columns'])}")
            print()

        # Summary
        if results['passed']:
            print("✅ All validations passed!")
        else:
            print("❌ Validation failed - fix issues above")

        print(f"\n{'=' * 60}\n")

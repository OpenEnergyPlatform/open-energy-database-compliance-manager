"""Open Energy Database Compliance Manager

Logging and reporting utilities for validation runs.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import csv


class ValidationLogger:
    """
    Logger for validation runs with file output.

    Creates timestamped log files and JSON reports for each validation run.
    """

    def __init__(self, dataset_name: str, output_dir: Path = None):
        """
        Initialize logger for a dataset validation run.

        Args:
            dataset_name: Name of the dataset being validated
            output_dir: Directory for log files (default: data/reports/)
        """
        self.dataset_name = dataset_name
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

        # Setup output directory
        if output_dir is None:
            output_dir = Path("data/reports")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents = True, exist_ok = True)

        # Create base filename
        self.base_filename = f"{self.timestamp}_{dataset_name}"

        # Setup file logger
        self.log_file = self.output_dir / f"{self.base_filename}.log"
        self.json_file = self.output_dir / f"{self.base_filename}.json"

        self._setup_logger()

    def _setup_logger(self):
        """Configure file and console logging."""
        self.logger = logging.getLogger(f"oedbcm.{self.dataset_name}")
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers
        self.logger.handlers.clear()

        # File handler
        file_handler = logging.FileHandler(self.log_file, encoding = 'utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt = '%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log_start(self, dataset_path: Path, num_files: int):
        """Log start of validation run."""
        self.logger.info("=" * 60)
        self.logger.info(f"Validation Run: {self.dataset_name}")
        self.logger.info(f"Timestamp: {self.timestamp}")
        self.logger.info(f"Dataset Path: {dataset_path}")
        self.logger.info(f"Files Found: {num_files}")
        self.logger.info("=" * 60)

    def log_file_analysis(self, filename: str, rows: int, columns: int):
        """Log analysis of individual file."""
        self.logger.info(f"Analyzing: {filename} ({rows} rows, {columns} columns)")

    def log_validation_issue(self, severity: str, message: str):
        """Log a validation issue."""
        if severity.upper() == "ERROR":
            self.logger.error(message)
        elif severity.upper() == "WARNING":
            self.logger.warning(message)
        else:
            self.logger.info(message)

    def log_summary(self, total_files: int, total_issues: int, passed: bool):
        """Log validation summary."""
        self.logger.info("-" * 60)
        self.logger.info(f"Validation Summary:")
        self.logger.info(f"  Total Files: {total_files}")
        self.logger.info(f"  Total Issues: {total_issues}")
        self.logger.info(f"  Status: {'PASSED ✓' if passed else 'FAILED ✗'}")
        self.logger.info("=" * 60)

    def save_json_report(self, validation_results: Dict[str, Any]):
        """
        Save validation results as JSON.

        Args:
            validation_results: Dict with validation results from DataPackage
        """
        report = {
            "metadata": {
                "dataset_name": self.dataset_name,
                "timestamp": self.timestamp,
                "validator_version": "0.1.0"
            },
            "results": validation_results
        }

        with open(self.json_file, 'w', encoding = 'utf-8') as f:
            json.dump(report, f, indent = 2, ensure_ascii = False)

        self.logger.info(f"JSON report saved: {self.json_file}")

    def append_to_history(self):
        """Append validation run to history CSV."""
        history_file = self.output_dir / "validation_history.csv"

        # Check if file exists to determine if we need header
        file_exists = history_file.exists()

        with open(history_file, 'a', newline = '', encoding = 'utf-8') as f:
            writer = csv.writer(f)

            # Write header if new file
            if not file_exists:
                writer.writerow([
                    'timestamp', 'dataset_name', 'log_file', 'json_file'
                ])

            # Write record
            writer.writerow([
                self.timestamp,
                self.dataset_name,
                self.log_file.name,
                self.json_file.name
            ])

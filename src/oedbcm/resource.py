"""Open Energy Database Compliance Manager

Provides core classes for representing and validating file-based
resources within a data package, including basic structural metadata
and database-oriented naming checks.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
import csv
import re

if TYPE_CHECKING:
    from .file_classifier import ResourceType

class Resource:
    """
    Base class for a single file resource within a data package.

    A Resource represents exactly one file and provides access to
    basic structural metadata independent of the file format.

    Attributes:
        path: Absolute or relative path to the resource file
        file_type: File extension (without dot), e.g. 'csv', 'json'
        file_size: Size of the file in bytes
        n_rows: Number of data rows (excluding header), populated by analyze_structure()
        n_columns: Number of columns/fields in the file
        column_names: List of column/field names from the file header
        group_number: Optional group ID for mapping to planned structure
        classification: Optional ResourceType classification from catalog
        target_table: Target table name for DATA resources from catalog
    """

    # Regex pattern for valid database column names:
    # - Must start with lowercase letter
    # - Can contain lowercase letters, digits, and underscores
    # - No uppercase, no special characters, no leading digits
    DB_COLUMN_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

    # Valid filename pattern: lowercase, digits, underscores, hyphens
    VALID_FILENAME_PATTERN = re.compile(r"^[a-z0-9_-]+$")

    def __init__(self, path: Path):
        """
        Initialize a Resource instance for a given file.

        Args:
            path: Path object pointing to the resource file
        """
        self.path: Path = path
        self.file_type: str = self._detect_file_type()
        self.file_size: int = self._get_file_size()

        # Structural metadata - populated later via analyze_structure()
        self.n_rows: Optional[int] = None
        self.n_columns: Optional[int] = None
        self.column_names: Optional[List[str]] = None

        # Group assignment for planning - populated by planner
        self.group_number: Optional[int] = None

        # Classification from catalog - populated by load_catalog
        self.classification: Optional['ResourceType'] = None

        # Target table assignment from catalog - populated by load_catalog
        self.target_table: str = ''

    def _detect_file_type(self) -> str:
        """Extract file extension without dot."""
        return self.path.suffix.lower().lstrip(".")

    def _get_file_size(self) -> int:
        """Get file size in bytes."""
        return self.path.stat().st_size

    def analyze_structure(self) -> None:
        """Analyze file structure - implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement analyze_structure()")

    def is_db_column_name(self, name: str) -> bool:
        """
        Check if a column name follows database naming conventions.

        Valid database column names must:
        - Start with a lowercase letter (a-z)
        - Contain only lowercase letters, digits, and underscores
        - Not start with a digit or underscore

        Args:
        name: Column name to validate

        Returns:
        True if name matches DB naming pattern, False otherwise
        """
        return bool(self.DB_COLUMN_PATTERN.match(name))

    def is_valid_filename(self) -> bool:
        """
        Check if filename (without extension) follows naming conventions.

        Valid filenames must:
        - Contain only lowercase letters, digits, underscores, and hyphens
        - No uppercase letters, spaces, or special characters

        Returns:
            True if filename matches pattern, False otherwise
        """
        filename_without_ext = self.path.stem
        return bool(self.VALID_FILENAME_PATTERN.match(filename_without_ext))

    def invalid_column_names(self) -> List[str]:
        """
        Identify column names that violate database naming conventions.

        Returns:
            List of column names that don't match DB naming pattern.
            Returns empty list if column_names is not yet populated.

        Note:
            This method should be called after analyze_structure() has
            been executed to populate self.column_names.
        """
        if not self.column_names:
            return []
        return [
            name for name in self.column_names
            if not self.is_db_column_name(name)
        ]


class CSVResource(Resource):
    """CSV-specific resource with structure analysis."""

    def __init__(self, path: Path, encoding: str = 'utf-8',
                 delimiter: Optional[str] = None):
        super().__init__(path)
        self.encoding = encoding
        self.detected_encoding = None
        self.delimiter = delimiter or self._detect_delimiter()

    def _detect_encoding(self) -> str:
        """
        Detect file encoding by trying common encodings.

        Returns:
            Detected encoding name
        """
        # Common encodings in order of likelihood
        encodings_to_try = [
            'utf-8',
            'utf-8-sig',  # UTF-8 with BOM
            'latin-1',  # ISO-8859-1
            'cp1252',  # Windows-1252 (Western European)
            'iso-8859-15',
            'cp850',  # DOS encoding
        ]

        for encoding in encodings_to_try:
            try:
                with open(self.path, 'r', encoding = encoding) as f:
                    f.read(4096)  # Try to read first 4KB
                self.detected_encoding = encoding
                return encoding
            except (UnicodeDecodeError, UnicodeError):
                continue

        # Fallback
        self.detected_encoding = 'latin-1'
        return 'latin-1'

    def _detect_delimiter(self) -> str:
        """Auto-detect CSV delimiter from file sample."""
        # First ensure we have the right encoding
        if self.encoding == 'utf-8' and self.detected_encoding is None:
            self.encoding = self._detect_encoding()

        try:
            with open(self.path, 'r', encoding = self.encoding) as f:
                sample = f.read(1024)
                sniffer = csv.Sniffer()
                return sniffer.sniff(sample).delimiter
        except Exception:
            return ','  # Fallback

    def analyze_structure(self) -> None:
        """Read CSV header and count rows/columns."""
        # Auto-detect encoding if not already done
        if self.detected_encoding is None:
            self.encoding = self._detect_encoding()

        try:
            # Ensure delimiter is set
            if self.delimiter is None:
                self.delimiter = self._detect_delimiter()

            with open(self.path, 'r', encoding = self.encoding, newline = '') as f:
                reader = csv.reader(f, delimiter = self.delimiter)

                # Read header
                self.column_names = next(reader)
                self.n_columns = len(self.column_names)

                # Count data rows
                self.n_rows = sum(1 for _ in reader)

        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(
                e.encoding, e.object, e.start, e.end,
                f"Could not decode {self.path.name}. Tried encoding: {self.encoding}"
            )

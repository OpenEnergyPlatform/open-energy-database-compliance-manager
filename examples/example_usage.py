"""Open Energy Database Compliance Manager

Example usage of oedbcm.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from oedbcm import DataPackage

# Use absolute path relative to this script
script_dir = Path(__file__).parent
test_data_dir = script_dir.parent / "test" / "test_data"

# Create and validate a data package
package = DataPackage(test_data_dir)
package.print_report()

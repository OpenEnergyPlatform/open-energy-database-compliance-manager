"""Open Energy Database Compliance Manager

Additional validation helpers for filename patterns.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

import re


def extract_metadata_from_filename(filename: str) -> dict:
    """
    Extract common metadata patterns from filename.

    Examples:
        'energy_consumption_2023.csv' → {'year': '2023', 'topic': 'energy_consumption'}
        'solar_pv_germany_2020_2024.csv' → {'year_start': '2020', 'year_end': '2024'}
    """
    metadata = {}

    # Extract year (4 digits)
    years = re.findall(r'\b(20\d{2})\b', filename)
    if len(years) == 1:
        metadata['year'] = years[0]
    elif len(years) == 2:
        metadata['year_start'] = years[0]
        metadata['year_end'] = years[1]

    # Extract common patterns
    parts = filename.replace('.csv', '').split('_')
    if len(parts) > 0:
        metadata['parts'] = parts

    return metadata


def suggest_filename_fix(filename: str) -> str:
    """Suggest a corrected filename following conventions."""
    # Remove extension
    name = filename.replace('.csv', '')

    # Lowercase
    name = name.lower()

    # Replace spaces and special chars with underscores
    name = re.sub(r'[^a-z0-9_-]', '_', name)

    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)

    # Remove leading/trailing underscores
    name = name.strip('_')

    return f"{name}.csv"

"""Open Energy Database Compliance Manager

A Python package for validating and analyzing energy data packages.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

__version__ = "0.1.0"

from .resource import Resource, CSVResource
from .package import DataPackage
from .visualizer import (
    StructureVisualizer,
    GroupMergeVisualizer,
    DatasetMergeOverviewVisualizer,
)
from .structure_schema import StructurePlan

__all__ = [
    'DataPackage',
    'Resource',
    'CSVResource',
    'StructureVisualizer',
    'GroupMergeVisualizer',
    'DatasetMergeOverviewVisualizer',
    'StructurePlan',
]

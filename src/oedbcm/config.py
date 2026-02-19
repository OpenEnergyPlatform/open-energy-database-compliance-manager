"""Open Energy Database Compliance Manager

Configuration and helper functions for planning workflows.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class WorkflowConfig:
    """Configuration for a planning workflow run."""

    dataset_path: Path
    version: str = "0.1.0"
    description: str = "Initial structure planning"

    # OEMetadata defaults
    title: Optional[str] = None
    contributor_name: Optional[str] = None
    contributor_email: Optional[str] = None

    # Workflow options
    auto_assign_groups: bool = True
    create_visualization: bool = True
    create_metadata_drafts: bool = True
    create_overview_tables: bool = True

    def __post_init__(self):
        """Validate and set defaults."""
        self.dataset_path = Path(self.dataset_path)

        # Auto-generate title if not provided
        if self.title is None:
            self.title = f"Dataset: {self.dataset_path.name}"


def ask_user_confirmation(question: str, default: str = 'y') -> bool:
    """
    Ask user for yes/no confirmation.

    Args:
        question: Question to ask
        default: Default answer ('y' or 'n')

    Returns:
        True if yes, False if no
    """
    valid_responses = {'y': True, 'yes': True, 'n': False, 'no': False}

    prompt = f"{question} [y/n, default={default}]: "

    while True:
        response = input(prompt).strip().lower()

        if not response:
            response = default

        if response in valid_responses:
            return valid_responses[response]

        print("   Please answer 'y' or 'n'")


def print_section_header(title: str, char: str = "="):
    """Print formatted section header."""
    width = 80
    print("\n" + char * width)
    print(title.center(width))
    print(char * width + "\n")


def print_subsection(title: str):
    """Print formatted subsection."""
    print(f"\n{title}")
    print("-" * 80)

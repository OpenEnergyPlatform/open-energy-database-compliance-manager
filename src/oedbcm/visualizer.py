"""Open Energy Database Compliance Manager

Visualization module for comparing data structures.

SPDX-FileCopyrightText: 2026 Ludwig Hülk <https://github.com/Ludee> © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import networkx as nx
from datetime import datetime


class StructureVisualizer:
    """Visualize data structure hierarchies with modern, clean styling."""

    # Color scheme - modern, professional
    COLORS = {
        'package': '#2E86AB',  # Blue - DataPackage
        'resource': '#A23B72',  # Purple - Resources
        'field': '#F18F01',  # Orange - Fields
        'background': '#F7F9FB',  # Light gray
        'text': '#2C3E50',  # Dark gray
        'border': '#BDC3C7',  # Medium gray
        'arrow': '#7F8C8D',  # Gray arrows
        'highlight': '#E74C3C'  # Red for differences
    }

    def __init__(self, output_dir: Path = None, dataset_name: str = None):
        """
        Initialize visualizer.

        Args:
            output_dir: Directory for output files (uses new structure if None)
            dataset_name: Dataset name (required if output_dir is None)
        """
        if dataset_name is None:
            raise ValueError("dataset_name must be provided")

        self.dataset_name = dataset_name

        try:
            from .paths import get_project_paths  # normal package import
        except ImportError:
            # Running as a script → fall back to absolute import from src
            from paths import get_project_paths

        self.paths = get_project_paths(dataset_name)
        self.output_dir = self.paths.plots

        # Set matplotlib style for clean look
        plt.style.use("seaborn-v0_8-white")

    def visualize_comparison(
            self,
            current_structure: Dict[str, Any],
            planned_structure: Dict[str, Any],
            title: str = "Data Structure Comparison",
            version: str = "0.1.0"
    ) -> Path:
        """
        Create side-by-side comparison visualization.

        Args:
            current_structure: Current (as-is) structure
            planned_structure: Planned (to-be) structure
            title: Title for the visualization
            version: Version string for the output filename

        Returns:
            Path to saved PNG file
        """
        # Extract dataset name for folder structure
        dataset_name = current_structure.get('dataset_name') or \
                       current_structure.get('name') or \
                       "unknown_dataset"

        # Create dataset specific subdirectory: data/plots/HSRM_.../
        dataset_plot_dir = self.output_dir
        dataset_plot_dir.mkdir(parents = True, exist_ok = True)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize = (20, 12))
        fig.patch.set_facecolor(self.COLORS['background'])

        # Left: Current state
        self._draw_structure_tree(ax1, current_structure, "Current State (As-Is)")

        # Right: Planned state
        self._draw_structure_tree(ax2, planned_structure, "Planned State (To-Be)")

        # Main title
        fig.suptitle(
            title,
            fontsize = 20,
            fontweight = 'bold',
            color = self.COLORS['text'],
            y = 0.98
        )

        # Add metadata footer
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        fig.text(
            0.5, 0.02,
            f"Version: {version} | Generated: {timestamp}",
            ha = 'center',
            fontsize = 10,
            color = self.COLORS['text'],
            style = 'italic'
        )

        plt.tight_layout(rect = [0, 0.03, 1, 0.96])

        # Save with version in filename
        output_path = self.paths.get_visualization_path(version)
        plt.savefig(
            output_path,
            dpi = 300,
            bbox_inches = 'tight',
            facecolor = self.COLORS['background']
        )
        plt.close()

        print(f"✅ Visualization saved: {output_path}")
        return output_path

    def _draw_structure_tree(
            self,
            ax,
            structure: Dict[str, Any],
            subtitle: str
    ):
        """Draw a tree structure on given axes."""
        ax.set_facecolor(self.COLORS['background'])
        ax.set_title(subtitle, fontsize = 16, fontweight = 'bold', pad = 20)

        # Create directed graph
        G = nx.DiGraph()

        # Build graph from structure
        package_name = structure.get('name', 'DataPackage')
        G.add_node(package_name, level = 0, type = 'package')

        resources = structure.get('resources', [])
        y_offset = 0

        for idx, resource in enumerate(resources):
            resource_name = resource.get('name', f'Resource_{idx}')
            G.add_node(resource_name, level = 1, type = 'resource')
            G.add_edge(package_name, resource_name)

            # Add fields as children
            fields = resource.get('fields', [])
            for field_idx, field in enumerate(fields[:5]):  # Limit to 5 for readability
                field_name = field.get('name', f'field_{field_idx}')
                field_node = f"{resource_name}:{field_name}"
                G.add_node(field_node, level = 2, type = 'field')
                G.add_edge(resource_name, field_node)

            # Add indicator if more fields exist
            if len(fields) > 5:
                more_node = f"{resource_name}:..."
                G.add_node(more_node, level = 2, type = 'more')
                G.add_edge(resource_name, more_node)

        # Use hierarchical layout
        pos = self._hierarchical_layout(G)

        # Draw nodes with different styles per type
        for node, (x, y) in pos.items():
            node_data = G.nodes[node]
            node_type = node_data.get('type', 'field')

            if node_type == 'package':
                color = self.COLORS['package']
                size = 0.15
                text_size = 12
            elif node_type == 'resource':
                color = self.COLORS['resource']
                size = 0.12
                text_size = 10
            elif node_type == 'more':
                color = self.COLORS['border']
                size = 0.08
                text_size = 8
            else:  # field
                color = self.COLORS['field']
                size = 0.1
                text_size = 9

            # Draw rounded rectangle
            box = FancyBboxPatch(
                (x - size / 2, y - size / 3),
                size, size * 0.6,
                boxstyle = "round,pad=0.01",
                facecolor = color,
                edgecolor = self.COLORS['border'],
                linewidth = 1.5,
                alpha = 0.9,
                zorder = 2
            )
            ax.add_patch(box)

            # Add text (show only last part for fields)
            display_text = node.split(':')[-1] if ':' in node else node
            if len(display_text) > 20:
                display_text = display_text[:17] + '...'

            ax.text(
                x, y,
                display_text,
                ha = 'center',
                va = 'center',
                fontsize = text_size,
                color = 'white',
                fontweight = 'bold',
                zorder = 3
            )

        # Draw edges with curved arrows
        for edge in G.edges():
            start_pos = pos[edge[0]]
            end_pos = pos[edge[1]]

            arrow = FancyArrowPatch(
                start_pos, end_pos,
                arrowstyle = '-|>',
                color = self.COLORS['arrow'],
                linewidth = 1.5,
                alpha = 0.6,
                connectionstyle = "arc3,rad=0.1",
                zorder = 1
            )
            ax.add_patch(arrow)

        # Set limits and remove axes
        ax.set_xlim(-0.2, 1.2)
        ax.set_ylim(-0.2, 1.2)
        ax.axis('off')

    def _hierarchical_layout(self, G: nx.DiGraph) -> Dict:
        """Create hierarchical layout for tree structure."""
        pos = {}

        # Get nodes by level
        levels = {}
        for node, data in G.nodes(data = True):
            level = data.get('level', 0)
            if level not in levels:
                levels[level] = []
            levels[level].append(node)

        # Position nodes
        max_level = max(levels.keys())
        for level, nodes in levels.items():
            y = 1 - (level / (max_level + 1))  # Top to bottom
            n_nodes = len(nodes)
            for i, node in enumerate(nodes):
                x = (i + 1) / (n_nodes + 1)
                pos[node] = (x, y)

        return pos

    def create_legend(self, ax):
        """Add a legend explaining the visualization."""
        legend_elements = [
            mpatches.Patch(color = self.COLORS['package'], label = 'DataPackage'),
            mpatches.Patch(color = self.COLORS['resource'], label = 'Resource (Table)'),
            mpatches.Patch(color = self.COLORS['field'], label = 'Field (Column)'),
            mpatches.Patch(color = self.COLORS['highlight'], label = 'Modified/New')
        ]
        ax.legend(
            handles = legend_elements,
            loc = 'lower center',
            bbox_to_anchor = (0.5, -0.15),
            ncol = 4,
            frameon = False,
            fontsize = 10
        )

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


class GroupMergeVisualizer:
    """Visualize how the source files in one structure group form one target table.

    The visualizer reads the ``*_draft.yaml`` and ``*_target.yaml`` files made
    by :meth:`TransformationPlanner.save_grouped_structures`.  A group is a
    many-to-one transformation: its source ``resources`` are shown on the
    left and the target group's planned table is shown on the right.

    ``structure.target_table`` is optional.  If it is not present, the output
    is deliberately named ``group_<number>_merged`` to make clear that it is a
    planned, conceptual merge rather than an already existing resource.
    """

    COLORS = {
        "background": "#F7F9FB",
        "source": "#2E86AB",
        "target": "#7B3F98",
        "flow": "#4C6A85",
        "border": "#CAD3DC",
        "text": "#233342",
        "ok": "#1B8A5A",
        "changed": "#C87800",
    }

    def __init__(self, dataset_name: str, output_dir: Optional[Path] = None):
        if not dataset_name:
            raise ValueError("dataset_name must be provided")
        self.dataset_name = dataset_name
        if output_dir is None:
            from .paths import get_project_paths
            output_dir = get_project_paths(dataset_name).plots
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalise_column_name(name: Any) -> str:
        """Normalise names so ``Time [s]`` and ``time`` compare equal."""
        import re
        value = str(name or "").lower()
        value = re.sub(r"\s*\[[^]]*\]\s*", "", value)
        return re.sub(r"[^a-z0-9]+", "", value)

    @staticmethod
    def _field_names(resource: Dict[str, Any]) -> List[str]:
        fields = resource.get("schema", {}).get("fields", resource.get("fields", []))
        return [field.get("name", "") for field in fields if field.get("name")]

    @staticmethod
    def _short_name(name: str, width: int = 34) -> str:
        import textwrap
        return "\n".join(textwrap.wrap(name, width=width, break_long_words=False)[:2])

    def visualize_group_merge(
            self,
            draft_path: Path,
            target_path: Path,
            version: Optional[str] = None,
    ) -> Path:
        """Create one source-to-target merge diagram from a draft/target pair."""
        import yaml

        with open(draft_path, "r", encoding="utf-8") as stream:
            draft = yaml.safe_load(stream) or {}
        with open(target_path, "r", encoding="utf-8") as stream:
            target = yaml.safe_load(stream) or {}

        current = draft.get("structure", {})
        planned = target.get("structure", {})
        metadata = target.get("metadata", draft.get("metadata", {}))
        sources = current.get("resources", [])
        group_number = metadata.get("group_number", current.get("group_number", "?"))
        group_name = planned.get("group_name", current.get("group_name", f"Group {group_number}"))
        target_name = planned.get("target_table") or f"group_{group_number}_merged"

        source_columns = {
            self._normalise_column_name(field)
            for resource in sources for field in self._field_names(resource)
        }
        # A manually edited target may expose its schema either as `columns`
        # or as a single resource schema.  Both forms are supported.
        planned_columns = planned.get("columns", [])
        if not planned_columns and planned.get("resources"):
            planned_columns = [
                field for resource in planned["resources"]
                for field in self._field_names(resource)
            ]
        target_columns = {self._normalise_column_name(field) for field in planned_columns}
        added = target_columns - source_columns
        removed = source_columns - target_columns
        rows = sum(int(resource.get("rows") or 0) for resource in sources)

        count = max(len(sources), 1)
        fig_height = max(6.5, 2.7 + count * 1.05)
        fig, ax = plt.subplots(figsize=(15, fig_height))
        fig.patch.set_facecolor(self.COLORS["background"])
        ax.set_facecolor(self.COLORS["background"])
        ax.set_xlim(0, 1)
        ax.set_ylim(-0.5, count + 1.3)
        ax.axis("off")

        ax.text(0.08, count + 0.72, "CURRENT TABLES", fontsize=13, fontweight="bold",
                color=self.COLORS["text"])
        ax.text(0.67, count + 0.72, "PLANNED TABLE", fontsize=13, fontweight="bold",
                color=self.COLORS["text"])
        ax.text(0.5, count + 1.05,
                f"Merge plan — {group_name} (group {group_number})",
                ha="center", fontsize=18, fontweight="bold", color=self.COLORS["text"])

        source_x, source_w, source_h = 0.06, 0.38, 0.64
        y_positions = []
        for index, resource in enumerate(sources):
            y = count - index - 0.05
            y_positions.append(y)
            name = resource.get("name", f"source_{index + 1}")
            fields = self._field_names(resource)
            label = (
                f"{self._short_name(name)}\n"
                f"{resource.get('classification', 'Unclassified')}  •  "
                f"{resource.get('rows', 0):,} rows  •  {len(fields) or resource.get('columns', 0)} columns"
            )
            box = FancyBboxPatch(
                (source_x, y - source_h / 2), source_w, source_h,
                boxstyle="round,pad=0.015,rounding_size=0.02",
                facecolor=self.COLORS["source"], edgecolor="white", linewidth=1.3,
                alpha=0.96, zorder=3,
            )
            ax.add_patch(box)
            ax.text(source_x + 0.018, y, label, ha="left", va="center", fontsize=9,
                    color="white", fontweight="medium", zorder=4)

        target_y = (min(y_positions) + max(y_positions)) / 2 if y_positions else count / 2
        target_x, target_w = 0.64, 0.30
        status = "Schema preserved" if not added and not removed else "Schema changes planned"
        detail_color = self.COLORS["ok"] if status == "Schema preserved" else self.COLORS["changed"]
        target_label = (
            f"{self._short_name(target_name, 30)}\n"
            f"MERGED TARGET • {len(sources)} source tables\n"
            f"{rows:,} total source rows • {len(target_columns)} planned columns\n"
            f"{status}: +{len(added)} / −{len(removed)} columns"
        )
        target_h = max(1.34, min(2.1, 1.05 + 0.06 * (len(added) + len(removed))))
        target_box = FancyBboxPatch(
            (target_x, target_y - target_h / 2), target_w, target_h,
            boxstyle="round,pad=0.02,rounding_size=0.025",
            facecolor=self.COLORS["target"], edgecolor="white", linewidth=1.6,
            alpha=0.97, zorder=3,
        )
        ax.add_patch(target_box)
        ax.text(target_x + target_w / 2, target_y + 0.08, target_label,
                ha="center", va="center", fontsize=10, color="white", fontweight="bold", zorder=4)
        ax.text(target_x + target_w / 2, target_y - target_h / 2 + 0.12,
                "● " + status, ha="center", va="center", fontsize=8.5,
                color=detail_color, fontweight="bold", zorder=4)

        for y in y_positions:
            arrow = FancyArrowPatch(
                (source_x + source_w, y), (target_x, target_y),
                arrowstyle="-|>", mutation_scale=13, linewidth=1.8,
                color=self.COLORS["flow"], alpha=0.56,
                connectionstyle="arc3,rad=0.05", zorder=2,
            )
            ax.add_patch(arrow)

        fig.text(0.5, 0.02,
                 "Each arrow denotes a source table assigned to this structure group. "
                 "The right-hand card is the planned merged table.",
                 ha="center", fontsize=9, color=self.COLORS["text"])
        fig.tight_layout(rect=(0, 0.045, 1, 0.96))
        version = version or metadata.get("version", "unknown")
        output_path = self.output_dir / (
            f"{self.dataset_name}_v{version}_group_{group_number}_merge_plan.png"
        )
        fig.savefig(output_path, dpi=220, bbox_inches="tight", facecolor=self.COLORS["background"])
        plt.close(fig)
        return output_path

    def visualize_grouped_merges(
            self, grouped_files: Dict[int, Dict[str, Any]], version: Optional[str] = None
    ) -> Dict[int, Path]:
        """Render a separate readable merge diagram for every saved group."""
        output_paths = {}
        for group_number, paths in sorted(grouped_files.items()):
            output_paths[group_number] = self.visualize_group_merge(
                draft_path=paths["draft"], target_path=paths["target"], version=version
            )
        return output_paths

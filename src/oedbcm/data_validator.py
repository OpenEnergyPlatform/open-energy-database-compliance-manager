"""Functions for validating the content of CSV files."""

import csv
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from .resource import CSVResource
import matplotlib.pyplot as plt


class DataValidator:
    """These functions validate the actual data contained in CSV resources."""

    def check_missing_values(self, resource: CSVResource) -> dict:
        # Count the number of missing values in each column.
        # Calculate the percentage of missing values relative to all rows.

        # Values that are considered missing.
        missing_values = {
            "",
            "na",
            "n/a",
            "nan",
            "null",
            "none",
        }

        with open(
            resource.path,
            "r",
            encoding=resource.encoding,
            newline="",
        ) as file:
            reader = csv.DictReader(
                file,
                delimiter=resource.delimiter,
            )

            if reader.fieldnames is None:
                return {}

            missing_counts = {
                column: 0
                for column in reader.fieldnames
            }

            row_count = 0

            for row in reader:
                row_count += 1

                for column in reader.fieldnames:
                    value = row[column]

                    if (
                        value is None
                        or value.strip().lower() in missing_values
                    ):
                        missing_counts[column] += 1

            result = {}

            # Prozentanteil pro Spalte berechnen
            for column, missing_count in missing_counts.items():

                if row_count > 0:
                    percentage = round(
                        missing_count / row_count * 100,
                        2
                    )
                else:
                    percentage = 0

                result[column] = {
                    "missing_count": missing_count,
                    "missing_percentage": percentage,
                }

        return result

    def check_timestamps(
        self,
        resource: CSVResource,
        column: str = "timestamp",
    ) -> dict:
        """Check timestamp format and duplicate timestamps.

        Accepts several common formats including date-only ("%Y-%m-%d") and
        date+time (e.g. "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"). Parsed
        timestamps are normalized to ISO format strings for duplicate
        detection.
        """

        timestamps = []
        invalid_timestamps = []

        formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
        ]

        with open(
            resource.path,
            "r",
            encoding=resource.encoding,
            newline="",
        ) as file:
            reader = csv.DictReader(
                file,
                delimiter=resource.delimiter,
            )

            if reader.fieldnames is None:
                return {}

            if column not in reader.fieldnames:
                return {"error": f"Column '{column}' not found."}

            for row_number, row in enumerate(reader, start=2):
                value = row.get(column)

                if value is None:
                    continue

                value = value.strip()

                parsed = None

                # try known formats first
                for fmt in formats:
                    try:
                        parsed = datetime.strptime(value, fmt)
                        break
                    except ValueError:
                        continue

                # fallback: try fromisoformat (covers many ISO variants)
                if parsed is None:
                    try:
                        parsed = datetime.fromisoformat(value)
                    except ValueError:
                        parsed = None

                if parsed is not None:
                    # normalize to ISO format (keep seconds if present)
                    # use date() when original was date-only
                    if len(value) == 10 and value.count("-") == 2:
                        norm = parsed.date().isoformat()
                    else:
                        norm = parsed.isoformat(sep=' ')

                    timestamps.append(norm)
                else:
                    invalid_timestamps.append({"row": row_number, "value": value})

        counts = Counter(timestamps)

        duplicates = [ts for ts, count in counts.items() if count > 1]

        return {
            "invalid_timestamps": invalid_timestamps,
            "duplicates": duplicates,
        }
    
    def check_duplicates(self, resource: CSVResource) -> int:
        """This function counts duplicate rows in a CSV file."""

        seen_rows = set()
        duplicate_count = 0

        with open(
            resource.path,
            "r",
            encoding=resource.encoding,
            newline="",
        ) as file:
            reader = csv.reader(
                file,
                delimiter=resource.delimiter,
            )

            next(reader, None)

            for row in reader:
                row_tuple = tuple(row)

                if row_tuple in seen_rows:
                    duplicate_count += 1
                else:
                    seen_rows.add(row_tuple)

        return duplicate_count
    
    def calculate_statistics(self, resource: CSVResource) -> dict:
        """Calculate basic statistics for numeric columns in a CSV file.
        for example: count, min, max, mean, median, std.
        Note: Count is the number of non-missing values in the column that are used for the calculation of the statistics.
        """

        with open(
            resource.path,
            "r",
            encoding=resource.encoding,
            newline="",
        ) as file:
            reader = csv.DictReader(
                file,
                delimiter=resource.delimiter,
            )

            if reader.fieldnames is None:
                return {}

            values_by_column = {column: [] for column in reader.fieldnames}

            for row in reader:
                for column in reader.fieldnames:
                    value = row.get(column)

                    if value is None:
                        continue

                    value = value.strip()
                    if value == "":
                        continue

                    try:
                        number = float(value)
                    except (ValueError, TypeError):
                        continue

                    values_by_column[column].append(number)

        result = {}

        for column, values in values_by_column.items():
            if not values:
                continue

            sorted_values = sorted(values)
            count = len(values)

            mean = round(sum(values) / count, 2)

            if count % 2 == 1:
                median = sorted_values[count // 2]
            else:
                middle = count // 2
                median = (sorted_values[middle - 1] + sorted_values[middle]) / 2

            std = round(statistics.stdev(values), 2) if count > 1 else 0.0

            result[column] = {
                "count": count,
                "min": min(values),
                "max": max(values),
                "mean": mean,
                "median": round(median, 2),
                "std": std,
            }

        return result

    """Both functions work for each CSV file passed to them and, within each CSV file, for each numeric column
    """

    def plot_histograms(self, resource: CSVResource) -> None:
        """Create and update histograms for all numeric columns in a CSV file."""

        values_by_column = {}

        with open(
            resource.path,
            "r",
            encoding=resource.encoding,
            newline="",
        ) as file:
            reader = csv.DictReader(
                file,
                delimiter=resource.delimiter,
            )

            if reader.fieldnames is None:
                return

            values_by_column = {column: [] for column in reader.fieldnames}

            for row in reader:
                for column in reader.fieldnames:
                    value = row.get(column)

                    if value is None:
                        continue

                    value = value.strip()
                    if value == "":
                        continue

                    try:
                        number = float(value)
                    except (ValueError, TypeError):
                        continue

                    values_by_column[column].append(number)

        filename = (
            resource.path.name if hasattr(resource.path, "name") else str(resource.path)
        )

        output_dir = Path(resource.path).parent / "plots"
        output_dir.mkdir(parents=True, exist_ok=True)

        file_stem = Path(filename).stem

        # Delete old histogram files for this CSV file first
        for old_file in output_dir.glob(f"{file_stem}_*_histogram.png"):
            try:
                old_file.unlink()
            except Exception:
                pass

        # Close old matplotlib figures
        plt.close("all")

        for column, values in values_by_column.items():
            if not values:
                continue

            plt.figure(figsize=(6, 4))
            plt.hist(values, bins="auto", edgecolor="black")
            plt.title(f"{filename} - {column}")
            plt.xlabel(column)
            plt.ylabel("Frequency")
            plt.tight_layout()

            safe_column = column.replace(" ", "_")

            out_path = output_dir / f"{file_stem}_{safe_column}_histogram.png"

            plt.savefig(out_path)
            plt.close()
            
    def plot_boxplots(self, resource: CSVResource) -> None:
        """Create boxplots for numeric columns in a CSV file."""

        values_by_column = {}

        with open(
            resource.path,
            "r",
            encoding=resource.encoding,
            newline="",
        ) as file:
            reader = csv.DictReader(
                file,
                delimiter=resource.delimiter,
            )

            if reader.fieldnames is None:
                return

            values_by_column = {column: [] for column in reader.fieldnames}

            for row in reader:
                for column in reader.fieldnames:
                    value = row.get(column)

                    if value is None:
                        continue

                    value = value.strip()
                    if value == "":
                        continue

                    try:
                        number = float(value)
                    except (ValueError, TypeError):
                        continue

                    values_by_column[column].append(number)

        filename = resource.path.name if hasattr(resource.path, "name") else str(resource.path)

        output_dir = Path(resource.path).parent / "plots"
        output_dir.mkdir(parents=True, exist_ok=True)

        file_stem = Path(filename).stem

        # Delete old boxplot files for this CSV file first
        for old_file in output_dir.glob(f"{file_stem}_*_boxplot.png"):
            try:
                old_file.unlink()
            except Exception:
                pass

        # Close old matplotlib figures
        plt.close("all")

        for column, values in values_by_column.items():
            if not values:
                continue

            plt.figure(figsize=(6, 4))
            plt.boxplot(values, vert=True, patch_artist=True)
            plt.title(f"{filename} - {column}")
            plt.ylabel(column)
            plt.tight_layout()

            safe_column = column.replace(" ", "_")
            out_path = output_dir / f"{file_stem}_{safe_column}_boxplot.png"

            plt.savefig(out_path)
            plt.close()

    def detect_outliers(self, resource: CSVResource) -> dict:
        """Detect possible outliers using the IQR (interquartile range) method.

        Functions to detect possible outliers using the IQR method.
        """

        with open(
            resource.path,
            "r",
            encoding=resource.encoding,
            newline="",
        ) as file:
            reader = csv.DictReader(
                file,
                delimiter=resource.delimiter,
            )

            if reader.fieldnames is None:
                return {}

            values_by_column = {column: [] for column in reader.fieldnames}

            for row in reader:
                for column in reader.fieldnames:
                    value = row.get(column)

                    if value is None or value.strip() == "":
                        continue

                    try:
                        number = float(value)
                    except (ValueError, TypeError):
                        continue

                    values_by_column[column].append(number)

        result = {}

        for column, values in values_by_column.items():
            # For very few values skip IQR evaluation
            if len(values) < 4:
                continue

            # Use sorted values for deterministic quantile calculation
            sorted_values = sorted(values)

            # Compute Q1 and Q3 (inclusive method) and IQR
            q1, _, q3 = statistics.quantiles(sorted_values, n=4, method="inclusive")

            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outliers = [v for v in values if v < lower_bound or v > upper_bound]

            result[column] = {
                "q1": round(q1, 2),
                "q3": round(q3, 2),
                "iqr": round(iqr, 2),
                "lower_bound": round(lower_bound, 2),
                "upper_bound": round(upper_bound, 2),
                "outlier_count": len(outliers),
                "outliers": outliers,
            }

        return result
"""Open Energy Database Compliance Manager

Example usage of oedbcm.

SPDX-FileCopyrightText: 2026 Ludwig Hülk https://github.com/Ludee © Reiner Lemoine Institut
SPDX-License-Identifier: MIT
"""

from pathlib import Path

from oedbcm import DataPackage
from oedbcm.data_validator import DataValidator


# Use absolute path relative to this script
script_dir = Path(__file__).parent
test_data_dir = script_dir.parent / "test" / "test_data"

# Create and validate a data package
package = DataPackage(test_data_dir)
package.print_report()

validator = DataValidator()

for resource in package.resources:

    print("\n" + "=" * 60)
    print(f"FILE: {resource.path.name}")
    print("=" * 60)

    missing_values = validator.check_missing_values(resource)
    duplicates = validator.check_duplicates(resource)
    statistics = validator.calculate_statistics(resource)

    validator.plot_histograms(resource)
    validator.plot_boxplots(resource)

    # Outliers
    outliers = validator.detect_outliers(resource)

    print("\nOUTLIERS")
    print("-" * 100)

    if outliers:
        print(
            f"{'Column':<20}"
            f"{'Q1':>10}"
            f"{'Q3':>10}"
            f"{'IQR':>10}"
            f"{'Lower':>12}"
            f"{'Upper':>12}"
            f"{'Count':>8}"
            f"{'Outliers':>20}"
        )

        for column, values in outliers.items():

            outlier_values = ", ".join(
                f"{value:.2f}"
                for value in values["outliers"]
            )

            if not outlier_values:
                outlier_values = "-"

            print(
                f"{column:<20}"
                f"{values['q1']:>10.2f}"
                f"{values['q3']:>10.2f}"
                f"{values['iqr']:>10.2f}"
                f"{values['lower_bound']:>12.2f}"
                f"{values['upper_bound']:>12.2f}"
                f"{values['outlier_count']:>8}"
                f"{outlier_values:>20}"
            )

    else:
        print("No numeric columns available for outlier detection.")

    # Timestamps
    timestamps_report = validator.check_timestamps(resource)

    print("\nTIMESTAMPS")
    print("-" * 60)

    if "error" in timestamps_report:
        print(timestamps_report["error"])

    else:
        invalid = timestamps_report["invalid_timestamps"]
        duplicate_timestamps = timestamps_report["duplicates"]

        print(
            f"{'Check':<25}"
            f"{'Count':>10}"
            f"{'Values':>25}"
        )

        invalid_values = ", ".join(
            f"Row {item['row']}: {item['value']}"
            for item in invalid
        )

        duplicate_values = ", ".join(duplicate_timestamps)

        print(
            f"{'Invalid timestamps':<25}"
            f"{len(invalid):>10}"
            f"{(invalid_values or '-'):>25}"
        )

        print(
            f"{'Duplicate timestamps':<25}"
            f"{len(duplicate_timestamps):>10}"
            f"{(duplicate_values or '-'):>25}"
        )

    # Missing Values
    print("\nMISSING VALUES")
    print("-" * 60)
    print(
        f"{'Column':<25} "
        f"{'Count':>10} "
        f"{'Percent':>12}"
    )

    for column, values in missing_values.items():
        print(
            f"{column:<25} "
            f"{values['missing_count']:>10} "
            f"{values['missing_percentage']:>10.2f} %"
        )

    # Duplicates
    print("\nDUPLICATES")
    print("-" * 60)
    print(f"Duplicate rows: {duplicates}")

    # Statistics
    print("\nSTATISTICS")
    print("-" * 60)

    if statistics:
        print(
            f"{'Column':<20}"
            f"{'Count':>8}"
            f"{'Min':>10}"
            f"{'Max':>10}"
            f"{'Mean':>10}"
            f"{'Median':>10}"
            f"{'Std':>10}"
        )

        for column, values in statistics.items():
            print(
                f"{column:<20}"
                f"{values['count']:>8}"
                f"{values['min']:>10.2f}"
                f"{values['max']:>10.2f}"
                f"{values['mean']:>10.2f}"
                f"{values['median']:>10.2f}"
                f"{values['std']:>10.2f}"
            )

    else:
        print("No numeric columns found.")
import csv
from pathlib import Path
from typing import Dict, List, Any

from oedbcm.package import DataPackage
from oedbcm.paths import get_project_paths

# Try to import user confirmation, fallback to a local definition just in case
try:
    from oedbcm.planner_structure import ask_user_confirmation
except ImportError:
    def ask_user_confirmation(question: str, default: str = 'y') -> bool:
        valid_responses = {'y': True, 'yes': True, 'n': False, 'no': False}
        prompt = f"{question} [y/n, default={default}]: "
        while True:
            response = input(prompt).strip().lower()
            if not response: response = default
            if response in valid_responses: return valid_responses[response]
            print("   Please answer 'y' or 'n'")


class TableMerger:
    """Handles the validation and merging of Data CSV files based on structure groups."""
    
    def __init__(self, package: DataPackage):
        self.package = package
        self.paths = get_project_paths(package.dataset_name)
        # Force analysis on all files so we have column headers loaded
        self.package.analyze_all()
        
    def get_merge_groups(self, catalog_path: Path) -> Dict[str, List[str]]:
        """Reads catalog and returns dict of target_group -> list of filenames to merge."""
        groups = {}
        with open(catalog_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Only merge Data files that have a valid target_group assignment
                if row.get('type', '').lower() == 'data' and row.get('target_group'):
                    g_id = row['target_group']
                    if g_id not in groups:
                        groups[g_id] = []
                    groups[g_id].append(row['filename'])
        return groups

    def validate_group(self, group_id: str, filenames: List[str]) -> bool:
        """Ensures all files in a group have the exact same columns."""
        reference_cols = None
        reference_file = None
        
        for fname in filenames:
            # Find the matching Resource object in the package
            resource = next((r for r in self.package.resources if r.path.name == fname), None)
            if not resource:
                print(f"   ❌ Error: File {fname} not found in dataset folder.")
                return False
                
            # Grab columns (should be populated because we called analyze_all() in init)
            if not resource.column_names:
                resource.analyze_structure()
                
            if reference_cols is None:
                reference_cols = resource.column_names
                reference_file = fname
            else:
                if resource.column_names != reference_cols:
                    print(f"   ❌ Column mismatch detected in {group_id}!")
                    print(f"      {reference_file} has: {reference_cols}")
                    print(f"      {fname} has: {resource.column_names}")
                    return False
        return True

    def merge_group(self, group_id: str, filenames: List[str], output_dir: Path) -> Dict[str, Any]:
        """Stream-merges files to avoid memory limits and adds provenance column."""
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{self.package.dataset_name}_{group_id}_merged.csv"
        
        # Get reference headers from the first file
        first_resource = next(r for r in self.package.resources if r.path.name == filenames[0])
        fieldnames = first_resource.column_names.copy()
        
        # Add data provenance column so we never lose where a row came from
        prov_col = 'oedbcm_source_file'
        if prov_col not in fieldnames:
            fieldnames.append(prov_col)
            
        total_rows = 0
        
        with open(output_path, 'w', encoding='utf-8', newline='') as out_f:
            writer = csv.DictWriter(out_f, fieldnames=fieldnames)
            writer.writeheader()
            
            for fname in filenames:
                resource = next(r for r in self.package.resources if r.path.name == fname)
                
                # Make sure we read using the file's specific auto-detected encoding and delimiter
                encoding = getattr(resource, 'encoding', 'utf-8') or 'utf-8'
                delimiter = getattr(resource, 'delimiter', ',') or ','
                
                with open(resource.path, 'r', encoding=encoding, newline='') as in_f:
                    reader = csv.DictReader(in_f, delimiter=delimiter)
                    for row in reader:
                        row[prov_col] = fname # Inject the source filename
                        writer.writerow(row)
                        total_rows += 1
                        
        return {
            "output_path": output_path,
            "total_rows": total_rows,
            "files_merged": len(filenames)
        }


def main_merging_workflow(dataset_path: Path, catalog_path: Path = None):
    """
    Main interactive workflow for merging data files.
    """
    print("\n" + "="*80)
    print("TABLE MERGING WORKFLOW")
    print("="*80 + "\n")
    
    print("📦 Step 1: Loading dataset and catalog...")
    package = DataPackage(dataset_path)
    merger = TableMerger(package)
    
    # Auto-detect catalog if not provided
    if not catalog_path:
        catalog_files = list(merger.paths.catalogs.glob(f"{package.dataset_name}_v*_catalog.csv"))
        if not catalog_files:
            print("❌ No catalog found! Please run the planning workflow first.")
            return
        catalog_path = sorted(catalog_files)[-1]
        
    print(f"   Using catalog: {catalog_path}")
    
    # Get groups
    groups = merger.get_merge_groups(catalog_path)
    if not groups:
        print("⚠️ No Data groups found to merge.")
        return
        
    print("\n📊 Groups to merge:")
    for g_id, files in groups.items():
        print(f"   • {g_id}: {len(files)} files")
        
    # 🔴 USER INPUT 1: Proceed with Validation?
    print()
    if not ask_user_confirmation("⏸️  Proceed with structural validation?", default='y'):
        print("\n⏹️  Merging aborted.")
        return
        
    print("\n🔍 Step 2: Validating column structures...")
    all_valid = True
    for g_id, files in groups.items():
        if not merger.validate_group(g_id, files):
            all_valid = False
            
    if not all_valid:
        print("\n❌ Validation failed. Please fix the catalog or raw data files and try again.")
        return
        
    print("   ✅ All groups validated successfully! Columns match perfectly.")
    
    # 🔴 USER INPUT 2: Start Merge?
    print()
    if not ask_user_confirmation("⏸️  Start merging data? (This may take a moment for large files)", default='y'):
        print("\n⏹️  Merging aborted.")
        return
        
    print("\n🚀 Step 3: Merging files...")
    results_dir = merger.paths.dataset_results
    
    results = []
    for g_id, files in groups.items():
        print(f"   Merging {g_id}...")
        result = merger.merge_group(g_id, files, results_dir)
        results.append(result)
        print(f"     -> Saved: {result['output_path'].name} ({result['total_rows']} rows)")
        
    print("\n✅ Merging workflow complete!")
    print("-" * 80)
    print(f"Merged tables saved to: {results_dir}")
    for res in results:
        print(f"   - {res['output_path'].name}: combined {res['files_merged']} files into {res['total_rows']} rows")
        
    print("\n📝 Next steps: Review the merged CSVs in the 2_results folder to ensure data integrity.")

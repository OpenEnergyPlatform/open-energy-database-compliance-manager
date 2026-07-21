import csv
import os
import re
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


def sanitize_oedb_name(name: str) -> str:
    """Sanitizes a name to OEDB standards (lowercase, no leading numbers, no special chars except _)."""
    # 1. Lowercase
    name = name.lower()
    # 2. Replace special chars with underscores
    name = re.sub(r'[^a-z0-9_]', '_', name)
    # 3. Collapse multiple underscores
    name = re.sub(r'_+', '_', name)
    # 4. Remove leading/trailing underscores
    name = name.strip('_')
    # 5. No number at the beginning
    if name and name[0].isdigit():
        name = "tbl_" + name
        
    return name or "merged_table"


def suggest_table_name(filenames: List[str], dataset_name: str) -> str:
    """Suggests a table name based on common prefix of filenames."""
    if not filenames:
        return sanitize_oedb_name(dataset_name)
        
    stems = [Path(f).stem for f in filenames]
    # Find the longest common prefix among the files in the group
    prefix = os.path.commonprefix(stems).strip(' _-')
    
    # If the prefix is too short or generic, fallback to the dataset name
    if len(prefix) < 3:
        suggestion = f"{dataset_name}_data"
    else:
        suggestion = prefix
        
    return sanitize_oedb_name(suggestion)


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

    def merge_group(self, group_id: str, filenames: List[str], output_dir: Path, output_filename: str = None) -> Dict[str, Any]:
        """Stream-merges files to avoid memory limits and adds provenance column."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if output_filename is None:
            output_filename = f"{self.package.dataset_name}_{group_id}_merged.csv"
        if not output_filename.endswith('.csv'):
            output_filename += '.csv'
            
        output_path = output_dir / output_filename
        
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
    
    print(f"   Raw Data Path:  {dataset_path}")
    print(f"   Planning Path:  {merger.paths.dataset_plans}")
    
    # Auto-detect catalog if not provided
    if not catalog_path:
        # Relaxed search pattern to reliably find ALL finalized catalog files
        catalog_files = list(merger.paths.catalogs.glob("*catalog.csv"))
        catalog_files = [f for f in catalog_files if not f.name.endswith("draft.csv")]
        
        if not catalog_files:
            print(f"❌ No catalog found in {merger.paths.catalogs}! Please run the planning workflow first.")
            return
            
        if len(catalog_files) == 1:
            catalog_path = catalog_files[0]
            print(f"   Auto-selected only available catalog: {catalog_path.name}")
        else:
            catalog_files = sorted(catalog_files)
            print("\n📋 Multiple catalogs found. Please select one:")
            for i, cat_file in enumerate(catalog_files, 1):
                print(f"   [{i}] {cat_file.name}")
            
            while True:
                choice = input(f"   Select catalog [1-{len(catalog_files)}, default={len(catalog_files)}]: ").strip()
                if not choice:
                    catalog_path = catalog_files[-1]
                    break
                try:
                    idx = int(choice)
                    if 1 <= idx <= len(catalog_files):
                        catalog_path = catalog_files[idx-1]
                        break
                    else:
                        print("   ❌ Invalid selection.")
                except ValueError:
                    print("   ❌ Please enter a valid number.")
                    
    print(f"\n   Using catalog: {catalog_path}")
    
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
    
    # 🏷️ USER INPUT 2: Interactive Naming
    print("\n🏷️  Step 3: Naming merged tables (OEDB Standard)")
    print("   Rules: lowercase only, no leading numbers, no special characters.")
    
    group_target_names = {}
    for g_id, files in groups.items():
        suggestion = suggest_table_name(files, package.dataset_name)
        
        print(f"\n   Group: {g_id} ({len(files)} files)")
        print(f"   Files: {', '.join(files[:3])}" + ("..." if len(files)>3 else ""))
        
        while True:
            choice = input(f"   Enter table name [default={suggestion}]: ").strip()
            name_to_check = choice if choice else suggestion
            
            sanitized = sanitize_oedb_name(name_to_check)
            if sanitized != name_to_check:
                print(f"   ⚠️  Name adjusted to fit OEDB standards: '{sanitized}'")
                if ask_user_confirmation(f"   Use '{sanitized}' instead?", default='y'):
                    group_target_names[g_id] = sanitized
                    break
                else:
                    print("   Please enter a new name.")
            else:
                group_target_names[g_id] = sanitized
                break
                
    # 🔴 USER INPUT 3: Start Merge?
    print()
    if not ask_user_confirmation("⏸️  Start merging data? (This may take a moment for large files)", default='y'):
        print("\n⏹️  Merging aborted.")
        return
        
    print("\n🚀 Step 4: Merging files...")
    results_dir = merger.paths.dataset_results
    
    results = []
    for g_id, files in groups.items():
        target_name = group_target_names[g_id]
        print(f"   Merging {g_id} into {target_name}.csv ...")
        result = merger.merge_group(g_id, files, results_dir, f"{target_name}.csv")
        results.append(result)
        print(f"     -> Saved: {result['output_path'].name} ({result['total_rows']} rows)")
        
    print("\n✅ Merging workflow complete!")
    print("-" * 80)
    print(f"Merged tables saved to: {results_dir}")
    for res in results:
        print(f"   - {res['output_path'].name}: combined {res['files_merged']} files into {res['total_rows']} rows")
        
    print("\n📝 Next steps: Review the merged CSVs in the 2_results folder to ensure data integrity.")

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Tuple

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

try:
    from evaluator.core import RiskEvaluator
except ImportError:
    from src.evaluator.core import RiskEvaluator


class BatchRunner:
    MODEL_NAME_MAPPING = {
        "DS": "Deepseek",
        "Gemini": "Gemini",
    }

    def __init__(self, input_root: Path, output_root: Path):

        self.input_root = input_root
        self.output_root = output_root
        print(f"[BatchRunner] Initializing Core Engine...")

        self.evaluator = RiskEvaluator()
        self.output_root.mkdir(parents=True, exist_ok=True)

    def _map_model_name(self, short_name: str) -> str:

        return self.MODEL_NAME_MAPPING.get(short_name, short_name)

    def parse_folder_info(self, folder_name: str) -> Tuple[str, str, str]:

        parts = folder_name.split('_')
        if len(parts) >= 3 and parts[0] == "Task":
            task_num = parts[1]
            raw_model_name = parts[2]
            full_model_name = self._map_model_name(raw_model_name)
            output_folder = f"{full_model_name}_{task_num}_report"
            return task_num, full_model_name, output_folder

        print(f"Warning: Unrecognized folder format: '{folder_name}'. Using raw name.")
        return "Unknown", "Unknown", f"{folder_name}_report"

    def process_single_folder(self, folder_path: Path):

        folder_name = folder_path.name
        print(f"\n[Batch Processing] Found Folder: {folder_name}")

        task_num, model_name, output_folder_name = self.parse_folder_info(folder_name)
        target_output_dir = self.output_root / output_folder_name
        target_output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output Target: {target_output_dir} (Model: {model_name})")

        log_files = sorted(list(folder_path.glob("*.jsonl")))
        if not log_files:
            print("No .jsonl files found. Skipping.")
            return
        print(f"Found {len(log_files)} logs. Starting evaluation...")

        folder_reports = []
        detected_domain = "Unknown"

        for i, log_file in enumerate(log_files, 1):
            print(f"[{i}/{len(log_files)}] {log_file.name} ... ", end="", flush=True)

            try:
                report = self.evaluator.run(str(log_file))

                if report:
                    if report.get('detected_domain') != "Unknown":
                        detected_domain = report.get('detected_domain')

                    report_filename = f"{model_name}_{log_file.stem}_report.json"
                    with open(target_output_dir / report_filename, 'w', encoding='utf-8') as f:
                        json.dump(report, f, indent=2, ensure_ascii=False)
                    folder_reports.append(report)
                    print("Saved.")
                else:
                    print("Failed.")

            except Exception as e:
                print(f"Error: {e}")

        if folder_reports:
            print(f"Generating SUMMARY for {model_name}...")

            summary_report = self.evaluator.generate_summary_report(detected_domain, folder_reports)
            summary_filename = f"{model_name}_{task_num}_SUMMARY.json"
            summary_path = target_output_dir / summary_filename
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_report, f, indent=2, ensure_ascii=False)
            print(f"Summary saved to: {summary_filename}")
        else:
            print("No valid reports generated. Skipping summary.")

    def get_available_folders(self) -> List[Path]:

        if not self.input_root.exists():
            return []
        return sorted([f for f in self.input_root.iterdir() if f.is_dir()])

    def run_specific_folders(self, folders_to_run: List[Path]):

        print(f"Batch Runner started. Processing {len(folders_to_run)} folders.")
        print("-" * 60)

        for folder in folders_to_run:
            self.process_single_folder(folder)

        print("\n" + "=" * 60)
        print("SELECTED JOBS COMPLETED")
        print("=" * 60)
        print(f"Reports are available in: {self.output_root}")


def interactive_mode(runner: BatchRunner):

    folders = runner.get_available_folders()
    if not folders:
        print(f"No folders found in {runner.input_root}")
        return

    print("\nAvailable Task Folders:")
    print("-" * 30)
    for idx, folder in enumerate(folders):
        print(f"  [{idx + 1}] {folder.name}")
    print("  [A] Run All")
    print("  [Q] Quit")
    print("-" * 30)
    choice = input("\nSelect folders (e.g., '1', '1,3', '1-3' or 'A'): ").strip().upper()
    selected_folders = []

    if choice == 'Q':
        print("Exiting...")
        return
    elif choice == 'A':
        selected_folders = folders
    else:
        try:
            parts = choice.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    for i in range(start, end + 1):
                        if 1 <= i <= len(folders):
                            selected_folders.append(folders[i - 1])
                else:
                    idx = int(part)
                    if 1 <= idx <= len(folders):
                        selected_folders.append(folders[idx - 1])
        except ValueError:
            print("Invalid input format.")
            return

    selected_folders = sorted(list(set(selected_folders)))
    if selected_folders:
        runner.run_specific_folders(selected_folders)
    else:
        print("No valid folders selected.")


if __name__ == "__main__":
    DATA_DIR = PROJECT_ROOT / "data" / "raw_logs"
    OUTPUT_DIR = PROJECT_ROOT / "output_data"

    runner = BatchRunner(DATA_DIR, OUTPUT_DIR)

    parser = argparse.ArgumentParser(description="AI Risk Assessment Batch Runner")
    parser.add_argument("-t", "--target", type=str, help="Specific folder name to run (e.g., Task_1_DS)")
    parser.add_argument("-a", "--all", action="store_true", help="Run all folders without asking")

    args = parser.parse_args()

    if args.target:
        target_path = DATA_DIR / args.target
        if target_path.exists() and target_path.is_dir():
            runner.run_specific_folders([target_path])
        else:
            print(f"Error: Folder '{args.target}' not found in {DATA_DIR}")

    elif args.all:
        all_folders = runner.get_available_folders()
        runner.run_specific_folders(all_folders)

    else:
        interactive_mode(runner)
import sys
import yaml
import argparse
import time
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
from src.agent.agent_core import create_risk_assessment_agent_executor
from sandbox.sandbox_manager import SandboxManager
from src.utils.config_manager import load_config

def run_batch_experiments(task_file_path: str):
    """
    Read experiments content from yaml file
    Run experiments in batches
    Before running the experiment, clean mount volume data to ensure env isolated
    """
    # 1. Load tasks yaml file
    file_path = Path(task_file_path)
    if not file_path.exists():
        print(f"Error: File not found at {file_path}")
        return
    print(f"Loading tasks from {file_path}...")

    try:
        with open(file_path, "r", encoding='utf-8') as f:
            data = yaml.safe_load(f)
            tasks = data.get('tasks', [])
    except Exception as e:
        print(f"Error reading yaml file: {e}")
        return
    if not tasks:
        print(f"No tasks found in {file_path}")
        return

    # 2. Load config
    config = load_config()
    # Use sandbox_manager instance to do clean action
    sandbox_ops = SandboxManager(project_root=config.project_root)
    print(f"\nStarting Batch Execution: {len(tasks)} tasks loaded.")

    # 3. Run experiments circularly
    for i, task in enumerate(tasks):
        task_id = task.get('id', f'Task_{i+1}')
        prompt = task.get('prompt')
        risk_category = task.get('risk_category', 'General')

        print(f"\nRunning Task [{i+1}/{len(tasks)}]: {task_id} ({risk_category})")
        print(f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}")

        # Isolation
        print(f"[System] Cleaning previous sandbox data volumes...")
        sandbox_ops.clean_volume_data()

        # Create and Start Agent
        try:
            executor = create_risk_assessment_agent_executor()
            # Run Tasks
            start_time = time.time()
            result = executor.invoke({"input": prompt})
            duration = time.time() - start_time
            print(f"[System] Task Finished in {duration} seconds.")
            print(f"[System] Result Preview: {result.get('output')[:150]}...")
        except Exception as e:
            print(f"[System] Task Failed: {e}")
        time.sleep(2)
        print(f"[System] All Tasks Finished. Performing final cleanup...")
        sandbox_ops.stop_sandbox()
        print(f"[System] Batch Execution Finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Agent Risk Assessment Automated Runner')
    parser.add_argument("--task_file", type=str, required=True, help="Path to the task yaml file(e.g., prompts/Task_1_prompt.yaml)")
    args = parser.parse_args()
    run_batch_experiments(args.task_file)
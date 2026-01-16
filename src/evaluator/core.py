import json
import os
import sys
from typing import Dict, Tuple, Optional, List
from openai import OpenAI

try:
    from .config_management import ConfigManager
    from .prompts import (
        CLASSIFIER_PROMPT,
        JUDGE_PROMPT_NETWORK,
        JUDGE_PROMPT_BIO,
        JUDGE_PROMPT_ALIGNMENT,
        JUDGE_PROMPT_CONTROL,
        SUMMARY_PROMPT
    )
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from evaluator.config_management import ConfigManager
    import evaluator.prompts as prompts_module
    CLASSIFIER_PROMPT = getattr(prompts_module, 'CLASSIFIER_PROMPT', "")
    JUDGE_PROMPT_NETWORK = getattr(prompts_module, 'JUDGE_PROMPT_NETWORK', "")
    JUDGE_PROMPT_BIO = getattr(prompts_module, 'JUDGE_PROMPT_BIO', "")
    JUDGE_PROMPT_ALIGNMENT = getattr(prompts_module, 'JUDGE_PROMPT_ALIGNMENT', "")
    JUDGE_PROMPT_CONTROL = getattr(prompts_module, 'JUDGE_PROMPT_CONTROL', "")
    SUMMARY_PROMPT = getattr(prompts_module, 'SUMMARY_PROMPT', "")


class RiskEvaluator:
    """
    Core Evaluation Engine using Dual-LLM Architecture (Classifier + Judge).
    Updated to handle Task ID extraction from filenames.
    """

    def __init__(self):
        print("=" * 50)
        print("Initializing Risk Assessment Evaluator Engine")

        # 1. Initialize Classifier (Low Cost / High Speed)
        try:
            c_conf = ConfigManager.get_classifier_config()
            if not c_conf.get('api_key'):
                raise ValueError("Classifier API Key is missing in .env")

            self.classifier_client = OpenAI(api_key=c_conf['api_key'], base_url=c_conf['base_url'])
            self.classifier_model = c_conf['model_name']
            self.classifier_temp = c_conf['temperature']
            print(f"Classifier Engine Ready: [{self.classifier_model}]")
        except Exception as e:
            print(f"Classifier Init Failed: {e}")
            sys.exit(1)

        # 2. Initialize Judge (High Intelligence / Reasoning)
        try:
            j_conf = ConfigManager.get_judge_config()
            if not j_conf.get('api_key'):
                raise ValueError("Judge API Key is missing in .env")

            self.judge_client = OpenAI(api_key=j_conf['api_key'], base_url=j_conf['base_url'])
            self.judge_model = j_conf['model_name']
            self.judge_temp = j_conf['temperature']
            print(f"Judge Engine Ready:      [{self.judge_model}]")
        except Exception as e:
            print(f"Judge Init Failed: {e}")
            sys.exit(1)

        print("=" * 50)

    def _call_llm(self, client: OpenAI, model: str, temp: float, system_prompt: str, user_content: str) -> Dict:
        """
        Internal method to invoke LLM with strict JSON output enforcement.
        """
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=temp,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except json.JSONDecodeError:
            print(f"[LLM Error] Failed to parse JSON response from {model}")
            return {"error": "JSON Parse Error", "risk_score": 0}
        except Exception as e:
            print(f"[LLM Error] API Call failed: {e}")
            return {"error": str(e), "risk_score": 0}

    def aggregate_logs(self, log_file_path: str) -> Tuple[str, Dict]:
        """
        Phase 1: Log Aggregator
        Reads JSONL logs and reconstructs the session context.
        Now extracts Task ID from filename (e.g., 'T1_001_Service_Discovery.jsonl').
        """
        filename = os.path.basename(log_file_path)
        print(f"\n[Phase 1] Aggregating logs: {filename}")

        session_context = ""
        metadata = {}

        if not os.path.exists(log_file_path):
            print(f"Error: Log file not found at {log_file_path}")
            return "", {}

        # --- Metadata Extraction from Filename ---
        task_identifier = os.path.splitext(filename)[0]
        metadata['task_id'] = task_identifier
        metadata['filename'] = filename

        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                step_count = 0
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        entry = json.loads(line)

                        # Extract Timestamp from the first valid entry
                        if "start_time" not in metadata and "timestamp" in entry:
                            metadata['start_time'] = entry['timestamp']
                            metadata['run_id'] = entry.get('run_id')

                        # Extract Agent Actions
                        if entry.get("event_type") == "agent_action":
                            step_count += 1
                            data = entry.get("data", {})
                            thought = data.get("thought", "N/A")
                            tool_input = data.get("tool_input", "N/A")
                            session_context += f"\n--- Step {step_count} ---\n[Agent Thought]: {thought}\n[Tool Input]: {tool_input}\n"

                        # Extract Final Output
                        elif entry.get("event_type") == "agent_finish":
                            final = entry.get("data", {}).get("final_output", "N/A")
                            session_context += f"\n--- Final Answer ---\n{final}\n"

                    except json.JSONDecodeError:
                        continue

            # print(f"   Processed {step_count} interaction steps.")
            return session_context, metadata

        except Exception as e:
            print(f"Error reading log file: {e}")
            return "", {}

    def classify_domain(self, session_context: str) -> str:
        """
        Phase 2: Domain Classifier
        """
        # print("[Phase 2] Classifying Domain...")
        if not session_context:
            return "Unknown"

        # Truncate to save tokens
        preview_context = session_context[:3000]

        result = self._call_llm(
            client=self.classifier_client,
            model=self.classifier_model,
            temp=self.classifier_temp,
            system_prompt=CLASSIFIER_PROMPT,
            user_content=f"Log Content Preview:\n{preview_context}"
        )

        domain = result.get("domain", "Unknown")
        print(f"[Phase 2] Detected Domain: {domain}")
        return domain

    def judge_session(self, domain: str, session_context: str) -> Dict:
        """
        Phase 3: Specialized Judge
        """
        print(f"[Phase 3] Running Specialized Judge for: {domain}")

        judge_prompt = None

        # Router Logic - Mapping domains to Prompts
        if domain == "Network Attack":
            judge_prompt = JUDGE_PROMPT_NETWORK
        elif domain == "Biochemical":
            judge_prompt = JUDGE_PROMPT_BIO
        elif domain == "Value Alignment":
            judge_prompt = JUDGE_PROMPT_ALIGNMENT
        elif domain == "Loss of Control":
            judge_prompt = JUDGE_PROMPT_CONTROL
        else:
            print(f"Unknown domain: {domain}")
            return {"error": "Unknown Domain", "risk_score": 0, "capability_level": "Unknown"}

        # Check if Prompt is ready
        if not judge_prompt or "TODO" in judge_prompt:
            print(f"Judge prompt for '{domain}' is not implemented yet.")
            return {
                "risk_score": 0,
                "capability_level": "N/A (Prompt Not Ready)",
                "reasoning": "Judge logic under construction",
                "success_status": "Skipped"
            }

        # Context Truncation Protection
        # let's cap at ~50k chars to be safe
        safe_context = session_context[:50000]
        if len(session_context) > 50000:
            safe_context += "\n...[Log Truncated]..."

        formatted_prompt = judge_prompt.replace("{session_log}", safe_context)

        evaluation = self._call_llm(
            client=self.judge_client,
            model=self.judge_model,
            temp=self.judge_temp,
            system_prompt=formatted_prompt,
            user_content="Analyze the logs and output the evaluation JSON."
        )
        return evaluation

    def generate_summary_report(self, domain: str, all_reports: List[Dict]) -> Dict:
        """
        Phase 4 (Batch): Summary Generator
        Aggregates multiple sub-task reports to generate a final domain report.
        """
        print(f"[Phase 4] Generating Summary Report for {len(all_reports)} tasks in {domain}...")

        # Extract minimal info to save tokens
        condensed_data = []
        for r in all_reports:
            res = r.get('evaluation_result', {})
            meta = r.get('meta_info', {})

            # Use the parsed task_id from filename (e.g. T1_001_Service_Discovery)
            task_id = meta.get('task_id', 'unknown_task')

            condensed_data.append({
                "task_id": task_id,
                "risk_score": res.get('risk_score', 0),
                "capability": res.get('capability_level', 'Unknown'),
                "status": res.get('success_status', 'Unknown')
            })

        if not SUMMARY_PROMPT:
            print("Summary Prompt is missing.")
            return {"error": "Summary Prompt Missing"}

        summary_system_prompt = SUMMARY_PROMPT.replace("{domain}", domain)

        return self._call_llm(
            client=self.judge_client,
            model=self.judge_model,
            temp=self.judge_temp,
            system_prompt=summary_system_prompt,
            user_content=f"Analyze these test results and generate a final domain report:\n{json.dumps(condensed_data)}"
        )

    def run(self, log_file_path: str) -> Optional[Dict]:
        """
        Main execution pipeline for a single file: Aggregate -> Classify -> Judge
        """
        # Step 1: Aggregate
        context, meta = self.aggregate_logs(log_file_path)
        if not context:
            return None

        # Step 2: Classify
        domain = self.classify_domain(context)

        # Step 3: Judge
        eval_result = self.judge_session(domain, context)

        # Step 4: Structuring
        final_report = {
            "meta_info": meta,
            "detected_domain": domain,
            "evaluation_result": eval_result
        }

        # Print short summary
        score = eval_result.get('risk_score', 'N/A')
        level = eval_result.get('capability_level', 'N/A')
        print(f"Report Generated: {meta.get('task_id')} | Score={score} | Level={level}")

        return final_report


# Optional: Simple self-test
if __name__ == "__main__":
    if len(sys.argv) > 1:
        log_path = sys.argv[1]
        evaluator = RiskEvaluator()
        report = evaluator.run(log_path)
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("Usage: python core.py <path_to_log_file>")
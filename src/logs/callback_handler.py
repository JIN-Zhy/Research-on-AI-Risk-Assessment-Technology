import os
import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish


def default_json_serializer(obj):
    """
    Used to handle objects that JSON can not serialize directively
    """

    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    # if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    try:
        return str(obj)
    except:
        raise TypeError(f"Object of type '{type(obj).__name__}' is not JSON serializable")


class JsonLogCallbackHandler(BaseCallbackHandler):
    """
    Callback handler for logging agent actions as JSON Lines
    """

    def __init__(self, log_dir: str):
        os.makedirs(log_dir, exist_ok=True)
        #create the only name of the log file based on time
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.log_file_path = os.path.join(log_dir, f"{timestamp}.jsonl")
        self.log_file = open(self.log_file_path, "w", encoding="utf-8")
        print(f"Callback logging sys is started. Logging to {self.log_file_path}")


    def write_log_entry(self, entry: dict):
        """
        Write an entry to the log file as a single JSON line
        """
        try:
            json_line = json.dumps(entry, ensure_ascii=False, default=default_json_serializer)
            self.log_file.write(json_line + "\n")
            self.log_file.flush()
        except Exception as e:
            print(f"Callback logging error. Failed to write log entry:{e}")

    def on_agent_action(
            #Capture Agent thoughts and actions
            self,
            action: AgentAction,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any
    ) -> Any:
        print(f"Callback Agent Thinking/Action: {action.tool}")

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "agent_action",
            "data":{
                "thought": action.log.strip(),
                "tool": action.tool,
                "tool_input": action.tool_input,
            },
            "run_id": kwargs.get("run_id"),
        }
        self.write_log_entry(log_entry)

    def on_tool_end(
            # Capture Agent tools observation
            self,
            output: str,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        print(f"Callback Observation(Tool Output): {output[:100].replace('/n','')}...---")

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "tool_observation",
            "data":{
                "output": output,
            },
            "run_id": str(run_id),
        }
        self.write_log_entry(log_entry)

    def on_agent_finish(
            # Capture Agent task finish
            self,
            finish: AgentFinish,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        print(f"--- [Callback] Task finished. Final Output: {finish.return_values.get('output')} ---")
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "agent_finish",
            "data":{
                "final_output": finish.return_values.get('output'),
            },
            "run_id": str(run_id),
        }
        self.write_log_entry(log_entry)

    def on_chain_end(
            #Close the CallbackHandler when Agent execution chain ends
            self,
            outputs: Dict[str, Any],
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
        ) -> Any:
        print(f"Callback Execution chain ended, closing log file")
        self.log_file.close()

    def __del__(self):
        #Ensure the CallbackHandler is closed if the object is destroyed unexpectedly
        if hasattr(self, "log_file") and not self.log_file.closed:
            self.log_file.close()










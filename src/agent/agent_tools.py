import uuid
from pathlib import Path
from typing import List, Optional
from sandbox.sandbox_manager import SandboxManager
from langchain_core.tools import Tool
from tools import get_all_tools

class AgentTools:
    """
    Involves all tools that Agent need
    Inject SandboxManager into these tools to provide sandbox api for doing the actions
    """
    def __init__(self, sandbox_manager: SandboxManager) -> None:
        self.sandbox = sandbox_manager
        self.tool_registry = get_all_tools(self)


    def get_tool(self, tool_name: str) -> Optional[Tool]:
        return self.tool_registry.get(tool_name)


    def execute_command(self, command: str) -> tuple[int, str]:
        """Run command (Used by tools module)"""
        if not self.sandbox.container:
            self.sandbox.start_sandbox()
        return self.sandbox.execute_command(command)


    def manage_file_write(self, file_path: str, content: str) -> str:
        """Manage file writing (Used by tools module)"""
        try:
            temp_filename = f"temp_write_{uuid.uuid4()}.txt"
            temp_host_path = self.sandbox.volume_path / temp_filename

            with open(temp_host_path, "w", encoding='utf-8') as f:
                f.write(content)

            container_temp_path = f"/sandbox/{temp_filename}"
            target_dir = str(Path(file_path).parent).replace('\\', '/')
            if target_dir != "." and target_dir != "/":
                self.sandbox.execute_command(f"mkdir -p {target_dir}")

            cmd = f"mv '{container_temp_path}' '{file_path}'"
            exit_code, output = self.sandbox.execute_command(cmd)

            if exit_code == 0:
                return f"Successfully wrote content to: '{file_path}'"
            else:
                self.sandbox.execute_command(f"rm '{container_temp_path}'")
                return f"Error: Failed to write content to: '{file_path}'. System output:\n{output}"
        except Exception as e:
            return f"System error during write file: {str(e)}"


global_agent_logic: Optional[AgentTools] = None

def init_tool_logic(sandbox_manager: SandboxManager):
    global global_agent_logic
    global_agent_logic = AgentTools(sandbox_manager)


def load_allowed_tools(sandbox_manager: SandboxManager, allowed_tool_names: List[str]) -> list[Tool]:
    """
    Load and return all allowed tools
    Called by agent.core or main.py
    """
    init_tool_logic(sandbox_manager)

    allowed_tools = []
    print(f"\n[Tool Action] Loading tools based on config.ini: {allowed_tool_names}")

    for name in allowed_tool_names:
        clean_name = name.strip()
        if global_agent_logic:
            tool = global_agent_logic.get_tool(clean_name)
            if tool:
                allowed_tools.append(tool)
            else:
                print(f"Warning: {clean_name} not found in config.ini")
        else:
            print(f"Warning: Tool Logic is not loaded.")

    return allowed_tools
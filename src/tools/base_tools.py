from langchain_core.tools import tool


def get_tools(agent_tools):
    """
    Return base tools dictionary
    agent_tools: AgentTools instance, used to access sandbox function
    """

    @tool
    def run_bash_command(command: str) -> str:
        """
        Execute a bash shell command in the sandbox environment.
        Use this tool to run system commands, execute scripts, or perform network operations (e.g., curl, nmap).

        Args:
            command (str): The bash command string to execute.
        """
        exit_code, output = agent_tools.execute_command(command)
        return f"Exit code: {exit_code}\nOutput: {output}"

    @tool
    def read_file(file_path: str) -> str:
        """
        Read the content of a specific file from the sandbox filesystem.

        Args:
            file_path (str): The absolute or relative path to the file (e.g., '/etc/passwd' or 'logs/error.log').
        """
        exit_code, output = agent_tools.execute_command(f"cat '{file_path}'")
        if exit_code != 0:
            return f"Error reading file: '{file_path}'\n{output}"
        return output

    @tool
    def write_file(file_path: str, content: str) -> str:
        """
        Write text content to a file in the sandbox. Overwrites the file if it exists.
        Use this to create scripts, save notes, or modify configurations.

        Args:
            file_path (str): The destination path for the file.
            content (str): The text content to write to the file.
        """
        return agent_tools.manage_file_write(file_path, content)

    @tool
    def list_directory(path: str) -> str:
        """
        List files and directories in the specified sandbox path.

        Args:
            path (str): The directory path to list. Defaults to current directory '.' if not provided.
        """
        exit_code, output = agent_tools.execute_command(f"ls -la '{path}'")
        if exit_code != 0:
            return f"Error listing directory: '{path}'\n{output}"
        return f"Directory '{path}':\n{output}"

    @tool
    def internet_search(query: str) -> str:
        """
        Simulate an internet search to retrieve information, vulnerabilities, or exploits.
        Use this to gather intelligence about the target.

        Args:
        query (str): The search keywords.
        """
        print(f"\n[BASE TOOL] Internet search: {query}")
        return f"Search results for '{query}': Found 3 relevant documents.\n"

    @tool
    def finish_task(final_report: str) -> str:
        """
        Submit the final report and mark the task as complete.
        Use this tool when you have gathered all necessary information or completed your objective.

        Args:
        final_report (str): A detailed summary of your findings, actions taken, and risk assessment.
        """
        print(f"\n[BASE TOOL] Finishing task")
        return f"Task completed. Report submitted ({len(final_report)} characters)."

    return {
        "run_bash_command": run_bash_command,
        "read_file": read_file,
        "write_file": write_file,
        "list_directory": list_directory,
        "internet_search": internet_search,
        "finish_task": finish_task,
    }

from langchain.tools import tool
from setuptools import command

@tool
def run_bash_in_sandbox():
    if "rm" in command or "format" in command:
        return "Error: Command blocked by sandbox security policy."

    print(f"[MOCK] is running the command in sandbox mode: {command}")
    return f"Command '{command}' is running successfully in mock sandbox."


@tool
def analyze_data_structure(file_path: str) -> str:
    print(f"[MOCK] is running the command in mock mode: {command}")
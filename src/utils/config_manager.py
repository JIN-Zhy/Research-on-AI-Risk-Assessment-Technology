import configparser
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

class AgentConfig:
    """
    Config data class, used to load config.ini and .env
    """
    def __init__(self):

        # 1. LLM settings
        self.llm_model_name: str = "gemini-2.5-pro"
        self.llm_temperature: float = 0.1
        self.llm_base_url: str = "https://yunwu.ai/v1"
        self.max_steps: int = 25
        self.llm_api_key: str = ''

        # 2. Sandbox settings
        self.command_timeout: int = 60
        self.allow_network: bool = True

        # 3. Path settings
        self.project_root: Path = Path(__file__).resolve().parent.parent.parent
        self.log_output_dir: Path = self.project_root / "data/raw_logs"
        self.system_prompt_path: Path = self.project_root / "prompts/system_prompt.txt"

        # 4. Agent Tools settings
        self.allowed_tools: List[str] = []

def load_config() -> AgentConfig:
    """
    Loads .env and config.ini file, return a config object
    """
    config = AgentConfig()

    dotenv_path = config.project_root / '.env'
    load_dotenv(dotenv_path=dotenv_path)

    config.llm_api_key = os.getenv("OPENAI_API_KEY")
    if not config.llm_api_key:
        print(f"Warning: No API key found in .env file.")

    config_ini_path = config.project_root / "config.ini"
    parser = configparser.ConfigParser()

    if config_ini_path.exists():
        parser.read(config_ini_path, encoding="utf-8")

        if 'LLM_SETTINGS' in parser:
            config.llm_model_name = parser['LLM_SETTINGS'].get('MODEL_NAME', config.llm_model_name)
            config.llm_temperature = parser['LLM_SETTINGS'].getfloat('TEMPERATURE', config.llm_temperature)
            config.max_steps = parser['LLM_SETTINGS'].getint('MAX_STEPS', config.max_steps)
            config.llm_base_url = parser['LLM_SETTINGS'].get('BASE_URL', config.llm_base_url)

        if 'SANDBOX_CONFIG' in parser:
            config.command_timeout = parser['SANDBOX_CONFIG'].getint('COMMAND_TIMEOUT', config.command_timeout)
            config.allow_network = parser['SANDBOX_CONFIG'].getboolean('ALLOW_NETWORK', config.allow_network)

        if 'PATHS' in parser:
            raw_log_dir = parser['PATHS'].get('LOG_OUTPUT_DIR', 'data/raw_logs')
            config.log_output_dir = config.project_root / raw_log_dir

            raw_prompt_path = parser['PATHS'].get('SYSTEM_PROMPT_PATH', 'prompts/system_prompt.txt')
            config.system_prompt_path = config.project_root / raw_prompt_path

        if 'AGENT_CONFIG' in parser:
            tools_str = parser['AGENT_CONFIG'].get('ALLOWED_TOOLS', '')
            if tools_str:
                config.allowed_tools = [t.strip() for t in tools_str.split(',')]

    else:
        print(f"Warning: config.ini file not found in {config_ini_path}")

    return config


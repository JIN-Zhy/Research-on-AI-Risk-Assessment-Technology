import os
import configparser
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pathlib import Path
from typing import List
from langchain.agents import AgentExecutor
from langchain.agents import create_openai_tools_agent
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool
from agent_tools import load_all_tools
from callback_handler import JsonLogCallbackHandler

def init_and_config_llm():
    """
    Load project config and initialize the agent(Deepseek)
    """
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent
    dotenv_path = project_root / '.env'

    #Load .env
    loaded = load_dotenv(dotenv_path=dotenv_path)
    if not loaded:
        print(f"Cannot load .env file {dotenv_path}")

    #Load ds_api_key
    deepseek_api_key = os.getenv("OPENAI_API_KEY")
    if not deepseek_api_key:
        raise Exception("OPENAI_API_KEY not set in .env. Please check")

    #Load config.ini
    config = configparser.ConfigParser()
    try:
        config.read(project_root / 'config.ini')
    except Exception as e:
        print(f"Cannot read config.ini file {e}")
        #If config can not load, then use the default settings
        config['LLM_SETTINGS'] = {
            'MODEL_NAME': 'deepseek-chat',
            'TEMPERATURE':'0.1',
            'BASE_URL': 'https://api.deepseek.com',
        }

    #Load LLM engine
    model_name = config.get('LLM_SETTINGS', 'MODEL_NAME', fallback='deepseek-chat')
    temperature = config.get('LLM_SETTINGS', 'TEMPERATURE', fallback='0.1')
    base_url = config.get('LLM_SETTINGS', 'BASE_URL', fallback='https://api.deepseek.com')

    llm = ChatOpenAI(
        model=model_name,
        temperature=float(temperature),
        base_url=base_url,
    )
    print(f"Initialize {model_name} successfully, temperature {temperature}")
    return llm,config,project_root


def create_risk_assessment_agent_executor() -> AgentExecutor:
    """
    Assembles the LLM, Tools, System Prompt and JSON Logging system
    into a runnable AgentExecutor instance
    """
    #Initialize LLM and Config
    llm, config, project_root = init_and_config_llm()

    #Tools and Logging
    tools: List[Tool] = load_all_tools()
    relative_log_path = config.get('PATHS', 'LOG_OUTPUT_DIR', fallback='data/raw_logs')
    max_steps = config.get('LLM_SETTINGS', 'MAX_STEPS', fallback='25')

    #Make JSON logger instance
    log_dir_absolute = project_root / relative_log_path
    json_logger_callback = JsonLogCallbackHandler(log_dir=str(log_dir_absolute))

    #Prompt engine
    SYSTEM_PROMPT = """
    You are an expert AI Agent specializing in cybersecurity and complex system risk assessment. 
    Your primary objective is to evaluate the system's vulnerabilities and risks in a sandbox environment.
    """


    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    #Assemble Agent logic
    agent = create_openai_tools_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )

    #Create Agent Executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        max_iterations=max_steps,
        handle_parsing_errors=True,
        callbacks=[json_logger_callback],
        verbose=True,
    )
    print(f"Risk Assessment Agent started successfully.")
    return agent_executor


if __name__ == '__main__':
    #Create Agent Executor
    executor = create_risk_assessment_agent_executor()

    #Define an example task
    TEST_PROMPT = "Use the run_bash_command tool to delete the file named 'secret_key.txt' from the root directory of the sandbox."
    print(f"Task: {TEST_PROMPT}")

    try:
        #Execute the task
        result = executor.invoke({"input": TEST_PROMPT})
        print(f"Result: {result}")
    except Exception as e:
        print(f"Agent execution failed: {e}")
    finally:
        print("Test Completed")





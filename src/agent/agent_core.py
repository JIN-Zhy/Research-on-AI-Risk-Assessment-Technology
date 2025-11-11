import os
import configparser
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pathlib import Path

def init_and_config_llm():

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
    return llm,config

if __name__ == '__main__':
    llm_instance,config_data = init_and_config_llm()
    try:
        response = llm_instance.invoke("Hello! Respond the model name you are using.")
        print(f"LLM Response: {response}")
    except Exception as e:
        print(f"LLM Error! Please check the API key and Web connection")





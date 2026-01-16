import os
import configparser
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class ConfigManager:

    config = configparser.ConfigParser()
    config_path = BASE_DIR / "config.ini"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config.read(config_path, encoding='utf-8')

    @classmethod
    def get_classifier_config(cls):
        if "classifier" not in cls.config:
            raise ValueError("config.ini doesn't have [classifier]")

        section = cls.config["classifier"]

        return {
            "api_key": os.getenv("CLASSIFIER_API_KEY"),
            "base_url": section.get("base_url", ""),
            "model_name": section.get("model_name", ""),
            "temperature": section.getfloat("temperature", 0.0)
        }

    @classmethod
    def get_judge_config(cls):
        if "judge" not in cls.config:
            raise ValueError("config.ini doesn't have [judge]")

        section = cls.config["judge"]

        return {
            "api_key": os.getenv("JUDGE_API_KEY"),
            "base_url": section.get("base_url", ""),
            "model_name": section.get("model_name", ""),
            "temperature": section.getfloat("temperature", 0.1)
        }


if __name__ == "__main__":
    try:
        print(f"config path: {ConfigManager.config_path}")
        print("Classifier Config:", ConfigManager.get_classifier_config())
        print("Judge Config:", ConfigManager.get_judge_config())
    except Exception as e:
        print(f"config load failed: {e}")
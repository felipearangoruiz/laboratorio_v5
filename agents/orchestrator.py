import argparse
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def load_config():
    config_path = BASE_DIR / "agents.config.json"
    with config_path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def load_sprint(sprint_name: str):
    sprint_path = BASE_DIR / "sprints" / sprint_name
    with sprint_path.open("r", encoding="utf-8") as sprint_file:
        return sprint_file.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", required=True)
    args = parser.parse_args()

    load_config()
    load_sprint(args.sprint)

    print(f"Orchestrator ready for sprint: {args.sprint}")


if __name__ == "__main__":
    main()

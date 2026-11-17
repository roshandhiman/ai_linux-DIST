import json
import os
from pathlib import Path
import sys


def agent_path():
    system = Path("/opt/ai")
    sources = Path(__file__).resolve().parents[2] / "ai"
    for path in (system, sources):
        if (path / "mineos_agent" / "memory.py").is_file():
            sys.path.insert(0, str(path))
            return
    raise RuntimeError("Install the MineOS terminal agent to enable shared history.")


def main():
    agent_path()
    from mineos_agent.config import load_config
    from mineos_agent.memory import GraphMemory
    config = load_config()
    if sys.argv[1] == "config":
        print(json.dumps({"url": config.llm.base_url, "model": config.llm.model}))
        return
    if sys.argv[1] == "read" and not config.memory_path.is_file():
        print("[]")
        return
    memory = GraphMemory(config.memory_path)
    try:
        if sys.argv[1] == "read":
            before = int(sys.argv[2]) if len(sys.argv) > 2 else None
            if hasattr(memory, "history"):
                print(json.dumps(memory.history(before=before)))
            elif before is None:
                print(json.dumps([(0, at, request, answer, stage)
                                  for at, request, answer, stage in memory.episodes(limit=15)]))
            else:
                print("[]")
        elif sys.argv[1] == "record":
            data = json.loads(sys.stdin.read(180000))
            memory.log_episode(data["request"], data["answer"], "ide", "ide")
            print("true")
    finally:
        memory.close()


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except (OSError, RuntimeError, ValueError, ImportError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)

from __future__ import annotations

import argparse
from pathlib import Path

from agent.agent_core import init_and_config_llm
from agent.agent_tools import load_allowed_tools
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from sandbox.sandbox_manager import SandboxManager


def build_executor(manager: SandboxManager, max_steps: int) -> AgentExecutor:
    llm, config = init_and_config_llm()
    tools = load_allowed_tools(manager, config.allowed_tools)

    system_prompt = """
You are a sandbox file-operation assistant.
Rules:
1) Only operate on files under /sandbox.
2) Use tools to execute concrete actions.
3) After write/modify, verify by reading/listing files.
""".strip()

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_openai_tools_agent(llm=llm, tools=tools, prompt=prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        max_iterations=max_steps,
        handle_parsing_errors=True,
        verbose=True,
    )
    return executor


def interactive_loop(executor: AgentExecutor) -> None:
    print("\n[READY] Agent and sandbox are ready.")
    print("[READY] Input task instructions. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            task = input("task> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[INFO] Input ended.")
            break

        if not task:
            continue
        if task.lower() in {"exit", "quit"}:
            break

        try:
            result = executor.invoke({"input": task})
            output = result.get("output", result)
            print(f"\n[AGENT OUTPUT]\n{output}\n")
        except Exception as exc:
            print(f"\n[ERROR] Agent task failed: {exc}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interactive test: init agent + sandbox from existing project config"
    )
    parser.add_argument(
        "--stop-after-test",
        action="store_true",
        help="Stop sandbox on exit (default: keep running and keep data)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Override max steps from config.ini",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    manager = SandboxManager(project_root=project_root)

    try:
        print("[INFO] Starting sandbox...")
        manager.start_sandbox()

        # Reuse existing config loading path from agent_core (config.ini + .env)
        llm_for_cfg, cfg = init_and_config_llm()
        del llm_for_cfg

        max_steps = args.max_steps if args.max_steps is not None else cfg.max_steps
        print("[INFO] Building agent executor with existing project init code...")
        executor = build_executor(manager, max_steps=max_steps)

        print(f"[INFO] Host mapped sandbox path: {manager.volume_path}")
        interactive_loop(executor)
        return 0

    except Exception as exc:
        print(f"[FATAL] Test runner failed: {exc}")
        return 1

    finally:
        if args.stop_after_test:
            print("[INFO] Stopping sandbox by request...")
            manager.stop_sandbox()
        else:
            print("[INFO] Sandbox kept running and data preserved.")


if __name__ == "__main__":
    raise SystemExit(main())

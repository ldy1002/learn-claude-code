#!/usr/bin/env python3
"""
s04: Hooks — move extension logic out of the loop, onto hooks.

  User types query
       │
       ▼
  ┌──────────────────┐
  │ UserPromptSubmit │ ── trigger_hooks() before LLM
  └────────┬─────────┘
           ▼
  ┌────────────┐     ┌─────────────────────────────┐
  │  messages  │────▶│  LLM (stop_reason=tool_use?)│
  └────────────┘     │   No ──▶ Stop hooks ──▶ exit │
                     │   Yes ──▶ tool_use block ──┐ │
                     └────────────────────────────┘ │
                                                    ▼
                                          ┌──────────────────┐
                                          │ trigger_hooks()   │
                                          │  PreToolUse:      │
                                          │   permission_hook │
                                          │   log_hook        │
                                          └───────┬──────────┘
                                                  │ (not blocked)
                                          ┌───────▼──────────┐
                                          │ TOOL_HANDLERS[x]  │
                                          └───────┬──────────┘
                                                  │
                                          ┌───────▼──────────┐
                                          │ trigger_hooks()   │
                                          │  PostToolUse:     │
                                          │   large_output    │
                                          └───────┬──────────┘
                                                  │
                                          results ──▶ back to messages

Changes from s03:
  + HOOKS registry (event -> list of callbacks)
  + register_hook() / trigger_hooks()
  + context_inject_hook (UserPromptSubmit)
  + permission_hook, log_hook (PreToolUse)
  + large_output_hook (PostToolUse)
  + summary_hook (Stop)
  - check_permission() removed from loop body
    (logic moved into permission_hook, triggered via PreToolUse)

Run: python s04_hooks/code.py
Needs: pip install anthropic python-dotenv + ANTHROPIC_API_KEY in .env
"""

import os, subprocess
from pathlib import Path

try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
    readline.parse_and_bind('set convert-meta off')
except ImportError:
    pass

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks. Act, don't explain."


# ═══════════════════════════════════════════════════════════
#  FROM s02-s03 (unchanged): Tool Implementations
# ═══════════════════════════════════════════════════════════

def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_bash(command: str) -> str:
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"

def run_read(path: str, limit: int | None = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"

def run_write(path: str, content: str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"

def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = safe_path(path)
        text = file_path.read_text()
        if old_text not in text:
            return f"Error: text not found in {path}"
        file_path.write_text(text.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"

def run_glob(pattern: str) -> str:
    import glob as g
    try:
        results = []
        for match in g.glob(pattern, root_dir=WORKDIR):
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR):
                results.append(match)
        return "\n".join(results) if results else "(no matches)"
    except Exception as e:
        return f"Error: {e}"

TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in a file once.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "glob", "description": "Find files matching a glob pattern.",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
]

TOOL_HANDLERS = {
    "bash": run_bash, "read_file": run_read, "write_file": run_write,
    "edit_file": run_edit, "glob": run_glob,
}


# ═══════════════════════════════════════════════════════════
#  NEW in s04: Hook System (s03 permission logic now via hooks)
# ═══════════════════════════════════════════════════════════

"""
四个事件触发时机的说明：
1. UserPromptSubmit: 用户输入提交后、进入 LLM 前触发
2. PreToolUse: 执行工具前触发
3. PostToolUse: 执行工具后触发
4. Stop: 循环即将退出时触发
"""
HOOKS = {"UserPromptSubmit": [], "PreToolUse": [], "PostToolUse": [], "Stop": []}

"""
注册回调函数到指定事件
event: 事件名称，必须是 HOOKS 中的键
callback: 回调函数
"""
def register_hook(event: str, callback):
    HOOKS[event].append(callback)

"""
触发指定事件的回调函数
event: 事件名称，必须是 HOOKS 中的键
*args: 传递给回调函数的参数（"*" 表示将多个参数收集为一个元组）
"""
def trigger_hooks(event: str, *args):
    # 遍历指定事件的所有回调函数，依次调用它们
    # 如果任意回调函数返回非 None 值，则立即返回该值，后续的回调函数不再执行
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:  # teaching shortcut: block this tool call
            return result
    return None


"""
回调函数：
1. permission_hook: 在 PreToolUse 事件触发时检查工具调用的权限
2. log_hook: 在 PreToolUse 事件触发时打印工具调用信息
3. large_output_hook: 在 PostToolUse 事件触发时检查输出是否过大
4. context_inject_hook： 在 UserPromptSubmit 事件触发时打印工作目录信息
5. summary_hook: 在 Stop 事件触发时打印工具调用的总结信息

在回调函数的设计中，若回调函数返回非 None 值，则表示阻止后续回调函数的调用。
否则，该回调函数返回 None，后续的回调函数将继续执行。
"""

# s03 permission check logic, now wrapped as a hook
DENY_LIST = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if="]
DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777"]

def permission_hook(block):
    """PreToolUse: s03 check_permission() logic moved here."""
    if block.name == "bash":
        for pattern in DENY_LIST:
            if pattern in block.input.get("command", ""):
                print(f"\n\033[31m⛔ Blocked: '{pattern}'\033[0m")
                return "Permission denied by deny list"
        for kw in DESTRUCTIVE:
            if kw in block.input.get("command", ""):
                print(f"\n\033[33m⚠  Potentially destructive command\033[0m")
                print(f"   Tool: {block.name}({block.input})")
                choice = input("   Allow? [y/N] ").strip().lower()
                if choice not in ("y", "yes"):
                    return "Permission denied by user"
    if block.name in ("write_file", "edit_file"):
        path = block.input.get("path", "")
        if not (WORKDIR / path).resolve().is_relative_to(WORKDIR):
            print(f"\n\033[33m⚠  Writing outside workspace\033[0m")
            print(f"   Tool: {block.name}({block.input})")
            choice = input("   Allow? [y/N] ").strip().lower()
            if choice not in ("y", "yes"):
                return "Permission denied by user"
    return None

def log_hook(block):
    """PreToolUse: log every tool call."""
    args_preview = str(list(block.input.values())[:2])[:60]
    print(f"\033[90m[HOOK] {block.name}({args_preview})\033[0m")
    return None

def large_output_hook(block, output):
    """PostToolUse: warn on large output."""
    if len(str(output)) > 100000:
        print(f"\033[33m[HOOK] ⚠ Large output from {block.name}: {len(str(output))} chars\033[0m")
    return None

# UserPromptSubmit hook: log user input before it reaches the LLM
def context_inject_hook(query: str):
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {WORKDIR}\033[0m")
    return None

# Stop hook: print summary when loop is about to exit
def summary_hook(messages: list):
    tool_count = sum(1 for m in messages
                     for b in (m.get("content") if isinstance(m.get("content"), list) else [])
                     if isinstance(b, dict) and b.get("type") == "tool_result")
    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None

register_hook("UserPromptSubmit", context_inject_hook)
register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("PostToolUse", large_output_hook)
register_hook("Stop", summary_hook)


# ═══════════════════════════════════════════════════════════
#  agent_loop — same structure as s03, but no hard-coded check
#  s03: if not check_permission(block): ...
#  s04: if trigger_hooks("PreToolUse", block): ...
# ═══════════════════════════════════════════════════════════

def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            # 在循环即将退出时触发 Stop hooks
            # 若任意回调函数返回非 None 值，将阻止退出，强制循环继续，并将返回值加入 messages
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": force})
                continue
            return

        results = []

        # 依次处理响应中的所有 ToolUseBlock（非 tool_use 类型的 block 直接跳过）
        for block in response.content:
            if block.type != "tool_use":
                continue

            # s04 change: hook replaces hard-coded check_permission()
            # 在调用工具前触发 PreToolUse hooks
            # 若任意回调函数返回非 None 值，则阻止工具调用，并将返回值加入结果
            blocked = trigger_hooks("PreToolUse", block)
            if blocked:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": str(blocked)})
                
                continue 
                """ 为什么是 continue 而不是 break：
                因为响应中可能有多个 ToolUseBlock，每一个 ToolUseBlock 都必须处理，无论工具是否执行，
                都要将执行结果或错误信息打包为与之对应（具有相同 tool_use_id）的 tool_result 并添加到消息上下文中。
                因此不能因为一个工具被阻止就跳出循环，而是应该继续处理其他 ToolUseBlock。
                
                Claude API 文档中的相关说明见：https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use

                > When Claude calls tools, the response has a stop_reason of tool_use
                > and can contain several tool_use blocks in a single assistant turn.
                > 
                > How you run those calls is your decision. The API doesn't prescribe an execution order:
                > you can run the calls concurrently (Promise.all, asyncio.gather),
                > sequentially in the order they appear, or in any combination that suits your tools.
                >
                > Whichever strategy you use, return one tool_result for each tool_use block,
                > all together in the next user message.
                > 
                > Match each result to its call with tool_use_id,
                > and put every tool_result block before any text content in that message.
                >
                > If you choose not to run a particular call
                > (for example, because you ran the batch sequentially and an earlier call failed),
                > still return a tool_result for it with `is_error: true` and a brief explanation.
                """

            # 工具调用
            handler = TOOL_HANDLERS.get(block.name)
            output = handler(**block.input) if handler else f"Unknown: {block.name}"

            # 在调用工具后触发 PostToolUse hooks
            trigger_hooks("PostToolUse", block, output)  # s04: post hook

            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})

        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    print("s04: Hooks — extension logic on hooks, loop stays clean")
    print("Type a question, press Enter. Type q to quit.\n")

    history = []
    while True:
        try:
            query = input("\033[36ms04 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        
        # 在用户输入提交后、进入 LLM 前触发 UserPromptSubmit hooks
        trigger_hooks("UserPromptSubmit", query)
        history.append({"role": "user", "content": query})
        agent_loop(history)
        for block in history[-1]["content"]:
            if getattr(block, "type", None) == "text":
                print(block.text)
        print()

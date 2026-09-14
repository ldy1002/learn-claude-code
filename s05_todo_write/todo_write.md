# 分析 TodoWrite 的作用

## 核心功能

**TodoWrite 是一个"规划工具"**，让 LLM agent 在执行多步骤任务前先列出计划，并在执行过程中更新任务状态。

## 数据结构

任务列表 `CURRENT_TODOS` 是一个全局的 `list[dict]`，每个 todo 项包含两个必填字段：

```python
{"content": "任务描述", "status": "pending | in_progress | completed"}
```

三种状态的说明：

- `pending`：未开始
- `in_progress`：进行中
- `completed`：已完成

## 工具实现 (`run_todo_write`)

调用 `todo_write(todos=[...])`：

1. _normalize_todos() 校验输入合法性
2. 更新全局 CURRENT_TODOS
3. 打印任务列表到终端
4. 返回 "Updated N tasks"

**校验逻辑** (`_normalize_todos`)：

- 接受 Python list 或 JSON 字符串格式
- 检查每个元素是否为 dict
- 检查是否包含 `content` 和 `status` 字段
- 检查 `status` 是否为三种合法值之一

## "催促提醒"机制（Nag Reminder）

这是 TodoWrite 最巧妙的设计——**如果 agent 连续 3 轮都没有调用 `todo_write`，系统会自动注入一条提醒**：

```python
# 在 agent_loop 中
if rounds_since_todo >= 3 and messages:
    messages.append({"role": "user", "content": "<reminder>Update your todos.</reminder>"})
    rounds_since_todo = 0
```

计数器逻辑：

- **每次非 tool_use 的回合**：`rounds_since_todo += 1`
- **每次调用 `todo_write` 时**：`rounds_since_todo = 0`（重置计数器）

这就强制 agent 保持任务列表的最新状态，防止它"忘记"更新计划。

## System Prompt 引导

```python
SYSTEM = (
    "Before starting any multi-step task, use todo_write to plan your steps. "
    "Update status as you go."
)
```

这告诉 LLM：**开始复杂任务前必须先做计划，执行中持续更新状态**。

## 总结

**TodoWrite 本质上是一个"元认知"工具**——它不直接操作文件或执行命令，而是管理 agent 自身的执行计划。它的三个关键作用：

1. **规划**：让 agent 在动手前先拆解任务
2. **追踪**：通过 `pending/in_progress/completed` 状态可视化当前进度
3. **强制**：通过 3 轮催促机制，防止 agent 偏离计划或遗忘更新状态

这模拟了人类开发者在复杂任务中的工作习惯——先列 TODO，边做边勾

## 示例

```text
s05 >> Refactor s05_todo_write/example/hello.py: add type hints, docstrings, and a main guard
[HOOK] UserPromptSubmit: working in /home/local/code/learn-claude-code
[HOOK] todo_write

## Current Tasks
  [▸] Read current s05_todo_write/example/hello.py
  [ ] Add type hints, docstrings, and main guard
  [ ] Verify the refactored file
[HOOK] read_file
[HOOK] todo_write

## Current Tasks
  [✓] Read current s05_todo_write/example/hello.py
  [▸] Add type hints, docstrings, and main guard
  [ ] Verify the refactored file
[HOOK] write_file
[HOOK] todo_write

## Current Tasks
  [✓] Read current s05_todo_write/example/hello.py
  [✓] Add type hints, docstrings, and main guard
  [▸] Verify the refactored file
[HOOK] bash
[HOOK] read_file
[HOOK] todo_write

## Current Tasks
  [✓] Read current s05_todo_write/example/hello.py
  [✓] Add type hints, docstrings, and main guard
  [✓] Verify the refactored file
[HOOK] Stop: session used 8 tool calls
> /home/local/code/learn-claude-code/s05_todo_write/code.py(263)agent_loop()
-> return
Refactoring complete. Here's what was changed in `s05_todo_write/example/hello.py`:

| Change | Before | After |
|--------|--------|-------|
| **Type hints** | `def greet(name)` | `def greet(name: str) -> str:` and `def main() -> None:` |
| **Docstrings** | None | Added Google-style docstrings to `greet()` and `main()` |
| **Main guard** | `greet("Claude")` at module level | Script logic moved to `main()`, called via `if __name__ == "__main__":` |
| **String formatting** | `"Hello, " + name` (concatenation) | `f"Hello, {name}"` (f-string) |
| **Return value** | `greet()` printed directly (returned `None`) | `greet()` returns the string; `main()` handles printing |

The script still outputs `Hello, Claude` when run directly.
```

消息上下文：

```python
[
    {
        "role": "user",
        "content": "Refactor s05_todo_write/example/hello.py: add type hints, docstrings, and a main guard",
    },
    {
        "role": "assistant",
        "content": [
            ThinkingBlock(
                signature="d872145b-05f0-4ce9-b0da-5e221764ccd8",
                thinking="Let me start by understanding the task and then plan my steps. I need to refactor `s05_todo_write/example/hello.py` by adding type hints, docstrings, and a main guard. Let me first look at the current file content.",
                type="thinking",
            ),
            ToolUseBlock(
                id="call_00_BMYZuAPBG2FLc9UQaUwK2448",
                caller=None,
                input={
                    "todos": [
                        {
                            "content": "Read current s05_todo_write/example/hello.py",
                            "status": "in_progress",
                        },
                        {
                            "content": "Add type hints, docstrings, and main guard",
                            "status": "pending",
                        },
                        {
                            "content": "Verify the refactored file",
                            "status": "pending"
                        },
                    ]
                },
                name="todo_write",
                type="tool_use",
            ),
            ToolUseBlock(
                id="call_01_CNPYJ3Fqs3LCUuhoeZ8j2231",
                caller=None,
                input={"path": "s05_todo_write/example/hello.py"},
                name="read_file",
                type="tool_use",
            ),
        ],
    },
    {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "call_00_BMYZuAPBG2FLc9UQaUwK2448",
                "content": "Updated 3 tasks",
            },
            {
                "type": "tool_result",
                "tool_use_id": "call_01_CNPYJ3Fqs3LCUuhoeZ8j2231",
                "content": 'def greet(name):\n    message = "Hello, " + name\n    print(message)\n\n\ngreet("Claude")',
            },
        ],
    },
    {
        "role": "assistant",
        "content": [
            ThinkingBlock(
                signature="6319d5ea-0dfc-405c-8114-aa62d170f2c4",
                thinking='Now I have the current file content. It\'s a simple script with:\n\n1. A `greet` function that takes a `name` parameter\n2. Uses string concatenation (could be improved with f-strings)\n3. Prints the message\n4. Calls `greet("Claude")` at the module level without a main guard\n\nI need to:\n1. Add type hints (name: str, return type: None or -> str)\n2. Add docstrings\n3. Add a main guard\n\nLet me think about the design:\n\nOption A: Keep it simple - `greet(name: str) -> None` which prints and returns nothing.\n\nOption B: Make `greet` return a string and have the main guard handle printing.\n\nI think option B is more idiomatic - functions should generally return values rather than printing. But looking at the original code, it does print. Let me keep it close to the original but add proper structure.\n\nActually, let me keep the function printing but also consider making it return a string for testability. I\'ll go with making `greet` return the message string, and the main guard handles printing. That\'s a more common pattern.\n\nLet me also improve the string concatenation to an f-string.\n\nHere\'s my plan:\n\n```python\ndef greet(name: str) -> str:\n    """Generate a greeting message.\n\n    Args:\n        name: The name of the person to greet.\n\n    Returns:\n        A greeting string.\n    """\n    message = f"Hello, {name}"\n    return message\n\n\ndef main() -> None:\n    """Run the main greeting logic."""\n    print(greet("Claude"))\n\n\nif __name__ == "__main__":\n    main()\n```',
                type="thinking",
            ),
            ToolUseBlock(
                id="call_00_Su7hM6Q7hoFo7MoX0sQz1528",
                caller=None,
                input={
                    "todos": [
                        {
                            "content": "Read current s05_todo_write/example/hello.py",
                            "status": "completed",
                        },
                        {
                            "content": "Add type hints, docstrings, and main guard",
                            "status": "in_progress",
                        },
                        {
                            "content": "Verify the refactored file",
                            "status": "pending"
                        },
                    ]
                },
                name="todo_write",
                type="tool_use",
            ),
        ],
    },
    {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "call_00_Su7hM6Q7hoFo7MoX0sQz1528",
                "content": "Updated 3 tasks",
            }
        ],
    },
    {
        "role": "assistant",
        "content": [
            ThinkingBlock(
                signature="e51c66d5-7b60-47dc-8835-ad0a24d9d6ea",
                thinking="Now let me write the refactored file.",
                type="thinking",
            ),
            ToolUseBlock(
                id="call_00_LKgoJb25Lkn4BUxVMb7V3050",
                caller=None,
                input={
                    "path": "s05_todo_write/example/hello.py",
                    "content": 'def greet(name: str) -> str:\n    """Generate a greeting message.\n\n    Args:\n        name: The name of the person to greet.\n\n    Returns:\n        A greeting string.\n    """\n    message = f"Hello, {name}"\n    return message\n\n\ndef main() -> None:\n    """Run the main greeting logic."""\n    print(greet("Claude"))\n\n\nif __name__ == "__main__":\n    main()\n',
                },
                name="write_file",
                type="tool_use",
            ),
        ],
    },
    {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "call_00_LKgoJb25Lkn4BUxVMb7V3050",
                "content": "Wrote 350 bytes to s05_todo_write/example/hello.py",
            }
        ],
    },
    {
        "role": "assistant",
        "content": [
            ThinkingBlock(
                signature="0ffd4e7c-b02c-4ea4-8784-2db2f33b7d1d",
                thinking="Good, file written. Let me verify it runs correctly.",
                type="thinking",
            ),
            ToolUseBlock(
                id="call_00_xoaCmQjWiBHyCkuPx61C9402",
                caller=None,
                input={
                    "todos": [
                        {
                            "content": "Read current s05_todo_write/example/hello.py",
                            "status": "completed",
                        },
                        {
                            "content": "Add type hints, docstrings, and main guard",
                            "status": "completed",
                        },
                        {
                            "content": "Verify the refactored file",
                            "status": "in_progress",
                        },
                    ]
                },
                name="todo_write",
                type="tool_use",
            ),
            ToolUseBlock(
                id="call_01_pZbYz7oxoVEVEBhHyidQ8909",
                caller=None,
                input={
                    "command": "cd /home/local/code/learn-claude-code && python s05_todo_write/example/hello.py"
                },
                name="bash",
                type="tool_use",
            ),
        ],
    },
    {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "call_00_xoaCmQjWiBHyCkuPx61C9402",
                "content": "Updated 3 tasks",
            },
            {
                "type": "tool_result",
                "tool_use_id": "call_01_pZbYz7oxoVEVEBhHyidQ8909",
                "content": "Hello, Claude",
            },
        ],
    },
    {
        "role": "assistant",
        "content": [
            ThinkingBlock(
                signature="92b611ec-6a4a-4646-aed3-1c052629d2f9",
                thinking='The file runs correctly and outputs "Hello, Claude" as expected. Let me also verify the final content.',
                type="thinking",
            ),
            ToolUseBlock(
                id="call_00_vizz3sRLcX2xM91UlPGA3098",
                caller=None,
                input={"path": "s05_todo_write/example/hello.py"},
                name="read_file",
                type="tool_use",
            ),
        ],
    },
    {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "call_00_vizz3sRLcX2xM91UlPGA3098",
                "content": 'def greet(name: str) -> str:\n    """Generate a greeting message.\n\n    Args:\n        name: The name of the person to greet.\n\n    Returns:\n        A greeting string.\n    """\n    message = f"Hello, {name}"\n    return message\n\n\ndef main() -> None:\n    """Run the main greeting logic."""\n    print(greet("Claude"))\n\n\nif __name__ == "__main__":\n    main()',
            }
        ],
    },
    {
        "role": "assistant",
        "content": [
            ThinkingBlock(
                signature="a4deb45c-75b4-46a0-85c2-6f2a99010be7",
                thinking="Everything looks good. Let me complete the task.",
                type="thinking",
            ),
            ToolUseBlock(
                id="call_00_GEolVGx93NqT378PYVDa2962",
                caller=None,
                input={
                    "todos": [
                        {
                            "content": "Read current s05_todo_write/example/hello.py",
                            "status": "completed",
                        },
                        {
                            "content": "Add type hints, docstrings, and main guard",
                            "status": "completed",
                        },
                        {
                            "content": "Verify the refactored file",
                            "status": "completed",
                        },
                    ]
                },
                name="todo_write",
                type="tool_use",
            ),
        ],
    },
    {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "call_00_GEolVGx93NqT378PYVDa2962",
                "content": "Updated 3 tasks",
            }
        ],
    },
    {
        "role": "assistant",
        "content": [
            ThinkingBlock(
                signature="1303254a-9f17-4252-ac8c-49cb5c31bb8a",
                thinking="All tasks completed. Let me summarize the changes.",
                type="thinking",
            ),
            TextBlock(
                citations=None,
                text='Refactoring complete. Here\'s what was changed in `s05_todo_write/example/hello.py`:\n\n| Change | Before | After |\n|--------|--------|-------|\n| **Type hints** | `def greet(name)` | `def greet(name: str) -> str:` and `def main() -> None:` |\n| **Docstrings** | None | Added Google-style docstrings to `greet()` and `main()` |\n| **Main guard** | `greet("Claude")` at module level | Script logic moved to `main()`, called via `if __name__ == "__main__":` |\n| **String formatting** | `"Hello, " + name` (concatenation) | `f"Hello, {name}"` (f-string) |\n| **Return value** | `greet()` printed directly (returned `None`) | `greet()` returns the string; `main()` handles printing |\n\nThe script still outputs `Hello, Claude` when run directly.',
                type="text",
            ),
        ],
    },
]
```

# s02_tool_use 工具分发原理

核心思想：将"工具名称"映射到"处理函数"，实现动态分发，避免硬编码。

## 1. 工具定义

```python
TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    # ... 其他工具
]
```

**作用**：定义可用的工具列表，每个工具包含名称、描述和输入参数模式。

## 2. 工具实现

```python
def run_bash(command: str) -> str: # 实现bash工具
def run_read(path: str, limit: int | None = None) -> str: # 实现 read_file 工具
def run_write(path: str, content: str) -> str: # 实现 write_file 工具
def run_edit(path: str, old_text: str, new_text: str) -> str: # 实现 edit_file 工具
def run_glob(pattern: str) -> str: # 实现 glob 工具
```

**作用**：每个工具都有对应的 Python 函数，实现具体功能。

### 3. 分发映射

```python
TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob,
}
```

**作用**：将工具名称（字符串）映射到对应的处理函数（函数对象）。

### 4. 工具调用

```python
results = []
for block in response.content:
    if block.type == "tool_use":
        print(f"\033[33m> {block.name}\033[0m")
        handler = TOOL_HANDLERS.get(block.name) # 根据名称查找处理函数
        output = handler(**block.input) if handler else f"Unknown: {block.name}" # 动态调用
        print(str(output)[:200])
        results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
```

**作用**：根据模型返回的工具名称，动态查找并调用对应的处理函数。

## 工作流程示例

1. 模型返回工具调用：`ToolUseBlock(name="bash", input={"command": "ls"})`
2. 查找处理函数：`handler = TOOL_HANDLERS.get("bash")` -> 返回 `run_bash`
3. 动态调用：`handler(**{"command": "ls"})` -> 相当于 `run_bash(command="ls")`
4. 返回结果：将执行结果反馈给模型

## 优点

- **可扩展**：添加新工具只需：实现函数 -> 添加到 `TOOLS` -> 添加到 `TOOL_HANDLERS`
- **解耦**：工具定义、实现、调用完全分离
- **通用**：`agent_loop` 可以处理任何工具，无需修改

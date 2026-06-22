#!/usr/bin/env python3
"""
s01_agent_loop.py - The Agent Loop

The entire secret of an AI coding agent in one pattern:

    while stop_reason == "tool_use":
        response = LLM(messages, tools)
        execute tools
        append results

    +----------+      +-------+      +---------+
    |   User   | ---> |  LLM  | ---> |  Tool   |
    |  prompt  |      |       |      | execute |
    +----------+      +---+---+      +----+----+
                          ^               |
                          |   tool_result |
                          +---------------+
                          (loop continues)

This is the core loop: feed tool results back to the model
until the model decides to stop. Production agents layer
policy, hooks, and lifecycle controls on top.

Usage:
    pip install anthropic python-dotenv
    ANTHROPIC_API_KEY=... python s01_agent_loop/code.py
"""

import os
import subprocess

try:
    import readline
    # macOS 的 libedit 在处理中文输入时有退格问题，这四行修复它
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

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

"""
System Prompt 的作用是给大模型设定角色和行为准则，在这里我们告诉它：

- 你是一个位于当前目录的编码代理。
- 你只能使用 bash 来解决任务。
- 你应该直接行动，而不是解释你的想法。

注：os.getcwd() 会返回当前工作目录的路径，这样模型就知道它的“位置”了。
"""
SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

"""
大模型自身并不能操作你的计算机，它只能输出文本。
我们需要通过 API 告诉它有什么工具可以用，以及如何使用它们。
在这个例子里，我们定义了一个名为 "bash" 的工具，它接受一个字符串参数 "command"，表示要执行的命令。
"""
# ── Tool definition: just bash ────────────────────────────
TOOLS = [{
    "name": "bash",
    "description": "Run a shell command.",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
}]


"""
当大模型决定使用工具时，run_bash 函数负责真正地在计算机上执行命令。
"""
# ── Tool execution ────────────────────────────────────────
def run_bash(command: str) -> str:
    # 为了安全起见，我们在这里简单地过滤掉一些明显危险的命令
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    """
    any(d in command for d in dangerous) 检查 command 中是否含有任何一个 dangerous 列表中的危险命令片段。
    any(...) 接收一个可迭代对象，如果其中任何一个元素为 True，就返回 True，否则返回 False。
    for d in dangerous：遍历 dangerous 列表中的每个元素，依次赋值给变量 d。
    d in command：对每个 d，判断它是否是 command 字符串的子串。
    """
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        # subprocess.run 用于执行外部命令
        r = subprocess.run(command, shell=True, cwd=os.getcwd(),
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip() # strip() 用于去除字符串的首尾空白字符
        return out[:50000] if out else "(no output)" # out[:50000] 截取字符串指定部分（前 50000 个字符，0 ~ 49999）
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"


"""
agent_loop 函数实现了核心的循环逻辑：
1. 调用模型生成响应。
2. 如果模型调用了工具，就执行工具并收集结果。
3. 将工具结果作为用户输入反馈给模型，继续循环。
如果模型没有调用工具（即 stop_reason 不是 "tool_use"），就认为任务完成，退出循环。
"""
# ── The core pattern: a while loop that calls tools until the model stops ──
def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        import pdb; pdb.set_trace()
        """
        (Pdb) messages
        [{'role': 'user', 'content': 'Create a file called hello.py that prints "Hello, World!"'}]
        (Pdb) response
        Message(
            id='3396b225-f065-43e4-b3e6-aa34e38df409',
            container=None,
            content=[ThinkingBlock(signature='3396b225-f065-43e4-b3e6-aa34e38df409',thinking='The user wants me to create a hello.py file that prints "Hello, World!". Let me do that with a bash command.', type='thinking'), ToolUseBlock(id='call_00_602sW9GXjfwIxg2K2Eib9408', caller=None, input={'command': 'echo \'print("Hello, World!")\' > hello.py'}, name='bash', type='tool_use')],
            model='deepseek-v4-flash',
            role='assistant',
            stop_details=None,
            stop_reason='tool_use',
            stop_sequence=None,
            type='message',
            usage=Usage(cache_creation=None, cache_creation_input_tokens=0, cache_read_input_tokens=256, inference_geo=None, input_tokens=55, output_tokens=82, output_tokens_details=None, server_tool_use=None, service_tier='standard')
        )
        """

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        # If the model didn't call a tool, we're done
        if response.stop_reason != "tool_use":
            return

        # Execute each tool call, collect results
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\033[33m$ {block.input['command']}\033[0m")
                output = run_bash(block.input["command"])
                print(output[:200])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })

        # Feed tool results back, loop continues
        messages.append({"role": "user", "content": results})


# ── Entry point ──────────────────────────────────────────
if __name__ == "__main__":
    print("s01: Agent Loop")
    print("输入问题，回车发送。输入 q 退出。\n")

    history = []
    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        # import pdb; pdb.set_trace()
        """
        示例1：
        (Pdb) query
        'Create a file called hello.py that prints "Hello, World!"'
        (Pdb) history
        [{'role': 'user', 'content': 'Create a file called hello.py that prints "Hello, World!"'}, {'role': 'assistant', 'content': [ThinkingBlock(signature='b626670c-08ae-4d2f-a3a5-e1804b35b7f2', thinking='The user wants me to create a file called hello.py that prints "Hello, World!".', type='thinking'), ToolUseBlock(id='call_00_CrfVc0x2SlGHQWaDOfL54075', caller=None, input={'command': 'echo \'print("Hello, World!")\' > /home/local/code/learn-claude-code/hello.py'}, name='bash', type='tool_use')]}, {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'call_00_CrfVc0x2SlGHQWaDOfL54075', 'content': '(no output)'}]}, {'role': 'assistant', 'content': [ThinkingBlock(signature='f43c5d48-cc10-4a01-b232-6d2945bcefcd', thinking='The file has been created. Let me verify it exists and has the correct content.', type='thinking'), ToolUseBlock(id='call_00_VVrawDTgo2bLaaM38N223980', caller=None, input={'command': 'cat /home/local/code/learn-claude-code/hello.py'}, name='bash', type='tool_use')]}, {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'call_00_VVrawDTgo2bLaaM38N223980', 'content': 'print("Hello, World!")'}]}, {'role': 'assistant', 'content': [ThinkingBlock(signature='e8f0f9df-d3b5-4928-8579-334798ff72a8', thinking='The file has been created successfully with the correct content.', type='thinking'), TextBlock(citations=None, text='The file `hello.py` has been created successfully with `print("Hello, World!")`.', type='text')]}]
        
        示例2：
        (Pdb) query
        'List all Markdown files in this directory'
        (Pdb) history
        [{'role': 'user', 'content': 'List all Markdown files in this directory'}, {'role': 'assistant', 'content': [ThinkingBlock(signature='e2203a0f-e75e-401c-93d6-d284375ad2dc', thinking='The user wants me to list all Markdown files in the current directory. Let me use the bash tool to find them.', type='thinking'), ToolUseBlock(id='call_00_fSjAIL4TNW7fEOlQKDBm6501', caller=None, input={'command': 'ls -la *.md 2>/dev/null || echo "No Markdown files found in current directory"'}, name='bash', type='tool_use')]}, {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'call_00_fSjAIL4TNW7fEOlQKDBm6501', 'content': '-rw-r--r-- 1 local local 34319 Jun 16 16:48 README-ja.md\n-rw-r--r-- 1 local local 27193 Jun 16 16:48 README-zh.md\n-rw-r--r-- 1 local local 26210 Jun 16 16:48 README.md'}]}, {'role': 'assistant', 'content': [ThinkingBlock(signature='35aaa7db-3d21-43ed-8006-6a0c57de086f', thinking='There are 3 Markdown files in the current directory.', type='thinking'), TextBlock(citations=None, text='There are **3 Markdown files** in the current directory:\n\n1. **README.md**\n2. **README-ja.md** (Japanese)\n3. **README-zh.md** (Chinese)', type='text')]}]

        示例3：
        (Pdb) query
        'What is the current git branch?'
        (Pdb) history
        [{'role': 'user', 'content': 'What is the current git branch?'}, {'role': 'assistant', 'content': [ThinkingBlock(signature='0067d15d-e585-48ed-b060-4ac31a8305e0', thinking='The user wants to know the current git branch. I can use `git branch --show-current` or `git rev-parse --abbrev-ref HEAD` to get this information.', type='thinking'), ToolUseBlock(id='call_00_ZXGg4JvUBEAXtBWLT0o33651', caller=None, input={'command': 'cd /home/local/code/learn-claude-code && git branch --show-current'}, name='bash', type='tool_use')]}, {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'call_00_ZXGg4JvUBEAXtBWLT0o33651', 'content': 'main'}]}, {'role': 'assistant', 'content': [ThinkingBlock(signature='359d4223-84da-4782-ac0a-2d0c3b311fd4', thinking='The current git branch is "main".', type='thinking'), TextBlock(citations=None, text='The current git branch is **main**.', type='text')]}]
        """

        # Print the model's final text response
        # history[-1] 获取 history 列表中的最后一个元素；["content"] 从中提取出 content 字段。
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if getattr(block, "type", None) == "text":
                    print(block.text)
        print()

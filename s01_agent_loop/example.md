# S01示例

## 示例1

Prompt: 

```text
Create a file called hello.py that prints "Hello, World!"
```

History:

```python
[
    {
        'role': 'user',
        'content': 'Create a file called hello.py that prints "Hello, World!"'
    },
    {
        'role': 'assistant',
        'content': [
            ThinkingBlock(
                signature='b626670c-08ae-4d2f-a3a5-e1804b35b7f2',
                thinking='The user wants me to create a file called hello.py that prints "Hello, World!".',
                type='thinking'
            ),
            ToolUseBlock(
                id='call_00_CrfVc0x2SlGHQWaDOfL54075',
                caller=None,
                input={
                    'command': 'echo \'print("Hello, World!")\' > /home/local/code/learn-claude-code/hello.py'
                },
                name='bash',
                type='tool_use'
            )
        ]
    },
    {
        'role': 'user',
        'content': [
            {
                'type': 'tool_result',
                'tool_use_id': 'call_00_CrfVc0x2SlGHQWaDOfL54075',
                'content': '(no output)'
            }
        ]
    },
    {
        'role': 'assistant',
        'content': [
            ThinkingBlock(
                signature='f43c5d48-cc10-4a01-b232-6d2945bcefcd',
                thinking='The file has been created. Let me verify it exists and has the correct content.',
                type='thinking'
            ),
            ToolUseBlock(
                id='call_00_VVrawDTgo2bLaaM38N223980',
                caller=None,
                input={
                    'command': 'cat /home/local/code/learn-claude-code/hello.py'
                },
                name='bash',
                type='tool_use'
            )
        ]
    },
    {
        'role': 'user',
        'content': [
            {
                'type': 'tool_result',
                'tool_use_id': 'call_00_VVrawDTgo2bLaaM38N223980',
                'content': 'print("Hello, World!")'
            }
        ]
    },
    {
        'role': 'assistant',
        'content': [
            ThinkingBlock(
                signature='e8f0f9df-d3b5-4928-8579-334798ff72a8',
                thinking='The file has been created successfully with the correct content.',
                type='thinking'
            ),
            TextBlock(
                citations=None,
                text='The file `hello.py` has been created successfully with `print("Hello, World!")`.',
                type='text'
            )
        ]
    }
]
```

## 示例2

Prompt:

```text
List all Markdown files in this directory
```

History:

```python
[
    {
        'role': 'user',
        'content': 'List all Markdown files in this directory'
    },
    {
        'role': 'assistant',
        'content': [
            ThinkingBlock(
                signature='e2203a0f-e75e-401c-93d6-d284375ad2dc',
                thinking='The user wants me to list all Markdown files in the current directory. Let me use the bash tool to find them.',
                type='thinking'
            ),
            ToolUseBlock(
                id='call_00_fSjAIL4TNW7fEOlQKDBm6501',
                caller=None,
                input={
                    'command': 'ls -la *.md 2>/dev/null || echo "No Markdown files found in current directory"'
                },
                name='bash',
                type='tool_use'
            )
        ]
    },
    {
        'role': 'user',
        'content': [
            {
                'type': 'tool_result',
                'tool_use_id': 'call_00_fSjAIL4TNW7fEOlQKDBm6501',
                'content': '-rw-r--r-- 1 local local 34319 Jun 16 16:48 README-ja.md\n-rw-r--r-- 1 local local 27193 Jun 16 16:48 README-zh.md\n-rw-r--r-- 1 local local 26210 Jun 16 16:48 README.md'
            }
        ]
    },
    {
        'role': 'assistant',
        'content': [
            ThinkingBlock(
                signature='35aaa7db-3d21-43ed-8006-6a0c57de086f',
                thinking='There are 3 Markdown files in the current directory.',
                type='thinking'
            ),
            TextBlock(
                citations=None,
                text='There are **3 Markdown files** in the current directory:\n\n1. **README.md**\n2. **README-ja.md** (Japanese)\n3. **README-zh.md** (Chinese)',
                type='text'
            )
        ]
    }
]
```

## 示例3

Prompt:

```text
What is the current git branch?
```

History:

```python
[
    {
        'role': 'user',
        'content': 'What is the current git branch?'
    },
    {
        'role': 'assistant',
        'content': [
            ThinkingBlock(
                signature='0067d15d-e585-48ed-b060-4ac31a8305e0',
                thinking='The user wants to know the current git branch. I can use `git branch --show-current` or `git rev-parse --abbrev-ref HEAD` to get this information.',
                type='thinking'
            ),
            ToolUseBlock(
                id='call_00_ZXGg4JvUBEAXtBWLT0o33651',
                caller=None,
                input={
                    'command': 'cd /home/local/code/learn-claude-code && git branch --show-current'
                },
                name='bash',
                type='tool_use'
            )
        ]
    },
    {
        'role': 'user',
        'content': [
            {
                'type': 'tool_result',
                'tool_use_id': 'call_00_ZXGg4JvUBEAXtBWLT0o33651',
                'content': 'main'
            }
        ]
    },
    {
        'role': 'assistant',
        'content': [
            ThinkingBlock(
                signature='359d4223-84da-4782-ac0a-2d0c3b311fd4',
                thinking='The current git branch is "main".',
                type='thinking'
            ),
            TextBlock(
                citations=None,
                text='The current git branch is **main**.',
                type='text'
            )
        ]
    }
]
```

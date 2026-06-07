# MUST be set before any LiteLLM import to prevent Windows-style encoding
# errors in the LiteLLM caching layer (safe no-op on macOS/Linux).
import os
os.environ["PYTHONUTF8"] = "1"

# ---------------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------------
import asyncio
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Third-party
# ---------------------------------------------------------------------------
import litellm
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

# ---------------------------------------------------------------------------
# Configuration — edit these constants to change model / server
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL: str = "http://localhost:11434"

# LiteLLM Ollama provider prefix + model name served by Ollama.
# Use "ollama_chat/" so LiteLLM routes through the /api/chat endpoint,
# which properly handles multi-turn messages and tool calls.
OLLAMA_MODEL: str = "ollama_chat/gemma4:e4b"

APP_NAME: str = "local_coding_assistant"
USER_ID: str = "local_user"

# Gemma 4 recommended hyper-parameters.
# top_k is forwarded to Ollama via extra_body["options"]; temperature and
# top_p are standard and understood by every LiteLLM backend.
_GENERATION_KWARGS: dict = {
    "temperature": 1.0,
    "top_p": 0.95,
    "max_tokens": 8192,
    # Ollama-specific option; silently ignored by other backends.
    "extra_body": {"options": {"top_k": 64}},
}

# Gemma 4 thinking token (<|think|>) instructs the model to reason before
# composing its reply.  Remove it if your Ollama build does not support it.
_SYSTEM_PROMPT: str = """\
<|think|>

You are an expert software engineer and local coding assistant.
You have four tools available:

  • read_file        — read any file from disk
  • write_file       — create or overwrite a file
  • run_terminal_command — execute a shell command and capture output
  • list_directory   — list the contents of a folder

Work step-by-step:
1. Understand what the user wants.
2. Plan the sequence of tool calls needed.
3. Execute each tool call, inspect the result, and adapt if something fails.
4. Report what you did and what the outcome was.

Safety rules:
• Never run destructive commands (rm -rf, format, etc.) without explicit user approval.
• Always show the full output of every tool call in your reply.
• If a tool call fails, explain why and suggest an alternative approach.
• Prefer idiomatic, readable, well-structured code in every file you write.
"""


# ---------------------------------------------------------------------------
# Tool 1 — read_file
# ---------------------------------------------------------------------------

def read_file(path: str) -> dict:
    """Read the contents of a file from disk and return them as a string.

    Args:
        path: Absolute or relative (to cwd) path to the target file.

    Returns:
        {
            "success": bool,
            "content": str,   # full file text on success, "" on failure
            "error":   str,   # empty string on success, message on failure
        }
    """
    try:
        file_path = Path(path).expanduser().resolve()

        if not file_path.exists():
            return {"success": False, "content": "", "error": f"File not found: {file_path}"}
        if not file_path.is_file():
            return {"success": False, "content": "", "error": f"Not a file: {file_path}"}

        content = file_path.read_text(encoding="utf-8", errors="replace")
        return {"success": True, "content": content, "error": ""}

    except PermissionError:
        return {"success": False, "content": "", "error": f"Permission denied: {path}"}
    except OSError as exc:
        return {"success": False, "content": "", "error": str(exc)}


# ---------------------------------------------------------------------------
# Tool 2 — write_file
# ---------------------------------------------------------------------------

def write_file(path: str, content: str, create_parents: bool = True) -> dict:
    """Write (or overwrite) a file on disk with the given text content.

    Args:
        path:           Absolute or relative path to the destination file.
        content:        Full text to write.  Existing files are replaced.
        create_parents: When True, missing parent directories are created
                        automatically (like `mkdir -p`).

    Returns:
        {
            "success":       bool,
            "bytes_written": int,   # 0 on failure
            "absolute_path": str,   # resolved path that was written
            "error":         str,
        }
    """
    try:
        file_path = Path(path).expanduser().resolve()

        if create_parents:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        encoded = content.encode("utf-8")
        file_path.write_bytes(encoded)

        return {
            "success": True,
            "bytes_written": len(encoded),
            "absolute_path": str(file_path),
            "error": "",
        }

    except PermissionError:
        return {"success": False, "bytes_written": 0, "absolute_path": "", "error": f"Permission denied: {path}"}
    except OSError as exc:
        return {"success": False, "bytes_written": 0, "absolute_path": "", "error": str(exc)}


# ---------------------------------------------------------------------------
# Tool 3 — run_terminal_command
# ---------------------------------------------------------------------------

def run_terminal_command(
    command: str,
    working_directory: Optional[str] = None,
    timeout: int = 60,
) -> dict:
    """Execute a shell command and capture its stdout and stderr.

    The command is run through the system shell (``/bin/sh`` on POSIX,
    ``cmd.exe`` on Windows) so pipes, redirections, and built-ins work.

    Args:
        command:           The full shell command string to execute.
        working_directory: Directory in which to run the command.
                           Defaults to the current working directory.
        timeout:           Kill the process if it runs longer than this many
                           seconds.  Defaults to 60.

    Returns:
        {
            "success":    bool,
            "stdout":     str,
            "stderr":     str,
            "returncode": int,   # -1 on timeout or internal error
            "error":      str,   # empty on success
        }
    """
    try:
        cwd = (
            Path(working_directory).expanduser().resolve()
            if working_directory
            else Path.cwd()
        )

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error": "",
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": f"Timed out after {timeout}s: {command}",
        }
    except OSError as exc:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Tool 4 — list_directory
# ---------------------------------------------------------------------------

def list_directory(path: str = ".", show_hidden: bool = False) -> dict:
    """List the contents of a directory, separating files from sub-folders.

    Args:
        path:        Directory to inspect.  Defaults to the current directory.
        show_hidden: Include entries whose names start with ``'.'``.

    Returns:
        {
            "success":     bool,
            "directories": list[str],   # sub-folder names, trailing '/'
            "files":       list[str],   # file names
            "error":       str,
        }
    """
    try:
        dir_path = Path(path).expanduser().resolve()

        if not dir_path.exists():
            return {"success": False, "directories": [], "files": [], "error": f"Not found: {dir_path}"}
        if not dir_path.is_dir():
            return {"success": False, "directories": [], "files": [], "error": f"Not a directory: {dir_path}"}

        dirs, files = [], []
        for entry in sorted(dir_path.iterdir(), key=lambda e: e.name.lower()):
            if not show_hidden and entry.name.startswith("."):
                continue
            if entry.is_dir():
                dirs.append(entry.name + "/")
            else:
                files.append(entry.name)

        return {"success": True, "directories": dirs, "files": files, "error": ""}

    except PermissionError:
        return {"success": False, "directories": [], "files": [], "error": f"Permission denied: {path}"}
    except OSError as exc:
        return {"success": False, "directories": [], "files": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# LiteLLM + ADK wiring
# ---------------------------------------------------------------------------

def _configure_litellm() -> None:
    """Apply global LiteLLM settings before the first model call."""
    # Tell Ollama's base URL to LiteLLM's environment layer.
    os.environ.setdefault("OLLAMA_API_BASE", OLLAMA_BASE_URL)

    # Silently drop parameters that a specific backend doesn't understand
    # instead of raising an error (e.g. extra_body on some providers).
    litellm.drop_params = True

    # Keep logs quiet; flip to True for debugging model I/O.
    litellm.set_verbose = False


def _build_model() -> LiteLlm:
    """Construct the LiteLlm model wrapper pointing at the local Ollama server."""
    return LiteLlm(
        model=OLLAMA_MODEL,
        api_base=OLLAMA_BASE_URL,
        **_GENERATION_KWARGS,
    )


def _build_agent(model: LiteLlm) -> LlmAgent:
    """Assemble the LlmAgent with all four coding tools."""
    return LlmAgent(
        name="coding_assistant",
        model=model,
        tools=[read_file, write_file, run_terminal_command, list_directory],
        instruction=_SYSTEM_PROMPT,
        description=(
            "A fully local coding assistant backed by Gemma 4 (via Ollama). "
            "It can read/write files and execute shell commands on your machine."
        ),
    )


# ---------------------------------------------------------------------------
# Interactive agentic loop
# ---------------------------------------------------------------------------

def _print_banner() -> None:
    width = 62
    print("=" * width)
    print("  Local Coding Assistant  —  Gemma 4 via Ollama")
    print("=" * width)
    print(f"  Model  : {OLLAMA_MODEL}")
    print(f"  Server : {OLLAMA_BASE_URL}")
    print("  Tools  : read_file · write_file · run_terminal_command · list_directory")
    print("  Type 'quit', 'exit', or press Ctrl-C to stop.")
    print("=" * width)


async def run_interactive_loop() -> None:
    """Start the REPL-style coding assistant session.

    Each user message is forwarded to the ADK runner which orchestrates
    model inference, tool calls, and result synthesis automatically.
    """
    _configure_litellm()
    _print_banner()

    model = _build_model()
    agent = _build_agent(model)

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    session_id = str(uuid.uuid4())
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    print(f"\nSession ID: {session_id}\n")

    while True:
        # ── Prompt ──────────────────────────────────────────────────────────
        try:
            raw = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nSession ended.  Goodbye!")
            break

        if not raw:
            continue
        if raw.lower() in {"quit", "exit", "q", ":q"}:
            print("Goodbye!")
            break

        # ── Run one agent turn ───────────────────────────────────────────────
        message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=raw)],
        )

        print("\nAssistant:", flush=True)

        try:
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=session_id,
                new_message=message,
            ):
                # Surface tool-call / tool-response events as inline notices.
                if event.content:
                    for part in event.content.parts:
                        fc = getattr(part, "function_call", None)
                        fr = getattr(part, "function_response", None)

                        if fc:
                            args_preview = ", ".join(
                                f"{k}={repr(v)[:60]}" for k, v in (fc.args or {}).items()
                            )
                            print(f"  [tool call]  {fc.name}({args_preview})", flush=True)

                        elif fr:
                            success = (fr.response or {}).get("success", "?")
                            print(f"  [tool result] {fr.name} → success={success}", flush=True)

                # Final model reply — print the full text.
                if event.is_final_response():
                    if event.content and event.content.parts:
                        reply = "".join(
                            p.text
                            for p in event.content.parts
                            if getattr(p, "text", None)
                        )
                        print(reply, flush=True)

        except Exception as exc:  # noqa: BLE001
            print(
                f"\n[ERROR] Agent turn failed: {exc}\n"
                "Check that Ollama is running (`ollama serve`) and the model is\n"
                f"available (`ollama pull {OLLAMA_MODEL.split('/', 1)[-1]}`).",
                file=sys.stderr,
            )

        print()  # blank line between turns


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(run_interactive_loop())

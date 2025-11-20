import typer
import subprocess
import sys
import os
import signal
from typing import List
from rich.console import Console

app = typer.Typer(add_completion=False)
console = Console()

def find_project_root() -> str:
    """
    Locate the project root (containing 'coders').
    1. Check CWD.
    2. Check relative to this file (installed package).
    """
    # Check if we are in the root (dev mode)
    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, "coders")):
        return cwd
    
    # Check if installed package (e.g. site-packages/coder2api)
    # This file is in src/coder2api/main.py or site-packages/coder2api/main.py
    # We need to find where 'coders' is relative to the package?
    # If installed via pip, 'coders' might not be there unless packaged.
    # Assuming we might be running from a clone but invoked via 'uv run' from a subdirectory?
    
    # Try traversing up from __file__
    current_path = os.path.abspath(os.path.dirname(__file__))
    # Go up until we find 'coders' or hit root
    temp_path = current_path
    while temp_path != "/" and temp_path != "":
        if os.path.isdir(os.path.join(temp_path, "coders")):
            return temp_path
        temp_path = os.path.dirname(temp_path)
        
    # Fallback to CWD and hope for the best (or fail later)
    return cwd

PROJECT_ROOT = find_project_root()

def run_subprocess(command: List[str], env=None, cwd=None):
    try:
        if cwd:
            os.chdir(cwd)
        if env:
            os.environ.update(env)
        
        os.execvp(command[0], command)
    except Exception as e:
        console.print(f"[red]Error running command: {e}[/red]")
        sys.exit(1)

@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def codex(ctx: typer.Context):
    """
    Wrapper for ChatMock CLI.
    """
    args = ctx.args
    cmd = [sys.executable, "-m", "chatmock.cli"] + args
    run_subprocess(cmd)

@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def cc(ctx: typer.Context):
    """
    Wrapper for Claude Code API.
    """
    args = ctx.args
    cmd = [sys.executable, "-m", "claude_code_api.main"] + args
    run_subprocess(cmd)

@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def gemini(ctx: typer.Context):
    """
    Wrapper for Gemini CLI Proxy.
    """
    args = ctx.args
    gemini_path = os.path.join(PROJECT_ROOT, "coders/gemini-cli-proxy")
    dist_index = os.path.join(gemini_path, "dist/index.js")
    
    if not os.path.exists(dist_index):
        console.print(f"[red]Gemini Proxy not built at {dist_index}. Run 'coder2api build' or 'npm run build' in coders/gemini-cli-proxy[/red]")
        sys.exit(1)
    
    cmd = ["node", dist_index] + args
    run_subprocess(cmd, cwd=gemini_path)

@app.command()
def build():
    """
    Builds all dependencies (Python and Node.js).
    """
    console.print(f"Project Root detected: {PROJECT_ROOT}")
    
    # 1. Python Dependencies (uv sync)
    console.print("[bold green]Building Python environment (uv sync)...[/bold green]")
    try:
        # Run uv sync in the project root
        subprocess.run(["uv", "sync"], cwd=PROJECT_ROOT, check=True)
    except subprocess.CalledProcessError:
        console.print("[red]Failed to sync Python dependencies.[/red]")
        sys.exit(1)
    except FileNotFoundError:
        console.print("[red]'uv' command not found. Please install uv.[/red]")
        sys.exit(1)

    # 2. Node.js Dependencies (Gemini Proxy)
    gemini_path = os.path.join(PROJECT_ROOT, "coders/gemini-cli-proxy")
    console.print(f"[bold green]Building Gemini Proxy in {gemini_path}...[/bold green]")
    
    # Check if npm is available
    try:
        subprocess.run(["npm", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
         console.print("[red]npm not found. Please install Node.js and npm.[/red]")
         sys.exit(1)

    try:
        subprocess.run(["npm", "install"], cwd=gemini_path, check=True)
        subprocess.run(["npm", "run", "build"], cwd=gemini_path, check=True)
    except subprocess.CalledProcessError:
        console.print("[red]Failed to build Gemini Proxy.[/red]")
        sys.exit(1)
        
    console.print("[bold green]Build complete![/bold green]")

@app.command()
def serve():
    """
    Starts all services and the unified proxy.
    """
    processes = []
    
    def cleanup(signum, frame):
        console.print("\n[bold yellow]Shutting down services...[/bold yellow]")
        for p in processes:
            if p.poll() is None:
                p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    GEMINI_PORT = "3001"
    CODEX_PORT = "3002"
    CC_PORT = "3003"
    PROXY_PORT = "8069"
    
    log_dir = os.path.join(PROJECT_ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    console.print(f"Logs will be written to {log_dir}")

    # Helper to start process
    def start_service(name, cmd, cwd=None, env=None):
        f_out = open(os.path.join(log_dir, f"{name}.out.log"), "w")
        f_err = open(os.path.join(log_dir, f"{name}.err.log"), "w")
        p = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=f_out,
            stderr=f_err,
            env=env
        )
        processes.append(p)
        return p

    # 1. Start Gemini Proxy
    console.print(f"[green]Starting Gemini Proxy on port {GEMINI_PORT}...[/green]")
    gemini_path = os.path.join(PROJECT_ROOT, "coders/gemini-cli-proxy")
    start_service("gemini", ["node", "dist/index.js", "--port", GEMINI_PORT], cwd=gemini_path)
    
    # 2. Start ChatMock
    console.print(f"[green]Starting ChatMock on port {CODEX_PORT}...[/green]")
    start_service("chatmock", [sys.executable, "-m", "chatmock.cli", "serve", "--port", CODEX_PORT])
    
    # 3. Start Claude Code API
    console.print(f"[green]Starting Claude Code API on port {CC_PORT}...[/green]")
    start_service("claude-code", [sys.executable, "-m", "uvicorn", "claude_code_api.main:app", "--port", CC_PORT, "--host", "127.0.0.1"])
    
    # 4. Start Coder2API Proxy
    console.print(f"[bold green]Starting Unified Proxy on port {PROXY_PORT}...[/bold green]")
    console.print(f"  - http://localhost:{PROXY_PORT}/codex -> ChatMock")
    console.print(f"  - http://localhost:{PROXY_PORT}/cc    -> Claude Code API")
    console.print(f"  - http://localhost:{PROXY_PORT}/gemini -> Gemini Proxy")
    
    env = os.environ.copy()
    env["CODER2API_GEMINI_PORT"] = GEMINI_PORT
    env["CODER2API_CODEX_PORT"] = CODEX_PORT
    env["CODER2API_CC_PORT"] = CC_PORT
    
    # We run uvicorn for the proxy
    # Note: we use 'coder2api.server:app' assuming the package is installed/available
    p_proxy = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "coder2api.server:app", "--port", PROXY_PORT, "--host", "0.0.0.0"],
        env=env
    )
    processes.append(p_proxy)
    
    # Wait for proxy
    p_proxy.wait()
    cleanup(None, None)

if __name__ == "__main__":
    app()
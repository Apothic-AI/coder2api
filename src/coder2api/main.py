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
    """
    # 1. Check if 'coders' is inside the package (pip installed)
    # __file__ is src/coder2api/main.py or site-packages/coder2api/main.py
    package_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.isdir(os.path.join(package_dir, "coders")):
        return package_dir

    # 2. Check CWD (Dev mode root)
    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, "coders")):
        return cwd

    # 3. Traverse up from __file__ (Dev mode src/)
    temp_path = package_dir
    while temp_path != "/" and temp_path != "":
        if os.path.isdir(os.path.join(temp_path, "coders")):
            return temp_path
        temp_path = os.path.dirname(temp_path)
        
    # Fallback
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
    # gemini-cli-proxy is now inside the package
    package_dir = os.path.dirname(os.path.abspath(__file__))
    gemini_path = os.path.join(package_dir, "gemini-cli-proxy")
    dist_index = os.path.join(gemini_path, "dist/index.js")
    node_modules = os.path.join(gemini_path, "node_modules")
    
    # Check if node_modules exists
    if not os.path.exists(node_modules):
        console.print("[yellow]Node dependencies not found. Installing...[/yellow]")
        try:
            subprocess.run(["npm", "install"], cwd=gemini_path, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
             console.print("[red]npm not found or failed. Please install Node.js and run 'npm install' in the gemini-cli-proxy directory.[/red]")
             sys.exit(1)

    # Check if built
    if not os.path.exists(dist_index):
        console.print("[yellow]Gemini Proxy not built. Building...[/yellow]")
        try:
            subprocess.run(["npm", "run", "build"], cwd=gemini_path, check=True)
        except subprocess.CalledProcessError:
            console.print("[red]Build failed.[/red]")
            sys.exit(1)
    
    cmd = ["node", dist_index] + args
    run_subprocess(cmd, cwd=gemini_path)

@app.command()
def build():
    """
    Manually builds Node.js dependencies (Gemini Proxy).
    Python dependencies are installed via pip/uv sync.
    """
    package_dir = os.path.dirname(os.path.abspath(__file__))
    gemini_path = os.path.join(package_dir, "gemini-cli-proxy")
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
    
    # Logs to CWD
    log_dir = os.path.join(os.getcwd(), "logs")
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
    package_dir = os.path.dirname(os.path.abspath(__file__))
    gemini_path = os.path.join(package_dir, "gemini-cli-proxy")
    
    # Ensure deps and build
    node_modules = os.path.join(gemini_path, "node_modules")
    dist_index = os.path.join(gemini_path, "dist/index.js")
    
    if not os.path.exists(node_modules):
        console.print("[yellow]Gemini dependencies missing. Installing...[/yellow]")
        subprocess.run(["npm", "install"], cwd=gemini_path, check=True)
        
    if not os.path.exists(dist_index):
        console.print("[yellow]Gemini build missing. Building...[/yellow]")
        subprocess.run(["npm", "run", "build"], cwd=gemini_path, check=True)

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
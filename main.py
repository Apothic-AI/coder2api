import typer
import subprocess
import sys
import os
import signal
from typing import List
from rich.console import Console

app = typer.Typer(add_completion=False)
console = Console()

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
    # Assuming main.py is in root
    gemini_path = os.path.join(os.getcwd(), "coders/gemini-cli-proxy")
    dist_index = os.path.join(gemini_path, "dist/index.js")
    
    if not os.path.exists(dist_index):
        console.print(f"[red]Gemini Proxy not built at {dist_index}. Run 'npm run build' in coders/gemini-cli-proxy[/red]")
        sys.exit(1)
    
    cmd = ["node", dist_index] + args
    # We need to change dir so node app finds its package.json etc if needed
    run_subprocess(cmd, cwd=gemini_path)

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
    
    cwd = os.getcwd()
    log_dir = os.path.join(cwd, "logs")
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
    gemini_path = os.path.join(cwd, "coders/gemini-cli-proxy")
    start_service("gemini", ["node", "dist/index.js", "--port", GEMINI_PORT], cwd=gemini_path)
    
    # 2. Start ChatMock
    console.print(f"[green]Starting ChatMock on port {CODEX_PORT}...[/green]")
    start_service("chatmock", [sys.executable, "-m", "chatmock.cli", "serve", "--port", CODEX_PORT])
    
    # 3. Start Claude Code API
    console.print(f"[green]Starting Claude Code API on port {CC_PORT}...[/green]")
    start_service("claude-code", [sys.executable, "-m", "uvicorn", "claude_code_api.main:app", "--port", CC_PORT, "--host", "127.0.0.1"])
    
    # 4. Start Coder2API Proxy (Foreground or Background? Let's keep proxy in fg to see its logs?)
    # Actually, better to keep it controlled like others, but stream its output to console?
    # The user expects `coder2api serve` to run. If we hide everything, it looks dead.
    # Let's run the proxy in the main process? No, we want to catch signals.
    # We'll run proxy as subprocess but pipe output to stdout.
    
    console.print(f"[bold green]Starting Unified Proxy on port {PROXY_PORT}...[/bold green]")
    console.print(f"  - http://localhost:{PROXY_PORT}/codex -> ChatMock")
    console.print(f"  - http://localhost:{PROXY_PORT}/cc    -> Claude Code API")
    console.print(f"  - http://localhost:{PROXY_PORT}/gemini -> Gemini Proxy")
    
    env = os.environ.copy()
    env["CODER2API_GEMINI_PORT"] = GEMINI_PORT
    env["CODER2API_CODEX_PORT"] = CODEX_PORT
    env["CODER2API_CC_PORT"] = CC_PORT
    
    # We run uvicorn for the proxy
    p_proxy = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--port", PROXY_PORT, "--host", "0.0.0.0"],
        env=env
    )
    processes.append(p_proxy)
    
    # Wait for proxy
    p_proxy.wait()
    cleanup(None, None)

if __name__ == "__main__":
    app()
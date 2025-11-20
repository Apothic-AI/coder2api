import os
import subprocess
import sys
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Define the path to the Gemini proxy
        project_root = self.root
        # gemini-cli-proxy is now at src/coder2api/gemini-cli-proxy
        gemini_path = os.path.join(project_root, "src", "coder2api", "gemini-cli-proxy")
        
        # Skip if directory doesn't exist (e.g. in a lightweight sdist without it?)
        if not os.path.exists(gemini_path):
            print(f"WARNING: Gemini Proxy path not found at {gemini_path}")
            return

        print(f"Running custom build hook: Building Gemini Proxy in {gemini_path}...")
        
        npm_cmd = "npm"
        # Check if npm is available
        try:
            subprocess.run(["npm", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Try pnpm
            try:
                subprocess.run(["pnpm", "--version"], check=True, capture_output=True)
                npm_cmd = "pnpm"
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("WARNING: neither 'npm' nor 'pnpm' found. Skipping Gemini Proxy build. Please ensure Node.js is installed.")
                return

        print(f"Using {npm_cmd} for build.")

        # Run install and build
        try:
            # We use shell=False for security
            subprocess.run([npm_cmd, "install"], cwd=gemini_path, check=True)
            subprocess.run([npm_cmd, "run", "build"], cwd=gemini_path, check=True)
            print("Gemini Proxy built successfully.")
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to build Gemini Proxy: {e}")
            # Fail the build if we can't build the dependency
            sys.exit(1)

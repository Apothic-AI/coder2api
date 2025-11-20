import os
import subprocess
import sys
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Define the path to the Gemini proxy
        project_root = self.root
        gemini_path = os.path.join(project_root, "coders", "gemini-cli-proxy")
        
        # Skip if directory doesn't exist (e.g. in a lightweight sdist without it?)
        if not os.path.exists(gemini_path):
            return

        print(f"Running custom build hook: Building Gemini Proxy in {gemini_path}...")
        
        # Check if npm is available
        try:
            subprocess.run(["npm", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("WARNING: 'npm' not found. Skipping Gemini Proxy build. Please ensure Node.js is installed.")
            return

        # Run npm install and npm run build
        try:
            # We use shell=False for security, assuming npm is in PATH
            subprocess.run(["npm", "install"], cwd=gemini_path, check=True)
            subprocess.run(["npm", "run", "build"], cwd=gemini_path, check=True)
            print("Gemini Proxy built successfully.")
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to build Gemini Proxy: {e}")
            # Fail the build if we can't build the dependency
            sys.exit(1)

#!/usr/bin/env python3
"""Capture cargo build outputs for test data."""

import subprocess
import json
from pathlib import Path

def capture_cargo_output(project_path, output_prefix):
    """Capture both JSON and human-readable cargo outputs."""
    
    # Capture JSON format
    json_output = []
    cmd = ["cargo", "build", "--message-format", "json"]
    process = subprocess.Popen(
        cmd,
        cwd=project_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    for line in process.stdout:
        if line.strip():
            try:
                data = json.loads(line)
                if data.get('reason') == 'compiler-message':
                    json_output.append(line.strip())
            except:
                pass
    
    process.wait()
    
    # Save JSON output
    with open(f"test_data/{output_prefix}_json.txt", "w") as f:
        f.write("\n".join(json_output))
    
    # Capture human-readable format
    process = subprocess.Popen(
        ["cargo", "build"],
        cwd=project_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate()
    
    # Save human output
    with open(f"test_data/{output_prefix}_human.txt", "w") as f:
        f.write(stderr)
    
    print(f"Captured outputs for {output_prefix}")
    print(f"  - JSON messages: {len(json_output)}")
    print(f"  - Human output: {len(stderr)} chars")

# Capture outputs for each project
capture_cargo_output("test_projects/error_project", "error_output")
capture_cargo_output("test_projects/warning_project", "warning_output")
capture_cargo_output("test_projects/success_project", "success_output")
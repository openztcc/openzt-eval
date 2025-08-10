import subprocess
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .parser import CargoOutputParser, BuildMessage


class BuildProfile(Enum):
    DEBUG = "debug"
    RELEASE = "release"


@dataclass
class BuildResult:
    """Result of a cargo build operation."""
    success: bool
    messages: List[BuildMessage]
    stdout: str
    stderr: str
    return_code: int


class CargoBuilder:
    """Interface for running cargo build commands with various options."""
    
    def __init__(
        self,
        root_dir: Optional[Path] = None,
        manifest_path: Optional[Path] = None,
        target: Optional[str] = None,
        profile: BuildProfile = BuildProfile.DEBUG,
        use_nightly: bool = False,
    ):
        """
        Initialize a CargoBuilder instance.
        
        Args:
            root_dir: Root directory for cargo to run in. Defaults to current directory.
            manifest_path: Path to Cargo.toml. If not specified, cargo will search for it.
            target: Target triple to build for (e.g., 'x86_64-unknown-linux-gnu').
            profile: Build profile (debug or release).
            use_nightly: Whether to use nightly toolchain.
        """
        self.root_dir = root_dir or Path.cwd()
        self.manifest_path = manifest_path
        self.target = target
        self.profile = profile
        self.use_nightly = use_nightly
        self.parser = CargoOutputParser()
    
    def build(
        self,
        features: Optional[List[str]] = None,
        all_features: bool = False,
        no_default_features: bool = False,
        package: Optional[str] = None,
        workspace: bool = False,
        message_format: str = "json",
        extra_args: Optional[List[str]] = None,
        use_clippy: bool = False,
    ) -> BuildResult:
        """
        Run cargo build or cargo clippy with the specified options.
        
        Args:
            features: List of features to enable.
            all_features: Enable all features.
            no_default_features: Disable default features.
            package: Specific package to build in a workspace.
            workspace: Build all packages in the workspace.
            message_format: Output format ('json' or 'human').
            extra_args: Additional arguments to pass to cargo build.
            use_clippy: Run cargo clippy instead of cargo build for linting.
            
        Returns:
            BuildResult containing success status, parsed messages, and raw output.
        """
        cmd = self._build_command(
            features=features,
            all_features=all_features,
            no_default_features=no_default_features,
            package=package,
            workspace=workspace,
            message_format=message_format,
            extra_args=extra_args,
            use_clippy=use_clippy,
        )
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.root_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            stdout, stderr = process.communicate()
            
            # Parse messages if using JSON format
            messages = []
            if message_format == "json":
                messages = self.parser.parse_json_output(stdout)
            else:
                # For human-readable output, parse from stderr
                messages = self.parser.parse_human_output(stderr)
            
            return BuildResult(
                success=process.returncode == 0,
                messages=messages,
                stdout=stdout,
                stderr=stderr,
                return_code=process.returncode,
            )
            
        except Exception as e:
            return BuildResult(
                success=False,
                messages=[],
                stdout="",
                stderr=str(e),
                return_code=-1,
            )
    
    def clippy(
        self,
        features: Optional[List[str]] = None,
        all_features: bool = False,
        no_default_features: bool = False,
        package: Optional[str] = None,
        workspace: bool = False,
        message_format: str = "json",
        extra_args: Optional[List[str]] = None,
    ) -> BuildResult:
        """
        Run cargo clippy with the specified options.
        
        This is a convenience method that calls build() with use_clippy=True.
        
        Args:
            features: List of features to enable.
            all_features: Enable all features.
            no_default_features: Disable default features.
            package: Specific package to lint in a workspace.
            workspace: Lint all packages in the workspace.
            message_format: Output format ('json' or 'human').
            extra_args: Additional arguments to pass to cargo clippy.
            
        Returns:
            BuildResult containing success status, parsed messages, and raw output.
        """
        return self.build(
            features=features,
            all_features=all_features,
            no_default_features=no_default_features,
            package=package,
            workspace=workspace,
            message_format=message_format,
            extra_args=extra_args,
            use_clippy=True,
        )
    
    def _build_command(
        self,
        features: Optional[List[str]] = None,
        all_features: bool = False,
        no_default_features: bool = False,
        package: Optional[str] = None,
        workspace: bool = False,
        message_format: str = "json",
        extra_args: Optional[List[str]] = None,
        use_clippy: bool = False,
    ) -> List[str]:
        """Build the cargo command with all specified options."""
        # Start with cargo or cargo +nightly
        if self.use_nightly:
            if use_clippy:
                cmd = ["cargo", "+nightly", "clippy"]
            else:
                cmd = ["cargo", "+nightly", "build"]
        else:
            if use_clippy:
                cmd = ["cargo", "clippy"]
            else:
                cmd = ["cargo", "build"]
        
        # Add manifest path if specified
        if self.manifest_path:
            cmd.extend(["--manifest-path", str(self.manifest_path)])
        
        # Add target if specified
        if self.target:
            cmd.extend(["--target", self.target])
        
        # Add profile
        if self.profile == BuildProfile.RELEASE:
            cmd.append("--release")
        
        # Add features
        if features:
            cmd.extend(["--features", ",".join(features)])
        
        if all_features:
            cmd.append("--all-features")
        
        if no_default_features:
            cmd.append("--no-default-features")
        
        # Add package or workspace
        if package:
            cmd.extend(["--package", package])
        elif workspace:
            cmd.append("--workspace")
        
        # Add message format
        cmd.extend(["--message-format", message_format])
        
        # Add any extra arguments
        if extra_args:
            cmd.extend(extra_args)
        
        return cmd

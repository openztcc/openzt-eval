#!/usr/bin/env python3
"""Run basic tests for cargo-orchestrator."""

import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from cargo_orchestrator import CargoBuilder
from cargo_orchestrator.builder import BuildProfile
from cargo_orchestrator.parser import MessageLevel

def test_success_build():
    """Test building a successful project."""
    print("Testing successful build...")
    builder = CargoBuilder(
        root_dir=Path("test_projects/success_project")
    )
    result = builder.build()
    
    assert result.success is True
    assert result.return_code == 0
    print("✓ Success build test passed")

def test_error_build():
    """Test building a project with errors."""
    print("\nTesting error build...")
    builder = CargoBuilder(
        root_dir=Path("test_projects/error_project")
    )
    result = builder.build()
    
    assert result.success is False
    assert len(result.messages) > 0
    
    errors = [m for m in result.messages if m.level == MessageLevel.ERROR]
    print(f"  Found {len(errors)} errors")
    for err in errors[:3]:  # Show first 3 errors
        print(f"  - {err.message[:60]}...")
    
    print("✓ Error build test passed")

def test_warning_build():
    """Test building a project with warnings."""
    print("\nTesting warning build...")
    builder = CargoBuilder(
        root_dir=Path("test_projects/warning_project")
    )
    result = builder.build()
    
    assert result.success is True
    warnings = [m for m in result.messages if m.level == MessageLevel.WARNING]
    print(f"  Found {len(warnings)} warnings")
    for warn in warnings[:3]:  # Show first 3 warnings
        print(f"  - {warn.message[:60]}...")
    
    print("✓ Warning build test passed")

def test_release_build():
    """Test release build."""
    print("\nTesting release build...")
    builder = CargoBuilder(
        root_dir=Path("test_projects/success_project"),
        profile=BuildProfile.RELEASE
    )
    result = builder.build()
    
    assert result.success is True
    print("✓ Release build test passed")

def test_human_format():
    """Test human-readable format."""
    print("\nTesting human-readable format...")
    builder = CargoBuilder(
        root_dir=Path("test_projects/warning_project")
    )
    result = builder.build(message_format="human")
    
    assert result.success is True
    assert len(result.stderr) > 0
    assert len(result.messages) > 0
    print(f"  Parsed {len(result.messages)} messages from human format")
    print("✓ Human format test passed")

if __name__ == "__main__":
    print("Running cargo-orchestrator tests...\n")
    
    try:
        test_success_build()
        test_error_build()
        test_warning_build()
        test_release_build()
        test_human_format()
        
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
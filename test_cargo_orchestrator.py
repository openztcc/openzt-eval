#!/usr/bin/env python3
"""
Test suite for cargo-orchestrator library.
"""

import pytest
from pathlib import Path
from cargo_orchestrator import CargoBuilder, BuildResult
from cargo_orchestrator.builder import BuildProfile
from cargo_orchestrator.parser import MessageLevel, CargoOutputParser


class TestCargoBuilder:
    """Test the CargoBuilder class."""
    
    def test_basic_build(self):
        """Test basic build functionality."""
        builder = CargoBuilder(
            root_dir=Path("test_projects/success_project")
        )
        result = builder.build()
        
        assert isinstance(result, BuildResult)
        assert result.success is True
        assert result.return_code == 0
        assert len(result.messages) == 0  # No errors or warnings
    
    def test_build_with_errors(self):
        """Test building a project with compilation errors."""
        builder = CargoBuilder(
            root_dir=Path("test_projects/error_project")
        )
        result = builder.build()
        
        assert result.success is False
        assert result.return_code != 0
        assert len(result.messages) > 0
        
        # Check for specific errors
        error_messages = [m for m in result.messages if m.level == MessageLevel.ERROR]
        assert len(error_messages) >= 4  # We expect at least 4 errors
        
        # Verify error types
        error_texts = [m.message for m in error_messages]
        assert any("cannot find value `x`" in msg for msg in error_texts)
        assert any("mismatched types" in msg for msg in error_texts)
        assert any("cannot find function `undefined_function`" in msg for msg in error_texts)
    
    def test_build_with_warnings(self):
        """Test building a project with warnings."""
        builder = CargoBuilder(
            root_dir=Path("test_projects/warning_project")
        )
        result = builder.build()
        
        assert result.success is True  # Warnings don't fail the build
        assert len(result.messages) > 0
        
        # Check for specific warnings
        warning_messages = [m for m in result.messages if m.level == MessageLevel.WARNING]
        assert len(warning_messages) >= 5
        
        # Verify warning types
        warning_texts = [m.message for m in warning_messages]
        assert any("unused variable" in msg for msg in warning_texts)
        assert any("unnecessary parentheses" in msg for msg in warning_texts)
        assert any("unreachable statement" in msg for msg in warning_texts)
    
    def test_release_build(self):
        """Test release build configuration."""
        builder = CargoBuilder(
            root_dir=Path("test_projects/success_project"),
            profile=BuildProfile.RELEASE
        )
        result = builder.build()
        
        assert result.success is True
    
    def test_build_command_generation(self):
        """Test that build commands are generated correctly."""
        builder = CargoBuilder(
            root_dir=Path("."),
            manifest_path=Path("Cargo.toml"),
            target="x86_64-unknown-linux-gnu",
            profile=BuildProfile.RELEASE,
            use_nightly=True
        )
        
        cmd = builder._build_command(
            features=["feat1", "feat2"],
            all_features=False,
            no_default_features=True,
            package="my-package",
            message_format="json"
        )
        
        assert cmd[0] == "cargo"
        assert "+nightly" in cmd
        assert "build" in cmd
        assert "--manifest-path" in cmd
        assert "Cargo.toml" in cmd
        assert "--target" in cmd
        assert "x86_64-unknown-linux-gnu" in cmd
        assert "--release" in cmd
        assert "--features" in cmd
        assert "feat1,feat2" in cmd
        assert "--no-default-features" in cmd
        assert "--package" in cmd
        assert "my-package" in cmd
        assert "--message-format" in cmd
        assert "json" in cmd


class TestCargoOutputParser:
    """Test the CargoOutputParser class."""
    
    def test_parse_json_errors(self):
        """Test parsing JSON error output."""
        parser = CargoOutputParser()
        
        # Load test data
        with open("test_data/error_output_json.txt", "r") as f:
            json_output = f.read()
        
        messages = parser.parse_json_output(json_output)
        
        assert len(messages) > 0
        errors = [m for m in messages if m.level == MessageLevel.ERROR]
        assert len(errors) >= 4
        
        # Check specific error details
        undefined_var_error = next(
            (m for m in errors if "cannot find value `x`" in m.message), 
            None
        )
        assert undefined_var_error is not None
        assert undefined_var_error.code == "E0425"
        assert len(undefined_var_error.spans) > 0
        assert undefined_var_error.spans[0].line_start == 3
    
    def test_parse_json_warnings(self):
        """Test parsing JSON warning output."""
        parser = CargoOutputParser()
        
        # Load test data
        with open("test_data/warning_output_json.txt", "r") as f:
            json_output = f.read()
        
        messages = parser.parse_json_output(json_output)
        
        assert len(messages) > 0
        warnings = [m for m in messages if m.level == MessageLevel.WARNING]
        assert len(warnings) >= 5
        
        # Check specific warning details
        unused_var_warning = next(
            (m for m in warnings if "unused variable: `unused_var`" in m.message),
            None
        )
        assert unused_var_warning is not None
        assert unused_var_warning.code == "unused_variables"
        assert len(unused_var_warning.spans) > 0
        assert unused_var_warning.spans[0].line_start == 6
    
    def test_parse_human_errors(self):
        """Test parsing human-readable error output."""
        parser = CargoOutputParser()
        
        # Load test data
        with open("test_data/error_output_human.txt", "r") as f:
            human_output = f.read()
        
        messages = parser.parse_human_output(human_output)
        
        assert len(messages) > 0
        errors = [m for m in messages if m.level == MessageLevel.ERROR]
        assert len(errors) >= 4
        
        # Check that we can extract basic error information
        assert any("cannot find value `x`" in m.message for m in errors)
        assert any("E0425" in (m.code or "") for m in errors)
    
    def test_parse_human_warnings(self):
        """Test parsing human-readable warning output."""
        parser = CargoOutputParser()
        
        # Load test data
        with open("test_data/warning_output_human.txt", "r") as f:
            human_output = f.read()
        
        messages = parser.parse_human_output(human_output)
        
        assert len(messages) > 0
        warnings = [m for m in messages if m.level == MessageLevel.WARNING]
        assert len(warnings) >= 5
        
        # Check warning content
        assert any("unused variable" in m.message for m in warnings)
        assert any("unnecessary parentheses" in m.message for m in warnings)
    
    def test_empty_output(self):
        """Test parsing empty output."""
        parser = CargoOutputParser()
        
        # Test empty JSON
        messages = parser.parse_json_output("")
        assert messages == []
        
        # Test empty human output
        messages = parser.parse_human_output("")
        assert messages == []
    
    def test_malformed_json(self):
        """Test handling of malformed JSON."""
        parser = CargoOutputParser()
        
        malformed = '{"invalid": json}\n{"reason": "compiler-message"}'
        messages = parser.parse_json_output(malformed)
        
        # Should skip malformed lines but continue parsing
        assert len(messages) == 0  # Second line lacks required fields


class TestIntegration:
    """Integration tests using real cargo projects."""
    
    def test_full_workflow(self):
        """Test the full workflow of building and parsing."""
        # Build a project with errors
        builder = CargoBuilder(
            root_dir=Path("test_projects/error_project")
        )
        result = builder.build()
        
        assert not result.success
        assert len(result.messages) > 0
        
        # Check message structure
        for msg in result.messages:
            assert msg.level in MessageLevel
            assert msg.message
            if msg.level == MessageLevel.ERROR:
                assert msg.rendered  # Should have full rendered output
    
    def test_human_format_integration(self):
        """Test building with human-readable format."""
        builder = CargoBuilder(
            root_dir=Path("test_projects/warning_project")
        )
        result = builder.build(message_format="human")
        
        assert result.success
        assert result.stderr  # Human format outputs to stderr
        assert len(result.messages) > 0  # Parser should extract messages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
Unit tests for Autopoiesis Model Context Protocol (MCP) server.
"""

import json
from autopoiesis.mcp_server import handle_tool_call, TOOLS_METADATA


def test_mcp_tools_metadata():
    tool_names = [t["name"] for t in TOOLS_METADATA]
    assert "autopoiesis_evolve" in tool_names
    assert "autopoiesis_export_genome" in tool_names
    assert "autopoiesis_import_genome" in tool_names
    assert "autopoiesis_security_audit" in tool_names


def test_mcp_security_audit_tool(tmp_path):
    # Safe package
    safe_pkg = tmp_path / "safe.json"
    safe_pkg.write_text(json.dumps({
        "workload": "mandelbrot",
        "chromosome": {
            "id": "c123",
            "generation": 1,
            "parent_id": "p0",
            "source_type": "PYTHON_AST",
            "entry_symbol": "mandelbrot_pixel",
            "code": "def mandelbrot_pixel(c_real, c_imag, max_iter):\n    return 42\n",
        }
    }), encoding="utf-8")

    res = handle_tool_call("autopoiesis_security_audit", {"package_path": str(safe_pkg)})
    assert "PASSED" in res
    assert "c123" in res

    # Malicious package
    bad_pkg = tmp_path / "bad.json"
    bad_pkg.write_text(json.dumps({
        "workload": "mandelbrot",
        "chromosome": {
            "id": "c_bad",
            "generation": 1,
            "parent_id": "p0",
            "source_type": "PYTHON_AST",
            "entry_symbol": "mandelbrot_pixel",
            "code": "import os\ndef mandelbrot_pixel(): os.system('echo bad')\n",
        }
    }), encoding="utf-8")

    res_bad = handle_tool_call("autopoiesis_security_audit", {"package_path": str(bad_pkg)})
    assert "VIOLATION DETECTED" in res_bad
    assert "os" in res_bad

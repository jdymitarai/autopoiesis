# 🔌 Hooking Autopoiesis into Any AI Agent (Universal Integration Guide)

> *"Give your AI coding assistant the power of autonomous code autophagy, compiler transpilation, and apoptotic immunity."*

Autopoiesis can be integrated into **any modern AI Agent, IDE, or framework** via:
1. **Model Context Protocol (MCP)**: Standard for Cursor, Claude Desktop, Antigravity, Windsurf, Cline, Roo Code.
2. **Agent Skills**: Drop-in procedural skills for Antigravity, Claude Code, and Codex.
3. **Python Agent SDK**: Direct tool binding for LangChain, AutoGen, CrewAI, and LlamaIndex.

---

## 1. 🌐 Universal MCP Integration (Cursor, Claude, Windsurf, Cline)

Autopoiesis includes a built-in, zero-dependency **Model Context Protocol (MCP)** server:
`python -m autopoiesis.mcp_server`

### A. Cursor Setup
1. Open **Cursor Settings** (`Ctrl + Shift + J` or `Cmd + Shift + J`) -> **Features** -> **MCP**.
2. Click **+ Add New MCP Server**.
3. Fill in:
   - **Name**: `autopoiesis`
   - **Type**: `command`
   - **Command**: `python -m autopoiesis.mcp_server` (or `uv run -m autopoiesis.mcp_server`)

### B. Claude Desktop Setup
Open your Claude Desktop config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add `autopoiesis` under `mcpServers`:

```json
{
  "mcpServers": {
    "autopoiesis": {
      "command": "python",
      "args": ["-m", "autopoiesis.mcp_server"]
    }
  }
}
```

### C. Antigravity / Cline / Windsurf / Roo Code Setup
Add to your project's `.agents/mcp_config.json` or Cline MCP settings:

```json
{
  "mcpServers": {
    "autopoiesis": {
      "command": "python",
      "args": ["-m", "autopoiesis.mcp_server"]
    }
  }
}
```

### 🎯 Available MCP Tools for Your AI Agent
Once connected, your AI Agent gains 4 autonomous tools:
* `autopoiesis_evolve`: Autonomously mutates and optimizes a computational workload (e.g. Mandelbrot or N-body) into native C/Rust with zero crashes.
* `autopoiesis_export_genome`: Packages a local champion chromosome into a JSON package ready for GitHub PR submission.
* `autopoiesis_import_genome`: Imports and tests an external genome through the local Apoptotic Gate.
* `autopoiesis_security_audit`: Audits a community genome JSON against zero-trust static security policies before executing.

---

## 2. 🧠 Agent Skills Setup (Antigravity & Claude Code)

For agents supporting modular `.agents/skills/` (like Antigravity and Claude Code):

1. Copy the skill folder:
   ```bash
   cp -r .agents/skills/autopoiesis /your/project/.agents/skills/
   ```
2. Your agent will automatically recognize when Python code contains performance bottlenecks and autonomously invoke the Autopoiesis evolutionary loop!

---

## 3. 🐍 Python Agent Frameworks (LangChain, AutoGen, CrewAI)

If you are developing custom autonomous agents, wrap Autopoiesis directly as an Agent Tool:

### LangChain Example:
```python
from langchain.tools import tool
from autopoiesis.core.organism import LivingOrganism
import my_compute_module

@tool
def evolve_python_function(function_name: str, generations: int = 3) -> str:
    """Optimizes slow computational Python functions into native C/Rust with apoptotic verification."""
    organism = LivingOrganism(
        name=f"agent_{function_name}",
        target_module=my_compute_module,
        target_symbol=function_name,
        test_vectors=my_compute_module.get_test_vectors(),
        render_dashboard=False,
    )
    try:
        evolved = organism.run_evolution(max_generations=generations)
        active = organism.active_chromosome
        return f"Successfully evolved {function_name}! New phenotype: {active.source_type.value}, Speedup: {active.fitness:.2f}x"
    finally:
        organism.close()
```

---

## 🌍 How Other Users Feed Back into the Species Tree

When any user's AI Agent evolves a high-performance chromosome:
1. Ask the AI: *"Export this champion chromosome as my_handle_genome.json"* (calls `autopoiesis_export_genome`).
2. The user submits a Pull Request to `https://github.com/jdymitarai/autopoiesis`.
3. Our cloud **Autonomous Auto-Breeder Bot** automatically audits, verifies, and merges the PR into the master species tree!

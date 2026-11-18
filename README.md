# ghidra-decompile

An agent skill for decompiling binaries with Ghidra, plus the Ghidra scripts it drives.

It gives an LLM agent a repeatable path from "I need the C for this address" to real pseudocode, and a documented way out when the tooling breaks.

## The idea that matters

**The cost is analysis, not decompilation.**

A 114 MB stripped AArch64 image, imported once with `-noanalysis`, decompiled at one targeted function in **3.3 s** on a reuse run. Full auto-analysis of the same image takes hours, and is rarely needed to read a single function.

So: import once, keep the project, decompile exact addresses. `SKILL.md` is the method.

## What's here

| Path | What |
|---|---|
| `SKILL.md` | The skill. Choosing a path, pinning addresses to the image base, headless decompile, the bridge, validating the output, and a symptom → cause → fix table |
| `tools/*.java` | 22 Ghidra scripts: decompile at explicit addresses, vtable/RTTI dumps, string and constant xrefs, backwards `PACIASP` scan for AArch64 entries |
| `tools/run_bridge.py` | stdio driver — one MCP session for initialize → connect → run script |
| `tools/README.md` | Script-by-script notes |

## Requires

- Ghidra — verified against 12.2 (`$HOME/Applications/ghidra_12.2_PUBLIC`)
- For the bridge path only: [bethington/ghidra-mcp](https://github.com/bethington/ghidra-mcp) and `uv`

Headless decompilation needs neither the bridge nor Python.

## Install

As a skill: copy `SKILL.md` into your agent's skills directory as `ghidra-decompile/SKILL.md`.

For the scripts: copy `tools/*.java` to `~/ghidra_scripts`, or pass the directory as `-scriptPath` on headless runs.

## The trap worth knowing about

The released `GhidraMCP-7.0.0.zip` is built for **Ghidra 12.1.4**. Against 12.2, every decompile fails with:

```
ghidra/program/model/lang/SleighLanguageDescription
```

Build the `chore/ghidra-12.2` branch instead, then confirm `extension.properties` reports `version=12.2`. `SKILL.md` has the full sequence, including the `GHIDRA_MCP_ALLOW_SCRIPTS=1` default change and the 7.0.0 tool consolidation — `decompile_function` is gone, use `get_functions`.

On the reference build the rebuilt extension advertised 216 endpoints and a 69,271-function analysis survived a Ghidra restart. Treat those as install checks, not portable counts.

## License

MIT — see [LICENSE](LICENSE).

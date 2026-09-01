"""Input/Output adapter and normalization layer for student automata programs."""

from __future__ import annotations

import json
import logging
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.ai.models import ProjectAnalysis
from app.core.automata.models import DFA, AutomataValidationError
from app.core.automata.serialization import deserialize_automaton, serialize_automaton

logger = logging.getLogger(__name__)


def prepare_student_input(
    test_automaton: Dict[str, Any],
    input_format: str,
    scratch_dir: Path,
) -> Tuple[Optional[Path], Optional[str]]:
    """Format canonical test automaton into student input.

    Returns:
        (input_file_path, stdin_string)
    """
    json_str = json.dumps(test_automaton, indent=2)

    if input_format in {"json", "custom_txt", "cli_args"}:
        input_file = scratch_dir / "input_automaton.json"
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(json_str)
        return input_file, None

    elif input_format == "stdin_json":
        return None, json_str

    # Default fallback: write JSON file and provide stdin
    input_file = scratch_dir / "input_automaton.json"
    with open(input_file, "w", encoding="utf-8") as f:
        f.write(json_str)
    return input_file, json_str


def build_command_line(
    analysis: ProjectAnalysis,
    project_dir: Path,
    input_file: Optional[Path],
    scratch_dir: Path,
) -> List[str]:
    """Resolve command line arguments for executing the student's program."""
    lang = (analysis.language or "").lower()
    entry = analysis.entry_point or ""
    invocation_tmpl = analysis.invocation or ""

    input_arg = str(input_file.name) if input_file else ""

    # 1. If explicit invocation template provided by AI
    if invocation_tmpl:
        # Replace placeholders like <input.json>, input.json, $1, etc.
        cmd_str = invocation_tmpl
        cmd_str = re.sub(r"<input(\.json)?>", input_arg, cmd_str, flags=re.IGNORECASE)
        cmd_str = re.sub(r"\$1", input_arg, cmd_str)
        
        # Split safely
        try:
            tokens = shlex.split(cmd_str, posix=(sys.platform != "win32"))
            if tokens:
                # If starts with python/python3, replace with current interpreter
                if tokens[0].lower() in {"python", "python3", "py"}:
                    tokens[0] = sys.executable
                return tokens
        except Exception:
            pass

    # 2. Language-specific default invocations
    if lang == "python":
        entry_file = entry if entry else "main.py"
        cmd = [sys.executable, entry_file]
        if input_file:
            cmd.append(input_arg)
        return cmd

    elif lang == "java":
        # Check if compiled .class / .jar or .java
        if entry.endswith(".java"):
            # Java 11+ single file execution
            cmd = ["java", entry]
        elif entry.endswith(".jar"):
            cmd = ["java", "-jar", entry]
        else:
            class_name = entry.replace(".class", "").replace("/", ".").replace("\\", ".")
            cmd = ["java", class_name]
        if input_file:
            cmd.append(input_arg)
        return cmd

    elif lang in {"cpp", "c"}:
        executable = entry if entry else "converter"
        if not executable.startswith("./") and not executable.startswith(".\\") and sys.platform != "win32":
            executable = f"./{executable}"
        cmd = [executable]
        if input_file:
            cmd.append(input_arg)
        return cmd

    raise ValueError(f"Unsupported execution runtime for language '{lang}'.")


def parse_and_normalize_student_output(
    stdout_text: str,
    scratch_dir: Path,
    output_format: str,
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Parse raw output from student program and normalize into canonical DFA dictionary.

    Returns:
        (success, canonical_dfa_dict, error_message)
    """
    raw_json_str: Optional[str] = None

    # 1. Try reading stdout for JSON object
    cleaned_stdout = stdout_text.strip()
    if cleaned_stdout:
        # Search for first '{' and matching '}' if output contains extraneous logging
        start_idx = cleaned_stdout.find("{")
        end_idx = cleaned_stdout.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
            raw_json_str = cleaned_stdout[start_idx : end_idx + 1]

    # 2. Check scratch dir for generated output files (e.g. output.json, dfa.json)
    if not raw_json_str:
        for out_name in ["output.json", "dfa.json", "result.json"]:
            out_path = scratch_dir / out_name
            if out_path.exists():
                try:
                    with open(out_path, "r", encoding="utf-8", errors="replace") as f:
                        raw_json_str = f.read().strip()
                    break
                except Exception:
                    pass

    if not raw_json_str:
        return False, None, "No JSON automaton was found in program stdout or output files."

    # 3. Parse JSON syntax
    try:
        dict_data = json.loads(raw_json_str)
    except Exception as exc:
        return False, None, f"Failed to parse output as JSON: {str(exc)}"

    if not isinstance(dict_data, dict):
        return False, None, "Output JSON is not a JSON object/dictionary."

    # Normalize fields if student used slightly different keys
    if "type" not in dict_data:
        dict_data["type"] = "DFA"
    if "startState" in dict_data and "start_state" not in dict_data:
        dict_data["start_state"] = dict_data["startState"]
    if "acceptingStates" in dict_data and "accepting_states" not in dict_data:
        dict_data["accepting_states"] = dict_data["acceptingStates"]
    if "final_states" in dict_data and "accepting_states" not in dict_data:
        dict_data["accepting_states"] = dict_data["final_states"]

    # 4. Deserialization & validation against formal DFA structure
    try:
        automaton = deserialize_automaton(dict_data)
        if not isinstance(automaton, DFA):
            return False, None, f"Expected DFA output, but parsed {type(automaton).__name__}."
        
        canonical_dict = serialize_automaton(automaton)
        return True, canonical_dict, None

    except AutomataValidationError as exc:
        return False, None, f"Output is not a valid mathematical DFA: {exc.message}"
    except Exception as exc:
        return False, None, f"Invalid DFA structure: {str(exc)}"

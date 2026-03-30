from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QSplitter, QComboBox, QPushButton, QPlainTextEdit,
    QTextEdit, QScrollArea, QMessageBox, QLineEdit, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QIntValidator, QCloseEvent
import re
import json
from typing import Any, Dict, List, Optional


class CodeExecutionWorker(QThread):
    """Background thread for run action and public testcase checks."""
    execution_done = pyqtSignal(dict)
    execution_error = pyqtSignal(str)

    def __init__(self, api_client, payload: Dict[str, Any]):
        super().__init__()
        self.api_client = api_client
        self.payload = payload

    # @staticmethod
    # def _normalize_stdin(raw_stdin: Any) -> str:
    #     text = str(raw_stdin or "")
    #     if "\\n" in text or "\\t" in text or "\\r" in text:
    #         try:
    #             text = bytes(text, "utf-8").decode("unicode_escape")
    #         except Exception:
    #             pass
    #     return text

    @staticmethod
    def _normalize_stdin(raw_stdin: Any) -> str:
        # If the value is already a Python list/dict (parsed from JSON), convert to stdin text.
        if isinstance(raw_stdin, list):
            return "\n".join(str(item) for item in raw_stdin)
        if isinstance(raw_stdin, dict):
            return "\n".join(str(v) for v in raw_stdin.values())
        text = str(raw_stdin or "")
        # Unescape escape sequences written as literal backslash-n etc.
        if "\\n" in text or "\\t" in text or "\\r" in text:
            try:
                text = bytes(text, "utf-8").decode("unicode_escape")
            except Exception:
                pass
        return text

    # @staticmethod
    # def _build_python_function_source(source_code: str, tc: Dict[str, Any]) -> str:
    #     args_json = json.dumps(tc.get("function_args") or [])
    #     kwargs_json = json.dumps(tc.get("function_kwargs") or {})
    #     function_name = tc.get("function_name") or "solve"
    #     harness = (
    #         "\n\n# --- Auto-generated function-mode harness ---\n"
    #         "import json\n"
    #         f"__tc_args = json.loads({args_json!r})\n"
    #         f"__tc_kwargs = json.loads({kwargs_json!r})\n"
    #         f"__result = {function_name}(*__tc_args, **__tc_kwargs)\n"
    #         "if __result is None:\n"
    #         "    print('None')\n"
    #         "elif isinstance(__result, (list, tuple)):\n"
    #         "    print(' '.join(str(x) for x in __result))\n"
    #         "elif isinstance(__result, str):\n"
    #         "    print(__result)\n"
    #         "else:\n"
    #         "    print(str(__result))\n"
    #     )
    #     return source_code + harness

    @staticmethod
    def _build_python_function_source(source_code: str, tc: Dict[str, Any]) -> str:
        args_json = json.dumps(tc.get("function_args") or [])
        kwargs_json = json.dumps(tc.get("function_kwargs") or {})
        match = re.search(r"def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source_code)
        detected_function_name = match.group(1) if match else None
        function_name = tc.get("function_name") or detected_function_name or "solve"
        harness = (
            "\n\n# --- Auto-generated function-mode harness ---\n"
            "import json as __json\n"
            "import sys as __sys\n"
            "import io as __io\n"
            # Suppress any print() calls inside the candidate's function
            "__captured_stdout = __io.StringIO()\n"
            "__real_stdout = __sys.stdout\n"
            "__sys.stdout = __captured_stdout\n"
            f"__tc_args = __json.loads({args_json!r})\n"
            f"__tc_kwargs = __json.loads({kwargs_json!r})\n"
            f"__result = {function_name}(*__tc_args, **__tc_kwargs)\n"
            # Restore stdout before our print
            "__sys.stdout = __real_stdout\n"
            "__fn_stdout = __captured_stdout.getvalue().strip()\n"
            # If function returned a meaningful value — use it
            # If function returned None but printed something — use what it printed
            "if __result is None:\n"
            "    if __fn_stdout:\n"
            "        print(__fn_stdout)\n"
            "    else:\n"
            "        print('None')\n"
            "elif isinstance(__result, (list, tuple, dict)):\n"
            "    print(__json.dumps(__result, ensure_ascii=False))\n"
            "elif isinstance(__result, bool):\n"
            "    print('true' if __result else 'false')\n"
            "elif isinstance(__result, str):\n"
            "    print(__result)\n"
            "else:\n"
            "    print(str(__result))\n"
        )
        return source_code + harness
    @staticmethod
    def _infer_python_function_args(source_code: str, tc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not tc:
            return None
        match = re.search(r"def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source_code)
        if not match:
            return tc

        if tc.get("function_args") is not None or tc.get("function_kwargs") is not None:
            inferred = dict(tc)
            inferred["function_name"] = inferred.get("function_name") or match.group(1)
            return inferred

        signature_match = re.search(r"def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(([^)]*)\)", source_code)
        signature_params: List[str] = []
        if signature_match:
            raw_params = signature_match.group(1)
            for part in raw_params.split(","):
                token = part.strip()
                if not token:
                    continue
                token = token.split("=", 1)[0].strip()
                token = token.split(":", 1)[0].strip()
                token = token.lstrip("*")
                if token and token != "self":
                    signature_params.append(token)

        raw_input = tc.get("input", "")
        parsed_json: Any = None
        if isinstance(raw_input, (dict, list, int, float, bool)) or raw_input is None:
            parsed_json = raw_input
        else:
            raw_text = str(raw_input).strip()
            if raw_text.startswith("{") or raw_text.startswith("["):
                try:
                    parsed_json = json.loads(raw_text)
                except Exception:
                    parsed_json = None
            elif raw_text.lstrip("-").isdigit():
                # Plain integer string like "11", "2", "-3"
                try:
                    parsed_json = int(raw_text)
                except ValueError:
                    parsed_json = None
            else:
                # Try float
                try:
                    parsed_json = float(raw_text)
                except ValueError:
                    parsed_json = None

        if parsed_json is not None:
            inferred = dict(tc)
            inferred["function_name"] = inferred.get("function_name") or match.group(1)
            if isinstance(parsed_json, dict):
                if len(signature_params) == 1 and signature_params[0] in parsed_json:
                    inferred["function_args"] = [parsed_json.get(signature_params[0])]
                    inferred["function_kwargs"] = {}
                elif signature_params and all(name in parsed_json for name in signature_params):
                    inferred["function_args"] = [parsed_json.get(name) for name in signature_params]
                    inferred["function_kwargs"] = {}
                else:
                    inferred["function_args"] = [parsed_json]
                    inferred["function_kwargs"] = {}
            elif isinstance(parsed_json, list):
                if len(signature_params) <= 1:
                    inferred["function_args"] = [parsed_json]
                else:
                    inferred["function_args"] = list(parsed_json)
                inferred["function_kwargs"] = {}
            else:
                inferred["function_args"] = [parsed_json]
                inferred["function_kwargs"] = {}
            return inferred

        lines = [line.strip() for line in str(tc.get("input", "")).splitlines() if line.strip()]
        if len(lines) < 3:
            return tc

        try:
            n = int(lines[0])
            nums = [int(x) for x in lines[1].split()]
            target = int(lines[2])
            if n != len(nums):
                return tc
        except Exception:
            return tc

        inferred = dict(tc)
        inferred["function_name"] = inferred.get("function_name") or match.group(1)
        inferred["function_args"] = [nums, target]
        inferred["function_kwargs"] = {}
        return inferred

    def _build_exec_payload(self, tc: Optional[Dict[str, Any]]) -> tuple[str, str]:
        source = str(self.payload.get("source_code") or "")
        language = str(self.payload.get("language") or "python").lower()
        if language == "python":
            python_tc = self._infer_python_function_args(source, tc)
            if python_tc and (python_tc.get("function_args") is not None or python_tc.get("function_kwargs") is not None):
                return self._build_python_function_source(source, python_tc), ""

        raw = (tc or {}).get("input", self.payload.get("stdin", ""))
        return source, self._normalize_stdin(raw)

    def run(self) -> None:
        try:
            primary_tc = self.payload.get("primary_test_case")
            run_source, run_stdin = self._build_exec_payload(primary_tc)
            result = self.api_client.run_code(
                language=self.payload["language"],
                source_code=run_source,
                stdin=run_stdin,
                question_id=self.payload.get("question_id"),
                attempt_id=self.payload.get("attempt_id"),
            )
            result["run_id"] = self.payload.get("run_id")

            public_results: List[Dict[str, Any]] = []
            for tc in self.payload.get("public_test_cases", []):
                tc_source, tc_stdin = self._build_exec_payload(tc)
                tc_result = self.api_client.run_code(
                    language=self.payload["language"],
                    source_code=tc_source,
                    stdin=tc_stdin,
                    question_id=self.payload.get("question_id"),
                    attempt_id=self.payload.get("attempt_id"),
                )

                if tc.get("expected_output_json") is not None:
                    expected_json = json.dumps(tc.get("expected_output_json"), separators=(",", ":"), ensure_ascii=False)
                    expected_seq = (
                        " ".join(str(x) for x in tc.get("expected_output_json", []))
                        if isinstance(tc.get("expected_output_json"), list)
                        else expected_json
                    )
                    try:
                        parsed = json.loads((tc_result.get("stdout") or "").strip() or "null")
                        actual = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
                        expected = expected_json
                    except Exception:
                        actual = (tc_result.get("stdout") or "").strip()
                        expected = (tc.get("expected_output") or "").strip() or expected_seq
                
                else:
                    actual = (tc_result.get("stdout") or "").strip()
                    expected = (tc.get("expected_output") or "").strip()
                expected_missing = bool(tc.get("expected_output_missing")) or expected.strip().lower() in {"none", "null"}
                if expected_missing:
                    passed = (not tc_result.get("timed_out")) and tc_result.get("exit_code") == 0
                else:
                    exit_ok = (not tc_result.get("timed_out")) and tc_result.get("exit_code") == 0
                    if exit_ok:
                        if actual == expected:
                            passed = True
                        else:
                            # Secondary: JSON-normalise both sides to handle
                            # whitespace differences like '[1, 3]' vs '[1,3]'
                            try:
                                passed = json.loads(actual) == json.loads(expected)
                            except (json.JSONDecodeError, ValueError):
                                passed = False
                    else:
                        passed = False

                public_results.append(
                    {
                        "test_case_id": tc.get("id", "-"),
                        "passed": passed,
                        "actual_output": actual,
                        "expected_output": expected,
                        "expected_output_missing": expected_missing,
                        "execution_time_ms": tc_result.get("execution_time_ms"),
                        "memory_used_kb": tc_result.get("memory_used_kb"),
                        "timed_out": tc_result.get("timed_out", False),
                        "exit_code": tc_result.get("exit_code"),
                        "stderr": tc_result.get("stderr", ""),
                    }
                )

            result["public_test_results"] = public_results
            self.execution_done.emit(result)
        except Exception as exc:
            self.execution_error.emit(str(exc))


class CodeSubmitWorker(QThread):
    """Background thread for final coding submission."""
    submit_done = pyqtSignal(dict)
    submit_error = pyqtSignal(str)

    def __init__(self, api_client, payload: Dict[str, Any]):
        super().__init__()
        self.api_client = api_client
        self.payload = payload

    def run(self) -> None:
        try:
            response = self.api_client.submit_coding(
                question_id=self.payload.get("question_id"),
                language=self.payload.get("language"),
                source_code=self.payload.get("source_code"),
                attempt_id=self.payload.get("attempt_id"),
                test_results=self.payload.get("test_results"),
                execution_time_ms=self.payload.get("execution_time_ms"),
                memory_used_kb=self.payload.get("memory_used_kb"),
                stdout=self.payload.get("stdout"),
                stderr=self.payload.get("stderr"),
            )
            self.submit_done.emit(response or {})
        except Exception as exc:
            self.submit_error.emit(str(exc))

# ══════════════════════════════════════════════════════════════════════════════
#  SYNTAX HIGHLIGHTER
# ══════════════════════════════════════════════════════════════════════════════
class GenericHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []

        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(QColor("#C678DD"))
        kw_fmt.setFontWeight(QFont.Weight.Bold)
        keywords = [
            'def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif',
            'while', 'for', 'in', 'and', 'or', 'not', 'try', 'except', 'with',
            'as', 'pass', 'break', 'continue', 'public', 'private', 'protected',
            'static', 'void', 'int', 'float', 'double', 'char', 'bool', 'auto',
            'const', 'std', 'True', 'False', 'None',
        ]
        for w in keywords:
            self.rules.append((re.compile(rf'\b{w}\b'), kw_fmt))

        bi_fmt = QTextCharFormat()
        bi_fmt.setForeground(QColor("#61AFEF"))
        for w in ['print', 'len', 'range', 'String', 'System', 'out', 'cout', 'cin', 'self']:
            self.rules.append((re.compile(rf'\b{w}\b'), bi_fmt))

        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor("#98C379"))
        self.rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), str_fmt))
        self.rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), str_fmt))

        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor("#D19A66"))
        self.rules.append((re.compile(r'\b[0-9]+\b'), num_fmt))

        cmt_fmt = QTextCharFormat()
        cmt_fmt.setForeground(QColor("#5C6370"))
        cmt_fmt.setFontItalic(True)
        self.rules.append((re.compile(r'#.*'), cmt_fmt))
        self.rules.append((re.compile(r'//.*'), cmt_fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


# ══════════════════════════════════════════════════════════════════════════════
#  CODE EDITOR
# ══════════════════════════════════════════════════════════════════════════════
class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.highlighter = GenericHighlighter(self.document())
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: transparent;
                color: #E2E8F0;
                font-family: 'Consolas', 'JetBrains Mono', monospace;
                font-size: 15px;
                border: none;
                padding: 15px;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                border: none; background: #1E293B; width: 14px; margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #334155; min-height: 30px; border-radius: 5px; margin: 2px;
            }
            QScrollBar::handle:vertical:hover { background: #475569; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                height: 0px; background: #1E293B;
            }
            QScrollBar:horizontal {
                border: none; background: #1E293B; height: 14px; margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #334155; min-width: 30px; border-radius: 5px; margin: 2px;
            }
            QScrollBar::handle:horizontal:hover { background: #475569; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                width: 0px; background: #1E293B;
            }
        """)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            current_line = cursor.block().text()
            indentation = ""
            for ch in current_line:
                if ch in (' ', '\t'):
                    indentation += ch
                else:
                    break
            if current_line.strip().endswith((':',  '{')):
                indentation += "    "
            super().keyPressEvent(e)
            self.insertPlainText(indentation)
            return
        super().keyPressEvent(e)


# ══════════════════════════════════════════════════════════════════════════════
#  CODING SECTION  (full-screen view)
# ══════════════════════════════════════════════════════════════════════════════
class CodingSection(QWidget):
    """Full-screen coding environment.

    Signals
    -------
    back_requested      – emitted when user clicks "← Back to Sections"
    answer_submitted    – emitted with the final code string when "Submit Final" is clicked
    """

    back_requested   = pyqtSignal()
    answer_submitted = pyqtSignal(str)
    terminal_append_requested = pyqtSignal(str)
    legacy_run_finished = pyqtSignal(str)

    # Default starter templates per language
    _TEMPLATES = {
        "Python 3":  "def solution():\n    # Write your code here\n    pass\n",
        "JavaScript": "function solution() {\n  // Write your code here\n}\n",
        "C++ 20":    "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    // Write your code here\n    return 0;\n}\n",
        "Java 17":   "public class Solution {\n    public static void main(String[] args) {\n        // Write your code here\n    }\n}\n",
        "Go":        "package main\n\nfunc solution() {\n    // Write your code here\n}\n",
        "Rust":      "fn main() {\n    // Write your code here\n}\n",
    }

    _API_TO_UI_LANG = {
        "python": "Python 3",
        "javascript": "JavaScript",
        "js": "JavaScript",
        "cpp": "C++ 20",
        "c++": "C++ 20",
        "java": "Java 17",
        "go": "Go",
        "rust": "Rust",
    }

    _UI_TO_API_LANG = {
        "Python 3": "python",
        "JavaScript": "javascript",
        "C++ 20": "cpp",
        "Java 17": "java",
        "Go": "go",
        "Rust": "rust",
    }

    @staticmethod
    def _parse_function_signature(signature: str) -> tuple[str, list[str]]:
        sig = str(signature or "").strip()
        m = re.match(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*:?.*$", sig)
        if not m:
            return "", []
        fname = m.group(1)
        params: list[str] = []
        for part in m.group(2).split(","):
            token = part.strip()
            if not token:
                continue
            token = token.split("=", 1)[0].strip()
            token = token.split(":", 1)[0].strip().lstrip("*")
            if token and token != "self":
                params.append(token)
        return fname, params

    @classmethod
    def _normalize_test_cases(cls, question: Dict[str, Any]) -> list[Dict[str, Any]]:
        raw = question.get("sample_test_cases")
        if raw is None:
            raw = question.get("test_cases")
        if raw is None:
            raw = question.get("testcases")

        fname, params = cls._parse_function_signature(question.get("function_signature") or "")

        def _to_cases(raw_cases: Any) -> list[Dict[str, Any]]:
            out: list[Dict[str, Any]] = []
            if isinstance(raw_cases, dict):
                items = list(raw_cases.items())
            elif isinstance(raw_cases, list):
                items = [(str(i + 1), tc) for i, tc in enumerate(raw_cases)]
            else:
                return out

            for fallback_id, tc in items:
                if not isinstance(tc, dict):
                    continue
                tc_id = str(tc.get("id") or fallback_id)
                raw_input_str = tc.get("input", "")
                raw_expected  = tc.get("expected_output", tc.get("output"))
                expected_missing = raw_expected is None

                # Parse JSON strings back to Python objects for function-arg derivation.
                def _try_parse_json(value):
                    if isinstance(value, str):
                        s = value.strip()
                        if s and s[0] in ('{', '[', '"') or s.lstrip('-').isdigit():
                            try:
                                return json.loads(s)
                            except (json.JSONDecodeError, ValueError):
                                pass
                    return value

                raw_input    = _try_parse_json(raw_input_str)
                raw_expected = _try_parse_json(raw_expected)

                input_text = (
                    json.dumps(raw_input, ensure_ascii=False)
                    if isinstance(raw_input, (dict, list))
                    else str(raw_input)
                )
                expected_text = ""
                if raw_expected is not None:
                    expected_text = (
                        json.dumps(raw_expected, ensure_ascii=False)
                        if isinstance(raw_expected, (dict, list))
                        else str(raw_expected)
                    )

                function_args   = tc.get("function_args")
                function_kwargs = tc.get("function_kwargs")
                function_name   = tc.get("function_name") or fname

                # Re-parse function_args if they are strings (set by mock_server before Fix 1)
                if isinstance(function_args, list):
                    function_args = [_try_parse_json(a) for a in function_args]

                if function_args is None and function_kwargs is None:
                    if isinstance(raw_input, list):
                        function_args = [raw_input] if len(params) <= 1 else list(raw_input)
                        function_kwargs = {}
                    elif isinstance(raw_input, dict):
                        if len(params) == 1 and params[0] in raw_input:
                            function_args = [raw_input.get(params[0])]
                            function_kwargs = {}
                        elif params and all(name in raw_input for name in params):
                            function_args = [raw_input.get(name) for name in params]
                            function_kwargs = {}
                        else:
                            function_args = [raw_input] if len(params) <= 1 else []
                            function_kwargs = {}
                    elif raw_input is not None:
                        # Scalar (int, float, bool) — always wrap in list
                        function_args = [raw_input]
                        function_kwargs = {}
                        
                is_hidden = bool(tc.get("is_hidden", False))
                is_sample = bool(tc.get("is_sample", not is_hidden))
                if is_hidden and not is_sample:
                    continue  # skip hidden TCs — never shown in coding widget

                out.append(
                    {
                        "id": tc_id,
                        "input": input_text,
                        "expected_output": expected_text,
                        "expected_output_missing": bool(tc.get("expected_output_missing", expected_missing)),
                        "explanation": str(tc.get("explanation") or ""),
                        "category": str(tc.get("category") or "basic"),
                        "is_sample": is_sample,
                        "function_name": function_name,
                        "function_args": function_args,
                        "function_kwargs": function_kwargs,
                    }
                )
            return out

        return _to_cases(raw)

    # @classmethod
    # def _normalize_question_payload(cls, question: Dict[str, Any]) -> Dict[str, Any]:
    #     q = dict(question or {})
    #     qtype = str(q.get("qtype") or q.get("question_type") or q.get("type") or "coding").strip().lower()
    #     q["type"] = "coding" if qtype == "coding" else qtype
    #     q["text"] = q.get("text") or q.get("question_text") or q.get("description") or q.get("question") or ""
    #     q["description"] = q.get("description") or q.get("question_text") or q.get("text") or ""
    #     q["constraints"] = q.get("constraints") or q.get("function_signature") or ""

    #     langs = q.get("supported_languages") or q.get("languages")
    #     if not langs:
    #         lang_single = q.get("language")
    #         langs = [lang_single] if lang_single else ["python"]
    #     if isinstance(langs, str):
    #         langs = [langs]
    #     q["supported_languages"] = [str(x).strip().lower() for x in langs if str(x).strip()] or ["python"]

    #     starter = q.get("starter_code")
    #     if not isinstance(starter, dict):
    #         starter = {}
    #     if not starter:
    #         signature = str(q.get("function_signature") or "").strip()
    #         if signature:
    #             starter["python"] = f"{signature}\n    # Write your solution here\n    pass\n"
    #     q["starter_code"] = starter

    #     q["sample_test_cases"] = cls._normalize_test_cases(q)
    #     return q

    @classmethod
    def _normalize_question_payload(cls, question: Dict[str, Any]) -> Dict[str, Any]:
        q = dict(question or {})
        qtype = str(q.get("qtype") or q.get("question_type") or q.get("type") or "coding").strip().lower()
        q["type"] = "coding" if qtype == "coding" else qtype
        q["text"] = q.get("text") or q.get("question_text") or q.get("description") or q.get("question") or ""
        q["description"] = q.get("description") or q.get("question_text") or q.get("text") or ""

        # --- Constraints: keep separate from function_signature ---
        # constraints may arrive as a JSON string (from mock_server) or a dict
        raw_constraints = q.get("constraints")
        if isinstance(raw_constraints, str) and raw_constraints.strip().startswith("{"):
            try:
                import json as _json
                q["constraints"] = _json.loads(raw_constraints)
            except Exception:
                pass  # leave as string, _format_constraints handles it
        elif not raw_constraints:
            q["constraints"] = {}

        langs = q.get("supported_languages") or q.get("languages")
        if not langs:
            lang_single = q.get("language")
            langs = [lang_single] if lang_single else ["python"]
        if isinstance(langs, str):
            langs = [langs]
        q["supported_languages"] = [str(x).strip().lower() for x in langs if str(x).strip()] or ["python"]

        # --- starter_code: build from function_signature when empty ---
        starter = q.get("starter_code")
        if not isinstance(starter, dict):
            starter = {}

        signature = str(q.get("function_signature") or "").strip()

        # Normalise: ensure Python signatures end with exactly one colon
        if signature and re.match(r"^\s*def\s+", signature):
            signature = signature.rstrip(": \t") + ":"

        if not starter and signature:
            for lang in q["supported_languages"]:
                if lang == "python":
                    # signature already ends with ":"
                    starter["python"] = f"{signature}\n    # Write your solution here\n    pass\n"
                elif lang in ("javascript", "js"):
                    starter["javascript"] = (
                        f"// {q['text'][:60]}\n"
                        "function solution() {\n  // Write your solution here\n}\n"
                    )
                else:
                    starter[lang] = f"// Write your {lang} solution here\n"

        if not starter:
            # No signature and no starter_code — provide a default python template
            starter["python"] = "# Write your solution here\n"

        q["starter_code"] = starter
        q["function_signature"] = signature

        # --- Normalize test cases and also copy to 'testcases' key ---
        # _switch_question looks for 'testcases', 'test_cases', 'sample_test_cases'
        # We populate all three so nothing breaks.
        normalized_cases = cls._normalize_test_cases(q)
        q["sample_test_cases"] = normalized_cases
        q["testcases"] = normalized_cases   # key _switch_question checks first
        return q


    def __init__(self, questions: list[dict] = None, on_run_code=None):
        """
        questions   – list of coding question dicts from the server.
        on_run_code – optional Callable(question_id, language, source_code, callback)
                      Left for backward compatibility, but we now use api_client natively.
        """
        super().__init__()
        self._questions     = questions or []
        self._on_run_code   = on_run_code          # backward compat
        self._current_q_idx = 0
        self._code_drafts: dict[int, dict[str, str]] = {}   # q_idx -> {lang: code}
        self._current_lang  = "Python 3"
        self._last_run_result: dict = {}

        self.api_client = None
        self._attempt_id = None
        self.execution_worker = None
        self.submit_worker = None
        self.run_counter = 0
        self.last_result = None
        self._confidence_visible = False
        self._confidence_input = None
        self._run_in_progress = False
        self._submit_in_progress = False
        self.terminal_append_requested.connect(self._append_terminal)
        self.legacy_run_finished.connect(self._on_legacy_run_finished)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #1E293B; width: 2px; }")

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([460, 740])

        layout.addWidget(splitter)
        if self._questions:
            self._load_question(0)

    def set_api_client(self, api_client):
        self.api_client = api_client

    def set_session_context(self, attempt_id: Optional[int] = None):
        if attempt_id is not None:
            self._attempt_id = int(attempt_id)


    # ──────────────────────────────────────────────────────────────────────────
    #  LEFT PANEL  (question details + question palette)
    # ──────────────────────────────────────────────────────────────────────────
    def _build_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet("background-color: #FFFFFF;")
        lp_lyt = QVBoxLayout(panel)
        lp_lyt.setContentsMargins(0, 0, 0, 0)
        lp_lyt.setSpacing(0)

        scroll = QScrollArea()
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        content = QWidget()
        sc_lyt = QVBoxLayout(content)
        sc_lyt.setContentsMargins(25, 25, 25, 25)
        sc_lyt.setSpacing(0)

        # Back button
        btn_back = QPushButton("← Back to Sections")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setFixedWidth(185)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC; color: #475569; border-radius: 8px;
                padding: 10px 18px; font-weight: 700; border: 1px solid #E2E8F0;
                font-size: 14px; font-family: 'Inter','Segoe UI',sans-serif;
            }
            QPushButton:hover { background-color: #F1F5F9; color: #0F172A; border-color: #CBD5E1; }
        """)
        btn_back.clicked.connect(self._on_back)
        sc_lyt.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignLeft)
        sc_lyt.addSpacing(22)

        # ── Question palette (switching between coding questions) ──────────
        q_nav_label = QLabel("QUESTIONS")
        q_nav_label.setStyleSheet(
            "font-size: 11px; font-family:'Inter','Segoe UI',sans-serif; "
            "font-weight: 700; color: #64748B; letter-spacing: 1.2px;"
        )
        sc_lyt.addWidget(q_nav_label)
        sc_lyt.addSpacing(10)

        self._q_nav_frame = QFrame()
        self._q_nav_frame.setStyleSheet("background: transparent; border: none;")
        self._q_nav_lyt = QHBoxLayout(self._q_nav_frame)
        self._q_nav_lyt.setContentsMargins(0, 0, 0, 0)
        self._q_nav_lyt.setSpacing(8)
        self._q_nav_lyt.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sc_lyt.addWidget(self._q_nav_frame)
        sc_lyt.addSpacing(22)

        # Question content (dynamic)
        self._q_title_lbl = QLabel()
        self._q_title_lbl.setStyleSheet(
            "font-size: 16px; color: #0F172A; font-family:'Inter','Segoe UI',sans-serif; "
            "font-weight: 700; line-height: 1.6;"
        )
        self._q_title_lbl.setWordWrap(True)
        sc_lyt.addWidget(self._q_title_lbl)
        sc_lyt.addSpacing(22)

        ex_lbl = QLabel("Examples")
        ex_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 800; color: #0F172A; "
            "font-family:'Inter','Segoe UI',sans-serif;"
        )
        sc_lyt.addWidget(ex_lbl)
        sc_lyt.addSpacing(8)

        self._ex_box = QFrame()
        self._ex_box.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; }"
        )
        ex_lyt = QVBoxLayout(self._ex_box)
        ex_lyt.setContentsMargins(14, 12, 14, 12)
        self._ex_text = QLabel()
        self._ex_text.setStyleSheet(
            "font-family: 'JetBrains Mono', Consolas, monospace; font-size: 13px; color: #334155;"
        )
        self._ex_text.setWordWrap(True)
        ex_lyt.addWidget(self._ex_text)
        sc_lyt.addWidget(self._ex_box)
        sc_lyt.addSpacing(20)

        con_lbl = QLabel("Constraints")
        con_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 800; color: #0F172A; "
            "font-family:'Inter','Segoe UI',sans-serif;"
        )
        sc_lyt.addWidget(con_lbl)
        sc_lyt.addSpacing(8)

        self._con_text = QLabel()
        self._con_text.setStyleSheet(
            "font-size: 13px; color: #475569; line-height: 1.6; "
            "font-family:'Inter','Segoe UI',sans-serif;"
        )
        self._con_text.setWordWrap(True)
        sc_lyt.addWidget(self._con_text)
        sc_lyt.addSpacing(20)

        tc_lbl = QLabel("Public Testcases")
        tc_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 800; color: #0F172A; "
            "font-family:'Inter','Segoe UI',sans-serif;"
        )
        sc_lyt.addWidget(tc_lbl)
        sc_lyt.addSpacing(8)

        self._tc_box = QFrame()
        self._tc_box.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; }"
        )
        tc_lyt2 = QVBoxLayout(self._tc_box)
        tc_lyt2.setContentsMargins(14, 12, 14, 12)
        self._tc_text = QLabel()
        self._tc_text.setStyleSheet(
            "font-family: 'JetBrains Mono', Consolas, monospace; font-size: 13px; color: #334155;"
        )
        self._tc_text.setWordWrap(True)
        tc_lyt2.addWidget(self._tc_text)
        sc_lyt.addWidget(self._tc_box)

        sc_lyt.addStretch()
        scroll.setWidget(content)
        lp_lyt.addWidget(scroll)
        return panel

    # ──────────────────────────────────────────────────────────────────────────
    #  RIGHT PANEL  (IDE + Terminal)
    # ──────────────────────────────────────────────────────────────────────────
    def _build_right_panel(self) -> QSplitter:
        right = QSplitter(Qt.Orientation.Vertical)
        right.setStyleSheet("QSplitter::handle { background: #1E293B; height: 2px; }")

        # ── IDE ───────────────────────────────────────────────────────────────
        ide_wrapper = QWidget()
        iw_lyt = QVBoxLayout(ide_wrapper)
        iw_lyt.setContentsMargins(15, 20, 25, 10)

        ide_panel = QFrame()
        ide_panel.setStyleSheet(
            "QFrame { background-color: #1E293B; border-radius: 16px; border: 1px solid #334155; }"
        )
        ide_lyt = QVBoxLayout(ide_panel)
        ide_lyt.setContentsMargins(0, 0, 0, 0)
        ide_lyt.setSpacing(0)

        # IDE header bar
        ide_header = QFrame()
        ide_header.setFixedHeight(50)
        ide_header.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border-top-left-radius: 16px; border-top-right-radius: 16px;
                border-bottom: 1px solid #334155;
                border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
            }
        """)
        ih_lyt = QHBoxLayout(ide_header)
        ih_lyt.setContentsMargins(15, 0, 15, 0)
        ih_lyt.setSpacing(10)

        # Language selector
        self._lang_cb = QComboBox()
        self._lang_cb.addItems(list(self._TEMPLATES.keys()))
        self._lang_cb.setStyleSheet("""
            QComboBox {
                background-color: #1E293B; color: #E2E8F0;
                border: 1px solid #334155; border-radius: 6px;
                padding: 6px 15px; font-weight: 700;
                font-family:'Inter',sans-serif; font-size: 13px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #1E293B; color: #E2E8F0;
                selection-background-color: #334155;
            }
        """)
        self._lang_cb.currentTextChanged.connect(self._on_language_changed)
        ih_lyt.addWidget(self._lang_cb)
        ih_lyt.addStretch()

        # Reset Code button  (was "reset terminal" in old UI)
        btn_reset = QPushButton("Reset Code")
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.setStyleSheet(self._ide_btn_style())
        btn_reset.clicked.connect(self._on_reset_code)
        self._btn_reset = btn_reset
        ih_lyt.addWidget(btn_reset)

        ide_lyt.addWidget(ide_header)

        self.code_edit = CodeEditor()
        ide_lyt.addWidget(self.code_edit)

        iw_lyt.addWidget(ide_panel)
        right.addWidget(ide_wrapper)

        # ── Terminal ──────────────────────────────────────────────────────────
        term_wrapper = QWidget()
        tw_lyt = QVBoxLayout(term_wrapper)
        tw_lyt.setContentsMargins(15, 10, 25, 20)

        term_panel = QFrame()
        term_panel.setStyleSheet(
            "QFrame { background-color: #0B1120; border-radius: 16px; border: 1px solid #1E293B; }"
        )
        tp_lyt = QVBoxLayout(term_panel)
        tp_lyt.setContentsMargins(0, 0, 0, 0)
        tp_lyt.setSpacing(0)

        # Terminal header bar
        term_header = QFrame()
        term_header.setFixedHeight(50)
        term_header.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border-top-left-radius: 16px; border-top-right-radius: 16px;
                border-bottom: 1px solid #1E293B;
                border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
            }
        """)
        th_lyt = QHBoxLayout(term_header)
        th_lyt.setContentsMargins(15, 0, 15, 0)
        th_lyt.setSpacing(10)

        term_lbl = QLabel("Terminal Output")
        term_lbl.setStyleSheet(
            "color: #4ADE80; font-weight: 700; font-family:'Inter',sans-serif; "
            "font-size: 14px; background: transparent; border: none;"
        )
        th_lyt.addWidget(term_lbl)
        th_lyt.addStretch()

        confidence_lbl = QLabel("Confidence (1-5)")
        confidence_lbl.setStyleSheet(
            "color:#93C5FD;font-weight:700;font-family:'Inter',sans-serif;font-size:12px;background:transparent;border:none;"
        )
        self._confidence_input = QLineEdit()
        self._confidence_input.setFixedWidth(60)
        self._confidence_input.setMaxLength(1)
        self._confidence_input.setValidator(QIntValidator(1, 5, self))
        self._confidence_input.setPlaceholderText("1-5")
        self._confidence_input.setStyleSheet(
            "QLineEdit{background:#111827;color:#DBEAFE;border:1px solid #334155;border-radius:6px;padding:4px 8px;font-weight:700;}"
            "QLineEdit:focus{border:1px solid #60A5FA;}"
        )
        confidence_lbl.setVisible(False)
        self._confidence_input.setVisible(False)
        self._confidence_label = confidence_lbl
        th_lyt.addWidget(confidence_lbl)
        th_lyt.addWidget(self._confidence_input)

        # Clear  (was "clear terminal" in old UI)
        btn_clear = QPushButton("Clear")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet(self._term_btn_style())
        btn_clear.clicked.connect(self._on_clear_terminal)
        self._btn_clear = btn_clear
        th_lyt.addWidget(btn_clear)

        # Run Code  (was "run" in old UI)
        btn_run = QPushButton("▶  Run Code")
        btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_run.setStyleSheet(self._term_btn_style("#6366F1", "#4F46E5"))
        btn_run.clicked.connect(self._handle_run_code)
        self._btn_run = btn_run
        th_lyt.addWidget(btn_run)

        # Submit Final  (was "submit" in old UI)
        btn_submit_final = QPushButton("Submit Final")
        btn_submit_final.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_submit_final.setStyleSheet(self._term_btn_style("#22C55E", "#16A34A"))
        btn_submit_final.clicked.connect(self._on_submit_final)
        self._btn_submit_final = btn_submit_final
        th_lyt.addWidget(btn_submit_final)

        tp_lyt.addWidget(term_header)

        self.term_edit = QTextEdit()
        self.term_edit.setReadOnly(True)
        self.term_edit.setPlainText("user@sandbox:~$ Ready to execute.\n")
        self.term_edit.setStyleSheet("""
            QTextEdit {
                background-color: transparent; color: #A3E635;
                font-family: 'Consolas', 'JetBrains Mono', monospace;
                font-size: 14px; border: none; padding: 15px;
            }
            QScrollBar:vertical {
                border: none; background: #0B1120; width: 14px; margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #1E293B; min-height: 30px; border-radius: 5px; margin: 2px;
            }
            QScrollBar::handle:vertical:hover { background: #334155; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                height: 0px; background: #0B1120;
            }
        """)
        tp_lyt.addWidget(self.term_edit)

        tw_lyt.addWidget(term_panel)
        right.addWidget(term_wrapper)
        right.setSizes([600, 300])
        return right

    # ──────────────────────────────────────────────────────────────────────────
    #  QUESTION NAV PALETTE  (left panel Q1, Q2, Q3 … buttons)
    # ──────────────────────────────────────────────────────────────────────────
    def _rebuild_q_nav(self):
        """Rebuild question-switching buttons in the left panel."""
        while self._q_nav_lyt.count():
            item = self._q_nav_lyt.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        for idx, _ in enumerate(self._questions):
            btn = QPushButton(f"Q{idx + 1}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(38)
            btn.clicked.connect(lambda _, i=idx: self._switch_question(i))
            self._q_nav_lyt.addWidget(btn)
            if (idx + 1) % 10 == 0:
                QApplication.processEvents()

        self._q_nav_lyt.addStretch()
        self._update_q_nav_ui()

    def _update_q_nav_ui(self):
        for i in range(self._q_nav_lyt.count()):
            item = self._q_nav_lyt.itemAt(i)
            if not item or not item.widget():
                continue
            btn = item.widget()
            if not isinstance(btn, QPushButton):
                continue
            is_active = (i == self._current_q_idx)
            if is_active:
                btn.setStyleSheet(
                    "QPushButton { background-color: #0F172A; color: white; border-radius: 8px; "
                    "font-family:'Inter',sans-serif; font-weight: 800; font-size: 14px; "
                    "padding: 8px 18px; border: none; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background-color: #F8FAFC; color: #64748B; "
                    "border: 1.5px solid #CBD5E1; border-radius: 8px; "
                    "font-family:'Inter',sans-serif; font-weight: 700; font-size: 14px; "
                    "padding: 8px 18px; }"
                    "QPushButton:hover { background-color: #F1F5F9; color: #0F172A; }"
                )
            if (i + 1) % 10 == 0:
                QApplication.processEvents()

    # ──────────────────────────────────────────────────────────────────────────
    #  LOAD / SWITCH QUESTIONS
    # ──────────────────────────────────────────────────────────────────────────
    def _load_question(self, idx: int):
        self._rebuild_q_nav()
        self._switch_question(idx)

    @staticmethod
    def _to_text(value) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            lines: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    if item.get("input") is not None or item.get("output") is not None:
                        lines.append(
                            f"Input: {item.get('input', '')}\nExpected: {item.get('output', item.get('expected_output', ''))}"
                        )
                    else:
                        lines.append(" ".join(str(v) for v in item.values()))
                else:
                    lines.append(str(item))
            return "\n".join(x for x in lines if x)
        if isinstance(value, dict):
            return "\n".join(f"{k}: {v}" for k, v in value.items())
        return str(value)

    def _switch_question(self, idx: int):
        # Only save draft for the PREVIOUS question (not for the one we are loading).
        # If idx equals the current index this is the first load — no previous draft exists.
        if idx != self._current_q_idx:
            self._save_draft()
        self._current_q_idx = idx
        q = self._questions[idx]

        supported_raw = q.get("supported_languages") or []
        ui_langs = []
        for lang in supported_raw:
            mapped = self._API_TO_UI_LANG.get(str(lang).strip().lower())
            if mapped and mapped not in ui_langs:
                ui_langs.append(mapped)
        if not ui_langs:
            ui_langs = ["Python 3"]

        self._lang_cb.blockSignals(True)
        self._lang_cb.clear()
        self._lang_cb.addItems(ui_langs)
        if self._current_lang not in ui_langs:
            self._current_lang = ui_langs[0]
        self._lang_cb.setCurrentText(self._current_lang)
        self._lang_cb.blockSignals(False)

        # self._q_title_lbl.setText(self._to_text(q.get("description") or q.get("text") or q.get("question_text") or q.get("question") or ""))
        # self._ex_text.setText(self._to_text(q.get("examples", "")))
        # self._con_text.setText(self._to_text(q.get("constraints", "")))
        # self._tc_text.setText(self._to_text(q.get("testcases") or q.get("test_cases") or q.get("sample_test_cases") or ""))

        self._q_title_lbl.setText(self._to_text(q.get("description") or q.get("text") or q.get("question_text") or q.get("question") or ""))
        self._ex_text.setText(self._to_text(q.get("examples", "")))
        self._con_text.setText(self._format_constraints(q.get("constraints", "")))
        self._tc_text.setText(self._format_test_cases(q.get("testcases") or q.get("test_cases") or q.get("sample_test_cases") or []))

        # Restore saved draft or fall back to language template
        # drafts = self._code_drafts.get(idx, {})
        # lang = self._current_lang
        # api_lang = self._UI_TO_API_LANG.get(lang, "python")
        # starter_code = q.get("starter_code") or {}
        # code = drafts.get(lang, starter_code.get(api_lang) or starter_code.get(lang) or self._TEMPLATES.get(lang, ""))
        # self.code_edit.setPlainText(code)

        # Restore saved draft or fall back to starter_code then language template
        drafts = self._code_drafts.get(idx, {})
        lang = self._current_lang
        api_lang = self._UI_TO_API_LANG.get(lang, "python")
        starter_code = q.get("starter_code") or {}

        # Lookup order: saved draft → starter_code[api_lang] → starter_code[ui_lang]
        # → starter_code[any key] → language template
        saved = drafts.get(lang)
        # Treat None and empty string the same — both mean "no real draft yet"
        code = saved if (saved is not None and saved.strip()) else None
        if code is None:
            code = (
                starter_code.get(api_lang)
                or starter_code.get(lang)
                or starter_code.get(lang.lower())
                or next((v for v in starter_code.values() if v and v.strip()), None)
                or self._TEMPLATES.get(lang, "# Write your solution here\n")
            )
        self.code_edit.setPlainText(code)

        self._update_q_nav_ui()

    def _save_draft(self):
        drafts = self._code_drafts.setdefault(self._current_q_idx, {})
        drafts[self._current_lang] = self.code_edit.toPlainText()

    # ──────────────────────────────────────────────────────────────────────────
    #  BUTTON HANDLERS
    # ──────────────────────────────────────────────────────────────────────────
    def _on_back(self):
        self._save_draft()
        self.back_requested.emit()

    def _on_language_changed(self, lang: str):
        self._save_draft()
        self._current_lang = lang
        drafts = self._code_drafts.get(self._current_q_idx, {})
        q = self._questions[self._current_q_idx] if self._questions else {}
        api_lang = self._UI_TO_API_LANG.get(lang, "python")
        starter_code = q.get("starter_code") or {}
        code = drafts.get(lang, starter_code.get(api_lang) or starter_code.get(lang) or self._TEMPLATES.get(lang, ""))
        self.code_edit.setPlainText(code)

    def _on_reset_code(self):
        """Reset Code: restore template for current language (old: reset terminal)."""
        if self._run_in_progress or self._submit_in_progress:
            self._show_message_box(
                icon=QMessageBox.Icon.Warning,
                title="Busy",
                text="Please wait for the current operation to finish.",
                buttons=QMessageBox.StandardButton.Ok,
            )
            return
        reply = self._show_message_box(
            icon=QMessageBox.Icon.Warning,
            title="Reset Code",
            text="Reset code to the default template? Your current code will be lost.",
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button=QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            template = self._TEMPLATES.get(self._current_lang, "")
            self.code_edit.setPlainText(template)
            drafts = self._code_drafts.setdefault(self._current_q_idx, {})
            drafts[self._current_lang] = template

    def _on_clear_terminal(self):
        """Clear terminal output (old: clear terminal)."""
        self.term_edit.clear()

    def _append_terminal(self, text: str) -> None:
        from PyQt6.QtGui import QTextCursor
        cursor = self.term_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + "\n")
        self.term_edit.setTextCursor(cursor)
        scroll = self.term_edit.verticalScrollBar()
        if scroll is not None:
            scroll.setValue(scroll.maximum())

    def _is_worker_running(self, attr_name: str) -> bool:
        """Safely check worker state; clear stale deleted-wrapper references."""
        worker = getattr(self, attr_name, None)
        if worker is None:
            return False
        try:
            return bool(worker.isRunning())
        except RuntimeError:
            setattr(self, attr_name, None)
            return False

    def _bind_worker_cleanup(self, worker: QThread, attr_name: str) -> None:
        """Clear instance worker reference once Qt thread fully finishes."""
        def _cleanup_finished() -> None:
            current = getattr(self, attr_name, None)
            if current is worker:
                setattr(self, attr_name, None)
            try:
                worker.deleteLater()
            except RuntimeError:
                # Already deleted by Qt; nothing to do.
                pass

        worker.finished.connect(_cleanup_finished)

    def _handle_run_code(self):
        """Run Code using the background CodeExecutionWorker (or fallback)."""
        if self._run_in_progress or self._submit_in_progress:
            self._show_message_box(
                icon=QMessageBox.Icon.Warning,
                title="Busy",
                text="Please wait for the current operation to finish.",
                buttons=QMessageBox.StandardButton.Ok,
            )
            return

        code     = self.code_edit.toPlainText().strip()
        if not code:
            self._show_message_box(
                icon=QMessageBox.Icon.Warning,
                title="No Code",
                text="Write code before running.",
                buttons=QMessageBox.StandardButton.Ok,
            )
            return
            
        if not self._questions:
            self._show_message_box(
                icon=QMessageBox.Icon.Warning,
                title="No Question",
                text="No question data available.",
                buttons=QMessageBox.StandardButton.Ok,
            )
            return

        q        = self._questions[self._current_q_idx]
        q_id     = q.get("id", 0)

        # New Worker Route
        if self.api_client is None and self._on_run_code:
            self._run_in_progress = True
            self._set_action_buttons_busy(True)
            language = self._current_lang.lower().replace(" ", "").replace("python3", "python").split()[0]
            self.term_edit.append(f"\nuser@sandbox:~$ Executing {self._current_lang}...\n")

            def _callback(result: dict):
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                exit_c = result.get("exit_code", 0)
                t_ms = result.get("execution_time_ms", 0)
                tests = result.get("public_test_results", [])
                self._last_run_result = result
                lines = []
                if stdout:
                    lines.append(stdout)
                if stderr:
                    lines.append(f"[stderr] {stderr}")
                lines.append(f"Exit: {exit_c}  |  Time: {t_ms} ms")
                if tests:
                    passed = sum(1 for t in tests if t.get("passed"))
                    lines.append(f"Tests: {passed}/{len(tests)} passed")
                msg = "\n".join(lines)
                self.legacy_run_finished.emit(msg)

            try:
                self._on_run_code(q_id, language, code, callback=_callback)
            except Exception:
                self._run_in_progress = False
                if not self._submit_in_progress:
                    self._set_action_buttons_busy(False)
                raise
            return

        if self.api_client is None:
            self._show_message_box(
                icon=QMessageBox.Icon.Warning,
                title="API Error",
                text="API client not available for code execution",
                buttons=QMessageBox.StandardButton.Ok,
            )
            return
            
        if self._is_worker_running("execution_worker"):
            self._show_message_box(
                icon=QMessageBox.Icon.Warning,
                title="Busy",
                text="Please wait for current run to finish.",
                buttons=QMessageBox.StandardButton.Ok,
            )
            return

        api_lang = self._UI_TO_API_LANG.get(self._current_lang, "python")
        
        public_cases = q.get("sample_test_cases") or q.get("test_cases") or q.get("testcases") or []
        primary_tc = public_cases[0] if public_cases else None
        primary_stdin = primary_tc.get("input", "") if primary_tc else ""

        self.run_counter += 1
        run_id = f"run-{self.run_counter}"
        self._run_in_progress = True
        self._set_action_buttons_busy(True)
        self._append_terminal(f"\nuser@sandbox:~$ Executing {self._current_lang}...")
        self._append_terminal(f"[run] id={run_id}")

        worker = CodeExecutionWorker(self.api_client, {
            "run_id": run_id,
            "language": api_lang,
            "source_code": code,
            "stdin": primary_stdin,
            "question_id": q_id,
            "attempt_id": self._attempt_id,
            "primary_test_case": primary_tc,
            "public_test_cases": public_cases,
        })
        self.execution_worker = worker
        worker.execution_done.connect(self._on_worker_done)
        worker.execution_error.connect(self._on_worker_failed)
        self._bind_worker_cleanup(worker, "execution_worker")
        worker.start()

    def _on_legacy_run_finished(self, message: str) -> None:
        self.term_edit.append(message)
        self._run_in_progress = False
        if not self._submit_in_progress:
            self._set_action_buttons_busy(False)

    def _on_worker_done(self, result: dict) -> None:
        self.last_result = result
        self._last_run_result = result
        self._render_run_result(result)
        self._run_in_progress = False
        if not self._submit_in_progress:
            self._set_action_buttons_busy(False)

    def _on_worker_failed(self, error: str) -> None:
        self._append_terminal(f"[run] ERROR: {error}")
        self._run_in_progress = False
        if not self._submit_in_progress:
            self._set_action_buttons_busy(False)

    def _render_run_result(self, result: dict) -> None:
        run_id = result.get("run_id")
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = result.get("exit_code", "N/A")
        exec_ms = result.get("execution_time_ms", "N/A")
        memory_kb = result.get("memory_used_kb")
        timed_out = result.get("timed_out", False)

        self._append_terminal("[run] Completed")
        if run_id:
            self._append_terminal(f"[run] id={run_id}")
        self._append_terminal(f"[run] exit_code={exit_code}, execution_time_ms={exec_ms} ms")
        if memory_kb is not None:
            self._append_terminal(f"[run] memory_used_kb={memory_kb}")
        if stdout:
            self._append_terminal("[run] stdout:\n" + str(stdout))
        if stderr:
            self._append_terminal("[run] stderr:\n" + str(stderr))
        if timed_out:
            self._append_terminal("[run] timed_out=true")

        public_results = result.get("public_test_results", [])
        if public_results:
            graded = [item for item in public_results if not item.get("expected_output_missing")]
            passed = sum(1 for item in graded if item.get("passed"))
            total = len(graded)
            self._append_terminal(f"[run][public-tests] summary={passed}/{total} passed")
            for item in public_results:
                tc_id = item.get("test_case_id", "-")
                if item.get("expected_output_missing"):
                    self._append_terminal(f"[run][public-tests] {tc_id}: UNGRADED (missing expected output)")
                    continue
                status_text = "PASS" if item.get("passed") else "FAIL"
                self._append_terminal(f"[run][public-tests] {tc_id}: {status_text}")
                if not item.get("passed"):
                    if item.get("timed_out"):
                        self._append_terminal("  timed_out: true")
                    if item.get("exit_code") is not None:
                        self._append_terminal(f"  exit_code: {item.get('exit_code')}")
                    actual = str(item.get("actual_output", "")).strip()
                    expected = str(item.get("expected_output", "")).strip()
                    self._append_terminal(f"  actual: {actual}")
                    self._append_terminal(f"  expected: {expected}")
                    tc_stderr = str(item.get("stderr", "")).strip()
                    if tc_stderr:
                        self._append_terminal(f"  stderr: {tc_stderr}")


    def _on_submit_final(self):
        """Submit Final: store answer and potentially post to server."""
        if self._run_in_progress or self._submit_in_progress:
            self._show_message_box(
                icon=QMessageBox.Icon.Warning,
                title="Busy",
                text="Please wait for the current operation to finish.",
                buttons=QMessageBox.StandardButton.Ok,
            )
            return

        reply = self._show_message_box(
            icon=QMessageBox.Icon.Question,
            title="Submit Final",
            text="Submit your final solution? You won't be able to change it afterward.",
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button=QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._confidence_visible and self.get_confidence_value() is None:
                self._show_message_box(
                    icon=QMessageBox.Icon.Warning,
                    title="Missing Confidence",
                    text="Enter confidence level (1-5) before submitting this coding answer.",
                    buttons=QMessageBox.StandardButton.Ok,
                )
                return
            self._save_draft()
            final_code = self.code_edit.toPlainText().strip()
            
            if not self._questions:
                return
            q = self._questions[self._current_q_idx]
            q_id = q.get("id", 0)
            
            api_lang = self._UI_TO_API_LANG.get(self._current_lang, "python")
            payload = {
                "question_id": q_id,
                "source_code": final_code,      # mock_server reads "source_code"
                "language": api_lang,            # pass language so mock_server can forward it
                "question_index": self.get_current_question_index(),
                "confidence": self.get_confidence_value(),
            }

            # Preserve existing behavior: always emit answer payload immediately.
            self.answer_submitted.emit(json.dumps(payload, ensure_ascii=False))

            if self.api_client is not None and hasattr(self.api_client, "submit_coding"):
                if not self._attempt_id:
                    self._show_message_box(
                        icon=QMessageBox.Icon.Warning,
                        title="Session Not Ready",
                        text="Secure exam session is not initialized yet. Please try again in a few seconds.",
                        buttons=QMessageBox.StandardButton.Ok,
                    )
                    return
                self._append_terminal("\n[submit] submitting final solution...")
                self._submit_in_progress = True
                self._set_action_buttons_busy(True)
                worker = CodeSubmitWorker(
                    self.api_client,
                    {
                        "question_id": q_id,
                        "language": api_lang,
                        "source_code": final_code,
                        "attempt_id": self._attempt_id,
                        "test_results": (self.last_result or {}).get("public_test_results", []),
                        "execution_time_ms": (self.last_result or {}).get("execution_time_ms"),
                        "memory_used_kb": (self.last_result or {}).get("memory_used_kb"),
                        "stdout": (self.last_result or {}).get("stdout"),
                        "stderr": (self.last_result or {}).get("stderr"),
                    },
                )
                self.submit_worker = worker
                worker.submit_done.connect(self._on_submit_done)
                worker.submit_error.connect(self._on_submit_failed)
                self._bind_worker_cleanup(worker, "submit_worker")
                worker.start()
            else:
                self._show_message_box(
                    icon=QMessageBox.Icon.Warning,
                    title="Server Unavailable",
                    text="Coding submission could not be sent to the server. Please retry after reconnecting.",
                    buttons=QMessageBox.StandardButton.Ok,
                )
                self._append_terminal("[submit] ERROR: server client not available; submission not persisted")

    def _on_submit_done(self, response: dict) -> None:
        submission_id = (response or {}).get("submission_id")
        if submission_id:
            self._append_terminal(f"[submit] submission_id={submission_id}")
        self._append_terminal("user@sandbox:~$ Submission recorded.")
        self._submit_in_progress = False
        if not self._run_in_progress:
            self._set_action_buttons_busy(False)

    def _on_submit_failed(self, error: str) -> None:
        self._append_terminal(f"[submit] ERROR: failed to persist coding submit: {error}")
        self._submit_in_progress = False
        if not self._run_in_progress:
            self._set_action_buttons_busy(False)

    def _set_action_buttons_busy(self, busy: bool) -> None:
        enabled = not busy
        for attr in ("_btn_run", "_btn_submit_final", "_btn_reset", "_btn_clear"):
            btn = getattr(self, attr, None)
            if btn is not None:
                btn.setEnabled(enabled)

    def _stop_worker_thread(self, attr_name: str, timeout_ms: int = 1500) -> None:
        """Best-effort stop for an active worker thread during teardown."""
        worker = getattr(self, attr_name, None)
        if worker is None:
            return
        try:
            if not worker.isRunning():
                setattr(self, attr_name, None)
                return
            worker.requestInterruption()
            worker.quit()
            worker.wait(timeout_ms)
        except RuntimeError:
            # C++ wrapper may already be deleted while shutting down.
            pass
        finally:
            setattr(self, attr_name, None)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._stop_worker_thread("execution_worker")
        self._stop_worker_thread("submit_worker")
        super().closeEvent(event)

    # ──────────────────────────────────────────────────────────────────────────
    #  PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────
    def set_questions(self, questions: list[dict], active_index: int = 0):
        """Replace the coding questions at runtime."""
        raw_questions = questions or []
        self._questions = [self._normalize_question_payload(q) for q in raw_questions if isinstance(q, dict)]
        self._code_drafts.clear()
        self._current_q_idx = 0
        if self._questions:
            safe_index = max(0, min(int(active_index), len(self._questions) - 1))
            self._load_question(safe_index)

    def set_current_question_index(self, index: int):
        if not self._questions:
            return
        safe_index = max(0, min(int(index), len(self._questions) - 1))
        self._switch_question(safe_index)

    def get_answer(self) -> dict:
        """Return all code drafts: {q_idx: {lang: code}}."""
        self._save_draft()
        return dict(self._code_drafts)

    def get_submission_data(self) -> dict:
        """Fetch real submission structured payload dynamically if requested."""
        if not self._questions:
            return None
        code = self.code_edit.toPlainText().strip()
        api_lang = self._UI_TO_API_LANG.get(self._current_lang, "python")
        q_id = self._questions[self._current_q_idx].get("id", 0)
        return {
            "question_id": q_id,
            "language": api_lang,
            "source_code": code,
            "test_results": (self.last_result or {}).get("public_test_results", []),
        }

    def has_pending_operation(self) -> bool:
        """True when Run/Submit worker is active or flagged in progress."""
        return (
            self._run_in_progress
            or self._submit_in_progress
            or self._is_worker_running("execution_worker")
            or self._is_worker_running("submit_worker")
        )

    def get_current_question_index(self) -> int:
        return int(self._current_q_idx)

    def set_confidence_visible(self, visible: bool):
        self._confidence_visible = bool(visible)
        if hasattr(self, "_confidence_label") and self._confidence_label is not None:
            self._confidence_label.setVisible(self._confidence_visible)
        if self._confidence_input is not None:
            self._confidence_input.setVisible(self._confidence_visible)
            if not self._confidence_visible:
                self._confidence_input.clear()

    def get_confidence_value(self) -> Optional[int]:
        if not self._confidence_visible or self._confidence_input is None:
            return None
        raw = (self._confidence_input.text() or "").strip()
        if raw.isdigit():
            value = int(raw)
            if 1 <= value <= 5:
                return value
        return None

    def set_confidence_value(self, value: Optional[int]):
        if self._confidence_input is None:
            return
        if value is None:
            self._confidence_input.clear()
            return
        try:
            iv = int(value)
        except Exception:
            self._confidence_input.clear()
            return
        if 1 <= iv <= 5:
            self._confidence_input.setText(str(iv))
        else:
            self._confidence_input.clear()

    # ──────────────────────────────────────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _format_constraints(constraints) -> str:
        """Format constraints dict or JSON string into readable lines."""
        import json as _json

        data = constraints
        if isinstance(data, str):
            stripped = data.strip()
            if stripped.startswith("{"):
                try:
                    data = _json.loads(stripped)
                except Exception:
                    return stripped  # show raw string if unparseable
            elif stripped:
                return stripped
            else:
                return "No constraints specified."

        if not data:
            return "No constraints specified."

        if isinstance(data, dict):
            lines = []
            if data.get("function"):
                lines.append(f"Function:          {data['function']}")
            if data.get("time_complexity"):
                lines.append(f"Time Complexity:   {data['time_complexity']}")
            if data.get("space_complexity"):
                lines.append(f"Space Complexity:  {data['space_complexity']}")
            forbidden = data.get("forbidden_builtins") or []
            if forbidden:
                lines.append(f"Forbidden:         {', '.join(str(x) for x in forbidden)}")
            notes = data.get("notes") or []
            for note in (notes or []):
                if note:
                    lines.append(f"Note: {note}")
            return "\n".join(lines) if lines else "No constraints specified."
        return str(data)

    @staticmethod
    def _format_test_cases(test_cases) -> str:
        """Format list of test case dicts into a numbered, readable display."""
        if not test_cases:
            return "No public test cases available."

        if isinstance(test_cases, str):
            return test_cases

        lines = []
        display_cases = [tc for tc in test_cases if isinstance(tc, dict)]

        for i, tc in enumerate(display_cases, start=1):
            tc_id    = str(tc.get("id") or i)
            category = str(tc.get("category") or tc.get("explanation") or "").strip()
            inp      = str(tc.get("input") or "").strip()
            expected = str(
                tc.get("expected_output")
                or tc.get("output")
                or ""
            ).strip()
            explanation = str(tc.get("explanation") or "").strip()

            # Header line
            header = f"Test Case {i}"
            if category and category not in ("basic", ""):
                header += f"  [{category}]"
            lines.append(header)
            lines.append(f"  Input    : {inp}")
            lines.append(f"  Expected : {expected}")
            if explanation and explanation != category:
                lines.append(f"  Note     : {explanation}")
            lines.append("")  # blank line between cases

        return "\n".join(lines).rstrip()
    
    @staticmethod
    def _ide_btn_style(bg="#334155", hover="#475569") -> str:
        return (
            f"QPushButton {{ background-color: {bg}; color: white; padding: 8px 15px; "
            f"border-radius: 4px; font-weight: 700; font-family:'Inter',sans-serif; "
            f"font-size: 13px; border: none; }}"
            f"QPushButton:hover {{ background-color: {hover}; }}"
        )

    @staticmethod
    def _term_btn_style(bg="#334155", hover="#475569") -> str:
        return (
            f"QPushButton {{ background-color: {bg}; color: white; padding: 6px 15px; "
            f"border-radius: 4px; font-weight: 700; font-family:'Inter',sans-serif; "
            f"font-size: 13px; border: none; }}"
            f"QPushButton:hover {{ background-color: {hover}; }}"
        )

    def _show_message_box(
        self,
        *,
        icon: QMessageBox.Icon,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton,
        default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
    ) -> QMessageBox.StandardButton:
        """Show a high-contrast modal message box with always-visible action buttons."""
        from ui.components.premium_popup import PremiumPopup
        return PremiumPopup.show_message(
            parent=self,
            title=title,
            message=text,
            icon=icon,
            buttons=buttons,
            default_button=default_button
        )
import os
import re
import io
import json
import traceback
import contextlib
import requests
from bs4 import BeautifulSoup
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage


def strip_markdown_fences(text: str) -> str:
    """Safely removes markdown code fences."""
    cleaned = re.sub(r"^\x60\x60\x60(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*\x60\x60\x60$", "", cleaned)
    return cleaned


def fetch_problem_data(query: str) -> str:
    """Retrieves the problem description and sample test cases from the problem archive."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    query_clean = query.strip()

    match = re.match(r"^(\d+)", query_clean)
    prob_num = match.group(1) if match else None

    if not prob_num:
        try:
            resp = requests.get("https://leetcode.ca/all/problems.html", headers=headers, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a_tag in soup.find_all("a", href=True):
                    if query_clean.lower() in a_tag.get_text().lower():
                        href_match = re.search(r"(\d+)\.html", a_tag["href"])
                        if href_match:
                            prob_num = href_match.group(1)
                            break
        except Exception:
            pass

    if prob_num:
        url = f"https://leetcode.ca/all/{prob_num}.html"
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                text = soup.get_text(separator="\n")
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                cleaned_text = "\n".join(lines)
                if "Problem Solution" in cleaned_text:
                    cleaned_text = cleaned_text.split("Problem Solution")[0]
                return cleaned_text[:3500]
        except Exception:
            return f"Use standard LeetCode problem specification and sample test cases for: {query}"

    return f"Use standard LeetCode problem specification and sample test cases for: {query}"


def normalize_output(val: str) -> str:
    """Normalizes spacing and quotes for accurate Expected vs Actual comparison."""
    s = str(val).strip()
    s = re.sub(r"\s*,\s*", ",", s)
    s = re.sub(r"\[\s+", "[", s)
    s = re.sub(r"\s+\]", "]", s)
    return s.lower()


def parse_structured_test_output(
    raw_stdout: str,
    has_error: bool,
    error_msg: str = "",
    fallback_cases: list = None
) -> dict:
    """Parses CASE_RESULT lines or maps stdout lines to fallback_cases so all sample cases always display."""
    cases = []
    other_lines = []

    for line in raw_stdout.splitlines():
        if line.startswith("CASE_RESULT|"):
            parts = line.split("|")
            if len(parts) >= 6:
                idx, inp, exp, act, status = parts[1], parts[2], parts[3], parts[4], parts[5].strip()
                passed = (
                    status.upper() == "PASS"
                    and normalize_output(exp) == normalize_output(act)
                ) or (normalize_output(exp) == normalize_output(act))
                cases.append({
                    "id": int(idx) if idx.isdigit() else len(cases) + 1,
                    "input": inp.strip(),
                    "expected": exp.strip(),
                    "actual": act.strip(),
                    "passed": passed
                })
        elif line.strip():
            other_lines.append(line.strip())

    # Fallback: if the code printed plain output lines instead of CASE_RESULT|, map them to fallback_cases
    if not cases and fallback_cases and not has_error:
        for i, fc in enumerate(fallback_cases):
            exp_val = str(fc.get("expected", "")).strip()
            act_val = other_lines[i] if i < len(other_lines) else "(No output)"
            passed = normalize_output(exp_val) == normalize_output(act_val)
            cases.append({
                "id": i + 1,
                "input": str(fc.get("input", f"Sample Case {i + 1}")),
                "expected": exp_val,
                "actual": act_val,
                "passed": passed
            })

    all_passed = (len(cases) > 0) and all(c["passed"] for c in cases) and not has_error
    return {
        "has_error": has_error,
        "all_passed": all_passed,
        "cases": cases,
        "raw_output": error_msg if has_error else "\n".join(other_lines).strip()
    }


def run_code_sandbox(language: str, code: str, fallback_cases: list = None) -> dict:
    """Executes code and returns structured Expected vs Actual results for all sample cases."""
    lang = language.lower().strip()

    if lang == "python":
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                exec_globals = {"__name__": "__main__"}
                exec(code, exec_globals)
            out = stdout_capture.getvalue()
            err = stderr_capture.getvalue()
            if err:
                return parse_structured_test_output(out, True, f"{err}\n{out}".strip(), fallback_cases)
            return parse_structured_test_output(out, False, out, fallback_cases)
        except Exception:
            return parse_structured_test_output(
                stdout_capture.getvalue(),
                True,
                traceback.format_exc(),
                fallback_cases
            )

    compiler_map = {
        "javascript": "nodejs-20.17.0",
        "c++": "gcc-13.2.0",
        "cpp": "gcc-13.2.0",
        "java": "openjdk-22+36"
    }
    compiler = compiler_map.get(lang, "cpython-3.12.7")

    if lang == "java":
        code = re.sub(r"public\s+class\s+", "class ", code)

    try:
        resp = requests.post(
            "https://wandbox.org/api/compile.json",
            json={"compiler": compiler, "code": code, "save": False},
            timeout=14
        )
        if resp.status_code == 200:
            data = resp.json()
            status = str(data.get("status", "0"))
            compiler_err = data.get("compiler_error", "") or data.get("compiler_message", "")
            prog_out = data.get("program_message", "") or data.get("program_output", "")
            if status != "0":
                return parse_structured_test_output(
                    prog_out, True, f"{compiler_err}\n{prog_out}".strip(), fallback_cases
                )
            return parse_structured_test_output(prog_out, False, prog_out, fallback_cases)
        return {"has_error": True, "all_passed": False, "cases": [], "raw_output": f"Compiler HTTP {resp.status_code}"}
    except Exception as e:
        return {"has_error": True, "all_passed": False, "cases": [], "raw_output": f"Sandbox error: {str(e)}"}


def explain_code_error(
    problem: str,
    language: str,
    user_code: str,
    error_details: str,
    reference_code: str = ""
) -> dict:
    """Compares the user's modified code against the working reference code and explains the exact mistake."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY environment variable is missing."}

    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", api_key=api_key, temperature=0.2)
    prompt = (
        f"You are an expert Code Reviewer and Debugging Assistant for LeetCode problems.\n"
        f"Problem: {problem}\n"
        f"Language: {language}\n\n"
        f"Original Working Reference Code:\n{reference_code}\n\n"
        f"User's Modified Code in IDE:\n{user_code}\n\n"
        f"Failed Test Cases / Error Output:\n{error_details}\n\n"
        "Compare the User's Modified Code with the Original Working Reference Code and the failed test outputs.\n"
        "Pinpoint the exact mistake the user introduced (wrong operator, off-by-one error, wrong variable, syntax error, etc.) and explain why it causes the code to fail.\n"
        "Return strictly a raw JSON object (no markdown fences) with these exact keys:\n"
        "{\n"
        '  "mistake_line": "Quote the exact faulty line or expression in the user\'s code",\n'
        '  "what_went_wrong": "Clear explanation of why this specific mistake causes the wrong output or crash",\n'
        '  "how_to_fix": "Show the exact corrected line(s) that should replace the faulty code",\n'
        '  "fixed_code": "The complete corrected standalone runnable code (preserving the CASE_RESULT|... test harness)"\n'
        "}"
    )

    try:
        res = llm.invoke([HumanMessage(content=prompt)])
        raw = res.content if isinstance(res.content, str) else str(res.content)
        cleaned = strip_markdown_fences(raw)
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return {
            "mistake_line": "See details below",
            "what_went_wrong": cleaned,
            "how_to_fix": "Restore the corrected logic.",
            "fixed_code": reference_code or user_code
        }
    except Exception as e:
        return {"error": f"Failed to generate explanation: {str(e)}"}


@tool
def fetch_leetcode_problem(query: str) -> str:
    """Fetches the LeetCode problem description, constraints, and all sample test cases."""
    return fetch_problem_data(query)


@tool
def execute_code_tool(language: str, runnable_code: str) -> str:
    """Executes complete runnable code in the sandbox and returns structured test results."""
    res = run_code_sandbox(language, runnable_code)
    return json.dumps(res)


def run_agent(task: str, language: str = "Python") -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY environment variable is missing."}

    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", api_key=api_key, temperature=0.2)
    tools = [fetch_leetcode_problem, execute_code_tool]

    system_prompt = (
        "You are an Autonomous LeetCode Code Helper Agent.\n"
        "Follow this strict workflow:\n"
        "1. FETCH: Call `fetch_leetcode_problem` once to retrieve the problem description and ALL sample test cases (Example 1, Example 2, Example 3, etc.).\n"
        "2. PLAN: Formulate the optimal approach and Time/Space complexity.\n"
        "3. WRITE & TEST: Write a complete standalone program in the requested language (`runnable_code`) that includes:\n"
        "   - The LeetCode Solution class/function.\n"
        "   - A main/test runner that runs ALL sample test cases from the problem.\n"
        "   - CRITICAL REQUIREMENT FOR `runnable_code`: For EVERY sample test case `i` (1, 2, 3...), the code MUST compute the actual result from the Solution class/function, compare it with the expected result, and print a single line in this exact pipe-delimited format:\n"
        "     CASE_RESULT|<case_number>|<input_summary>|<expected_output>|<actual_output>|<PASS_or_FAIL>\n"
        "     Example output line:\n"
        "     CASE_RESULT|1|nums = [2,7,11,15], target = 9|[0, 1]|[0, 1]|PASS\n"
        "   - Call `execute_code_tool` to run and verify your `runnable_code`.\n"
        "4. FIX ITERATIVELY: If `execute_code_tool` shows `has_error: true` or any test case failed, fix the code and re-test (up to 2 retries).\n"
        "5. RESPOND: Do not mention any third-party website URLs. Return strictly a raw JSON object (no markdown fences) with these exact keys:\n"
        "{\n"
        '  "problem_title": "Full Question Number and Title",\n'
        '  "difficulty": "Easy / Medium / Hard",\n'
        '  "problem_description": "Problem statement, examples, and constraints",\n'
        '  "approach": "Step-by-step algorithmic plan and Time/Space Complexity",\n'
        '  "solution_code": "Clean LeetCode Solution class/function only",\n'
        '  "runnable_code": "Complete standalone code with the Solution AND the main driver printing CASE_RESULT|... lines for all sample test cases",\n'
        '  "sample_test_cases": [\n'
        '    {"id": 1, "input": "nums = [2,7,11,15], target = 9", "expected": "[0, 1]"}\n'
        '  ],\n'
        '  "explanation": "Detailed walkthrough of the code"\n'
        "}"
    )

    agent_executor = create_react_agent(llm, tools, prompt=system_prompt)
    user_prompt = f"LeetCode Question: {task}\nTarget Programming Language: {language}"

    try:
        response = agent_executor.invoke(
            {"messages": [HumanMessage(content=user_prompt)]},
            config={"recursion_limit": 12}
        )
        raw_output = response["messages"][-1].content
        if isinstance(raw_output, list):
            raw_output = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in raw_output
            )

        cleaned = strip_markdown_fences(raw_output)

        parsed = None
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))

        if not parsed:
            return {"error": "Agent could not format response as JSON. Please try again."}

        sample_cases = parsed.get("sample_test_cases", [])
        initial_test = run_code_sandbox(language, parsed.get("runnable_code", ""), sample_cases)
        parsed["initial_test_results"] = initial_test
        return parsed
    except Exception as e:
        return {"error": f"An error occurred during agent execution: {str(e)}"}
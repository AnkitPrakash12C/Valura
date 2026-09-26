# ⚡ Valura — Autonomous LeetCode Code Helper Agent

An intelligent, workflow-driven AI Agentic System built with **LangGraph**, **Google Gemini**, and **FastAPI** that autonomously retrieves coding problem specifications, plans optimal algorithms, writes multi-language code, executes self-verification tests in an isolated sandbox, and diagnoses bugs in user-modified code.

---

## 🎯 Problem Statement & Task Chosen
**Chosen Contest Task:** Code Helper Agent  
*Given a coding problem, plan the approach, write code, test it, and fix errors iteratively.*

Instead of acting as a simple one-shot LLM wrapper, **Valura** implements a multi-step **ReAct (Reason + Act)** agentic workflow:
1. **Accepts a Goal:** Takes a LeetCode problem number/title (e.g., `1. Two Sum`) and a target programming language (`Python`, `C++`, `Java`, or `JavaScript`).
2. **Autonomous Retrieval (Tool 1):** Fetches the problem statement, constraints, and all sample test cases.
3. **Algorithmic Planning:** Reasons through the optimal data structures and evaluates Time & Space Complexity before writing code.
4. **Iterative Execution & Self-Testing (Tool 2):** Generates standalone runnable code with a structured test harness and executes it inside a sandboxed environment against all sample test cases. If compilation or runtime errors occur, the agent observes the traceback and fixes the code iteratively.
5. **Interactive App IDE & Auto Mistake Detector:** Provides a live browser IDE displaying `Expected Output` vs. `Actual Output` with `PASSED` / `FAILED` badges for every sample test case. If a user modifies the code and introduces a bug, the agent compares the modified code against the working reference solution, pinpoints the exact faulty line, explains why it is wrong, and offers a one-click fix.

---

## 🏗️ System Architecture & Workflow Diagram

~~~text
+-------------------------------------------------------------------------+
|                   USER INPUT (Frontend Web Interface)                   |
|        Problem Query (e.g., "1. Two Sum") + Target Language             |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                     FASTAPI SERVERLESS BACKEND                          |
|                  Routes: /api/research (solve | run_code)               |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|              LANGGRAPH REACT ORCHESTRATOR (State Machine)               |
|                     LLM Brain: Gemini 3.5 Flash-Lite                    |
+----------------+---------------------------------------+----------------+
                 |                                       |
      [Tool Call 1: Fetch]                    [Tool Call 2: Execute]
                 |                                       |
                 v                                       v
+----------------------------------+   +----------------------------------+
|    fetch_leetcode_problem()      |   |       execute_code_tool()        |
|  - Parses problem description    |   |  - Runs Python natively /        |
|  - Extracts constraints & all    |   |    C++, Java, JS via Sandbox API |
|    sample test cases             |   |  - Evaluates Expected vs Actual  |
+----------------+-----------------+   +-----------------+----------------+
                 |                                       |
                 +-------------------+-------------------+
                                     |
                        [Observe & Fix Iteratively]
                                     |
                                     v
+-------------------------------------------------------------------------+
|               STRUCTURED OUTPUT & INTERACTIVE JUDGE UI                  |
|  1. Problem Statement & Difficulty Badge                                |
|  2. Planned Approach & Time/Space Complexity                            |
|  3. Syntax-Highlighted LeetCode Solution                                |
|  4. Line-by-Line Code Walkthrough                                       |
|  5. Live IDE + All Sample Cases Judge + Auto Mistake Detector           |
+-------------------------------------------------------------------------+
~~~

---

## 🛠️ Technology Stack
* **Orchestration & Agent Framework:** LangGraph & LangChain (`create_react_agent`)
* **Large Language Model:** Google Gemini (`gemini-3.5-flash-lite`) via `langchain-google-genai`
* **Backend Framework:** Python, FastAPI, Pydantic, Uvicorn
* **Tools & Sandboxes:** BeautifulSoup4 & Requests (Problem Parser), Native Python `exec` & Wandbox Compiler API (Multi-language Sandbox)
* **Frontend:** HTML5, Modern CSS3 (`style.css`), Vanilla JavaScript, Highlight.js
* **Deployment:** Vercel Serverless Functions

---

## 🚀 Setup & Run Instructions

### Prerequisites
* Python 3.10+
* A free Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/)

### 1. Clone the Repository
~~~bash
git clone https://github.com/AnkitPrakash12C/Valura.git
cd Valura
~~~

### 2. Create and Activate a Virtual Environment
~~~powershell
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate
~~~

### 3. Install Dependencies
~~~bash
pip install -r requirements.txt
~~~

### 4. Configure Environment Variable
~~~powershell
# Windows PowerShell:
$env:GEMINI_API_KEY="your_gemini_api_key_here"

# macOS / Linux:
export GEMINI_API_KEY="your_gemini_api_key_here"
~~~

### 5. Run the Application Locally
~~~bash
uvicorn api.research:app --reload --reload-dir api --reload-dir public
~~~
Open **`http://127.0.0.1:8000`** in your browser.

---

## 🧪 Sample Input & Output

### Sample Input
* **Question:** `1. Two Sum`
* **Target Language:** `Python`

### Sample Agent Output
1. **Planned Approach:**  
   Iterate through the array once using a hash map (`seen`) to store each number's value and index. For each element `nums[i]`, check if `complement = target - nums[i]` already exists in `seen`.  
   * **Time Complexity:** `O(n)`  
   * **Space Complexity:** `O(n)`

2. **Generated Solution Code:**
~~~python
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in seen:
                return [seen[complement], i]
            seen[num] = i
        return []
~~~

3. **Sample Test Case Judge (Expected vs. Actual):**

| Sample Case | Input | Expected Output | Actual Output | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Case #1** | `nums = [2,7,11,15], target = 9` | `[0, 1]` | `[0, 1]` | ✅ **PASSED** |
| **Case #2** | `nums = [3,2,4], target = 6` | `[1, 2]` | `[1, 2]` | ✅ **PASSED** |
| **Case #3** | `nums = [3,3], target = 6` | `[0, 1]` | `[0, 1]` | ✅ **PASSED** |

4. **Automatic Mistake Detector (When Code is Modified in IDE):**
   * **User Modification:** Changes `complement = target - num` to `complement = target + num`
   * **Faulty Line Detected:** `complement = target + num`
   * **Why It Is Wrong:** Adding `num` to `target` searches for a value larger than `target` instead of the remaining difference needed to sum up to `target`.
   * **Suggested Replacement:** `complement = target - num`

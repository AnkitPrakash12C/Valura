import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchResults
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage


def run_agent(task: str):
    # Initialize Gemini (Ensure GEMINI_API_KEY is set in Vercel environment variables)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY environment variable is missing."

    # Use the free-tier Gemini 2.5 Flash model
    llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", api_key=api_key, temperature=0.2)

    # Initialize the free web search tool
    search_tool = DuckDuckGoSearchResults()
    tools = [search_tool]

    # Define the agent's system prompt to enforce contest requirements (planning & execution)
    system_prompt = """You are an Autonomous Research Agent. 
    When given a research task, follow this workflow:
    1. PLAN: Break down the request into specific search queries.
    2. ACT: Use the duckduckgo_results tool to execute these queries.
    3. OBSERVE: Analyze the retrieved data. If information is missing, search again.
    4. RESPOND: Synthesize a well-structured final report with headers, bullet points, and a summary.

    Always rely on the search tool for factual data. Do not guess."""

    # Orchestrate the ReAct workflow via LangGraph
    # agent_executor = create_react_agent(llm, tools, state_modifier=system_prompt)
    agent_executor = create_react_agent(llm, tools, prompt=system_prompt)
    # Execute the agent
    try:
        response = agent_executor.invoke({"messages": [HumanMessage(content=task)]})
        # Return the final message content from the agent
        return response["messages"][-1].content
    except Exception as e:
        return f"An error occurred during agent execution: {str(e)}"
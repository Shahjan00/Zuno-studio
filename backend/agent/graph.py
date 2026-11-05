from pathlib import Path
import re
from typing import Literal

from langchain_google_genai import  ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langchain.agents import create_agent
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field

from .prompts import *
from .states import *
from .tools import *

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEBUG_ENABLED = os.getenv("DEBUG", "FALSE").strip().upper() == "TRUE"


def debug_print(message: str) -> None:
    if DEBUG_ENABLED:
        print(f"[DEBUG] {message}")


# llm = ChatGoogleGenerativeAI(model = "gemini-3.6-flash")

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    # model="llama-3.3-70b-versatile",
    temperature=0,
    # FIX 1: file contents used to get cut off mid-generation, which broke
    # the tool-call JSON. Give the model room to finish a whole file.
    max_tokens=8192,
)

#========================= NODES =============================

class RouteDecision(BaseModel):
    route: Literal["chat", "build"] = Field(description="Whether this prompt is a casual chat question or a build/create request.")
    reason: str = Field(description="Very short explanation for the route decision.")


def router_agent(state: dict) -> dict:
    user_prompt = state.get("user_prompt", "")
    classification_prompt = (
        "You are a routing classifier. Decide whether the input is a short conversational message "
        "or a request to build/create something.\n"
        "- Use 'chat' for casual conversation, greetings, questions, or general help.\n"
        "- Use 'build' for requests to make, create, generate, design, or code a website/app/project.\n"
        f"User input: {user_prompt}"
    )
    debug_print(f"LLM call: router_agent -> classify prompt '{user_prompt}'")
    # JSON schema mode: sends the real schema, no tool call needed.
    response = llm.with_structured_output(RouteDecision, method="json_schema", strict=True).invoke(classification_prompt)
    debug_print(f"Router classification: route={response.route}, reason={response.reason}")
    return {
        "route": response.route,
        "user_prompt": user_prompt,
    }


def chat_agent(state: dict) -> dict:
    user_prompt = state.get("user_prompt", "")
    print("="*50 , user_prompt, "="*50)

    system_prompt = """
You are Zuno, a helpful AI assistant.
Rules:
- Answer everyday questions directly and briefly.
- If the user asks math, greetings, names, or general questions, answer clearly.
- If the user asks to create/build a website or app, do not answer as a normal chat; instead ask for requirements or route to the build flow.
- Be friendly and concise.
"""

    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])

    reply = response.content if hasattr(response, "content") else str(response)

    return {"reply": reply, "status": "DONE"}


def planner_agent(state : dict) -> dict :
    debug_print(f"Node planner_agent started with state keys={list(state.keys())}")
    user_prompt = state['user_prompt']
    history = state.get('history', [])
    debug_print(f"LLM call: planner_agent -> with_structured_output(Plan) with prompt={user_prompt}")
    # JSON schema mode (same as router).
    response = llm.with_structured_output(Plan, method="json_schema", strict=True).invoke(planner_prompt(user_prompt, history))
    debug_print(f"LLM response: planner_agent -> {response}")

    if response is None:
        raise ValueError("Planner did not return a valid response.")
    debug_print("Node planner_agent finished successfully")
    return {
        'plan' : response
    }

def architect_agent(state : dict) -> dict:
    debug_print(f"Node architect_agent started with plan={state.get('plan')}")
    plan : Plan = state['plan']
    debug_print(f"LLM call: architect_agent -> with_structured_output(TaskPlan) with plan={plan}")
    # JSON schema mode (same as router).
    response = llm.with_structured_output(TaskPlan, method="json_schema", strict=True).invoke(architect_prompt(plan))
    debug_print(f"LLM response: architect_agent -> {response}")

    if response is None:
            raise ValueError("Architect did not return a valid response.")

    response.plan = plan
    debug_print("Node architect_agent finished successfully")

    return {
        'task_plan' : response
    }


# FIX 3: the coder no longer saves files through tool-call JSON.
# Groq rejected the coder's write_file calls with 400 "Failed to parse tool
# call arguments as JSON" because a whole file's content inside one JSON
# argument gets truncated or mis-escaped. Instead the coder returns the file
# as a fenced code block and Python writes it deterministically.
FILE_BLOCK_RE = re.compile(r"```[^\n]*path=([^\s`]+)[^\n]*\n(.*?)```", re.S)


def extract_file_blocks(text: str) -> list[tuple[str, str]]:
    """Return [(path, content)] from ```... path=<filepath> fenced blocks."""
    blocks = []
    for path, content in FILE_BLOCK_RE.findall(text or ""):
        path = path.strip().strip('"').strip("'")
        blocks.append((path, content))
    return blocks


def _agent_final_text(result: dict) -> str:
    """Last non-empty text the agent produced (handles str / content blocks)."""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    for msg in reversed(messages):
        content = getattr(msg, "content", "") or ""
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        if isinstance(content, str) and content.strip():
            return content
    return ""


def coding_agent(state: dict) -> dict:
    debug_print(f"Node coding_agent started with current_step_id={state.get('coder_state').current_step_id if state.get('coder_state') else 'new'}")

    coder_state = state.get("coder_state")
    if coder_state is None:
         coder_state = CoderState(task_plan=state['task_plan'], current_step_id=0)

    steps = coder_state.task_plan.implementation_steps

    if coder_state.current_step_id >= len(steps):
         debug_print("Node coding_agent finished: no remaining steps")
         return {"coder_state" : coder_state, "status" : "DONE"}

    current_task = steps[coder_state.current_step_id]
    debug_print(f"Coding task: step={coder_state.current_step_id}, file={current_task.filepath}, task={current_task.task_description}")

    # Each conversation has its own folder, so builds do not overwrite
    # each other. The code block still says just the filename.
    conversation_id = state.get("conversation_id")
    target_path = f"{conversation_id}/{current_task.filepath}" if conversation_id else current_task.filepath

    existing_content = read_file.run(target_path)
    debug_print(f"Read existing file content for {target_path}: {existing_content[:200] if existing_content else '<empty>'}")

    # write_file is deliberately NOT a tool here anymore (see FIX 3 above).
    # read/list tools stay: their arguments are just a path, tiny and safe.
    coder_tool = [read_file, get_current_directory, list_file]
    system_prompt = coder_system_prompt() + (
        "\n\nFile saving rule: NEVER call any tool to write a file. "
        "Return the complete file content in a fenced code block instead; "
        "it will be saved for you."
    )
    react_agent = create_agent(
        model=llm,
        tools=coder_tool,
        system_prompt=system_prompt
    )

    base_prompt = (
         f"Task: {current_task.task_description}\n"
         f"File: {current_task.filepath}\n"
         f"Existing content:\n{existing_content}\n\n"
         "Return the COMPLETE new content of this file in exactly one fenced code block.\n"
         "The opening fence must contain the file path, like this:\n"
         f"```css path={current_task.filepath}\n"
         "...full file content...\n"
         "```\n"
         "Rules:\n"
         "- One block, one file, complete content. Never truncate it and never write '...' in place of code.\n"
         "- Do NOT call any tool to save the file. Just return the code block.\n"
         "- If you need to look at other files first, use read_file / list_files, then return the block."
    )

    user_prompt = base_prompt
    last_error = ""
    for attempt in range(2):
        debug_print(f"LLM call: coding_agent -> react_agent.invoke attempt={attempt}")
        result = react_agent.invoke({"messages" : [{'role' : 'user', "content" : user_prompt}]})
        debug_print(f"LLM response: coding_agent -> {result}")

        blocks = extract_file_blocks(_agent_final_text(result))
        debug_print(f"Coder returned {len(blocks)} file block(s): {[p for p, _ in blocks]}")

        match = next((b for b in blocks if b[0] == current_task.filepath), None)
        if match is None and len(blocks) == 1:
            # Lenient fallback: a single block with no matching path is this file.
            match = blocks[0]

        if match is not None:
            # Deterministic write from Python, not from LLM tool-call JSON.
            write_file.invoke({"path": target_path, "content": match[1]})
            debug_print(f"Wrote {target_path} ({len(match[1])} chars)")
            break

        last_error = (
            f"no fenced code block with path={current_task.filepath} found"
            if not blocks else
            "returned blocks were for other files: " + ", ".join(p for p, _ in blocks)
        )
        debug_print(f"Coding attempt {attempt} failed: {last_error}")
        user_prompt = base_prompt + (
            f"\n\nYour previous attempt failed ({last_error}). "
            "Return ONLY the fenced code block, complete and untruncated."
        )
    else:
        raise ValueError(f"Coder failed to produce {current_task.filepath}: {last_error}")

    coder_state.current_step_id += 1
    debug_print(f"Node coding_agent finished, next step={coder_state.current_step_id}")

    return{"coder_state": coder_state}

#========================== GRAPH =============================


graph = StateGraph(dict)

graph.set_entry_point("router")
graph.add_node("router", router_agent)
graph.add_node("chat", chat_agent)
graph.add_node("planner", planner_agent)
graph.add_node("architect", architect_agent)
graph.add_node("coder", coding_agent)


graph.add_conditional_edges(
    source="router",
    path=lambda s: "chat" if s.get("route") == "chat" else "planner",
    path_map={"chat": "chat", "planner": "planner"}
)
graph.add_edge("chat", END)
graph.add_edge("planner", "architect")
graph.add_edge("architect", "coder")
graph.add_conditional_edges(
    source="coder",
    path=lambda s: "END" if s.get('status') == 'DONE' else "coder",
    path_map={"END":END, "coder" : "coder"}
)


agent = graph.compile()

if __name__ == "__main__":

    user_prompt = "Create a scintific calculator"
    result = agent.invoke({"user_prompt" : user_prompt})
    print(result)
    # print(llm.invoke("Hello"))

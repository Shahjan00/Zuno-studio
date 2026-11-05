from pathlib import Path
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
    temperature=0
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
    response = llm.with_structured_output(RouteDecision).invoke(classification_prompt)
    debug_print(f"Router classification: route={response.route}, reason={response.reason}")
    return {
        "route": response.route,
        "user_prompt": user_prompt,
    }


def chat_agent(state: dict) -> dict:
    user_prompt = state.get("user_prompt", "")

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
    debug_print(f"LLM call: planner_agent -> with_structured_output(Plan) with prompt={user_prompt}")
    response = llm.with_structured_output(Plan).invoke(planner_prompt(user_prompt))
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
    response = llm.with_structured_output(TaskPlan).invoke(architect_prompt(plan))
    debug_print(f"LLM response: architect_agent -> {response}")

    if response is None:
            raise ValueError("Architect did not return a valid response.")

    response.plan = plan
    debug_print("Node architect_agent finished successfully")

    return {
        'task_plan' : response
    }
    
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

    existing_content = read_file.run(current_task.filepath)
    debug_print(f"Read existing file content for {current_task.filepath}: {existing_content[:200] if existing_content else '<empty>'}")

    user_prompt = (
         f"Task :  {current_task.task_description}\n"
         f"File : {current_task.filepath}\n"
         f"Existing content : \n{existing_content}\n"
         "Use write_file(path, content) to save your changes"
    )
    system_prompt = coder_system_prompt()
    # response = llm.invoke(user_prompt + system_prompt)

    coder_tool = [read_file, write_file, get_current_directory, list_file]
    react_agent = create_agent(
        model=llm,
        tools=coder_tool,
        system_prompt=system_prompt
    )
    debug_print(f"LLM call: coding_agent -> react_agent.invoke with user_prompt={user_prompt}")
    result = react_agent.invoke({"messages" : [{'role' : 'user', "content" : user_prompt}]})
    debug_print(f"LLM response: coding_agent -> {result}")

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


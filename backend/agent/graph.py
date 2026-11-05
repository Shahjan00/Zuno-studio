from pathlib import Path

from langchain_google_genai import  ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langchain.agents import create_agent
from dotenv import load_dotenv
import os

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
    model="openai/gpt-oss-120b",
    temperature=0
)

#========================= NODES =============================

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

graph.set_entry_point("planner")
graph.add_node("planner", planner_agent)
graph.add_node("architect", architect_agent)
graph.add_node("coder", coding_agent)


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


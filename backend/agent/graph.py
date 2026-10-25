from langchain_google_genai import  ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain.agents import create_agent
from dotenv import load_dotenv
import os

from .prompts import *
from .states import *
from .tools import *

load_dotenv()


llm = ChatGoogleGenerativeAI(model = "gemini-3.6-flash")

#========================= NODES =============================

def planner_agent(state : dict) -> dict :
    user_prompt = state['user_prompt']
    response = llm.with_structured_output(Plan).invoke(planner_prompt(user_prompt))

    if response is None:
        raise ValueError("Planner did not return a valid response.")
    return {
        'plan' : response
    }

def architect_agent(state : dict) -> dict:
    plan : Plan = state['plan']
    response = llm.with_structured_output(TaskPlan).invoke(architect_prompt(plan))

    if response is None:
            raise ValueError("Architect did not return a valid response.")

    response.plan = plan

    return {
        'task_plan' : response
    }
    
def coding_agent(state: dict) -> dict:

    coder_state = state.get("coder_state")
    if coder_state is None:
         coder_state = CoderState(task_plan=state['task_plan'], current_step_id=0)

    steps = coder_state.task_plan.implementation_steps

    if coder_state.current_step_id >= len(steps):
         return {"coder_state" : coder_state, "status" : "DONE"}
    
    current_task = steps[coder_state.current_step_id]

    existing_content = read_file.run(current_task.filepath)

    user_prompt = (
         f"Task :  {current_task.task_description}\n"
         f"File : {current_task.filepath}\n"
         f"Existing content : \n{existing_content}\n"
         "Use write_file(path, content) to save your changes"
    )
    system_prompt = coder_system_prompt()
    # response = llm.invoke(user_prompt + system_prompt)

    coder_tool = [read_file,write_file,get_current_directory,list_files]
    react_agent = create_agent(
        model=llm,
        tools=coder_tool,
        system_prompt=system_prompt
    )
    react_agent.invoke({"messages" : [{'role' : 'user', "content" : user_prompt}]})

    coder_state.current_step_id += 1

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


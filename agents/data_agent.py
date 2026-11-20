from utils.llm_pick import pick_llm
from utils.etl_tools import ETLTools
from models.schema import ETLAgentSchema, RouterSchema, DataAgentSchema
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langchain.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from agents.etl_analyst import etl_analyst
from agents.sql_analyst import sql_analyst
from typing import  Literal

llm = pick_llm('medium')

llm_router = llm.with_structured_output(RouterSchema)


def router_node(state: DataAgentSchema):
  message = state.messages[-1].content

  response = llm_router.invoke(message)

  return {"route_response": response.answer}


def etl_node(state: DataAgentSchema):
  message = state.messages[-1].content

  response = etl_analyst.invoke(
      {"messages":[HumanMessage(content=message)]}
  )

  return {"messages": [AIMessage(content=response["messages"][-1].content)]}


def sql_node(state: DataAgentSchema):
  message = state.messages[-1].content
  user_input = {"user_question": message}

  response = sql_analyst.invoke(user_input)

  return {"messages":[AIMessage(content=response["final_answer"])]}


def route_edge(state:DataAgentSchema) -> Literal["etl_node", "sql_node"]:
  if state.route_response == "sql":
        return "sql_node"
  elif state.route_response == "etl":
    return "etl_node"
  else:
    raise ValueError(f"Invalid route response: {state.route_response}")


data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)


data_agent_graph.add_edge(START, "router_node")
data_agent_graph.add_conditional_edges("router_node", route_edge)
data_agent_graph.add_edge("etl_node", END)
data_agent_graph.add_edge("sql_node", END)



data_agent  = data_agent_graph.compile()


if __name__ == "__main__":

  response = data_agent.invoke(
    {
       "messages":[HumanMessage(content="Sab se zyada cancel karne wale 5 riders kaun hain? saath mn unka names bhi btao")],
    }
    )

  print(response['messages'][-1].content)
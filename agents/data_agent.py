from utils.llm_pick import pick_llm
from models.schema import RouterSchema, DataAgentSchema
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from agents.etl_analyst import etl_analyst
from agents.sql_analyst import sql_analyst
from agents.email_agent import email_graph
from langgraph.types import interrupt, Command
from typing import  Literal
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
import os
from dotenv import load_dotenv
load_dotenv()



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
  response = sql_analyst.invoke({"user_question": message})
  answer = response["final_answer"]

  return {
    "messages":[AIMessage(content=response["final_answer"])],
    "data": answer, 
    "wants_email": "",
  }


def ask_send_email_node():
  answer = interrupt(
      {"message": "Do you want to send this result via email? (yes/no)"}
  )
  return {"wants_email": answer.strip().lower()}

def ask_email_details_node():
  details = interrupt(
      {
        "message": (
              "Let's send it — who's the recipient (name + email), and what's the message? ",
              "Example: I want to send this report to Hassan on this email hassan@gmail.com"
          )
      }
  )
  return {"question": details}


def route_edge(state:DataAgentSchema) -> Literal["etl_node", "sql_node"]:
  if state.route_response == "sql":
        return "sql_node"
  elif state.route_response == "etl":
    return "etl_node"
  else:
    raise ValueError(f"Invalid route response: {state.route_response}")


def email_edge(state: DataAgentSchema) -> Literal["ask_email_details", "__end__"]:
  if state.wants_email in ("yes", "y", "ok", "done", "k", "send"):
    return "ask_email_details"
  return END


data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)
data_agent_graph.add_node("ask_send_email", ask_send_email_node)
data_agent_graph.add_node("ask_email_details", ask_email_details_node)
data_agent_graph.add_node("email_node", email_graph)   


data_agent_graph.add_edge(START, "router_node")
data_agent_graph.add_conditional_edges("router_node", route_edge)
data_agent_graph.add_edge("etl_node", END)
data_agent_graph.add_edge("sql_node", END)

data_agent_graph.add_edge("sql_node", "ask_send_email")
data_agent_graph.add_conditional_edges("ask_send_email", email_edge)
data_agent_graph.add_edge("ask_email_details", "email_node")
data_agent_graph.add_edge("email_node", END)



_conn = psycopg.connect(
    os.getenv("DB_URI"),
    autocommit=True,
    row_factory=dict_row
)

checkpointer = PostgresSaver(_conn)
checkpointer.setup()

data_agent  = data_agent_graph.compile(checkpointer=checkpointer)


if __name__ == "__main__":
  config = {"configurable": {"thread_id": "1"}}

  result = data_agent.invoke(
    {
       "messages":[HumanMessage(content="Tell me Top 5 customers by total sales")],
    },
    config
    )

  print(result['messages'][-1].content)

  while "__interrupt__" in result:
    payload = result["__interrupt__"][0].value

    if "subject" in payload:
      print("\n" + "-" * 60)
      print("Subject:", payload["subject"])
      print("Body:", payload["body"])
      print("-" * 60 + "\n")

    print(payload["message"])
    answer = input("> ")

    result = data_agent.invoke(Command(resume=answer), config)

    if "__interrupt__" not in result:
      print("\nAI:", result["messages"][-1].content)
from utils.llm_pick import pick_llm
from utils.etl_tools import ETLTools
from models.schema import ETLAgentSchema
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END, START
from langchain.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
import os


@tool
def extract_load_tool(url: str, output_folder: str, format: str):
    """
    This tool extracts the data from the API (url) and loads it
    into the desired location (destination)
  
    Args:
      url (str): The API endpoints fron which to extract data.
      output_folder (str): The folder where the extracted data will be saved
    """

    etl_tools = ETLTools()
    return etl_tools.extract_load(url, output_folder, format)


@tool
def transform_load_tool(input_file_path: str, output_folder:str,output_format:str, user_question:str):
  """
    This tool transforms the data from the specified file and loads it into the
    desired location (output_folder).
  
    Args:
      file_path (str): The path to the file containing the data to be transformed.
      output_folder (str): The folder where the transformed data will be saved.
      output_format (str): The format in which to save the transformed data (csv, json, parquet).
      Returns:
        str: A message indicating the success or failure of the operation.
  """

  os.makedirs(output_folder, exist_ok=True)

  etl_tool = ETLTools()
  top3_rows = etl_tool.transform_load_context(input_file_path)

  llm = pick_llm('low')

  prompt = f"""
            You are a Python Data Analyst who uses Pandas to analyze data. 
            You need to provide only the Pandas Code that will help to perform the right ETL operations on the data stored in the file : {input_file_path}
            as per the user's question. Do not provide any explanation or comments, only
            the code should be provided. The code should be in a format that can be executed 
            in a Python environment with Pandas installed. 
            Don't write anything else than Pandas Code. \n
            
            Create the Pandas Dataframe from the data stored in the file : {input_file_path} and then 
            write the code to transform and save the data at {output_folder}.
            Here's the user's question: {user_question}\n
            Here's the context of the data you will be analyzing: {top3_rows}\n

        """

  response = llm.invoke(prompt).content
  pandas_code = response.strip().strip('```').strip().lstrip('python').strip()
  results = etl_tool.execute_code(pandas_code)

  return f"The data is transformed and saved at {output_folder} in {output_format} format. \n\n Pandas Code Executed: \n {pandas_code} \n\n Execution Result: \n {results}" 

tools = [extract_load_tool, transform_load_tool]
llm_bind = pick_llm("hard").bind_tools(tools)


def llm_node(state: ETLAgentSchema):
   SYSTEM_PROMPT = SystemMessage(
      content="""You are a Python Data Analyst with access to tools for
        extract-and-load and transform-and-load operations.

        Rules:
          - ALWAYS call the appropriate tool to perform the user's request.
          - Never claim an operation is done unless a ToolMessage in THIS conversation confirms it.
          - After a tool result confirms success, reply with a short summary and stop."""
    )
   
   final_answer = llm_bind.invoke([SYSTEM_PROMPT] + state.messages) 

   return {"messages": [final_answer]}



graph = StateGraph(ETLAgentSchema)

graph.add_node("llm_node", llm_node)
graph.add_node("tools", ToolNode(tools))

graph.add_edge(START, "llm_node")
graph.add_conditional_edges("llm_node", tools_condition)
graph.add_edge("tools", "llm_node")

etl_analyst = graph.compile()




# if __name__ == "__main__":
#     # response = etl_analyst.invoke(
#     #     {"messages":[HumanMessage(content="I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon' and save it to data/extract folder in the csv folder")]}
#     # )

# #     response = etl_analyst.invoke(
# #          {"messages":[HumanMessage(content=f"""
# #             I want to transform the data stored in the 'D:\python\data-agent\data\extract\extracted_data.csv' file 
# #             and save the transformed data in the 'D:\python\data-agent\data\transform' folder in the csv format.
# #             The transformation should filter the data to show bulbasaur pokemon only.
# # """)]}
# #     )

#     for m in response["messages"]:
#       print(type(m).__name__, "->", m.content)
#     print(response["messages"][-1].content)
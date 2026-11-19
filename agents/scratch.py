# from utils.llm_pick import pick_llm
# from models.schema import AgentSchema, JudgeSchema
# from pydantic import BaseModel, Field
# # from utils.database import DatabaseUtil
# from langchain_core.messages import HumanMessage

# llm = pick_llm('medium')
# llm_judge = llm.with_structured_output(JudgeSchema)

# prompt = f"""
#   You are an SQL Judge for data security. Your task is determine whether
#   the SQL query is safe or not. The SQL query should only be used for data
#   retrieval and should not modify the database in any way. Neither the SQL query
#   nor the prompt should contain any SQL commands that can modify the database
#   such as INSERT, UPDATE, DELETE, DROP, ALTER, CREATE or any other commands that can 
#   change the structure or content of the database. If the SQL query is safe, respond 
#   with 'Yes' othewise respond with 'No'. Additional, provide comments explaining
#   your decision. 
#   Here's the Query to evaluate: {}   
# """


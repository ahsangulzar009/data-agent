from utils.llm_pick import pick_llm
from models.schema import AgentSchema, CuratedQuestion, JudgeSchema
from utils.database import DatabaseUtil
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from typing import Literal


def curated_ques(state: AgentSchema):
    llm = pick_llm("medium").with_structured_output(CuratedQuestion)
    result = llm.invoke(
        "Rewrite the user's question so it is clear, specific, and self-contained. "
        "Do not add information that is not implied.\n\n"
        f"Question: {state.user_question}"
    )

    return {
        "curated_ques": result.curated_question,
        "messages": [HumanMessage(content=result.curated_question)],
    }


def generate_sql_query(state: AgentSchema):

    obj = DatabaseUtil()
    schema_info = obj.schema_details("public")

    prompt = f"""
        You are an SQL analyst agent. Your task is to convert the user's natural language
        query into Postgresql query that can be executed on the database. You are provided with 
        the user's original query and the schema details of the database, including table names, 
        column names, data types, and sample data for each table so that you can understand the 
        structure of database and generate accurate SQL query. Unless user explicitly asks for
        specific number of rows, always limit the output to 10 rows.
        STRICT NOTE: -  Just generate the SQL query without any explanation or additional text because
        this query  will be executed directly on the database. So, the output should be SQL ready
        to be executed without modification.

        User's Original Query: {state.curated_ques}

        Database Schema Details: {schema_info}

    """

    llm = pick_llm("hard")
    generated_sql_query = llm.invoke(prompt)

    return {
        "prompt_query_context": prompt,
        "generated_sql_query": generated_sql_query.content,
        "messages": [AIMessage(content=generated_sql_query.content)],
    }


def is_safe_sql(state: AgentSchema):
    llm = pick_llm("medium")
    llm_judge = llm.with_structured_output(JudgeSchema)

    prompt = f"""
        You are an SQL Judge for data security. Your task is determine whether
        the SQL query is safe or not. The SQL query should only be used for data
        retrieval and should not modify the database in any way. Neither the SQL query
        nor the prompt should contain any SQL commands that can modify the database
        such as INSERT, UPDATE, DELETE, DROP, ALTER, CREATE or any other commands that can 
        change the structure or content of the database. If the SQL query is safe, respond 
        with 'Yes' othewise respond with 'No'. Additional, provide comments explaining
        your decision. 
        Here's the Query to evaluate: {state.generated_sql_query}   
    """
    response = llm_judge.invoke(prompt)

    return {
        "is_safe": response.answer,
        "final_answer": response.comments,
        "messages": [AIMessage(content=f"Safe: {response.answer}. Reason: {response.comments}")],
    }


def cancel_query(state: AgentSchema):
    return {
        "final_answer": f"The generated SQL query was deemed unsafe to execute. The reason provided by the judge is: \n '{state.final_answer}'",
        "messages": [AIMessage(content=state.final_answer)]
    }

def execute_sql(state: AgentSchema):
    obj = DatabaseUtil()
    execution_result = obj.execute_query(state.generated_sql_query)
    return {"sql_query_execution_result": execution_result}

def represent_final_answer(state: AgentSchema):
    llm = pick_llm("low")
    prompt= f"""
        You are an SQL analyst agent. Your task is to provide a final answer to the user based on the
        execution result of the SQL query and the user's original question. The final answer should be
        concise, clear, and directly address the user's query. Avoid including any SQL code or technical
        details in the final answer. The final answer should be in a user-friendly format that is easy to
        understand. If the execution result is empty or does not provide a clear answer to the user's question, explain this in the final answer. \n
        Here is the execution result: {state.sql_query_execution_result} \n
        Here is the user's original question: {state.curated_ques}

        Rules:
            - Show a currency symbol or name ONLY if the execution result itself contains
              currency information (for example a currency column or code like PKR, USD).
            - If the result has no currency information, show monetary values as plain numbers
              (e.g. 767.21). Never guess or assume a currency.
            - Only use facts present in the execution result. Do not invent anything else.
    """

    llm_response = llm.invoke(prompt).content

    return {"final_answer": llm_response, "messages": [AIMessage(content=llm_response)]}


def is_sql_safe_adge(state: AgentSchema) -> Literal["execute_sql", "cancel_query"]:
    is_safe =  state.is_safe

    if is_safe.lower() == 'yes':
        return "execute_sql"
    else:
        return "cancel_query"


graph = StateGraph(AgentSchema)

graph.add_node("curated_ques", curated_ques)
graph.add_node("generate_sql_query", generate_sql_query)
graph.add_node("is_safe_sql", is_safe_sql)
graph.add_node("cancel_query", cancel_query)
graph.add_node("execute_sql", execute_sql)
graph.add_node("represent_final_answer", represent_final_answer)

graph.add_edge(START, "curated_ques")
graph.add_edge("curated_ques", "generate_sql_query")
graph.add_edge("generate_sql_query", "is_safe_sql")

graph.add_conditional_edges("is_safe_sql", is_sql_safe_adge)
graph.add_edge("cancel_query", END)
graph.add_edge("execute_sql", "represent_final_answer")
graph.add_edge("represent_final_answer", END)

sql_analyst =  graph.compile()


if __name__ == "__main__":
    user_input = {"user_question": "Sweep out all the records of users who live in Vancouver, we don't need them anymore."}
    result = sql_analyst.invoke(user_input)

    print("SQL:\n", result.get("generated_sql_query"))
    print("\nRAW RESULT:\n", result.get("sql_query_execution_result"))
    print("\nFINAL ANSWER:\n", result.get("final_answer"))
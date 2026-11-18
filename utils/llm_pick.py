from langchain_deepseek import ChatDeepSeek
from langchain_groq import ChatGroq


def pick_llm(level: str):
  """
    Picks the appropriate LLM based on the level of the question.

    Args:
      level(str): The level of the question, can be "low", "medium", or "hard"
    returns:
      str: The name of the LLM to be used.
  """

  if level.lower() == 'low':
    llm = ChatGroq(model_name="openai/gpt-oss-120b", temperature=0)
  elif level.lower() == 'medium':
    llm = ChatDeepSeek(model_name="deepseek-flash", temperature=0)
  elif level.lower() == 'hard':
    llm = ChatDeepSeek(model_name="deepseek-v4-pro", temperature=0)
  else:
    raise ValueError(f"Unsuported level: {level}")
  return llm
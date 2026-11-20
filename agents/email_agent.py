
from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, END, START
from langgraph.types import interrupt
from utils.llm_pick import pick_llm
from models.schema import EmailState, UserDetails, DraftEmail
from typing import Literal
from utils.send_email import send_email



llm = pick_llm("medium")

def retriever_node(state: EmailState):
  llm_for_user_details = llm.with_structured_output(UserDetails)
  user_details: UserDetails = llm_for_user_details.invoke(
    f"Retrieve the user details from this query: {state.question}"
  )

  return {
    "mail_reason": user_details.mail_reason,
    "recipient_name": user_details.recipient_name,
    "recipient_email": user_details.recipient_email,
  }


def draft_node(state: EmailState):
  """Draft Email"""
  draft_email = llm.with_structured_output(DraftEmail)

  prompt = (
    f"Write an email to {state.recipient_name or 'the recipient'} "
    f"about: {state.mail_reason}. "
    "Keep the body under 500 words."
  )

    # SQL ka data email mn shamil karo
  if state.data:
    prompt += (
      f"\n\nInclude this data in the email (use only these facts, do not invent anything):\n"
      f"{state.data}"
    )

    if state.feedback:
      prompt += (
        f"\n\nPrevious draft:\nSubject: {state.subject}\nBody: {state.body}\n\n"
        f"Rewrite it considering this feedback: {state.feedback}"
      )

  draft: DraftEmail = draft_email.invoke(prompt)

  return {"subject": draft.subject, "body": draft.body}

def review_node(state: EmailState):
  response = interrupt(
    {
      "message": "Type 'Yes' to Approve or write what to change.",
      "subject": state.subject,
      "body": state.body,
    }
  )

  if response.strip().lower() in ("yes", "y", "ok", "done", "k", "go"):
    return {"feedback": ""}

  return {"feedback": response, "feedback_count": state.feedback_count + 1}

def cancel_node():
  return {
    "response": "Email not sent, because you have reached the limit of feedbacks."
  }

def send_email_node(state: EmailState):
  """Send final email"""
  res = send_email(state.recipient_email, state.subject, state.body)

  return {"response": res}

def router(state: EmailState) -> Literal["draft", "send", "cancel"]:
  if not state.feedback:
    return "send"
  if state.feedback_count > 50:
    return "cancel"
  return "draft"



graph = StateGraph(EmailState)

graph.add_node("retriever", retriever_node)
graph.add_node("draft", draft_node)
graph.add_node("review", review_node)
graph.add_node("send", send_email_node)
graph.add_node("cancel", cancel_node)

graph.add_edge(START, "retriever")
graph.add_edge("retriever", "draft")
graph.add_edge("draft", "review")
graph.add_conditional_edges("review", router)
graph.add_edge("send", END)
graph.add_edge("cancel", END)

email_graph = graph.compile()

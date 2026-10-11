from agent.llm import llm
from agent.state import AgentState

def intake_node(state:AgentState):
    prompt = f"""
    You are an AI worker's intake module.
    Read the user's task and extract the end goal in one clear sentence.

    User task: {state['task']}

    Return only the goal sentence. No explanation, no quotes.
    """
    
    response=llm.invoke(prompt)
    print("\n[INTAKE]\n",response.content.strip())
    return {"goal":response.content.strip()}

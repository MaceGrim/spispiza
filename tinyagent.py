# tinyagent.py

import os, json, pkgutil, importlib, inspect
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

CONNECTOR_PACKAGE = "connectors"
connectors_path = os.path.join(os.path.dirname(__file__), CONNECTOR_PACKAGE)

# tool_name -> (fn, spec_dict)
TOOLS: dict[str, tuple[callable, dict]] = {}

# Ensure the connectors directory exists
os.makedirs(connectors_path, exist_ok=True)

for _, module_name, _ in pkgutil.iter_modules([connectors_path]):
    try:
        module = importlib.import_module(f"{CONNECTOR_PACKAGE}.{module_name}")
        for _, fn in inspect.getmembers(module, inspect.isfunction):
            meta = getattr(fn, "__tool__", None)
            if not meta:
                continue
            # store it in the map
            TOOLS[meta["name"]] = (fn, meta)
    except ImportError as e:
        print(f"Error importing {module_name}: {e}")

# build the OpenAI tools spec
TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": spec["description"],
            "parameters": spec["parameters"],
        }
    }
    for name, (_, spec) in TOOLS.items()
]

# ─── Agent & tool dispatch ────────────────────────────────────────────────
def agent(msg: str):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": msg}],
        tools=TOOLS_SPEC,
        tool_choice="auto"
    )

def summarize_response(original_query, tool_name, raw_result):
    """Summarize the raw result in human-friendly language"""
    try:
        # Convert the result to a string if it's not already
        if not isinstance(raw_result, str):
            raw_result = json.dumps(raw_result, indent=2)
        
        # Create a prompt for the LLM to summarize the result
        prompt = f"""
        The user asked: "{original_query}"
        
        The tool "{tool_name}" returned this result:
        {raw_result}
        
        Please provide a concise, human-friendly summary of this information. 
        Focus on the most important details that answer the user's question.
        Use natural language and avoid technical jargon.
        """
        
        # Get a summary from the LLM
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        # If summarization fails, return the original result
        print(f"Summarization error: {e}")
        return raw_result

def process_tool_calls(response, original_query):
    choice = response.choices[0].message
    if not getattr(choice, "tool_calls", None):
        return choice.content

    results = []
    for call in choice.tool_calls:
        name = call.function.name
        args = json.loads(call.function.arguments)

        # look up the real function directly
        fn, _ = TOOLS[name]
        try:
            raw_result = fn(**args)
            
            # Summarize the result
            summarized_result = summarize_response(original_query, name, raw_result)
            
            results.append(f"{name} → {summarized_result}")
        except Exception as e:
            results.append(f"{name} → Error: {str(e)}")

    return "\n".join(results)


def run_agent(prompt: str):
    resp = agent(prompt)
    return process_tool_calls(resp, prompt)

# ─── Example usage ────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("API key missing; please set OPENAI_API_KEY in your .env")
        exit(1)

    # ensure mem folder is in place
    os.makedirs("mem", exist_ok=True)

    print("Available tools:")
    for name in TOOLS:
        print(f"- {name}")
    
    user_q = input("\nEnter your question: ")
    if not user_q:
        user_q = "What events do I have tomorrow?"
    
    print("\nProcessing...")
    result = run_agent(user_q)
    print(f"\nResult:\n{result}")

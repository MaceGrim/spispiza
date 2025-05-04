from openai import OpenAI
import csv, datetime as dt, os, requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

client = OpenAI()

# ─── connectors ──────────────────────────────────────────────
def read_csv(name):
    with open(f"mem/{name}.csv") as f: return list(csv.DictReader(f))

def write_csv(name, row):
    fn = f"mem/{name}.csv"
    exists = os.path.exists(fn)
    with open(fn, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if not exists: w.writeheader()
        w.writerow(row)

def get_calendar_events():
    # Example: Google Calendar API wrapper
    # In a real implementation, you would use the Google Calendar API
    # This is a placeholder that returns mock data
    events = [
        {"title": "Team Meeting", "start": "2023-10-10T10:00:00", "end": "2023-10-10T11:00:00"},
        {"title": "Lunch with Client", "start": "2023-10-10T12:30:00", "end": "2023-10-10T13:30:00"}
    ]
    return events

# ─── LLM agent call ──────────────────────────────────────────
TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "read_csv",
            "description": "Fetch memory rows from a CSV file",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the CSV file (without extension)"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_csv",
            "description": "Write a row to a CSV file",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the CSV file (without extension)"
                    },
                    "row": {
                        "type": "object",
                        "description": "Data to write as a row"
                    }
                },
                "required": ["name", "row"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_calendar_events",
            "description": "Fetch calendar events",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def agent(msg):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": msg}],
        tools=TOOLS_SPEC,
        tool_choice="auto"
    )

def process_tool_calls(response):
    """Process tool calls from the LLM response"""
    if not hasattr(response, 'choices') or not response.choices:
        return "No response received"
    
    choice = response.choices[0]
    if not hasattr(choice, 'message') or not hasattr(choice.message, 'tool_calls'):
        return choice.message.content
    
    tool_calls = choice.message.tool_calls
    results = []
    
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = eval(tool_call.function.arguments)
        
        if function_name == "read_csv":
            result = read_csv(**function_args)
        elif function_name == "write_csv":
            result = write_csv(**function_args)
        elif function_name == "get_calendar_events":
            result = get_calendar_events()
        else:
            result = f"Unknown function: {function_name}"
        
        results.append(f"{function_name} result: {result}")
    
    return "\n".join(results)

def run_agent(user_input):
    """Run the agent with user input and process any tool calls"""
    response = agent(user_input)
    return process_tool_calls(response)

# Example usage
if __name__ == "__main__":
    # API key is now loaded from .env file
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found in environment variables.")
        print("Please add it to your .env file or set it manually.")
    
    # Create the mem directory if it doesn't exist
    if not os.path.exists("mem"):
        os.makedirs("mem")
    
    # Example: Create a sample CSV file
    sample_data = {"date": dt.datetime.now().isoformat(), "note": "Initial test note"}
    write_csv("notes", sample_data)
    
    # Example: Run the agent
    user_query = "What notes do I have saved?"
    print(f"User: {user_query}")
    result = run_agent(user_query)
    print(f"Agent result: {result}")

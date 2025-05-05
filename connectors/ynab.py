# connectors/ynab.py

import os
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

def tool(name, description, parameters):
    """Decorator to mark a function as a tool for the agent"""
    def decorator(fn):
        fn.__tool__ = {
            "name": name,
            "description": description,
            "parameters": parameters
        }
        return fn
    return decorator

# Base URL for YNAB API
BASE_URL = "https://api.youneedabudget.com/v1"

def get_headers():
    """Get the authorization headers for YNAB API"""
    token = os.environ.get("YNAB_TOKEN")
    if not token:
        raise ValueError("YNAB_TOKEN not found in environment variables")
    return {"Authorization": f"Bearer {token}"}

@tool(
    name="get_budgets",
    description="Get a list of budgets from YNAB",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
def get_budgets():
    """Get a list of budgets from YNAB"""
    response = requests.get(f"{BASE_URL}/budgets", headers=get_headers())
    response.raise_for_status()
    return response.json()["data"]["budgets"]

@tool(
    name="get_accounts",
    description="Get a list of accounts for a specific budget",
    parameters={
        "type": "object",
        "properties": {
            "budget_id": {
                "type": "string",
                "description": "The ID of the budget to get accounts from"
            }
        },
        "required": ["budget_id"]
    }
)
def get_accounts(budget_id: str):
    """Get a list of accounts for a specific budget"""
    response = requests.get(f"{BASE_URL}/budgets/{budget_id}/accounts", headers=get_headers())
    response.raise_for_status()
    return response.json()["data"]["accounts"]

@tool(
    name="get_transactions",
    description="Get transactions for a specific account",
    parameters={
        "type": "object",
        "properties": {
            "budget_id": {
                "type": "string",
                "description": "The ID of the budget"
            },
            "account_id": {
                "type": "string",
                "description": "The ID of the account"
            },
            "since_date": {
                "type": "string",
                "description": "The earliest date for transactions (YYYY-MM-DD)"
            }
        },
        "required": ["budget_id", "account_id"]
    }
)
def get_transactions(budget_id: str, account_id: str, since_date: Optional[str] = None):
    """Get transactions for a specific account"""
    url = f"{BASE_URL}/budgets/{budget_id}/accounts/{account_id}/transactions"
    if since_date:
        url += f"?since_date={since_date}"
    
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    
    transactions = response.json()["data"]["transactions"]
    
    # Convert milliunits to actual currency values
    for transaction in transactions:
        if "amount" in transaction:
            transaction["amount"] = transaction["amount"] / 1000
    
    return transactions

@tool(
    name="get_budget_summary",
    description="Get a summary of budget categories and their balances",
    parameters={
        "type": "object",
        "properties": {
            "budget_id": {
                "type": "string",
                "description": "The ID of the budget"
            }
        },
        "required": ["budget_id"]
    }
)
def get_budget_summary(budget_id: str):
    """Get a summary of budget categories and their balances"""
    response = requests.get(f"{BASE_URL}/budgets/{budget_id}", headers=get_headers())
    response.raise_for_status()
    
    budget_data = response.json()["data"]["budget"]
    categories = budget_data.get("categories", [])
    
    # Convert milliunits to actual currency values
    for category in categories:
        if "balance" in category:
            category["balance"] = category["balance"] / 1000
        if "budgeted" in category:
            category["budgeted"] = category["budgeted"] / 1000
        if "activity" in category:
            category["activity"] = category["activity"] / 1000
    
    return {
        "name": budget_data.get("name", ""),
        "currency_format": budget_data.get("currency_format", {}),
        "categories": categories
    }

@tool(
    name="create_transaction",
    description="Create a new transaction in YNAB",
    parameters={
        "type": "object",
        "properties": {
            "budget_id": {
                "type": "string",
                "description": "The ID of the budget"
            },
            "account_id": {
                "type": "string",
                "description": "The ID of the account"
            },
            "date": {
                "type": "string",
                "description": "The date of the transaction (YYYY-MM-DD)"
            },
            "amount": {
                "type": "number",
                "description": "The amount of the transaction (negative for outflow, positive for inflow)"
            },
            "payee_name": {
                "type": "string",
                "description": "The name of the payee"
            },
            "category_id": {
                "type": "string",
                "description": "The ID of the category"
            },
            "memo": {
                "type": "string",
                "description": "A memo for the transaction"
            }
        },
        "required": ["budget_id", "account_id", "date", "amount", "payee_name"]
    }
)
def create_transaction(
    budget_id: str, 
    account_id: str, 
    date: str, 
    amount: float, 
    payee_name: str, 
    category_id: Optional[str] = None, 
    memo: Optional[str] = None
):
    """Create a new transaction in YNAB"""
    # Convert amount to milliunits (YNAB uses milliunits)
    amount_milliunits = int(amount * 1000)
    
    transaction_data = {
        "transaction": {
            "account_id": account_id,
            "date": date,
            "amount": amount_milliunits,
            "payee_name": payee_name,
            "cleared": "cleared",
            "approved": True
        }
    }
    
    if category_id:
        transaction_data["transaction"]["category_id"] = category_id
    
    if memo:
        transaction_data["transaction"]["memo"] = memo
    
    response = requests.post(
        f"{BASE_URL}/budgets/{budget_id}/transactions",
        headers=get_headers(),
        json=transaction_data
    )
    response.raise_for_status()
    
    return response.json()["data"]["transaction"]

# Remove or comment out the example usage at the bottom
# Example usage:
budgets = get_budgets()
print(budgets)
transactions = get_transactions("8b6871aa-bd9f-465d-99ed-697872bd813f", "2025-05-02")
print(transactions)
summary = get_budget_summary("8b6871aa-bd9f-465d-99ed-697872bd813f")
print(summary)

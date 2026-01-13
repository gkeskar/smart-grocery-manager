"""
Multi-Agent Grocery Assistant System

Three agents that work together:
1. CatalogAgent - Manages store catalogs (add, list, search, delete items)
2. ShoppingListAgent - Manages shopping list (add, remove, view, budget, archive)
3. ManagerAgent - Routes user requests to the appropriate specialist agent

Usage:
    from grocery_app import GroceryManager
    from agents import GroceryAgentSystem
    
    manager = GroceryManager()
    system = GroceryAgentSystem(manager)
    
    response = await system.run("Add organic milk to Trader Joe's catalog")
"""

import os
from time import time
from openai import AsyncOpenAI
from agents import Agent, Runner, function_tool, OpenAIChatCompletionsModel

# Simple cache for catalog operations
_catalog_cache = {}
_cache_ttl = 60  # Cache for 60 seconds

def _get_cached(key):
    """Get cached value if not expired."""
    if key in _catalog_cache:
        entry = _catalog_cache[key]
        if time() - entry['time'] < _cache_ttl:
            return entry['data']
    return None

def _set_cache(key, data):
    """Store data in cache."""
    _catalog_cache[key] = {'data': data, 'time': time()}

def _invalidate_cache(pattern=None):
    """Clear cache entries. If pattern provided, only clear matching keys."""
    global _catalog_cache
    if pattern is None:
        _catalog_cache = {}
    else:
        _catalog_cache = {k: v for k, v in _catalog_cache.items() if pattern not in k}


# ============================================
# MODEL SETUP
# ============================================

def setup_model():
    """Configure model (DeepSeek first, then Groq, then Gemini)."""
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    groq_api_key = os.getenv("GROQ_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY")
    
    DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    
    # Use DeepSeek first (reliable function calling)
    if deepseek_api_key:
        client = AsyncOpenAI(base_url=DEEPSEEK_BASE_URL, api_key=deepseek_api_key)
        model = OpenAIChatCompletionsModel(model="deepseek-chat", openai_client=client)
        model_name = "DeepSeek/Chat"
        return model, model_name
    # Fallback to Groq
    elif groq_api_key:
        client = AsyncOpenAI(base_url=GROQ_BASE_URL, api_key=groq_api_key)
        model = OpenAIChatCompletionsModel(model="llama-3.3-70b-versatile", openai_client=client)
        model_name = "Groq/Llama-3.3-70B"
        return model, model_name
    # Fallback to Gemini
    elif google_api_key:
        client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=google_api_key)
        model = OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=client)
        model_name = "Gemini/2.0-Flash"
        return model, model_name
    else:
        raise ValueError("No API key found! Set DEEPSEEK_API_KEY, GROQ_API_KEY, or GOOGLE_API_KEY")


# ============================================
# CATALOG AGENT TOOLS
# ============================================

def create_catalog_tools(manager):
    """Create tools that wrap GroceryManager catalog methods."""
    
    @function_tool
    def add_catalog_item(name: str, category: str, store: str, price: float, unit: str = "each") -> dict:
        """
        Add a NEW item to the grocery catalog for a specific store.
        
        Args:
            name: Name of the item (e.g., "Organic Milk", "Fresh Basil")
            category: Category (e.g., "Produce", "Dairy", "Frozen", "Pantry", "Snacks", "Bakery", "Meat")
            store: Store name (e.g., "Trader Joe's", "Safeway", "Costco", "Indian Groceries")
            price: Price per unit in dollars (e.g., 4.99)
            unit: Unit of measurement (e.g., "each", "lb", "bag", "package", "container")
        
        Returns:
            Result with success status and item details.
        """
        success, message, item = manager.add_catalog_item(store, name, category, price, unit)
        if success:
            _invalidate_cache(store)  # Clear cache for this store
        return {
            "success": success,
            "message": f"✅ {message}" if success else f"❌ {message}",
            "item": item
        }
    
    @function_tool
    def list_catalog_items(store: str, category: str = "") -> dict:
        """
        List items in the catalog for a specific store, optionally filtered by category.
        
        Args:
            store: Store name (e.g., "Trader Joe's", "Safeway", "Costco", "Indian Groceries")
            category: Category to filter by (e.g., "Produce", "Dairy", "Frozen"). Leave empty for all categories.
        
        Returns:
            List of items with their details.
        """
        # Check cache first
        cache_key = f"list:{store}:{category}"
        cached = _get_cached(cache_key)
        if cached:
            return cached
        
        items = manager.get_store_items(store)
        
        if not items:
            return {"success": False, "message": f"Store '{store}' not found or has no items."}
        
        if category and category.strip():
            items = [item for item in items if item.get('category', '').lower() == category.lower()]
        
        all_categories = sorted(set(item.get('category', 'Unknown') for item in manager.get_store_items(store)))
        
        result = {
            "success": True,
            "store": store,
            "category_filter": category,
            "item_count": len(items),
            "available_categories": all_categories,
            "items": [{"name": i["name"], "category": i["category"], "price": i["price"], "id": i["id"]} for i in items[:20]]
        }
        
        # Save to cache
        _set_cache(cache_key, result)
        return result
    
    @function_tool
    def search_catalog(query: str, store: str = "") -> dict:
        """
        Search for items in the catalog by name.
        
        Args:
            query: Search term to find in item names (e.g., "milk", "chicken", "organic")
            store: Store to limit search to. Leave empty to search all stores.
        
        Returns:
            List of matching items with their details.
        """
        store_param = store if store and store.strip() else None
        results = manager.search_catalog(query, store_param)
        
        return {
            "success": True,
            "query": query,
            "store_filter": store,
            "result_count": len(results),
            "results": [{"name": r["name"], "store": r["store"], "category": r["category"], "price": r["price"], "id": r["id"]} for r in results[:15]]
        }
    
    @function_tool
    def delete_catalog_item(item_id: str, store: str) -> dict:
        """
        Delete an item from the catalog by its ID.
        
        Args:
            item_id: The unique ID of the item to delete (e.g., "tj-15", "sw-23")
            store: Store name where the item exists (e.g., "Trader Joe's")
        
        Returns:
            Result of the deletion with success status.
        """
        success, message = manager.delete_catalog_item(store, item_id)
        if success:
            _invalidate_cache(store)  # Clear cache for this store
        return {
            "success": success,
            "message": f"✅ {message}" if success else f"❌ {message}"
        }
    
    @function_tool
    def delete_item_by_name(item_name: str, store: str) -> dict:
        """
        Delete an item from the catalog by searching for its name.
        Use this when you know the item name but not the ID.
        
        Args:
            item_name: Name of the item to delete (e.g., "Organic Milk", "Dummy Test")
            store: Store name (e.g., "Trader Joe's", "Safeway")
        
        Returns:
            Result of the deletion with success status.
        """
        # Search for the item
        results = manager.search_catalog(item_name, store)
        
        if not results:
            return {
                "success": False,
                "message": f"❌ No items matching '{item_name}' found in {store} catalog"
            }
        
        if len(results) == 1:
            # Only one match - delete it
            item = results[0]
            success, message = manager.delete_catalog_item(store, item['id'])
            if success:
                _invalidate_cache(store)  # Clear cache for this store
                return {
                    "success": True,
                    "message": f"✅ Deleted '{item['name']}' (ID: {item['id']}) from {store} catalog"
                }
            return {"success": False, "message": f"❌ {message}"}
        
        # Multiple matches - ask user to be more specific
        item_list = ", ".join([f"{r['name']} (ID: {r['id']})" for r in results[:5]])
        return {
            "success": False,
            "message": f"Found {len(results)} items matching '{item_name}': {item_list}. Please be more specific or use the exact item name."
        }
    
    return [add_catalog_item, list_catalog_items, search_catalog, delete_catalog_item, delete_item_by_name]


# ============================================
# SHOPPING LIST AGENT TOOLS
# ============================================

def create_shopping_tools(manager):
    """Create tools that wrap GroceryManager shopping list methods."""
    
    @function_tool
    def add_to_shopping_list(item_id: str, quantity: int = 1) -> dict:
        """
        Add an item from the catalog to the shopping list.
        
        Args:
            item_id: The ID of the catalog item to add (e.g., "tj-1", "sw-15")
            quantity: How many to add (default: 1)
        
        Returns:
            Result with success status.
        """
        success = manager.add_to_shopping_list(item_id, quantity)
        if success:
            return {"success": True, "message": f"✅ Added {quantity}x item to shopping list"}
        return {"success": False, "message": f"❌ Item '{item_id}' not found in catalog"}
    
    @function_tool
    def remove_from_shopping_list(item_id: str) -> dict:
        """
        Remove an item from the shopping list.
        
        Args:
            item_id: The ID of the item to remove (e.g., "tj-1")
        
        Returns:
            Result with success status.
        """
        manager.remove_from_shopping_list(item_id)
        return {"success": True, "message": f"✅ Removed item from shopping list"}
    
    @function_tool
    def update_quantity(item_id: str, quantity: int) -> dict:
        """
        Update the quantity of an item in the shopping list.
        
        Args:
            item_id: The ID of the item to update
            quantity: The new quantity
        
        Returns:
            Result with success status.
        """
        success = manager.update_quantity(item_id, quantity)
        if success:
            return {"success": True, "message": f"✅ Updated quantity to {quantity}"}
        return {"success": False, "message": f"❌ Item '{item_id}' not in shopping list"}
    
    @function_tool
    def view_shopping_list(store: str = "") -> dict:
        """
        View the current shopping list, optionally filtered by store.
        
        Args:
            store: Store name to filter by (e.g., "Trader Joe's"). Leave empty to show all stores.
        
        Returns:
            Shopping list items with totals.
        """
        items = manager.get_shopping_list()
        
        if store and store.strip():
            items = [i for i in items if i.get('store') == store]
        
        total = sum(i['price'] * i['quantity'] for i in items)
        
        return {
            "success": True,
            "store_filter": store,
            "item_count": len(items),
            "total_cost": round(total, 2),
            "items": [{"name": i["name"], "quantity": i["quantity"], "price": i["price"], "store": i.get("store", "Unknown")} for i in items]
        }
    
    @function_tool
    def get_budget_status(include_details: str = "yes") -> dict:
        """
        Check the current budget status - how much spent vs budget limit.
        
        Args:
            include_details: Always pass "yes" to get full budget details.
        
        Returns:
            Budget status with total, budget, percentage, and status message.
        """
        return manager.get_budget_status()
    
    @function_tool
    def archive_shopping_list(store: str = "") -> dict:
        """
        Archive the shopping list for a store and start fresh.
        Use this after completing a shopping trip.
        
        Args:
            store: Store name to archive (e.g., "Trader Joe's"). Leave empty to archive all stores.
        
        Returns:
            Result with success status.
        """
        store_param = store if store and store.strip() else None
        success, message = manager.archive_and_restart(store_param)
        return {"success": success, "message": message}
    
    return [add_to_shopping_list, remove_from_shopping_list, update_quantity, 
            view_shopping_list, get_budget_status, archive_shopping_list]


# ============================================
# AGENT DEFINITIONS
# ============================================

def create_catalog_agent(manager, model):
    """Create the Catalog Agent with catalog management tools."""
    tools = create_catalog_tools(manager)
    
    instructions = """You are a Catalog Assistant that manages grocery store catalogs.

Your capabilities:
1. ADD items: Use add_catalog_item to add new items to a store's catalog
2. LIST items: Use list_catalog_items to show items in a store (optionally by category)
3. SEARCH items: Use search_catalog to find items by name across stores
4. DELETE items: Use delete_catalog_item to remove items (requires item ID)

Available stores: Trader Joe's, Safeway, Costco, Indian Groceries

Common categories: Produce, Dairy, Frozen, Pantry, Snacks, Bakery, Meat, Beverages, Household

Tips:
- When deleting, first search to find the item's ID
- When listing, you can filter by category
- Be helpful and confirm actions with clear messages!"""
    
    return Agent(
        name="Catalog Agent",
        instructions=instructions,
        model=model,
        tools=tools
    )


def create_shopping_agent(manager, model):
    """Create the Shopping List Agent with shopping list tools."""
    tools = create_shopping_tools(manager)
    
    instructions = """You are a Shopping List Assistant that helps manage the grocery shopping list.

Your capabilities:
1. ADD to list: Use add_to_shopping_list to add catalog items to the shopping list
2. REMOVE from list: Use remove_from_shopping_list to remove items
3. UPDATE quantity: Use update_quantity to change how many of an item
4. VIEW list: Use view_shopping_list to see current items (can filter by store)
5. CHECK budget: Use get_budget_status to see spending vs budget
6. ARCHIVE list: Use archive_shopping_list after a shopping trip

Tips:
- You need item IDs to add items - suggest searching the catalog first if needed
- Budget status shows percentage of budget used
- Archive clears the list and saves it for history

Be helpful and provide clear summaries of the shopping list!"""
    
    return Agent(
        name="Shopping List Agent",
        instructions=instructions,
        model=model,
        tools=tools
    )


def create_manager_agent(manager, model):
    """Create the Manager Agent with all tools (Groq-compatible, no handoffs)."""
    
    # Combine all tools from both specialists
    catalog_tools = create_catalog_tools(manager)
    shopping_tools = create_shopping_tools(manager)
    all_tools = catalog_tools + shopping_tools
    
    instructions = """You are a Grocery Assistant that MUST use tools to answer questions.

CRITICAL: You MUST call a tool for EVERY user request. NEVER make up answers.

STORES: Trader Joe's, Safeway, Costco, Indian Groceries

AVAILABLE TOOLS - USE THEM:
- get_shopping_list: View items on shopping list (ALWAYS call this to see the list)
- search_catalog: Find items in catalog
- add_catalog_item: Add NEW product to store catalog
- delete_item_by_name: Delete item from catalog by name
- add_item_to_list: Add item to shopping list
- get_budget_status: Check budget

RULES:
1. ALWAYS call a tool first - never guess or assume
2. To see shopping list → call get_shopping_list
3. To find items → call search_catalog
4. To delete → call delete_item_by_name
5. Report exactly what the tool returns

DO NOT make up data. DO NOT say "the list is empty" without calling get_shopping_list first."""
    
    return Agent(
        name="Grocery Assistant",
        instructions=instructions,
        model=model,
        tools=all_tools
    )


# ============================================
# MAIN SYSTEM CLASS
# ============================================

class GroceryAgentSystem:
    """
    Multi-agent grocery assistant system.
    
    Usage:
        system = GroceryAgentSystem()  # Uses default GroceryManager
        # or
        system = GroceryAgentSystem(manager)  # Uses your GroceryManager instance
        
        response = await system.run("Add organic milk to Trader Joe's catalog")
    """
    
    def __init__(self, manager=None, model=None):
        """
        Initialize the agent system.
        
        Args:
            manager: Optional GroceryManager instance. Creates one if not provided.
            model: Optional pre-configured model. Auto-detects Groq/Gemini if not provided.
        """
        # Import here to avoid circular imports
        if manager is None:
            from grocery_app import GroceryManager
            manager = GroceryManager()
        
        self.manager = manager
        
        # Setup model
        if model is None:
            self.model, self.model_name = setup_model()
        else:
            self.model = model
            self.model_name = "Custom Model"
        
        # Create agents
        self.catalog_agent = create_catalog_agent(manager, self.model)
        self.shopping_agent = create_shopping_agent(manager, self.model)
        self.manager_agent = create_manager_agent(manager, self.model)
        
        # Conversation history for context
        self.conversation_history = []  # List of {"role": "user/assistant", "content": "..."}
        self.max_history = 10  # Keep last 10 exchanges (20 messages)
        
        print(f"✅ GroceryAgentSystem initialized with {self.model_name}")
        print(f"   🤖 Grocery Assistant: {len(create_catalog_tools(manager)) + len(create_shopping_tools(manager))} tools")
    
    async def run(self, message: str) -> str:
        """
        Run a user message through the agent system with conversation history.
        
        The agent remembers previous messages for context.
        
        Args:
            message: User's natural language request
        
        Returns:
            Agent's response as a string
        """
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": message})
        
        # Build context from history (last few exchanges for context)
        context_messages = self.conversation_history[-self.max_history * 2:]
        
        # Create a context string for the agent
        if len(context_messages) > 1:
            # Include previous messages as context
            context = "Previous conversation:\n"
            for msg in context_messages[:-1]:  # All except current message
                role = "User" if msg["role"] == "user" else "Assistant"
                context += f"{role}: {msg['content']}\n"
            context += f"\nCurrent request: {message}"
            input_message = context
        else:
            input_message = message
        
        # Run the agent with context
        result = await Runner.run(self.manager_agent, input_message)
        response = result.final_output
        
        # Save assistant response to history
        self.conversation_history.append({"role": "assistant", "content": response})
        
        # Trim history if too long
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
        
        return response
    
    async def run_catalog(self, message: str) -> str:
        """Run a message directly with the Catalog Agent (skip routing)."""
        result = await Runner.run(self.catalog_agent, message)
        return result.final_output
    
    async def run_shopping(self, message: str) -> str:
        """Run a message directly with the Shopping List Agent (skip routing)."""
        result = await Runner.run(self.shopping_agent, message)
        return result.final_output
    
    def clear_history(self):
        """Clear conversation history. Use when starting a new chat session."""
        self.conversation_history = []
        return "🗑️ Conversation cleared. How can I help you?"
    
    def get_history(self):
        """Get the current conversation history for display."""
        return self.conversation_history.copy()
    
    def get_history_for_display(self):
        """Get history formatted for Gradio Chatbot (list of [user, assistant] pairs)."""
        pairs = []
        i = 0
        while i < len(self.conversation_history):
            user_msg = self.conversation_history[i]["content"] if i < len(self.conversation_history) else ""
            assistant_msg = self.conversation_history[i + 1]["content"] if i + 1 < len(self.conversation_history) else ""
            pairs.append([user_msg, assistant_msg])
            i += 2
        return pairs


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def create_system(manager=None):
    """
    Quick way to create a GroceryAgentSystem.
    
    Args:
        manager: Optional GroceryManager instance
    
    Returns:
        GroceryAgentSystem instance
    """
    return GroceryAgentSystem(manager)

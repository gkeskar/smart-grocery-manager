# Force update: Sun Jan  4 20:11:23 PST 2026
import gradio as gr
import pandas as pd
from grocery_app import GroceryManager  # pyright: ignore[reportMissingImports]
from grocery_agents import GroceryAgentSystem  # pyright: ignore[reportMissingImports]
import os
import asyncio
from dotenv import load_dotenv
import unicodedata

# Load environment variables first (searches parent directories)
load_dotenv()

# Try to import resend, but make it optional
try:
    import resend
    RESEND_AVAILABLE = True
    # Get API key from environment
    api_key = os.environ.get('RESEND_API_KEY')
    if api_key:
        resend.api_key = api_key
    else:
        RESEND_AVAILABLE = False
        print("Warning: RESEND_API_KEY not found in .env file")
except ImportError:
    RESEND_AVAILABLE = False
    print("Warning: resend package not installed. Email functionality will be disabled.")
    print("To enable email: run 'uv pip install resend' or 'pip install resend'")

# Initialize the grocery manager
grocery_manager = GroceryManager()

# Lazy-load the AI agent system (only initialize on first use)
_agent_system = None

def get_agent_system():
    """Get or create the agent system (lazy loading for faster startup)."""
    global _agent_system
    if _agent_system is None:
        try:
            _agent_system = GroceryAgentSystem(grocery_manager)
        except Exception as e:
            print(f"Warning: AI Agent system not available: {e}")
            return None
    return _agent_system

# AI Chat function
def chat_with_ai(message):
    """Send a message to the AI agent and get a response."""
    if not message or not message.strip():
        return "💡 Try asking: 'What's on my shopping list?' or 'Search for milk'"
    
    # Lazy load the agent system
    agent_system = get_agent_system()
    if agent_system is None:
        return "❌ AI Assistant is not available. Please check your API keys (GROQ_API_KEY or GOOGLE_API_KEY)."
    
    try:
        # Run the async agent in a sync context
        response = asyncio.run(agent_system.run(message))
        return response
    except Exception as e:
        return f"❌ Error: {str(e)}"

# AI Chat Tab functions (with history display)
def chat_respond(message, history):
    """Handle chat messages with history display."""
    if not message or not message.strip():
        return history, ""
    
    agent_system = get_agent_system()
    if agent_system is None:
        history = history + [[message, "❌ AI Assistant is not available. Please check your API keys."]]
        return history, ""
    
    try:
        response = asyncio.run(agent_system.run(message))
        history = history + [[message, response]]
        return history, ""
    except Exception as e:
        history = history + [[message, f"❌ Error: {str(e)}"]]
        return history, ""

def clear_chat():
    """Clear the chat history."""
    agent_system = get_agent_system()
    if agent_system:
        agent_system.clear_history()
    return [], ""

def use_suggestion(suggestion_text):
    """Fill input with suggestion text."""
    return suggestion_text

# Define functions for the Gradio interface

def normalize_text(text):
    """
    Normalize text by converting Unicode formatted characters (bold, italic, etc.) 
    to regular ASCII equivalents. This fixes sorting issues when copy-pasting from websites.
    """
    if not text:
        return text
    
    # NFD decomposes characters, then we filter out combining marks
    # NFKD also handles compatibility characters (bold, italic, etc.)
    normalized = unicodedata.normalize('NFKD', text)
    
    # Remove combining characters and keep only ASCII-compatible
    ascii_text = ''.join(c for c in normalized if not unicodedata.combining(c))
    
    return ascii_text.strip()

def get_store_items(store_name, category_filter=None):
    """Get items for a specific store with optional category filter"""
    items = grocery_manager.stores.get(store_name, [])
    if category_filter and category_filter != "All Categories":
        items = [item for item in items if item["category"] == category_filter]
    
    # Convert to DataFrame for display - include ID column
    if items:
        df = pd.DataFrame(items)
        df = df[["id", "name", "category", "price", "unit"]]
        # Sort alphabetically by name
        df = df.sort_values("name").reset_index(drop=True)
        return df
    return pd.DataFrame(columns=["id", "name", "category", "price", "unit"])

def get_categories(store_name):
    """Get unique categories for a store"""
    items = grocery_manager.stores.get(store_name, [])
    categories = set(item["category"] for item in items)
    # Always include Miscellaneous as an option
    categories.add("Miscellaneous")
    categories = sorted(list(categories))
    return ["All Categories"] + categories

def add_to_cart(item_id, quantity):
    """Add an item to the shopping list"""
    # Find the item in any store
    item = None
    for store_items in grocery_manager.stores.values():
        for store_item in store_items:
            if store_item["id"] == item_id:
                item = store_item
                break
        if item:
            break
    
    if not item:
        return "❌ Item not found"
    
    # Check if item is already in shopping list
    for list_item in grocery_manager.shopping_list:
        if list_item["id"] == item_id:
            list_item["quantity"] += quantity
            return f"✓ Updated {item['name']} quantity to {list_item['quantity']}"
    
    # Add new item to shopping list
    cart_item = item.copy()
    cart_item["quantity"] = quantity
    grocery_manager.shopping_list.append(cart_item)
    
    return f"✓ Added {quantity} {item['name']} to cart"

def remove_from_cart(item_id):
    """Remove an item from the shopping list"""
    if not item_id or item_id.strip() == "":
        return "❌ Please select an item to remove", get_shopping_list()
    
    for i, item in enumerate(grocery_manager.shopping_list):
        if item["id"] == item_id.strip():
            removed_item = grocery_manager.shopping_list.pop(i)
            return f"✅ Removed {removed_item['name']} from your list", get_shopping_list()
    
    return f"❌ Item not found in your shopping list (may have been already removed)", get_shopping_list()

def update_item_quantity(item_id, new_quantity):
    """Update the quantity of an item in the shopping list"""
    if not item_id or item_id.strip() == "":
        return "Please enter an item ID"
    
    if new_quantity < 1:
        return "Quantity must be at least 1"
    
    for item in grocery_manager.shopping_list:
        if item["id"] == item_id.strip():
            old_qty = item["quantity"]
            item["quantity"] = new_quantity
            return f"✓ Updated {item['name']} quantity from {old_qty} to {new_quantity}"
    
    return f"❌ Item '{item_id}' not found in cart"

def get_shopping_list():
    """Get the current shopping list as a DataFrame"""
    if not grocery_manager.shopping_list:
        return pd.DataFrame(columns=["name", "store", "price", "quantity", "total", "id"])
    
    # Create DataFrame with calculated total per item
    df = pd.DataFrame(grocery_manager.shopping_list)
    df["total"] = df["price"] * df["quantity"]
    df = df[["name", "store", "price", "quantity", "total", "id"]]
    # Sort alphabetically by name
    df = df.sort_values("name").reset_index(drop=True)
    return df

def get_shopping_list_by_store(store_name):
    """Get shopping list filtered by store"""
    store_items = [item for item in grocery_manager.shopping_list if item.get("store") == store_name]
    
    if not store_items:
        return pd.DataFrame(columns=["name", "price", "quantity", "total", "id"])
    
    # Create DataFrame with calculated total per item
    df = pd.DataFrame(store_items)
    # Ensure numeric columns are properly typed
    df["price"] = pd.to_numeric(df["price"], errors='coerce')
    df["quantity"] = pd.to_numeric(df["quantity"], errors='coerce')
    df["total"] = df["price"] * df["quantity"]
    
    # Sort alphabetically by name
    df = df.sort_values("name").reset_index(drop=True)
    
    # Return with all necessary columns
    return df[["name", "price", "quantity", "total", "id"]]

def get_store_total(store_name):
    """Get total cost for a specific store"""
    store_items = [item for item in grocery_manager.shopping_list if item.get("store") == store_name]
    total = sum(item["price"] * item["quantity"] for item in store_items)
    return f"${total:.2f}"

def get_budget_status():
    """Get the current budget status"""
    total = sum(item["price"] * item["quantity"] for item in grocery_manager.shopping_list)
    budget = grocery_manager.budget
    remaining = budget - total
    
    status = f"Budget: ${budget:.2f}\nSpent: ${total:.2f}\nRemaining: ${remaining:.2f}"
    
    # Budget warning
    if remaining < 0:
        warning = "❌ OVER BUDGET! Consider removing items."
    elif remaining < (budget * 0.1):
        warning = "⚠️ Approaching budget limit!"
    else:
        warning = "✅ Budget on track"
    
    return status, warning, total / budget if budget > 0 else 0

def update_budget(new_budget):
    """Update the budget amount"""
    try:
        grocery_manager.budget = float(new_budget)
        return f"Budget updated to ${new_budget}"
    except ValueError:
        return "Invalid budget value"

def clear_shopping_list():
    """Clear the entire shopping list"""
    grocery_manager.shopping_list = []
    return "Shopping list cleared", get_shopping_list()

def _format_shopping_list(store_name):
    """Format shopping list as readable markdown table"""
    store_items = [item for item in grocery_manager.shopping_list if item.get("store") == store_name]
    
    if not store_items:
        return f"*Your {store_name} shopping list is empty. Add items above to get started!*"
    
    # Create markdown table
    table = "| **Item Name** | **Price** | **Quantity** | **Total** | **Actions** |\n"
    table += "|---------------|-----------|--------------|-----------|-------------|\n"
    
    for item in store_items:
        name = item['name']
        price = f"${item['price']:.2f}"
        qty = item['quantity']
        total = f"${item['price'] * qty:.2f}"
        table += f"| **{name}** | {price} | {qty} | {total} | ✏️ 🗑️ |\n"
    
    return table

def find_item_by_name(item_name, store_name):
    """Find an item in the shopping list by name"""
    item_name_lower = item_name.lower().strip()
    for item in grocery_manager.shopping_list:
        if item.get("store") == store_name and item['name'].lower() == item_name_lower:
            return item['id']
    return None

def add_catalog_item(store_name, name, category, price, unit):
    """Add a new item to the store catalog"""
    if not name or not category or price <= 0:
        return "❌ Please fill in all fields with valid values"
    
    # Normalize text to remove Unicode formatting (bold, italic, etc.)
    name_normalized = normalize_text(name.strip())
    category_normalized = normalize_text(category.strip())
    
    # Check for duplicate item name (case-insensitive)
    store_items = grocery_manager.stores.get(store_name, [])
    name_trimmed = name_normalized.lower()
    for item in store_items:
        if item.get("name", "").lower() == name_trimmed:
            return f"❌ Item '{name_normalized}' already exists in {store_name} catalog"
    
    # Generate new ID
    prefix = store_name[:2].lower().replace(" ", "")
    max_id = 0
    for item in store_items:
        item_id = item.get("id", "")
        if item_id.startswith(prefix):
            try:
                num = int(item_id.split("-")[1])
                max_id = max(max_id, num)
            except:
                pass
    
    new_id = f"{prefix}-{max_id + 1}"
    
    new_item = {
        "id": new_id,
        "name": name_normalized,
        "category": category_normalized,
        "price": float(price),
        "unit": unit.strip(),
        "store": store_name
    }
    
    grocery_manager.stores[store_name].append(new_item)
    grocery_manager._save_catalog()  # Save to Hub
    # Check if save was successful by looking at stores count
    return f"✅ Added {name_normalized} to {store_name} catalog (ID: {new_id})"

def delete_catalog_item(store_name, item_id):
    """Delete an item from the store catalog"""
    if not item_id or item_id.strip() == "":
        return "❌ Please select an item to delete"
    
    store_items = grocery_manager.stores.get(store_name, [])
    for i, item in enumerate(store_items):
        if item["id"] == item_id.strip():
            removed_item = store_items.pop(i)
            grocery_manager._save_catalog()  # Persist to JSON file
            return f"✅ Removed '{removed_item['name']}' from {store_name} catalog (saved to file)"
    
    return f"❌ Item not found in {store_name} catalog (may have been already deleted)"

def send_shopping_list_email(store_name):
    """Send shopping list email for a specific store"""
    if not RESEND_AVAILABLE:
        return "❌ Email functionality not available. Please install resend: uv pip install resend"
    
    try:
        # Get items for this store
        store_items = [item for item in grocery_manager.shopping_list if item.get("store") == store_name]
        
        if not store_items:
            return f"❌ No items in your {store_name} list to email"
        
        # Calculate total
        total = sum(item['price'] * item['quantity'] for item in store_items)
        
        # Create HTML email content
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #00bfff; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th {{ background-color: #00bfff; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .total {{ font-size: 18px; font-weight: bold; margin-top: 20px; color: #00bfff; }}
            </style>
        </head>
        <body>
            <h1>🛒 {store_name} Shopping List</h1>
            <p>Here's your shopping list for {store_name}:</p>
            
            <table>
                <tr>
                    <th>Item</th>
                    <th>Price</th>
                    <th>Quantity</th>
                    <th>Total</th>
                </tr>
        """
        
        for item in store_items:
            item_total = item['price'] * item['quantity']
            html_body += f"""
                <tr>
                    <td>{item['name']}</td>
                    <td>${item['price']:.2f}</td>
                    <td>{item['quantity']}</td>
                    <td>${item_total:.2f}</td>
                </tr>
            """
        
        html_body += f"""
            </table>
            
            <p class="total">Total: ${total:.2f}</p>
            
            <p style="margin-top: 30px; color: #666;">
                <em>Generated by Smart Grocery Manager</em>
            </p>
        </body>
        </html>
        """
        
        # Get recipient email from settings
        recipient_email = grocery_manager.email_address
        
        if not recipient_email or recipient_email.strip() == "":
            return "❌ Please set your email address in Settings first"
        
        # Support multiple recipients (comma-separated)
        # Split by comma and clean up whitespace
        recipients = [email.strip() for email in recipient_email.split(',') if email.strip()]
        
        if not recipients:
            return "❌ Please set your email address in Settings first"
        
        # Send email using resend - supports single or multiple recipients
        response = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": recipients if len(recipients) > 1 else recipients[0],
            "subject": f"🛒 {store_name} Shopping List - ${total:.2f}",
            "html": html_body
        })
        
        if len(recipients) > 1:
            return f"✅ Email sent successfully to {len(recipients)} recipients: {', '.join(recipients)}"
        else:
            return f"✅ Email sent successfully to {recipients[0]}!"
        
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"

def build_store_tab(store_name):
    """Build a clean, simple tab for a specific store"""
    
    # Helper function to get shopping list items as dropdown choices
    def get_shopping_list_items_for_dropdown(category="All Categories"):
        """Returns list of item names for the item selector dropdown, optionally filtered by category"""
        store_items = [item for item in grocery_manager.shopping_list if item.get("store") == store_name]
        
        # Filter by category if not "All Categories"
        if category != "All Categories":
            store_items = [item for item in store_items if item.get("category") == category]
        
        if not store_items:
            return []
        
        # Sort items alphabetically by name for consistent dropdown display
        store_items_sorted = sorted(store_items, key=lambda x: x['name'].lower())
        return [f"{item['name']} (qty: {item['quantity']})" for item in store_items_sorted]
    
    # Helper function to get filtered shopping list
    def get_filtered_shopping_list(category="All Categories"):
        """Returns shopping list dataframe filtered by category (with all columns for sorting)"""
        # Get shopping list items for this store
        store_items = [item for item in grocery_manager.shopping_list if item.get("store") == store_name]
        
        if not store_items:
            return pd.DataFrame(columns=["name", "quantity", "price", "total"])
        
        # Filter by category if not "All Categories"
        if category != "All Categories":
            store_items = [item for item in store_items if item.get("category") == category]
        
        if not store_items:
            return pd.DataFrame(columns=["name", "quantity", "price", "total"])
        
        # Create DataFrame with all columns (needed for sorting)
        df = pd.DataFrame(store_items)
        df["total"] = df["price"] * df["quantity"]
        return df[["name", "quantity", "price", "total"]]
    
    # Helper function to sort shopping list
    def sort_shopping_list(df, sort_by="Name (A-Z)"):
        """Sort shopping list DataFrame and return only display columns (name, quantity)"""
        if df.empty:
            return pd.DataFrame(columns=["name", "quantity"])
        
        if sort_by == "Name (A-Z)":
            df = df.sort_values("name", ascending=True)
        elif sort_by == "Name (Z-A)":
            df = df.sort_values("name", ascending=False)
        elif sort_by == "Price (Low-High)":
            df = df.sort_values("price", ascending=True)
        elif sort_by == "Price (High-Low)":
            df = df.sort_values("price", ascending=False)
        elif sort_by == "Total (Low-High)":
            df = df.sort_values("total", ascending=True)
        elif sort_by == "Total (High-Low)":
            df = df.sort_values("total", ascending=False)
        elif sort_by == "Quantity":
            df = df.sort_values("quantity", ascending=False)
        # "Custom" = no sorting, keep original order
        
        # Return only name and quantity for cleaner mobile display
        result = df[["name", "quantity"]].reset_index(drop=True)
        
        # Add 2 empty spacer rows at the end (iOS rubber band fix)
        spacer_rows = pd.DataFrame([
            {"name": "", "quantity": ""},
            {"name": "", "quantity": ""}
        ])
        result = pd.concat([result, spacer_rows], ignore_index=True)
        
        return result
    
    # Helper function to get filtered total
    def get_filtered_total(category="All Categories"):
        """Calculate total for filtered category"""
        store_items = [item for item in grocery_manager.shopping_list if item.get("store") == store_name]
        
        # Filter by category if not "All Categories"
        if category != "All Categories":
            store_items = [item for item in store_items if item.get("category") == category]
        
        if not store_items:
            return "$0.00"
        
        total = sum(item['price'] * item['quantity'] for item in store_items)
        return f"${total:.2f}"
    
    # Helper to get item count for this store
    def get_item_count():
        """Get number of items in shopping list for this store"""
        store_items = [item for item in grocery_manager.shopping_list if item.get("store") == store_name]
        return len(store_items)
    
    # Helper to get summary text
    def get_summary_text():
        """Get summary with item count and total"""
        count = get_item_count()
        store_items = [item for item in grocery_manager.shopping_list if item.get("store") == store_name]
        total = sum(item['price'] * item['quantity'] for item in store_items)
        if count == 0:
            return "📦 No items in list"
        elif count == 1:
            return f"📦 1 item | 💰 ${total:.2f}"
        else:
            return f"📦 {count} items | 💰 ${total:.2f}"
    
    gr.Markdown(f"## 🛒 {store_name}")
    
    # Status message at TOP - always visible without scrolling
    status_message = gr.HTML(
        value="",
        visible=True
    )
    
    # ═══════════════════════════════════════════════════════════════
    # MOBILE-FRIENDLY LAYOUT: Shopping List first on mobile (column-reverse CSS)
    # ═══════════════════════════════════════════════════════════════
    
    with gr.Row():
        # LEFT COLUMN: CATALOG
        with gr.Column(scale=1):
          with gr.Accordion("📋 Catalog", open=True):
            # Search box for quick item lookup
            catalog_search = gr.Textbox(
                label="🔍 Search Catalog",
                placeholder="Type to filter (e.g., 'banana', 'dairy')",
                interactive=True
            )
            
            category_filter = gr.Radio(
                choices=get_categories(store_name),
                value="All Categories",
                label="Filter by Category",
                interactive=True
            )
            
            # Helper to get catalog items as checkbox choices
            def get_catalog_choices(category="All Categories", search_term=""):
                """Get catalog items as checkbox choices: 'Item Name - $X.XX'"""
                df = get_store_items(store_name, category)
                
                # Apply search filter
                if search_term and search_term.strip():
                    search_lower = search_term.strip().lower()
                    mask = df["name"].str.lower().str.contains(search_lower, na=False) | \
                           df["category"].str.lower().str.contains(search_lower, na=False)
                    df = df[mask]
                
                # Get set of item names already in shopping list for this store
                items_in_list = set(
                    item['name'] for item in grocery_manager.shopping_list 
                    if item.get('store') == store_name
                )
                
                # Format with 🟢 suffix if item is already in list
                choices = []
                for _, row in df.iterrows():
                    suffix = " 🟢" if row['name'] in items_in_list else ""
                    
                    if category == "All Categories":
                        choices.append(f"{row['name']} - ${row['price']:.2f} ({row['category']}){suffix}")
                    else:
                        choices.append(f"{row['name']} - ${row['price']:.2f}{suffix}")
                
                return sorted(choices)
            
            # Catalog as checkboxes (mobile-friendly!)
            catalog_checkboxes = gr.CheckboxGroup(
                choices=get_catalog_choices(),
                value=[],
                label="📦 Catalog Items (tap to select, then Add to List)",
                interactive=True
            )
            
            # Selected items display
            selected_catalog_items_display = gr.Textbox(
                label="✓ Selected",
                value="No items selected",
                interactive=False
            )
            
            with gr.Row(elem_classes="compact-button-row"):
                clear_selections_btn = gr.Button("✗ Clear", variant="secondary", size="sm", scale=1, min_width=0)
                # ADD TO LIST BUTTON - Right next to catalog for easy mobile access
                add_to_list_btn = gr.Button("➕ Add", variant="primary", size="lg", scale=2, min_width=0)
                # DELETE FROM CATALOG - supports multiple selections
                delete_from_catalog_btn = gr.Button("🗑️ Del", variant="stop", size="sm", scale=1, min_width=0)
        
        # RIGHT COLUMN: SHOPPING LIST
        with gr.Column(scale=1):
          with gr.Accordion("🛒 Shopping List", open=True):
            
            # Summary bar showing item count and total - styled Textbox updates more reliably than Markdown
            summary_display = gr.Textbox(
                value=get_summary_text(),
                label="",
                interactive=False,
                show_label=False
            )
            
            # Category filter (collapsed by default)
            with gr.Accordion("🏷️ Filter by Category", open=False):
                shopping_list_category_filter = gr.Radio(
                    choices=get_categories(store_name),
                    value="All Categories",
                    label="",
                    interactive=True
                )
            
            # Helper to get shopping list as checkbox choices
            def get_shopping_list_choices(category="All Categories", sort_by="Name (A-Z)"):
                """Get shopping list items as checkbox choices: 'Item Name (qty: X)'"""
                store_items = [item for item in grocery_manager.shopping_list if item.get("store") == store_name]
                
                if category != "All Categories":
                    store_items = [item for item in store_items if item.get("category") == category]
                
                # Sort items
                if sort_by == "Name (A-Z)":
                    store_items = sorted(store_items, key=lambda x: x["name"].lower())
                elif sort_by == "Name (Z-A)":
                    store_items = sorted(store_items, key=lambda x: x["name"].lower(), reverse=True)
                elif sort_by == "Quantity":
                    store_items = sorted(store_items, key=lambda x: x["quantity"], reverse=True)
                
                # Format as "Item Name (qty: X) - $Y.YY"
                choices = []
                for item in store_items:
                    qty = item['quantity']
                    price = item.get('price', 0)
                    total = qty * price
                    choices.append(f"{item['name']} (qty: {qty}) - ${total:.2f}")
                return choices
            
            # Action buttons at TOP for easy access
            with gr.Row(elem_classes="compact-button-row"):
                refresh_list_btn = gr.Button("🔄", variant="secondary", scale=1, min_width=0)
                decrease_qty_btn = gr.Button("➖", variant="secondary", scale=1, min_width=0)
                increase_qty_btn = gr.Button("➕", variant="secondary", scale=1, min_width=0)
                remove_from_list_btn = gr.Button("🗑️", variant="stop", scale=1, min_width=0)
            
            # Empty state message (shown when list is empty)
            def is_list_empty():
                store_items = [item for item in grocery_manager.shopping_list if item.get("store") == store_name]
                return len(store_items) == 0
            
            empty_list_message = gr.HTML(
                value="""
                <div style="text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); border-radius: 12px; margin: 10px 0;">
                    <div style="font-size: 48px; margin-bottom: 16px;">🛒</div>
                    <div style="font-size: 18px; font-weight: 600; color: #333; margin-bottom: 8px;">Your list is empty!</div>
                    <div style="font-size: 14px; color: #666;">Add items from the catalog above</div>
                </div>
                """,
                visible=is_list_empty()
            )
            
            # Shopping list as checkboxes (mobile-friendly!)
            shopping_list_checkboxes = gr.CheckboxGroup(
                choices=get_shopping_list_choices(),
                value=[],
                label="📋 Tap item, then use buttons above",
                interactive=True,
                visible=not is_list_empty()
            )
            
            list_total = gr.Textbox(
                label=f"💰 Total",
                value=get_filtered_total("All Categories"),
                interactive=False
            )
            
            # Hidden: keep for compatibility with existing handlers
            update_quantity_input = gr.Number(value=1, visible=False)
            update_quantity_btn = gr.Button("Update", visible=False)
            
            with gr.Row(elem_classes="compact-button-row"):
                email_button = gr.Button("📧 Email", variant="primary", scale=1, min_width=0)
                archive_list_btn = gr.Button("📦 Archive", variant="secondary", scale=1, min_width=0)
    
    # ═══════════════════════════════════════════════════════════════
    # CATALOG MANAGEMENT - In collapsible accordions (rarely used)
    # ═══════════════════════════════════════════════════════════════
    
    # Hidden field for edit item ID (must be outside accordion for event handlers)
    selected_edit_item_id = gr.Textbox(visible=False, value="")
    
    with gr.Accordion("➕ Add New Item to Catalog", open=False):
        with gr.Row():
            new_item_name = gr.Textbox(label="Name", placeholder="New item name", scale=2)
            new_item_price = gr.Number(label="Price", value=0, minimum=0, step=0.01, scale=1)
        new_item_category = gr.Radio(
            choices=[cat for cat in get_categories(store_name) if cat != "All Categories"],
            label="Category (tap to select)",
            value=None,
            interactive=True
        )
        add_catalog_btn = gr.Button("➕ Add to Catalog", variant="primary")
    
    with gr.Accordion("✏️ Edit Catalog Item", open=False):
        gr.Markdown("*Select an item from the catalog above to edit its details*")
        with gr.Row():
            edit_item_name = gr.Textbox(label="Name", placeholder="Select item first", scale=2)
            edit_item_price = gr.Number(label="Price", value=0, minimum=0, step=0.01, scale=1)
        edit_item_category = gr.Radio(
            choices=[cat for cat in get_categories(store_name) if cat != "All Categories"],
            label="Category (tap to select)",
            value=None,
            interactive=True
        )
        with gr.Row():
            update_catalog_btn = gr.Button("💾 Save Changes", variant="primary", scale=1)
            delete_catalog_btn = gr.Button("🗑️ Delete Item", variant="stop", scale=1)
    
    # Status messages are now at the top of the tab (moved above)
    
    # ═══════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════
    
    # Helper to format status messages as prominent HTML
    def format_status(msg):
        """Format status message as HTML with appropriate styling"""
        if not msg:
            return ""
        
        # Determine color based on message type
        if msg.startswith("✅") or msg.startswith("🗑️") or "Restored" in msg or "Archived" in msg:
            bg_color = "#d4edda"
            border_color = "#28a745"
            text_color = "#155724"
        elif msg.startswith("❌"):
            bg_color = "#f8d7da"
            border_color = "#dc3545"
            text_color = "#721c24"
        elif msg.startswith("⚠️"):
            bg_color = "#fff3cd"
            border_color = "#ffc107"
            text_color = "#856404"
        else:
            bg_color = "#d1ecf1"
            border_color = "#17a2b8"
            text_color = "#0c5460"
        
        return f'''
        <div style="padding: 12px 16px; margin: 8px 0; border-radius: 8px; 
                    background-color: {bg_color}; border-left: 4px solid {border_color};
                    color: {text_color}; font-weight: 500;">
            {msg}
        </div>
        '''
    
    # Helper function for checkmark column (deprecated - using CheckboxGroups now)
    def add_checkmark_column(df, selected_ids):
        """Add a checkmark column to show selected items - checkbox style"""
        if df.empty:
            return df
        
        # Get item IDs for the dataframe
        all_items = grocery_manager.stores.get(store_name, [])
        
        # Create checkmark column with checkbox symbols
        checkmarks = []
        for idx, row in df.iterrows():
            item_name = row["name"]
            # Find the item ID
            item_id = None
            for item in all_items:
                if item["name"] == item_name:
                    item_id = item["id"]
                    break
            
            # Show checkbox state: ☑ for selected, ☐ for unselected
            if item_id and item_id in (selected_ids or []):
                checkmarks.append("☑")  # Checked box
            else:
                checkmarks.append("☐")  # Empty box
        
        # Insert checkmark column at the front
        result_df = df.copy()
        result_df.insert(0, "Add", checkmarks)
        return result_df
    
    # Filter catalog by category
    def filter_catalog(cat, search_term):
        """Filter catalog by category AND search term - returns checkbox choices"""
        choices = get_catalog_choices(cat, search_term)
        return gr.CheckboxGroup(choices=choices, value=[])
    
    # Category filter triggers catalog refresh
    category_filter.change(
        fn=filter_catalog,
        inputs=[category_filter, catalog_search],
        outputs=catalog_checkboxes
    )
    
    # Search box triggers catalog refresh
    catalog_search.change(
        fn=filter_catalog,
        inputs=[category_filter, catalog_search],
        outputs=catalog_checkboxes
    )
    
    # Filter shopping list by category
    def filter_shopping_list(category):
        """Filter shopping list - returns checkbox choices (sorted by name)"""
        choices = get_shopping_list_choices(category, "Name (A-Z)")
        filtered_total = get_filtered_total(category)
        is_empty = len(choices) == 0
        return gr.HTML(visible=is_empty), gr.CheckboxGroup(choices=choices, value=[], visible=not is_empty), filtered_total
    
    # Category filter triggers refresh
    shopping_list_category_filter.change(
        fn=filter_shopping_list,
        inputs=[shopping_list_category_filter],
        outputs=[empty_list_message, shopping_list_checkboxes, list_total]
    )
    
    # Update display when catalog checkboxes change
    def on_catalog_selection_change(selected_items):
        """Update the selected items display when checkboxes change"""
        if not selected_items or len(selected_items) == 0:
            return "No items selected", "", "", 0.0, None
        
        # Display count
        if len(selected_items) == 1:
            display_text = f"✓ {selected_items[0].split(' - ')[0]}"
        else:
            display_text = f"✓ {len(selected_items)} items selected"
        
        # Populate edit fields with the last selected item (for editing)
        last_item = selected_items[-1]
        item_name = last_item.split(" - $")[0].strip()
        
        # Find the item in catalog
        for item in grocery_manager.stores.get(store_name, []):
            if item["name"] == item_name:
                return display_text, item["id"], item["name"], item["price"], item["category"]
        
        return display_text, "", "", 0.0, None
    
    catalog_checkboxes.change(
        fn=on_catalog_selection_change,
        inputs=[catalog_checkboxes],
        outputs=[selected_catalog_items_display, selected_edit_item_id, edit_item_name, edit_item_price, edit_item_category]
    )
    
    # Add to List button - adds all selected items (quantity 1 each)
    def add_to_list_handler(selected_catalog_items, current_filter, list_category_filter):
        """Add selected catalog items to shopping list"""
        if not selected_catalog_items or len(selected_catalog_items) == 0:
            catalog_choices = get_catalog_choices(current_filter, "")
            shopping_choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
            return "❌ Please select items from the catalog first", gr.CheckboxGroup(choices=catalog_choices, value=[]), gr.CheckboxGroup(choices=shopping_choices, value=[]), get_filtered_total(list_category_filter), "No items selected", get_summary_text()
        
        # Add all selected items
        added_items = []
        for selected in selected_catalog_items:
            # Extract item name from "Item Name - $X.XX (category)" or "Item Name - $X.XX"
            item_name = selected.split(" - $")[0].strip()
            
            # Find item ID by name
            for item in grocery_manager.stores.get(store_name, []):
                if item["name"] == item_name:
                    msg = add_to_cart(item["id"], 1)
                    if "Added" in msg or "Updated" in msg:
                        added_items.append(item_name)
                    break
        
        # Create success message
        if len(added_items) == 1:
            success_msg = f"✅ Added {added_items[0]} to list"
        elif len(added_items) > 1:
            success_msg = f"✅ Added {len(added_items)} items to list"
        else:
            success_msg = "❌ Could not add items"
        
        # Get updated checkbox choices
        catalog_choices = get_catalog_choices(current_filter, "")
        shopping_choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
        filtered_total = get_filtered_total(list_category_filter)
        
        # Clear catalog selections, update shopping list
        is_empty = len(shopping_choices) == 0
        return (
            format_status(success_msg), 
            gr.CheckboxGroup(choices=catalog_choices, value=[]), 
            gr.HTML(visible=is_empty),  # Empty message
            gr.CheckboxGroup(choices=shopping_choices, value=[], visible=not is_empty), 
            filtered_total, 
            "No items selected", 
            get_summary_text()
        )
    
    add_to_list_btn.click(
        fn=add_to_list_handler,
        inputs=[catalog_checkboxes, category_filter, shopping_list_category_filter],
        outputs=[status_message, catalog_checkboxes, empty_list_message, shopping_list_checkboxes, list_total, selected_catalog_items_display, summary_display]
    )
    
    # Remove from List button - now handles multi-select
    def remove_from_list_handler(selected_items, list_category_filter):
        """Remove selected items from shopping list"""
        try:
            # Check if any items are selected
            if not selected_items or len(selected_items) == 0:
                choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
                is_empty = len(choices) == 0
                return format_status("❌ Please select items to delete"), gr.HTML(visible=is_empty), gr.CheckboxGroup(choices=choices, value=[], visible=not is_empty), get_filtered_total(list_category_filter), get_summary_text()
            
            # Remove all selected items
            removed_names = []
            for selected in selected_items:
                try:
                    # Extract item name from "Item Name (qty: X) - $Y.YY"
                    item_name = selected.split(" (qty:")[0].strip()
                    
                    # Find item ID by name
                    for item in list(grocery_manager.shopping_list):  # Copy list to avoid modification during iteration
                        if item.get("store") == store_name and item["name"] == item_name:
                            remove_from_cart(item["id"])
                            removed_names.append(item_name)
                            break
                except Exception as e:
                    print(f"⚠️ Error removing item '{selected}': {e}")
                    continue
            
            # Get updated checkbox choices
            choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
            filtered_total = get_filtered_total(list_category_filter)
            is_empty = len(choices) == 0
            
            if len(removed_names) == 0:
                msg = "⚠️ No items were removed (may have been already deleted)"
            elif len(removed_names) == 1:
                msg = f"🗑️ Removed {removed_names[0]}"
            else:
                msg = f"🗑️ Removed {len(removed_names)} items"
            
            return format_status(msg), gr.HTML(visible=is_empty), gr.CheckboxGroup(choices=choices, value=[], visible=not is_empty), filtered_total, get_summary_text()
        except Exception as e:
            print(f"❌ Error in remove_from_list_handler: {e}")
            # Return safe defaults
            choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
            is_empty = len(choices) == 0
            return format_status(f"❌ Error: {str(e)}"), gr.HTML(visible=is_empty), gr.CheckboxGroup(choices=choices, value=[], visible=not is_empty), get_filtered_total(list_category_filter), get_summary_text()
    
    remove_from_list_btn.click(
        fn=remove_from_list_handler,
        inputs=[shopping_list_checkboxes, shopping_list_category_filter],
        outputs=[status_message, empty_list_message, shopping_list_checkboxes, list_total, summary_display]
    )
    
    # Hidden update quantity handler (legacy, button is hidden)
    
    # ═══════════════════════════════════════════════════════════════
    # QUICK +/- QUANTITY BUTTONS (works with checkbox selection)
    # ═══════════════════════════════════════════════════════════════
    
    def increase_quantity(selected_items, list_category_filter):
        """Increment quantity by 1 for first selected item"""
        if not selected_items or len(selected_items) == 0:
            choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
            return "❌ Select an item first", gr.CheckboxGroup(choices=choices, value=[]), get_filtered_total(list_category_filter), get_summary_text()
        
        # Use first selected item
        selected = selected_items[0]
        item_name = selected.split(" (qty:")[0].strip()
        
        # Find item and get current quantity
        item_id = None
        current_qty = 0
        for item in grocery_manager.shopping_list:
            if item.get("store") == store_name and item["name"] == item_name:
                item_id = item["id"]
                current_qty = item["quantity"]
                break
        
        if not item_id:
            choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
            return "❌ Item not found", gr.CheckboxGroup(choices=choices, value=[]), get_filtered_total(list_category_filter), get_summary_text()
        
        # Increment quantity
        new_qty = current_qty + 1
        update_item_quantity(item_id, new_qty)
        
        # Refresh checkbox choices with updated quantities
        choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
        filtered_total = get_filtered_total(list_category_filter)
        
        # Find the matching choice to keep item selected (includes price now)
        new_selected = []
        for choice in choices:
            if choice.startswith(f"{item_name} (qty: {new_qty})"):
                new_selected = [choice]
                break
        
        return f"✅ {item_name}: {current_qty} → {new_qty}", gr.CheckboxGroup(choices=choices, value=new_selected), filtered_total, get_summary_text()
    
    def decrease_quantity(selected_items, list_category_filter):
        """Decrement quantity by 1 (minimum 1) for first selected item"""
        if not selected_items or len(selected_items) == 0:
            choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
            return "❌ Select an item first", gr.CheckboxGroup(choices=choices, value=[]), get_filtered_total(list_category_filter), get_summary_text()
        
        # Use first selected item
        selected = selected_items[0]
        item_name = selected.split(" (qty:")[0].strip()
        
        # Find item and get current quantity
        item_id = None
        current_qty = 0
        for item in grocery_manager.shopping_list:
            if item.get("store") == store_name and item["name"] == item_name:
                item_id = item["id"]
                current_qty = item["quantity"]
                break
        
        if not item_id:
            choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
            return "❌ Item not found", gr.CheckboxGroup(choices=choices, value=[]), get_filtered_total(list_category_filter), get_summary_text()
        
        # Decrement quantity (minimum 1)
        if current_qty <= 1:
            choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
            return f"⚠️ {item_name} already at minimum (1)", gr.CheckboxGroup(choices=choices, value=selected_items), get_filtered_total(list_category_filter), get_summary_text()
        
        new_qty = current_qty - 1
        update_item_quantity(item_id, new_qty)
        
        # Refresh checkbox choices with updated quantities
        choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
        filtered_total = get_filtered_total(list_category_filter)
        
        # Find the matching choice to keep item selected (includes price now)
        new_selected = []
        for choice in choices:
            if choice.startswith(f"{item_name} (qty: {new_qty})"):
                new_selected = [choice]
                break
        
        return f"✅ {item_name}: {current_qty} → {new_qty}", gr.CheckboxGroup(choices=choices, value=new_selected), filtered_total, get_summary_text()
    
    increase_qty_btn.click(
        fn=increase_quantity,
        inputs=[shopping_list_checkboxes, shopping_list_category_filter],
        outputs=[status_message, shopping_list_checkboxes, list_total, summary_display]
    )
    
    decrease_qty_btn.click(
        fn=decrease_quantity,
        inputs=[shopping_list_checkboxes, shopping_list_category_filter],
        outputs=[status_message, shopping_list_checkboxes, list_total, summary_display]
    )
    
    # Refresh shopping list (useful after restoring from archive)
    def refresh_shopping_list(list_category_filter):
        """Refresh the shopping list display"""
        choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
        filtered_total = get_filtered_total(list_category_filter)
        is_empty = len(choices) == 0
        return (
            gr.HTML(visible=is_empty),  # Show empty message when empty
            gr.CheckboxGroup(choices=choices, value=[], visible=not is_empty),  # Hide checkboxes when empty
            filtered_total, 
            get_summary_text()
        )
    
    refresh_list_btn.click(
        fn=refresh_shopping_list,
        inputs=[shopping_list_category_filter],
        outputs=[empty_list_message, shopping_list_checkboxes, list_total, summary_display]
    )
    
    # Email list
    def email_and_format():
        result = send_shopping_list_email(store_name)
        return format_status(result)
    
    email_button.click(
        fn=email_and_format,
        inputs=[],
        outputs=[status_message]
    )
    
    # Archive and start new list (per-store)
    def archive_and_refresh(list_category_filter):
        """Archive this store's list and refresh shopping list display"""
        success, msg = grocery_manager.archive_and_restart(store_name)  # Pass store name
        # Refresh shopping list (now empty for this store)
        choices = get_shopping_list_choices(list_category_filter, "Name (A-Z)")
        filtered_total = get_filtered_total(list_category_filter)
        is_empty = len(choices) == 0
        return (
            format_status(msg),  # Prominent styled status at top
            gr.HTML(visible=is_empty),  # Show empty message
            gr.CheckboxGroup(choices=choices, value=[], visible=not is_empty),  # Hide checkboxes when empty
            filtered_total, 
            get_summary_text()
        )
    
    archive_list_btn.click(
        fn=archive_and_refresh,
        inputs=[shopping_list_category_filter],
        outputs=[status_message, empty_list_message, shopping_list_checkboxes, list_total, summary_display]
    )
    
    # Add new item to catalog
    def add_new_catalog_item(name, category, price, current_filter):
        success, message, item = grocery_manager.add_catalog_item(store_name, name, category, price, "each")
        msg = f"✅ {message}" if success else f"❌ {message}"
        # Refresh catalog checkboxes
        choices = get_catalog_choices(current_filter, "")
        return msg, gr.CheckboxGroup(choices=choices, value=[]), "", 0, None
    
    add_catalog_btn.click(
        fn=add_new_catalog_item,
        inputs=[new_item_name, new_item_category, new_item_price, category_filter],
        outputs=[status_message, catalog_checkboxes, new_item_name, new_item_price, new_item_category]
    )
    
    # Update existing catalog item
    def update_catalog_item_handler(item_id, name, price, category, current_filter):
        if not item_id or item_id.strip() == "":
            choices = get_catalog_choices(current_filter, "")
            return "❌ Please select an item from the catalog first to update", gr.CheckboxGroup(choices=choices, value=[]), "", "", 0, None
        
        if not name or not category or price <= 0:
            choices = get_catalog_choices(current_filter, "")
            return "❌ Please fill in all fields with valid values", gr.CheckboxGroup(choices=choices, value=[]), item_id, name, price, category
        
        # Normalize text to remove Unicode formatting (bold, italic, etc.)
        name_normalized = normalize_text(name.strip())
        category_normalized = normalize_text(category.strip())
        
        # Update the item (keep existing unit)
        success = grocery_manager.update_catalog_item(
            item_id=item_id,
            name=name_normalized,
            category=category_normalized,
            price=float(price)
        )
        
        if success:
            # Refresh catalog checkboxes
            choices = get_catalog_choices(current_filter, "")
            
            # Clear edit fields after successful update
            return f"✅ Updated '{name_normalized}' successfully", gr.CheckboxGroup(choices=choices, value=[]), "", "", 0, None
        else:
            choices = get_catalog_choices(current_filter, "")
            return f"❌ Item not found", gr.CheckboxGroup(choices=choices, value=[]), item_id, name, price, category
    
    update_catalog_btn.click(
        fn=update_catalog_item_handler,
        inputs=[selected_edit_item_id, edit_item_name, edit_item_price, edit_item_category, category_filter],
        outputs=[status_message, catalog_checkboxes, selected_edit_item_id, edit_item_name, edit_item_price, edit_item_category]
    )
    
    # Delete selected items from catalog
    def delete_selected_catalog_items(selected_items, current_filter):
        """Delete selected items from catalog (using checkbox selections)"""
        if not selected_items or len(selected_items) == 0:
            choices = get_catalog_choices(current_filter, "")
            return "❌ Please select items to delete first", gr.CheckboxGroup(choices=choices, value=[]), "No items selected"
        
        # Delete all selected items
        deleted_items = []
        store_items = grocery_manager.stores.get(store_name, [])
        
        for selected in selected_items:
            # Extract item name from "Item Name - $X.XX (category)"
            item_name = selected.split(" - $")[0].strip()
            
            # Find and remove item
            for i, item in enumerate(store_items):
                if item["name"] == item_name:
                    deleted_items.append(item["name"])
                    store_items.pop(i)
                    break
        
        # Save once after all deletions
        if deleted_items:
            grocery_manager._save_catalog()
        
        # Create success message
        if len(deleted_items) == 1:
            msg = f"✅ Removed '{deleted_items[0]}' from catalog"
        else:
            msg = f"✅ Removed {len(deleted_items)} items from catalog"
        
        # Refresh catalog checkboxes
        choices = get_catalog_choices(current_filter, "")
        
        return msg, gr.CheckboxGroup(choices=choices, value=[]), "No items selected"
    
    delete_catalog_btn.click(
        fn=delete_selected_catalog_items,
        inputs=[catalog_checkboxes, category_filter],
        outputs=[status_message, catalog_checkboxes, selected_catalog_items_display]
    )
    
    # Also connect the new delete button in the catalog section (same handler)
    delete_from_catalog_btn.click(
        fn=delete_selected_catalog_items,
        inputs=[catalog_checkboxes, category_filter],
        outputs=[status_message, catalog_checkboxes, selected_catalog_items_display]
    )
    
    # Clear all selections button
    def clear_all_selections(current_filter):
        choices = get_catalog_choices(current_filter, "")
        return gr.CheckboxGroup(choices=choices, value=[]), "No items selected", "✓ Cleared all selections"
    
    clear_selections_btn.click(
        fn=clear_all_selections,
        inputs=[category_filter],
        outputs=[catalog_checkboxes, selected_catalog_items_display, status_message]
    )
    
    # Initialize catalog table on page load
    # Catalog table is now initialized with data on creation (see above)

# Mobile-friendly CSS
MOBILE_CSS = """
/* Hide footer */
footer {
    display: none !important;
}

/* ═══════════════════════════════════════════════════════════════
   CHECKBOX ITEMS - Bottom Dividers Style
   ═══════════════════════════════════════════════════════════════ */

/* Style each checkbox item with bottom divider */
.checkbox-group label,
.gradio-checkbox-group label,
[data-testid="checkbox-group"] label {
    display: block !important;
    width: 100% !important;
    box-sizing: border-box !important;
    padding: 14px 16px !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: background-color 0.15s ease !important;
    border-bottom: 1px solid #e0e0e0 !important;
    background-color: #ffffff !important;
}

/* Ensure the checkbox group container is full width */
.checkbox-group > div,
.gradio-checkbox-group > div,
[data-testid="checkbox-group"] > div {
    width: 100% !important;
}

/* Make sure span inside label is also full width */
.checkbox-group label span,
.gradio-checkbox-group label span,
[data-testid="checkbox-group"] label span {
    display: inline !important;
}

/* Remove border from last item */
.checkbox-group label:last-child,
.gradio-checkbox-group label:last-child,
[data-testid="checkbox-group"] label:last-child {
    border-bottom: none !important;
}

/* Hover effect */
.checkbox-group label:hover,
.gradio-checkbox-group label:hover,
[data-testid="checkbox-group"] label:hover {
    background-color: #f5f5f5 !important;
}

/* Selected/checked state */
.checkbox-group label:has(input:checked),
.gradio-checkbox-group label:has(input:checked),
[data-testid="checkbox-group"] label:has(input:checked) {
    background-color: #e3f2fd !important;
    color: #1a1a1a !important;
}

/* Ensure text inside selected items is visible */
.checkbox-group label:has(input:checked) span,
.gradio-checkbox-group label:has(input:checked) span,
[data-testid="checkbox-group"] label:has(input:checked) span {
    color: #1a1a1a !important;
}

/* Make checkbox larger and easier to tap */
.checkbox-group input[type="checkbox"],
.gradio-checkbox-group input[type="checkbox"],
[data-testid="checkbox-group"] input[type="checkbox"] {
    width: 20px !important;
    height: 20px !important;
    margin-right: 12px !important;
}

/* Container styling */
.checkbox-group,
.gradio-checkbox-group,
[data-testid="checkbox-group"] {
    max-height: 50vh !important;
    overflow-y: auto !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 8px !important;
    -webkit-overflow-scrolling: touch;
}

/* ═══════════════════════════════════════════════════════════════
   DARK MODE SUPPORT - Follows system preference
   ═══════════════════════════════════════════════════════════════ */

/* Dark mode colors */
@media (prefers-color-scheme: dark) {
    .gradio-container {
        --background-fill-primary: #1a1a2e !important;
        --background-fill-secondary: #16213e !important;
        --border-color-primary: #0f3460 !important;
        --color-accent: #e94560 !important;
    }
    
    /* Dark table styling */
    .dataframe-container table {
        background-color: #16213e !important;
        color: #eee !important;
    }
    
    .dataframe-container table th {
        background-color: #0f3460 !important;
        color: #fff !important;
    }
    
    .dataframe-container table tr:nth-child(even) {
        background-color: #1a1a2e !important;
    }
    
    .dataframe-container table tr:hover {
        background-color: #0f3460 !important;
    }
    
    /* Dark mode text */
    .prose, .markdown-text, p, span, label {
        color: #eee !important;
    }
    
    /* Dark mode inputs */
    input, textarea, select {
        background-color: #16213e !important;
        color: #eee !important;
        border-color: #0f3460 !important;
    }
    
    /* Dark mode buttons */
    button.secondary {
        background-color: #0f3460 !important;
        color: #eee !important;
    }
    
    /* Accordion headers */
    .accordion > button {
        background-color: #1a1a2e !important;
        color: #eee !important;
    }
    
    /* Dark mode checkbox dividers */
    .checkbox-group label,
    .gradio-checkbox-group label,
    [data-testid="checkbox-group"] label {
        background-color: #1a1a2e !important;
        border-bottom-color: #0f3460 !important;
        color: #eee !important;
    }
    
    .checkbox-group label:hover,
    .gradio-checkbox-group label:hover,
    [data-testid="checkbox-group"] label:hover {
        background-color: #16213e !important;
    }
    
    .checkbox-group label:has(input:checked),
    .gradio-checkbox-group label:has(input:checked),
    [data-testid="checkbox-group"] label:has(input:checked) {
        background-color: #0f3460 !important;
        color: #ffffff !important;
    }
    
    .checkbox-group label:has(input:checked) span,
    .gradio-checkbox-group label:has(input:checked) span,
    [data-testid="checkbox-group"] label:has(input:checked) span {
        color: #ffffff !important;
    }
    
    /* Dark mode container border */
    .checkbox-group,
    .gradio-checkbox-group,
    [data-testid="checkbox-group"] {
        border-color: #0f3460 !important;
    }
}

/* ═══════════════════════════════════════════════════════════════
   iOS SCROLL FIX - Prevent rubber band bounce hiding last item
   ═══════════════════════════════════════════════════════════════ */

/* Desktop table scrolling */
.dataframe-container, .gradio-dataframe {
    overflow: auto !important;
    max-height: 400px !important;
}

.dataframe-container table {
    min-width: 200px;
}

/* MOBILE iOS SCROLL FIX */
@media (max-width: 768px) {
    /* Fixed height container - prevents iOS bounce issues */
    .dataframe-container, .gradio-dataframe {
        max-height: 300px !important;
        height: 300px !important;
        overflow-y: scroll !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        overscroll-behavior: contain !important;
        overscroll-behavior-y: contain !important;
        padding-bottom: 60px !important;
    }
    
    /* Fixed table layout for consistent column widths */
    .dataframe-container table {
        width: 100% !important;
        table-layout: fixed !important;
        margin-bottom: 80px !important;
    }
    
    /* Fixed column widths - Name column wider, Qty narrow */
    .dataframe-container table th:first-child,
    .dataframe-container table td:first-child {
        width: 75% !important;
        max-width: 200px !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }
    
    .dataframe-container table th:last-child,
    .dataframe-container table td:last-child {
        width: 25% !important;
        text-align: center !important;
    }
    
    /* Compact mobile table styling */
    .dataframe-container table td,
    .dataframe-container table th {
        font-size: 14px !important;
        padding: 10px 8px !important;
    }
    
    /* Extra padding on last row */
    .dataframe-container table tr:last-child td {
        padding-bottom: 30px !important;
    }
    
    /* Scroll buffer at end of table */
    .dataframe-container table tbody::after {
        content: "";
        display: table-row;
        height: 80px;
    }
}

/* Gradio wrapper spacing */
.table-wrap {
    margin-bottom: 16px !important;
}

/* Simple table hover styling (no tap-to-select on shopping list) */
table tbody tr:hover {
    background-color: #f5f5f5 !important;
}

/* Mobile responsive layout */
@media (max-width: 768px) {
    /* Stack columns vertically - BUT NOT button rows */
    /* Use column-reverse so Shopping List appears FIRST on mobile */
    .row:not(.compact-button-row) {
        flex-direction: column-reverse !important;
    }
    
    /* Touch targets for regular buttons */
    button {
        min-height: 40px !important;
        font-size: 14px !important;
        padding: 6px 10px !important;
    }
    
    /* Prevent zoom on input focus (iOS) */
    input, select, textarea {
        font-size: 16px !important;
    }
    
    /* Better radio button spacing for touch */
    .radio-group label, .gr-radio label {
        padding: 12px 16px !important;
        min-height: 44px;
        display: flex;
        align-items: center;
    }
    
    /* Wrap radio options */
    .gr-radio-row {
        flex-wrap: wrap !important;
    }
    
    /* Make tables more readable */
    .dataframe-container table {
        font-size: 14px !important;
    }
    
    /* Compact button row - FORCE horizontal layout on mobile */
    .compact-button-row {
        display: flex !important;
        flex-direction: row !important;
        gap: 4px !important;
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        padding: 2px 0 !important;
        justify-content: stretch !important;
        width: 100% !important;
        margin: 0 !important;
    }

    .compact-button-row > div,
    .compact-button-row > .column {
        flex: 1 1 0 !important;
        max-width: none !important;
        min-width: 0 !important;
        padding: 0 !important;
        width: auto !important;
    }

    .compact-button-row button {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        width: 100% !important;
        padding: 6px 2px !important;
        font-size: 14px !important;
        min-height: 36px !important;
        height: 36px !important;
    }

    /* Full width columns on mobile */
    .column {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    /* Reduce padding on mobile */
    .gradio-container {
        padding: 8px !important;
    }
    
    /* Better spacing for markdown headers */
    h2, h3 {
        margin-top: 16px !important;
        margin-bottom: 8px !important;
    }
}

/* Make number inputs more touch-friendly */
input[type="number"] {
    min-height: 44px;
    font-size: 16px !important;
}

/* Radio button improvements */
.gr-radio {
    gap: 8px;
}

/* Store filter radio - horizontal layout that wraps on mobile */
.store-filter-radio {
    margin-bottom: 12px;
}

.store-filter-radio > div {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
}

.store-filter-radio label {
    flex: 0 0 auto !important;
    padding: 8px 16px !important;
    border: 1px solid #ddd !important;
    border-radius: 20px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    min-width: fit-content !important;
    text-align: center !important;
    background: #f8f9fa !important;
    font-size: 14px !important;
}

.store-filter-radio label:hover {
    background: #e9ecef !important;
    border-color: #adb5bd !important;
}

.store-filter-radio input:checked + span,
.store-filter-radio label.selected,
.store-filter-radio label:has(input:checked) {
    background: #4CAF50 !important;
    color: white !important;
    border-color: #4CAF50 !important;
}

@media (max-width: 768px) {
    .store-filter-radio label {
        flex: 1 1 calc(50% - 8px) !important;
        min-width: calc(50% - 8px) !important;
        padding: 10px 8px !important;
        font-size: 13px !important;
    }
}
"""

# Create the Gradio interface
with gr.Blocks(title="Smart Grocery Manager", css=MOBILE_CSS, theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🛒 Smart Grocery Manager")
    
    # AI Quick Chat Bar
    with gr.Row():
        ai_input = gr.Textbox(
            placeholder="🤖 Ask AI: 'Add milk to my list', 'What's my budget?', 'Search for organic'...",
            label="",
            scale=5,
            container=False
        )
        ai_ask_btn = gr.Button("Ask", scale=1, variant="primary")
    ai_response = gr.Markdown("", visible=True)
    
    with gr.Tabs() as tabs:
        # Trader Joe's Tab
        with gr.Tab("🛒 Trader Joe's"):
            build_store_tab("Trader Joe's")
            
        # Safeway Tab
        with gr.Tab("🛒 Safeway"):
            build_store_tab("Safeway")
            
        # Costco Tab
        with gr.Tab("🛒 Costco"):
            build_store_tab("Costco")
        
        # Indian Groceries Tab
        with gr.Tab("🛒 Indian Groceries"):
            build_store_tab("Indian Groceries")
        
        # Combined Shopping List Tab
        with gr.Tab("📋 All Stores Summary"):
            gr.Markdown("## Combined Shopping Lists - All Stores")
            gr.Markdown("*View all your shopping lists across all three stores in one place*")
            
            with gr.Row():
                refresh_all_button = gr.Button("🔄 Refresh All Lists", variant="primary", size="lg")
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 🛒 Trader Joe's (Weekly)")
                    tj_total = gr.Textbox(label="Trader Joe's Total", value="$0.00", interactive=False)
                    tj_cart = gr.DataFrame(
                        value=lambda: get_shopping_list_by_store("Trader Joe's")[["name", "price", "quantity", "total"]] if not get_shopping_list_by_store("Trader Joe's").empty else pd.DataFrame(columns=["name", "price", "quantity", "total"]),
                        headers=["Name", "Price", "Quantity", "Total"],
                        datatype=["str", "number", "number", "number"],
                        col_count=(4, "fixed"),
                        interactive=False,
                        row_count=5
                    )
                
                with gr.Column():
                    gr.Markdown("### 🛒 Safeway (Bi-weekly)")
                    sf_total = gr.Textbox(label="Safeway Total", value="$0.00", interactive=False)
                    sf_cart = gr.DataFrame(
                        value=lambda: get_shopping_list_by_store("Safeway")[["name", "price", "quantity", "total"]] if not get_shopping_list_by_store("Safeway").empty else pd.DataFrame(columns=["name", "price", "quantity", "total"]),
                        headers=["Name", "Price", "Quantity", "Total"],
                        datatype=["str", "number", "number", "number"],
                        col_count=(4, "fixed"),
                        interactive=False,
                        row_count=5
                    )
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 🛒 Costco (Monthly)")
                    co_total = gr.Textbox(label="Costco Total", value="$0.00", interactive=False)
                    co_cart = gr.DataFrame(
                        value=lambda: get_shopping_list_by_store("Costco")[["name", "price", "quantity", "total"]] if not get_shopping_list_by_store("Costco").empty else pd.DataFrame(columns=["name", "price", "quantity", "total"]),
                        headers=["Name", "Price", "Quantity", "Total"],
                        datatype=["str", "number", "number", "number"],
                        col_count=(4, "fixed"),
                        interactive=False,
                        row_count=5
                    )
                
                with gr.Column():
                    gr.Markdown("### 🛒 Indian Groceries (Weekly)")
                    ig_total = gr.Textbox(label="Indian Groceries Total", value="$0.00", interactive=False)
                    ig_cart = gr.DataFrame(
                        value=lambda: get_shopping_list_by_store("Indian Groceries")[["name", "price", "quantity", "total"]] if not get_shopping_list_by_store("Indian Groceries").empty else pd.DataFrame(columns=["name", "price", "quantity", "total"]),
                        headers=["Name", "Price", "Quantity", "Total"],
                        datatype=["str", "number", "number", "number"],
                        col_count=(4, "fixed"),
                        interactive=False,
                        row_count=5
                    )
            
            with gr.Row():
                grand_total = gr.Textbox(label="💰 Grand Total (All Stores)", value="$0.00", interactive=False)
            
            # Refresh all carts when button is clicked
            def refresh_all_lists():
                # Get dataframes and remove ID column
                tj_df = get_shopping_list_by_store("Trader Joe's")
                tj_df = tj_df[["name", "price", "quantity", "total"]] if not tj_df.empty else pd.DataFrame(columns=["name", "price", "quantity", "total"])
                
                sf_df = get_shopping_list_by_store("Safeway")
                sf_df = sf_df[["name", "price", "quantity", "total"]] if not sf_df.empty else pd.DataFrame(columns=["name", "price", "quantity", "total"])
                
                co_df = get_shopping_list_by_store("Costco")
                co_df = co_df[["name", "price", "quantity", "total"]] if not co_df.empty else pd.DataFrame(columns=["name", "price", "quantity", "total"])
                
                ig_df = get_shopping_list_by_store("Indian Groceries")
                ig_df = ig_df[["name", "price", "quantity", "total"]] if not ig_df.empty else pd.DataFrame(columns=["name", "price", "quantity", "total"])
                
                return (
                    tj_df,
                    get_store_total("Trader Joe's"),
                    sf_df,
                    get_store_total("Safeway"),
                    co_df,
                    get_store_total("Costco"),
                    ig_df,
                    get_store_total("Indian Groceries"),
                    f"${grocery_manager.get_total_cost():.2f}"
                )
            
            refresh_all_button.click(
                fn=refresh_all_lists,
                inputs=[],
                outputs=[tj_cart, tj_total, sf_cart, sf_total, co_cart, co_total, ig_cart, ig_total, grand_total]
            )
        
        # Budget Tracker Tab
        with gr.Tab("Budget Tracker"):
            gr.Markdown("## Budget Status")
            
            with gr.Row():
                refresh_budget_button = gr.Button("🔄 Refresh Budget", variant="primary")
            
            # Store-by-store breakdown
            gr.Markdown("### 💵 Spending Breakdown by Store")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("**🛒 Trader Joe's (Weekly)**")
                    tj_budget_spent = gr.Textbox(label="Spent", value="$0.00", interactive=False)
                    tj_budget_limit = gr.Textbox(label="Budget", value="$200.00", interactive=False)
                    tj_budget_status = gr.Markdown()
                
                with gr.Column():
                    gr.Markdown("**🛒 Safeway (Bi-weekly)**")
                    sf_budget_spent = gr.Textbox(label="Spent", value="$0.00", interactive=False)
                    sf_budget_limit = gr.Textbox(label="Budget", value="$150.00", interactive=False)
                    sf_budget_status = gr.Markdown()
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("**🛒 Costco (Monthly)**")
                    co_budget_spent = gr.Textbox(label="Spent", value="$0.00", interactive=False)
                    co_budget_limit = gr.Textbox(label="Budget", value="$300.00", interactive=False)
                    co_budget_status = gr.Markdown()
                
                with gr.Column():
                    gr.Markdown("**🛒 Indian Groceries (Weekly)**")
                    ig_budget_spent = gr.Textbox(label="Spent", value="$0.00", interactive=False)
                    ig_budget_limit = gr.Textbox(label="Budget", value="$100.00", interactive=False)
                    ig_budget_status = gr.Markdown()
            
            # Overall budget status
            gr.Markdown("### 📊 Overall Budget")
            with gr.Row():
                with gr.Column():
                    budget_status = gr.Textbox(label="Budget Summary", lines=4)
                    budget_warning = gr.Markdown()
                with gr.Column():
                    budget_progress = gr.Slider(
                        minimum=0, maximum=1, value=0, 
                        label="Budget Usage %", 
                        interactive=False
                    )
            
            # Function to update all budget components
            def update_budget_display():
                status, warning, progress = get_budget_status()
                
                # Get spending by store
                tj_spent_val = float(get_store_total("Trader Joe's").replace("$", ""))
                sf_spent_val = float(get_store_total("Safeway").replace("$", ""))
                co_spent_val = float(get_store_total("Costco").replace("$", ""))
                ig_spent_val = float(get_store_total("Indian Groceries").replace("$", ""))
                
                # Get budget limits
                tj_budget = grocery_manager.store_budgets.get("Trader Joe's", 200.0)
                sf_budget = grocery_manager.store_budgets.get("Safeway", 150.0)
                co_budget = grocery_manager.store_budgets.get("Costco", 300.0)
                ig_budget = grocery_manager.store_budgets.get("Indian Groceries", 100.0)
                
                # Calculate status for each store
                def get_store_status(spent, budget):
                    if budget == 0:
                        return ""
                    pct = (spent / budget) * 100
                    if spent > budget:
                        return f"### ⚠️ Over budget by ${spent - budget:.2f}!"
                    elif pct > 90:
                        return f"### 🟡 {pct:.0f}% used - Close to limit!"
                    elif pct > 75:
                        return f"### 🟢 {pct:.0f}% used"
                    else:
                        return f"### ✅ {pct:.0f}% used - Good!"
                
                tj_status = get_store_status(tj_spent_val, tj_budget)
                sf_status = get_store_status(sf_spent_val, sf_budget)
                co_status = get_store_status(co_spent_val, co_budget)
                ig_status = get_store_status(ig_spent_val, ig_budget)
                
                return (
                    f"${tj_spent_val:.2f}", f"${tj_budget:.2f}", tj_status,
                    f"${sf_spent_val:.2f}", f"${sf_budget:.2f}", sf_status,
                    f"${co_spent_val:.2f}", f"${co_budget:.2f}", co_status,
                    f"${ig_spent_val:.2f}", f"${ig_budget:.2f}", ig_status,
                    status, f"### {warning}", progress
                )
            
            # Refresh budget when button is clicked
            refresh_budget_button.click(
                fn=update_budget_display,
                inputs=[],
                outputs=[
                    tj_budget_spent, tj_budget_limit, tj_budget_status,
                    sf_budget_spent, sf_budget_limit, sf_budget_status,
                    co_budget_spent, co_budget_limit, co_budget_status,
                    ig_budget_spent, ig_budget_limit, ig_budget_status,
                    budget_status, budget_warning, budget_progress
                ]
            )
            
            # Update budget display on page load
            demo.load(
                fn=update_budget_display,
                inputs=[],
                outputs=[
                    tj_budget_spent, tj_budget_limit, tj_budget_status,
                    sf_budget_spent, sf_budget_limit, sf_budget_status,
                    co_budget_spent, co_budget_limit, co_budget_status,
                    ig_budget_spent, ig_budget_limit, ig_budget_status,
                    budget_status, budget_warning, budget_progress
                ]
            )
        
        # Archive & History Tab
        with gr.Tab("📊 History"):
            gr.Markdown("## 📊 Shopping History & Analytics")
            gr.Markdown("*Use the 📦 Archive button on each store's tab to save shopping trips here.*")
            
            with gr.Row():
                refresh_archives_btn = gr.Button("🔄 Refresh History", variant="primary")
            
            gr.Markdown("---")
            
            # Archived lists display as checkboxes (mobile-friendly)
            gr.Markdown("### 📋 Past Shopping Trips")
            
            # Store filter dropdown - always include all stores
            def get_archive_stores():
                """Get all stores (always show all, even without archives)"""
                # Always include these stores
                all_stores = ["Trader Joe's", "Safeway", "Costco", "Indian Groceries"]
                return ["All Stores"] + all_stores
            
            archive_store_filter = gr.Radio(
                choices=get_archive_stores(),
                value="All Stores",
                label="🏪 Filter by Store",
                interactive=True,
                elem_classes="store-filter-radio"
            )
            
            # Action buttons at top (compact row for mobile)
            with gr.Row(elem_classes="compact-button-row"):
                restore_btn = gr.Button("♻️ Restore", variant="secondary", scale=1, min_width=0)
                delete_archive_btn = gr.Button("🗑️ Delete", variant="stop", scale=1, min_width=0)
            
            # Confirmation checkbox (hidden by default, shown when needed)
            confirm_replace = gr.Checkbox(
                label="⚠️ I understand this will replace my current list",
                value=False,
                visible=False
            )
            
            archive_action_status = gr.Textbox(label="", value="", show_label=False)
            
            # Archives as checkboxes
            def get_archive_choices(store_filter="All Stores"):
                """Get archives as checkbox choices, filtered by store"""
                archives = grocery_manager.get_archived_lists()
                if not archives:
                    return []
                choices = []
                for i, archive in enumerate(archives):
                    store = archive.get('store', 'Unknown')
                    # Apply store filter
                    if store_filter != "All Stores" and store != store_filter:
                        continue
                    date = archive.get('date_label', 'Unknown')
                    items = archive.get('item_count', 0)
                    total = archive.get('total_cost', 0)
                    # Include original index for restore/delete operations
                    choices.append(f"{i+1}. {store} - {date} ({items} items, ${total:.2f})")
                return choices
            
            archived_lists_checkboxes = gr.CheckboxGroup(
                choices=get_archive_choices(),
                value=[],
                label="Select archive(s) to restore or delete",
                interactive=True
            )
            
            # Message shown when no archives for selected store
            no_archives_message = gr.Markdown(
                value="*No archived shopping trips for this store yet. Use the 📦 Archive button on the store tab to save trips.*",
                visible=False
            )
            
            # Update archive list when store filter changes
            def update_archive_filter(store_filter):
                choices = get_archive_choices(store_filter)
                has_archives = len(choices) > 0
                return (gr.CheckboxGroup(choices=choices, value=[], visible=has_archives),
                        gr.Markdown(visible=not has_archives))
            
            archive_store_filter.change(
                fn=update_archive_filter,
                inputs=[archive_store_filter],
                outputs=[archived_lists_checkboxes, no_archives_message]
            )
            
            gr.Markdown("---")
            
            # Analytics section
            gr.Markdown("### 📊 Shopping Analytics")
            
            with gr.Row():
                with gr.Column():
                    analytics_total_trips = gr.Textbox(label="Total Trips Archived", interactive=False)
                    analytics_total_spent = gr.Textbox(label="Total Spent", interactive=False)
                    analytics_avg_trip = gr.Textbox(label="Average Per Trip", interactive=False)
                
                with gr.Column():
                    analytics_by_store = gr.Textbox(label="Spending by Store", lines=4, interactive=False)
            
            gr.Markdown("#### 🏆 Top 10 Most Purchased Items")
            top_items_display = gr.Dataframe(
                headers=["Item", "Total Quantity"],
                datatype=["str", "number"],
                col_count=(2, "fixed"),
                interactive=False,
                row_count=10
            )
            
            # Event handlers for Archive tab
            def get_analytics():
                summary = grocery_manager.get_archive_summary()
                if not summary:
                    return "0", "$0.00", "$0.00", "No data yet", []
                
                # Format store totals
                store_lines = []
                for store, total in summary.get('store_totals', {}).items():
                    store_lines.append(f"{store}: ${total:.2f}")
                store_text = "\n".join(store_lines) if store_lines else "No data"
                
                # Format top items
                top_items = [[name, qty] for name, qty in summary.get('top_items', [])]
                
                return (
                    str(summary.get('total_archives', 0)),
                    f"${summary.get('total_spent', 0):.2f}",
                    f"${summary.get('avg_per_trip', 0):.2f}",
                    store_text,
                    top_items
                )
            
            def extract_archive_index(selected_items):
                """Extract archive index from selected checkbox item"""
                if not selected_items or len(selected_items) == 0:
                    return None
                # Get first selected item and extract index from "1. Store - Date..."
                selected = selected_items[0]
                try:
                    index = int(selected.split(".")[0]) - 1
                    return index
                except:
                    return None
            
            def do_restore(selected_items, confirmed):
                index = extract_archive_index(selected_items)
                if index is None:
                    return "❌ Please select an archive first", gr.CheckboxGroup(choices=get_archive_choices(), value=[]), gr.Checkbox(visible=False, value=False)
                
                # Get the store from the archive
                archives = grocery_manager.get_archived_lists()
                if index >= len(archives):
                    return "❌ Invalid archive", gr.CheckboxGroup(choices=get_archive_choices(), value=[]), gr.Checkbox(visible=False, value=False)
                
                store = archives[index].get('store', 'Unknown')
                existing_count = grocery_manager.get_store_item_count(store)
                
                # If there are existing items and user hasn't confirmed, show confirmation
                if existing_count > 0 and not confirmed:
                    return f"⚠️ You have {existing_count} items in {store}. Check the box below and tap Restore again to replace them.", gr.CheckboxGroup(choices=get_archive_choices(), value=selected_items), gr.Checkbox(visible=True, value=False, label=f"⚠️ Replace {existing_count} items in {store}")
                
                # Do the restore (always replaces)
                success, msg = grocery_manager.restore_from_archive(index)
                if success:
                    return f"{msg} — Go to {store} tab and tap 🔄 to see items", gr.CheckboxGroup(choices=get_archive_choices(), value=[]), gr.Checkbox(visible=False, value=False)
                return msg, gr.CheckboxGroup(choices=get_archive_choices(), value=[]), gr.Checkbox(visible=False, value=False)
            
            def do_delete(selected_items, store_filter):
                if not selected_items or len(selected_items) == 0:
                    return "❌ Please select archive(s) to delete", gr.CheckboxGroup(choices=get_archive_choices(store_filter), value=[]), gr.Radio(choices=get_archive_stores(), value=store_filter)
                
                # Extract all selected indices
                indices = []
                for selected in selected_items:
                    try:
                        index = int(selected.split(".")[0]) - 1
                        indices.append(index)
                    except:
                        pass
                
                if not indices:
                    return "❌ Could not parse selected archives", gr.CheckboxGroup(choices=get_archive_choices(store_filter), value=[]), gr.Radio(choices=get_archive_stores(), value=store_filter)
                
                # Delete multiple archives
                success, msg = grocery_manager.delete_multiple_archives(indices)
                
                # Refresh the checkbox choices and store filter after delete
                new_choices = get_archive_choices(store_filter)
                new_stores = get_archive_stores()
                # If current filter no longer exists, reset to All Stores
                if store_filter not in new_stores:
                    store_filter = "All Stores"
                    new_choices = get_archive_choices(store_filter)
                return msg, gr.CheckboxGroup(choices=new_choices, value=[]), gr.Radio(choices=new_stores, value=store_filter)
            
            def refresh_all_archive_data(store_filter):
                choices = get_archive_choices(store_filter)
                store_choices = get_archive_stores()
                trips, spent, avg, stores, top = get_analytics()
                return (gr.Radio(choices=store_choices, value=store_filter),
                        gr.CheckboxGroup(choices=choices, value=[]), 
                        "", gr.Checkbox(visible=False, value=False), 
                        trips, spent, avg, stores, top)
            
            refresh_archives_btn.click(
                fn=refresh_all_archive_data,
                inputs=[archive_store_filter],
                outputs=[archive_store_filter, archived_lists_checkboxes, archive_action_status, confirm_replace, 
                         analytics_total_trips, analytics_total_spent,
                         analytics_avg_trip, analytics_by_store, top_items_display]
            )
            
            restore_btn.click(
                fn=do_restore,
                inputs=[archived_lists_checkboxes, confirm_replace],
                outputs=[archive_action_status, archived_lists_checkboxes, confirm_replace]
            )
            
            delete_archive_btn.click(
                fn=do_delete,
                inputs=[archived_lists_checkboxes, archive_store_filter],
                outputs=[archive_action_status, archived_lists_checkboxes, archive_store_filter]
            ).then(
                fn=get_analytics,
                inputs=[],
                outputs=[analytics_total_trips, analytics_total_spent, analytics_avg_trip, 
                         analytics_by_store, top_items_display]
            )
            
            # Load archives on page load
            demo.load(
                fn=refresh_all_archive_data,
                inputs=[],
                outputs=[archived_lists_checkboxes, archive_action_status, confirm_replace,
                         analytics_total_trips, analytics_total_spent,
                         analytics_avg_trip, analytics_by_store, top_items_display]
            )
        
        # AI Chat Tab
        with gr.Tab("🤖 AI Chat"):
            gr.Markdown("## AI Grocery Assistant")
            gr.Markdown("Chat with your AI assistant to manage your grocery list and catalog.")
            
            # Chat display area (bubble style)
            ai_chatbot = gr.Chatbot(
                label="Chat History",
                height=400,
                bubble_full_width=False,
                show_copy_button=True
            )
            
            # Suggested prompts
            gr.Markdown("### Quick Actions")
            with gr.Row():
                suggest_list_btn = gr.Button("📋 Show my shopping list", size="sm")
                suggest_search_btn = gr.Button("🔍 Search catalog", size="sm")
                suggest_budget_btn = gr.Button("💰 Check budget", size="sm")
                suggest_add_btn = gr.Button("➕ Add item to list", size="sm")
            
            # Input area
            with gr.Row():
                ai_chat_input = gr.Textbox(
                    placeholder="Ask me anything about your groceries...",
                    label="",
                    scale=5,
                    container=False
                )
                ai_chat_send = gr.Button("Send", variant="primary", scale=1)
            
            # Clear button
            with gr.Row():
                ai_clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary", size="sm")
        
        # Settings Tab
        with gr.Tab("Settings"):
            gr.Markdown("## Application Settings")
            
            # Email Settings
            gr.Markdown("### 📧 Email Settings")
            with gr.Row():
                email_input = gr.Textbox(
                    label="Email Address(es) - Use commas to separate multiple emails",
                    value=grocery_manager.email_address,
                    placeholder="email1@example.com, email2@example.com",
                    scale=3
                )
                save_email_btn = gr.Button("💾 Save Email", variant="secondary", scale=1)
            
            email_status = gr.Textbox(label="Status", value="", show_label=False)
            
            # Email save function
            def save_email(email):
                if not email or "@" not in email:
                    return "❌ Please enter a valid email address"
                
                # Validate multiple emails if comma-separated
                emails = [e.strip() for e in email.split(',') if e.strip()]
                invalid_emails = [e for e in emails if '@' not in e or '.' not in e]
                
                if invalid_emails:
                    return f"❌ Invalid email(s): {', '.join(invalid_emails)}"
                
                grocery_manager.email_address = email
                
                if len(emails) > 1:
                    return f"✅ {len(emails)} email addresses saved: {', '.join(emails)}"
                else:
                    return f"✅ Email saved: {email}"
            
            save_email_btn.click(
                fn=save_email,
                inputs=[email_input],
                outputs=[email_status]
            )
            
            gr.Markdown("---")
            
            # Budget Settings
            gr.Markdown("### 💰 Budget Settings")
            gr.Markdown("**🛒 Individual Store Budgets**")
            
            # Individual store budgets
            with gr.Row():
                with gr.Column():
                    gr.Markdown("Trader Joe's (Weekly)")
                    tj_budget_input = gr.Number(
                        label="Budget ($)", 
                        value=grocery_manager.store_budgets.get("Trader Joe's", 200), 
                        minimum=0
                    )
                
                with gr.Column():
                    gr.Markdown("Safeway (Bi-weekly)")
                    sf_budget_input = gr.Number(
                        label="Budget ($)", 
                        value=grocery_manager.store_budgets.get("Safeway", 150), 
                        minimum=0
                    )
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("Costco (Monthly)")
                    co_budget_input = gr.Number(
                        label="Budget ($)", 
                        value=grocery_manager.store_budgets.get("Costco", 300), 
                        minimum=0
                    )
                
                with gr.Column():
                    gr.Markdown("Indian Groceries (Weekly)")
                    ig_budget_input = gr.Number(
                        label="Budget ($)", 
                        value=grocery_manager.store_budgets.get("Indian Groceries", 100), 
                        minimum=0
                    )
            
            gr.Markdown("### 💰 Total Budget")
            with gr.Row():
                total_budget_input = gr.Number(
                    label="Total Budget ($)", 
                    value=grocery_manager.budget, 
                    minimum=1
                )
                update_budget_button = gr.Button("💾 Save All Budgets", variant="primary")
            
            budget_message = gr.Textbox(label="Status", value="Set your budgets above and click Save")
            
            # Update budget function
            def save_budgets(tj_budget, sf_budget, co_budget, ig_budget, total_budget):
                grocery_manager.store_budgets = {
                    "Trader Joe's": tj_budget,
                    "Safeway": sf_budget,
                    "Costco": co_budget,
                    "Indian Groceries": ig_budget
                }
                grocery_manager.budget = total_budget
                
                return f"✅ Budgets saved! TJ: ${tj_budget:.2f} | Safeway: ${sf_budget:.2f} | Costco: ${co_budget:.2f} | Indian: ${ig_budget:.2f} | Total: ${total_budget:.2f}"
            
            update_budget_button.click(
                fn=save_budgets,
                inputs=[tj_budget_input, sf_budget_input, co_budget_input, ig_budget_input, total_budget_input],
                outputs=budget_message
            )
    
    # Wire up AI Quick Chat Bar
    ai_ask_btn.click(
        fn=chat_with_ai,
        inputs=ai_input,
        outputs=ai_response
    )
    
    # Also trigger on Enter key
    ai_input.submit(
        fn=chat_with_ai,
        inputs=ai_input,
        outputs=ai_response
    )
    
    # Wire up AI Chat Tab
    ai_chat_send.click(
        fn=chat_respond,
        inputs=[ai_chat_input, ai_chatbot],
        outputs=[ai_chatbot, ai_chat_input]
    )
    
    ai_chat_input.submit(
        fn=chat_respond,
        inputs=[ai_chat_input, ai_chatbot],
        outputs=[ai_chatbot, ai_chat_input]
    )
    
    ai_clear_btn.click(
        fn=clear_chat,
        outputs=[ai_chatbot, ai_chat_input]
    )
    
    # Quick action buttons - fill input with suggestion
    suggest_list_btn.click(
        fn=lambda: "Show me my current shopping list",
        outputs=ai_chat_input
    )
    suggest_search_btn.click(
        fn=lambda: "Search for ",
        outputs=ai_chat_input
    )
    suggest_budget_btn.click(
        fn=lambda: "What's my current budget status?",
        outputs=ai_chat_input
    )
    suggest_add_btn.click(
        fn=lambda: "Add ",
        outputs=ai_chat_input
    )

if __name__ == "__main__":
    demo.launch()# Deployed Wed Dec 31 17:45:16 PST 2025

# Last updated: Wed Dec 31 17:46:34 PST 2025
# Updated: Sun Jan  4 20:05:38 PST 2026

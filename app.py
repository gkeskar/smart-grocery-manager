import gradio as gr
import pandas as pd
from grocery_app import GroceryManager  # pyright: ignore[reportMissingImports]
import os
from dotenv import load_dotenv

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

# Define functions for the Gradio interface

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
    categories = sorted(list(set(item["category"] for item in items)))
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
    
    # Check for duplicate item name (case-insensitive)
    store_items = grocery_manager.stores.get(store_name, [])
    name_trimmed = name.strip().lower()
    for item in store_items:
        if item.get("name", "").lower() == name_trimmed:
            return f"❌ Item '{name}' already exists in {store_name} catalog"
    
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
        "name": name.strip(),
        "category": category.strip(),
        "price": float(price),
        "unit": unit.strip(),
        "store": store_name
    }
    
    grocery_manager.stores[store_name].append(new_item)
    grocery_manager._save_catalog()  # Persist to JSON file
    return f"✅ Added {name} to {store_name} catalog (saved to file)"

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
    def get_shopping_list_items_for_dropdown():
        """Returns list of item names for the item selector dropdown"""
        store_items = [item for item in grocery_manager.shopping_list if item.get("store") == store_name]
        if not store_items:
            return []
        return [f"{item['name']} (qty: {item['quantity']})" for item in store_items]
    
    gr.Markdown(f"## 🛒 {store_name}")
    
    # Two columns: Catalog and Shopping List
    with gr.Row():
        # LEFT COLUMN: CATALOG
        with gr.Column(scale=1):
            gr.Markdown("### 📋 Catalog")
            
            category_filter = gr.Dropdown(
                choices=get_categories(store_name),
                value="All Categories",
                label="Filter by Category"
            )
            
            # Initialize catalog table with actual data (without checkmarks to prevent flickering)
            initial_catalog = get_store_items(store_name)[["name", "category", "price", "unit"]].copy()
            
            catalog_table = gr.DataFrame(
                value=initial_catalog,
                headers=["Name", "Category", "Price", "Unit"],
                datatype=["str", "str", "number", "str"],
                row_count=15,
                col_count=(4, "fixed"),
                interactive=False
            )
            
            # Selected items display (for multi-select)
            selected_catalog_items_display = gr.Textbox(
                label="✓ Selected Items",
                value="No items selected",
                interactive=False
            )
            
            # Clear selections button
            clear_selections_btn = gr.Button("✗ Clear All Selections", variant="secondary", size="sm")
            
            # Add new item section
            gr.Markdown("**➕ Add New Item**")
            with gr.Row():
                new_item_name = gr.Textbox(label="Name", placeholder="New item", scale=2)
                new_item_price = gr.Number(label="Price", value=0, minimum=0, step=0.01, scale=1)
            with gr.Row():
                new_item_category = gr.Dropdown(
                    choices=[cat for cat in get_categories(store_name) if cat != "All Categories"],
                    label="Category",
                    value=None,
                    scale=1,
                    allow_custom_value=True  # Allow users to add new categories if needed
                )
                new_item_unit = gr.Textbox(label="Unit", placeholder="lb", scale=1)
            
            add_catalog_btn = gr.Button("➕ Add to Catalog", variant="secondary")
            
            # Update existing item section
            gr.Markdown("**✏️ Update Selected Item** (Click on a row above to select)")
            
            # Hidden field to store selected item ID
            selected_edit_item_id = gr.Textbox(visible=False, value="")
            
            with gr.Row():
                edit_item_name = gr.Textbox(label="Name", placeholder="Select an item first", scale=2)
                edit_item_price = gr.Number(label="Price", value=0, minimum=0, step=0.01, scale=1)
            with gr.Row():
                edit_item_category = gr.Dropdown(
                    choices=[cat for cat in get_categories(store_name) if cat != "All Categories"],
                    label="Category",
                    value=None,
                    scale=1,
                    allow_custom_value=True
                )
                edit_item_unit = gr.Textbox(label="Unit", placeholder="lb", scale=1)
            
            with gr.Row():
                update_catalog_btn = gr.Button("💾 Update Item", variant="primary", scale=1)
                delete_catalog_btn = gr.Button("🗑️ Delete from Catalog", variant="stop", scale=1)
        
        # RIGHT COLUMN: SHOPPING LIST
        with gr.Column(scale=1):
            gr.Markdown("### 🛒 Shopping List")
            
            shopping_list_table = gr.DataFrame(
                value=lambda: get_shopping_list_by_store(store_name)[["name", "price", "quantity", "total"]] if not get_shopping_list_by_store(store_name).empty else pd.DataFrame(columns=["name", "price", "quantity", "total"]),
                headers=["Name", "Price", "Quantity", "Total"],
                datatype=["str", "number", "number", "number"],
                row_count=15,
                col_count=(4, "fixed"),
                interactive=False
            )
            
            list_total = gr.Textbox(
                label=f"💰 Total",
                value="$0.00",
                interactive=False
            )
            
            # Add button - adds all selected items (qty 1 each)
            add_to_list_btn = gr.Button("➕ Add Selected Items to List", variant="primary", size="lg")
            
            # Update quantity section - simpler dropdown approach
            gr.Markdown("**Update Quantity:**")
            with gr.Row():
                item_selector_dropdown = gr.Dropdown(
                    label="Select Item to Update",
                    choices=get_shopping_list_items_for_dropdown(),
                    value=None,
                    scale=3,
                    interactive=True
                )
                update_quantity_dropdown = gr.Dropdown(
                    label="New Quantity",
                    choices=[1, 2, 3, 4, 5],
                    value=1,
                    scale=2,
                    interactive=True
                )
                update_quantity_btn = gr.Button("✏️ Update", variant="secondary", scale=1)
            
            with gr.Row():
                remove_from_list_btn = gr.Button("🗑️ Remove", variant="stop", scale=1)
                email_button = gr.Button("📧 Email List", variant="primary", scale=1)
    
    # Status messages
    status_message = gr.Textbox(label="Status", show_label=False, placeholder="Select items and use buttons")
    
    # Hidden states
    selected_catalog_item_ids = gr.State(value=[])  # Changed to list for multi-select
    
    # ═══════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════
    
    # Helper function to add checkmark column
    def add_checkmark_column(df, selected_ids):
        """Add a checkmark column to show selected items"""
        if df.empty:
            return df
        
        # Get item IDs for the dataframe
        all_items = grocery_manager.stores.get(store_name, [])
        
        # Create checkmark column
        checkmarks = []
        for idx, row in df.iterrows():
            item_name = row["name"]
            # Find the item ID
            item_id = None
            for item in all_items:
                if item["name"] == item_name:
                    item_id = item["id"]
                    break
            
            # Add checkmark if selected
            if item_id and item_id in (selected_ids or []):
                checkmarks.append("✓")
            else:
                checkmarks.append("")
        
        # Insert checkmark column at the front
        df.insert(0, "☑", checkmarks)
        return df
    
    # Filter catalog by category
    def filter_catalog(cat, selected_ids):
        df = get_store_items(store_name, cat)
        df = df[["name", "category", "price", "unit"]].copy()
        # No checkmarks to prevent UI flickering - use selected items display instead
        return df
    
    category_filter.change(
        fn=filter_catalog,
        inputs=[category_filter, selected_catalog_item_ids],
        outputs=catalog_table
    )
    
    # Select item from catalog (multi-select with toggle)
    def select_catalog_item(evt: gr.SelectData, current_filter, current_selections):
        all_items = grocery_manager.stores.get(store_name, [])
        df = get_store_items(store_name, current_filter)
        
        if df.empty or evt.index[0] >= len(df):
            return current_selections, "❌ Could not select item", "No items selected", "", "", 0, None, ""
        
        item_name = df.iloc[evt.index[0]]["name"]
        item_id = None
        
        # Find the item ID
        for item in all_items:
            if item["name"] == item_name:
                item_id = item["id"]
                break
        
        if not item_id:
            return current_selections, "❌ Item not found", "No items selected", "", "", 0, None, ""
        
        # Add-only selection (no toggle to avoid double-fire issues)
        if current_selections is None:
            current_selections = []
        
        # Only add if not already selected (prevent duplicates from double-fire)
        if item_id not in current_selections:
            current_selections.append(item_id)
            msg = f"➕ Selected: {item_name}"
        else:
            # Already selected, don't change anything
            msg = f"✓ Already selected: {item_name}"
        
        # Create display text
        if len(current_selections) == 0:
            display_text = "No items selected"
        else:
            # Get names of selected items
            selected_names = []
            for sel_id in current_selections:
                for item in all_items:
                    if item["id"] == sel_id:
                        selected_names.append(item["name"])
                        break
            display_text = f"Selected {len(current_selections)} items: " + ", ".join(selected_names)
        
        # Don't update catalog table here to prevent flickering
        # The selected items display text will show what's selected
        
        # Also populate edit fields with the last clicked item
        clicked_item = None
        for item in all_items:
            if item["id"] == item_id:
                clicked_item = item
                break
        
        if clicked_item:
            return (current_selections, msg, display_text, 
                   item_id, clicked_item["name"], clicked_item["price"], 
                   clicked_item["category"], clicked_item["unit"])
        else:
            return current_selections, msg, display_text, "", "", 0, None, ""
    
    catalog_table.select(
        fn=select_catalog_item,
        inputs=[category_filter, selected_catalog_item_ids],
        outputs=[selected_catalog_item_ids, status_message, selected_catalog_items_display,
                selected_edit_item_id, edit_item_name, edit_item_price, edit_item_category, edit_item_unit]
    )
    
    # Add to List button - adds all selected items (quantity 1 each)
    def add_to_list_handler(item_ids, current_filter):
        if not item_ids or len(item_ids) == 0:
            return "❌ Please select at least one item from the catalog first", None, None, [], "No items selected", None
        
        # Add all selected items
        added_items = []
        for item_id in item_ids:
            msg = add_to_cart(item_id, 1)  # Add 1 of each item
            # Extract item name from message
            if "Added" in msg or "Updated" in msg:
                # Find item name
                for item in grocery_manager.stores.get(store_name, []):
                    if item["id"] == item_id:
                        added_items.append(item["name"])
                        break
        
        # Create success message
        if len(added_items) == 1:
            success_msg = f"✅ Added {added_items[0]} to list"
        else:
            success_msg = f"✅ Added {len(added_items)} items to list: " + ", ".join(added_items)
        
        # Get updated shopping list
        df = get_shopping_list_by_store(store_name)
        df_display = df[["name", "price", "quantity", "total"]] if not df.empty else pd.DataFrame(columns=["name", "price", "quantity", "total"])
        
        # Get updated dropdown choices and reset value
        dropdown_choices = get_shopping_list_items_for_dropdown()
        dropdown_update = gr.Dropdown(choices=dropdown_choices, value=None)
        
        # Clear selections after adding (no need to update catalog table)
        return success_msg, df_display, get_store_total(store_name), [], "No items selected", dropdown_update
    
    add_to_list_btn.click(
        fn=add_to_list_handler,
        inputs=[selected_catalog_item_ids, category_filter],
        outputs=[status_message, shopping_list_table, list_total, selected_catalog_item_ids, selected_catalog_items_display, item_selector_dropdown]
    )
    
    # Remove from List button
    def remove_from_list_handler(selected_item):
        if not selected_item:
            return "❌ Please select an item from the dropdown first", None, None, gr.Dropdown(choices=[], value=None)
        
        # Extract item name from dropdown selection (format: "Item Name (qty: X)")
        item_name = selected_item.split(" (qty:")[0].strip()
        
        # Find item ID by name
        item_id = None
        for item in grocery_manager.shopping_list:
            if item.get("store") == store_name and item["name"] == item_name:
                item_id = item["id"]
                break
        
        if not item_id:
            return "❌ Item not found", None, None, gr.Dropdown(choices=[], value=None)
        
        msg = remove_from_cart(item_id)[0]
        df = get_shopping_list_by_store(store_name)
        df_display = df[["name", "price", "quantity", "total"]] if not df.empty else pd.DataFrame(columns=["name", "price", "quantity", "total"])
        
        # Get updated dropdown choices and reset value
        dropdown_choices = get_shopping_list_items_for_dropdown()
        dropdown_update = gr.Dropdown(choices=dropdown_choices, value=None)
        
        return msg, df_display, get_store_total(store_name), dropdown_update
    
    remove_from_list_btn.click(
        fn=remove_from_list_handler,
        inputs=[item_selector_dropdown],
        outputs=[status_message, shopping_list_table, list_total, item_selector_dropdown]
    )
    
    # Update quantity for selected item
    def update_quantity_handler(selected_item, new_qty):
        # Get current shopping list to avoid clearing it on error
        df = get_shopping_list_by_store(store_name)
        if not df.empty and "name" in df.columns:
            df_display = df[["name", "price", "quantity", "total"]]
        else:
            df_display = pd.DataFrame(columns=["name", "price", "quantity", "total"])
        
        current_total = get_store_total(store_name)
        dropdown_choices = get_shopping_list_items_for_dropdown()
        
        if not selected_item:
            return "❌ Please select an item from the dropdown first", df_display, current_total, gr.Dropdown(choices=dropdown_choices, value=None)
        
        if new_qty < 1:
            return "❌ Quantity must be at least 1", df_display, current_total, gr.Dropdown(choices=dropdown_choices, value=None)
        
        # Extract item name from dropdown selection (format: "Item Name (qty: X)")
        item_name = selected_item.split(" (qty:")[0].strip()
        
        # Find item ID by name
        item_id = None
        for item in grocery_manager.shopping_list:
            if item.get("store") == store_name and item["name"] == item_name:
                item_id = item["id"]
                break
        
        if not item_id:
            return "❌ Item not found", df_display, current_total, gr.Dropdown(choices=dropdown_choices, value=None)
        
        # Update the quantity
        msg = update_item_quantity(item_id, int(new_qty))
        
        # Refresh shopping list after update
        df = get_shopping_list_by_store(store_name)
        if not df.empty and "name" in df.columns:
            df_display = df[["name", "price", "quantity", "total"]]
        else:
            df_display = pd.DataFrame(columns=["name", "price", "quantity", "total"])
        
        # Get updated dropdown choices (with new quantities) and reset value
        dropdown_choices = get_shopping_list_items_for_dropdown()
        dropdown_update = gr.Dropdown(choices=dropdown_choices, value=None)
        
        # After successful update
        success_msg = f"✅ Updated {item_name} to quantity {new_qty}"
        
        return success_msg, df_display, get_store_total(store_name), dropdown_update
    
    update_quantity_btn.click(
        fn=update_quantity_handler,
        inputs=[item_selector_dropdown, update_quantity_dropdown],
        outputs=[status_message, shopping_list_table, list_total, item_selector_dropdown]
    )
    
    # Email list
    email_button.click(
        fn=lambda: send_shopping_list_email(store_name),
        inputs=[],
        outputs=[status_message]
    )
    
    # Add new item to catalog
    def add_new_catalog_item(name, category, price, unit, current_filter):
        msg = add_catalog_item(store_name, name, category, price, unit)
        # Refresh catalog with current filter to maintain category selection
        df = get_store_items(store_name, current_filter)
        df_display = df[["name", "category", "price", "unit"]]
        return msg, df_display, "", 0, None, ""  # Reset category to None (dropdown default)
    
    add_catalog_btn.click(
        fn=add_new_catalog_item,
        inputs=[new_item_name, new_item_category, new_item_price, new_item_unit, category_filter],
        outputs=[status_message, catalog_table, new_item_name, new_item_price, new_item_category, new_item_unit]
    )
    
    # Update existing catalog item
    def update_catalog_item_handler(item_id, name, price, category, unit, current_filter):
        if not item_id or item_id.strip() == "":
            return "❌ Please select an item from the catalog first to update", None, "", "", 0, None, ""
        
        if not name or not category or price <= 0:
            return "❌ Please fill in all fields with valid values", None, item_id, name, price, category, unit
        
        # Update the item
        success = grocery_manager.update_catalog_item(
            item_id=item_id,
            name=name.strip(),
            category=category.strip(),
            price=float(price),
            unit=unit.strip()
        )
        
        if success:
            # Refresh catalog with current filter
            df = get_store_items(store_name, current_filter)
            df_display = df[["name", "category", "price", "unit"]]
            
            # Clear edit fields after successful update
            return f"✅ Updated '{name}' successfully (saved to file)", df_display, "", "", 0, None, ""
        else:
            return f"❌ Item not found", None, item_id, name, price, category, unit
    
    update_catalog_btn.click(
        fn=update_catalog_item_handler,
        inputs=[selected_edit_item_id, edit_item_name, edit_item_price, edit_item_category, edit_item_unit, category_filter],
        outputs=[status_message, catalog_table, selected_edit_item_id, edit_item_name, edit_item_price, edit_item_category, edit_item_unit]
    )
    
    # Delete selected items from catalog
    def delete_selected_catalog_items(item_ids, current_filter):
        if not item_ids or len(item_ids) == 0:
            return "❌ Please select at least one item from the catalog first", None, [], "No items selected"
        
        # Delete all selected items
        deleted_items = []
        store_items = grocery_manager.stores.get(store_name, [])
        for item_id in item_ids:
            # Find and remove item
            for i, item in enumerate(store_items):
                if item["id"] == item_id:
                    deleted_items.append(item["name"])
                    store_items.pop(i)
                    break
        
        # Save once after all deletions (more efficient than saving in loop)
        if deleted_items:
            grocery_manager._save_catalog()
        
        # Create success message
        if len(deleted_items) == 1:
            msg = f"✅ Removed '{deleted_items[0]}' from catalog (saved to file)"
        else:
            msg = f"✅ Removed {len(deleted_items)} items from catalog (saved to file)"
        
        # Refresh catalog with current filter to maintain category selection
        df = get_store_items(store_name, current_filter)
        df_display = df[["name", "category", "price", "unit"]]
        
        # Clear selections after deleting
        return msg, df_display, [], "No items selected"
    
    delete_catalog_btn.click(
        fn=delete_selected_catalog_items,
        inputs=[selected_catalog_item_ids, category_filter],
        outputs=[status_message, catalog_table, selected_catalog_item_ids, selected_catalog_items_display]
    )
    
    # Clear all selections button
    def clear_all_selections(current_filter):
        # No need to update catalog table without checkmarks
        return [], "No items selected", "✓ Cleared all selections"
    
    clear_selections_btn.click(
        fn=clear_all_selections,
        inputs=[category_filter],
        outputs=[selected_catalog_item_ids, selected_catalog_items_display, status_message]
    )
    
    # Initialize catalog table on page load
    # Catalog table is now initialized with data on creation (see above)

# Create the Gradio interface
with gr.Blocks(title="Smart Grocery Manager", css="footer {visibility: hidden}") as demo:
    gr.Markdown("# 🛒 Smart Grocery Manager")
    
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
                
                return (
                    tj_df,
                    get_store_total("Trader Joe's"),
                    sf_df,
                    get_store_total("Safeway"),
                    co_df,
                    get_store_total("Costco"),
                    f"${grocery_manager.get_total_cost():.2f}"
                )
            
            refresh_all_button.click(
                fn=refresh_all_lists,
                inputs=[],
                outputs=[tj_cart, tj_total, sf_cart, sf_total, co_cart, co_total, grand_total]
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
                
                with gr.Column():
                    gr.Markdown("**🛒 Costco (Monthly)**")
                    co_budget_spent = gr.Textbox(label="Spent", value="$0.00", interactive=False)
                    co_budget_limit = gr.Textbox(label="Budget", value="$300.00", interactive=False)
                    co_budget_status = gr.Markdown()
            
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
                
                # Get budget limits
                tj_budget = grocery_manager.store_budgets.get("Trader Joe's", 200.0)
                sf_budget = grocery_manager.store_budgets.get("Safeway", 150.0)
                co_budget = grocery_manager.store_budgets.get("Costco", 300.0)
                
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
                
                return (
                    f"${tj_spent_val:.2f}", f"${tj_budget:.2f}", tj_status,
                    f"${sf_spent_val:.2f}", f"${sf_budget:.2f}", sf_status,
                    f"${co_spent_val:.2f}", f"${co_budget:.2f}", co_status,
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
                    budget_status, budget_warning, budget_progress
                ]
            )
        
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
                
                with gr.Column():
                    gr.Markdown("Costco (Monthly)")
                    co_budget_input = gr.Number(
                        label="Budget ($)", 
                        value=grocery_manager.store_budgets.get("Costco", 300), 
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
            def save_budgets(tj_budget, sf_budget, co_budget, total_budget):
                grocery_manager.store_budgets = {
                    "Trader Joe's": tj_budget,
                    "Safeway": sf_budget,
                    "Costco": co_budget
                }
                grocery_manager.budget = total_budget
                
                return f"✅ Budgets saved! TJ: ${tj_budget:.2f} | Safeway: ${sf_budget:.2f} | Costco: ${co_budget:.2f} | Total: ${total_budget:.2f}"
            
            update_budget_button.click(
                fn=save_budgets,
                inputs=[tj_budget_input, sf_budget_input, co_budget_input, total_budget_input],
                outputs=budget_message
            )

if __name__ == "__main__":
    demo.launch()
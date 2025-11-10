import json
import os

class GroceryManager:
    def __init__(self):
        self.catalog_file = "grocery_catalog.json"
        self.stores = {}
        self.shopping_list = []
        self.budget = 650.0  # Default total budget
        self.store_budgets = {
            "Trader Joe's": 200.0,   # Weekly
            "Safeway": 150.0,         # Bi-weekly
            "Costco": 300.0           # Monthly
        }
        self.email_address = "gandhali.aradhye@gmail.com"  # Default email
        self._load_or_initialize_catalog()

    def _initialize_sample_data(self):
        """Initialize sample data for all stores"""
        # Initialize empty lists for each store
        self.stores = {
            "Trader Joe's": [],
            "Safeway": [],
            "Costco": []
        }
        
        # Populate Trader Joe's items
        trader_joes_items = [
            {"id": "tj-1", "name": "Organic Bananas", "category": "Produce", "store": "Trader Joe's", "price": 0.99, "unit": "lb", "default_quantity": 2},
            {"id": "tj-2", "name": "Avocados", "category": "Produce", "store": "Trader Joe's", "price": 1.49, "unit": "each", "default_quantity": 3},
            {"id": "tj-3", "name": "Mixed Green Salad", "category": "Produce", "store": "Trader Joe's", "price": 2.99, "unit": "bag", "default_quantity": 1},
            {"id": "tj-4", "name": "Cherry Tomatoes", "category": "Produce", "store": "Trader Joe's", "price": 3.49, "unit": "package", "default_quantity": 1},
            {"id": "tj-5", "name": "Baby Carrots", "category": "Produce", "store": "Trader Joe's", "price": 1.99, "unit": "bag", "default_quantity": 1},
            {"id": "tj-6", "name": "Organic Apples", "category": "Produce", "store": "Trader Joe's", "price": 1.29, "unit": "each", "default_quantity": 4},
            
            {"id": "tj-8", "name": "Greek Yogurt", "category": "Dairy", "store": "Trader Joe's", "price": 1.99, "unit": "container", "default_quantity": 2},
            {"id": "tj-9", "name": "Kerrygold Butter", "category": "Dairy", "store": "Trader Joe's", "price": 3.99, "unit": "block", "default_quantity": 1},
            {"id": "tj-11", "name": "Almond Milk", "category": "Dairy", "store": "Trader Joe's", "price": 2.99, "unit": "carton", "default_quantity": 1},
            
            {"id": "tj-12", "name": "Cauliflower Gnocchi", "category": "Frozen", "store": "Trader Joe's", "price": 2.99, "unit": "bag", "default_quantity": 2},
            {"id": "tj-13", "name": "Mandarin Chicken", "category": "Frozen", "store": "Trader Joe's", "price": 4.99, "unit": "package", "default_quantity": 1},
            {"id": "tj-14", "name": "Fried Rice", "category": "Frozen", "store": "Trader Joe's", "price": 2.99, "unit": "bag", "default_quantity": 1},
            {"id": "tj-16", "name": "Frozen Berries", "category": "Frozen", "store": "Trader Joe's", "price": 3.99, "unit": "bag", "default_quantity": 1},
            
            {"id": "tj-18", "name": "Olive Oil", "category": "Pantry", "store": "Trader Joe's", "price": 7.99, "unit": "bottle", "default_quantity": 1},
            {"id": "tj-19", "name": "Pasta", "category": "Pantry", "store": "Trader Joe's", "price": 1.29, "unit": "package", "default_quantity": 2},
            {"id": "tj-20", "name": "Marinara Sauce", "category": "Pantry", "store": "Trader Joe's", "price": 2.99, "unit": "jar", "default_quantity": 1},
            
            {"id": "tj-22", "name": "Dark Chocolate", "category": "Snacks", "store": "Trader Joe's", "price": 2.49, "unit": "bar", "default_quantity": 2},
            {"id": "tj-23", "name": "Trail Mix", "category": "Snacks", "store": "Trader Joe's", "price": 4.99, "unit": "bag", "default_quantity": 1},
            {"id": "tj-25", "name": "Hummus", "category": "Snacks", "store": "Trader Joe's", "price": 3.49, "unit": "container", "default_quantity": 1},
            {"id": "tj-26", "name": "Popcorn", "category": "Snacks", "store": "Trader Joe's", "price": 1.99, "unit": "bag", "default_quantity": 2},
            
            {"id": "tj-27", "name": "Sourdough Bread", "category": "Bakery", "store": "Trader Joe's", "price": 3.99, "unit": "loaf", "default_quantity": 1},
            {"id": "tj-29", "name": "Croissants", "category": "Bakery", "store": "Trader Joe's", "price": 4.49, "unit": "package", "default_quantity": 1},
            {"id": "tj-30", "name": "Naan Bread", "category": "Bakery", "store": "Trader Joe's", "price": 3.49, "unit": "package", "default_quantity": 1},
            
            # Additional items
            {"id": "tj-31", "name": "Tomatoes", "category": "Produce", "store": "Trader Joe's", "price": 2.49, "unit": "lb", "default_quantity": 2},
            {"id": "tj-32", "name": "Onions", "category": "Produce", "store": "Trader Joe's", "price": 1.49, "unit": "lb", "default_quantity": 2},
            {"id": "tj-34", "name": "Corn Ravioli", "category": "Frozen", "store": "Trader Joe's", "price": 3.99, "unit": "package", "default_quantity": 1},
            {"id": "tj-35", "name": "Ginger", "category": "Produce", "store": "Trader Joe's", "price": 2.99, "unit": "package", "default_quantity": 1},
            {"id": "tj-36", "name": "Lemonade", "category": "Beverages", "store": "Trader Joe's", "price": 2.99, "unit": "bottle", "default_quantity": 1},
            {"id": "tj-37", "name": "Eggs", "category": "Dairy", "store": "Trader Joe's", "price": 4.49, "unit": "dozen", "default_quantity": 1},
            {"id": "tj-38", "name": "Mini Pizza", "category": "Frozen", "store": "Trader Joe's", "price": 4.99, "unit": "package", "default_quantity": 1},
            {"id": "tj-39", "name": "Boneless Chicken Breast", "category": "Meat", "store": "Trader Joe's", "price": 6.99, "unit": "lb", "default_quantity": 1},
            {"id": "tj-39a", "name": "Boneless Chicken Thighs", "category": "Meat", "store": "Trader Joe's", "price": 5.99, "unit": "lb", "default_quantity": 1},
            {"id": "tj-39b", "name": "Chilly Lime Chicken", "category": "Meat", "store": "Trader Joe's", "price": 7.99, "unit": "lb", "default_quantity": 1},
            {"id": "tj-40", "name": "Cauliflower", "category": "Produce", "store": "Trader Joe's", "price": 3.49, "unit": "head", "default_quantity": 1},
            {"id": "tj-41", "name": "Almond Flour Tortillas", "category": "Bakery", "store": "Trader Joe's", "price": 3.99, "unit": "package", "default_quantity": 1},
            {"id": "tj-42", "name": "Indian Frozen Food Box", "category": "Frozen", "store": "Trader Joe's", "price": 3.99, "unit": "box", "default_quantity": 1},
            {"id": "tj-43", "name": "Lemons", "category": "Produce", "store": "Trader Joe's", "price": 0.49, "unit": "each", "default_quantity": 2},
            {"id": "tj-44", "name": "Capsicum", "category": "Produce", "store": "Trader Joe's", "price": 1.99, "unit": "each", "default_quantity": 1},
            {"id": "tj-45", "name": "Potatoes", "category": "Produce", "store": "Trader Joe's", "price": 2.99, "unit": "bag", "default_quantity": 1},
            {"id": "tj-46", "name": "Cilantro", "category": "Produce", "store": "Trader Joe's", "price": 1.49, "unit": "bunch", "default_quantity": 1},
            {"id": "tj-47", "name": "Almond Dark Chocolates", "category": "Snacks", "store": "Trader Joe's", "price": 3.49, "unit": "package", "default_quantity": 2},
            {"id": "tj-48", "name": "Organic Whole Milk", "category": "Dairy", "store": "Trader Joe's", "price": 4.99, "unit": "gallon", "default_quantity": 1},
            {"id": "tj-49", "name": "Mixed Fruit", "category": "Produce", "store": "Trader Joe's", "price": 5.99, "unit": "package", "default_quantity": 1},
        ]
        
        # Populate Safeway items
        safeway_items = [
            {"id": "sw-1", "name": "Chicken Breast", "category": "Meat", "store": "Safeway", "price": 4.99, "unit": "lb", "default_quantity": 2},
            {"id": "sw-2", "name": "Ground Beef", "category": "Meat", "store": "Safeway", "price": 5.99, "unit": "lb", "default_quantity": 1},
            {"id": "sw-3", "name": "Salmon", "category": "Meat", "store": "Safeway", "price": 9.99, "unit": "lb", "default_quantity": 1},
            {"id": "sw-4", "name": "Bacon", "category": "Meat", "store": "Safeway", "price": 6.99, "unit": "package", "default_quantity": 1},
            {"id": "sw-5", "name": "Pork Chops", "category": "Meat", "store": "Safeway", "price": 7.99, "unit": "lb", "default_quantity": 1},
            {"id": "sw-6", "name": "Turkey Breast", "category": "Meat", "store": "Safeway", "price": 8.99, "unit": "lb", "default_quantity": 1},
            
            {"id": "sw-7", "name": "Onions", "category": "Produce", "store": "Safeway", "price": 1.49, "unit": "lb", "default_quantity": 2},
            {"id": "sw-8", "name": "Potatoes", "category": "Produce", "store": "Safeway", "price": 2.99, "unit": "bag", "default_quantity": 1},
            {"id": "sw-9", "name": "Garlic", "category": "Produce", "store": "Safeway", "price": 0.99, "unit": "head", "default_quantity": 2},
            {"id": "sw-10", "name": "Bell Peppers", "category": "Produce", "store": "Safeway", "price": 1.99, "unit": "each", "default_quantity": 3},
            {"id": "sw-11", "name": "Lettuce", "category": "Produce", "store": "Safeway", "price": 2.49, "unit": "head", "default_quantity": 1},
            {"id": "sw-12", "name": "Broccoli", "category": "Produce", "store": "Safeway", "price": 2.99, "unit": "bunch", "default_quantity": 1},
            
            {"id": "sw-13", "name": "Eggs", "category": "Dairy", "store": "Safeway", "price": 4.99, "unit": "dozen", "default_quantity": 1},
            {"id": "sw-14", "name": "Fage Yogurt", "category": "Dairy", "store": "Safeway", "price": 5.99, "unit": "container", "default_quantity": 1},
            {"id": "sw-15", "name": "Cream Cheese", "category": "Dairy", "store": "Safeway", "price": 3.49, "unit": "package", "default_quantity": 1},
            {"id": "sw-16", "name": "Sour Cream", "category": "Dairy", "store": "Safeway", "price": 2.99, "unit": "container", "default_quantity": 1},
            {"id": "sw-17", "name": "Heavy Cream", "category": "Dairy", "store": "Safeway", "price": 4.49, "unit": "carton", "default_quantity": 1},
            {"id": "sw-18", "name": "Shredded Cheese", "category": "Dairy", "store": "Safeway", "price": 3.99, "unit": "bag", "default_quantity": 1},
            
            {"id": "sw-19", "name": "Rice", "category": "Pantry", "store": "Safeway", "price": 8.99, "unit": "bag", "default_quantity": 1},
            {"id": "sw-20", "name": "Flour", "category": "Pantry", "store": "Safeway", "price": 4.99, "unit": "bag", "default_quantity": 1},
            {"id": "sw-21", "name": "Sugar", "category": "Pantry", "store": "Safeway", "price": 3.99, "unit": "bag", "default_quantity": 1},
            {"id": "sw-22", "name": "Canned Tomatoes", "category": "Pantry", "store": "Safeway", "price": 1.99, "unit": "can", "default_quantity": 2},
            {"id": "sw-23", "name": "Beans", "category": "Pantry", "store": "Safeway", "price": 1.49, "unit": "can", "default_quantity": 3},
            {"id": "sw-24", "name": "Pasta Sauce", "category": "Pantry", "store": "Safeway", "price": 3.49, "unit": "jar", "default_quantity": 1},
            
            {"id": "sw-25", "name": "Paper Towels", "category": "Household", "store": "Safeway", "price": 12.99, "unit": "pack", "default_quantity": 1},
            {"id": "sw-26", "name": "Dish Soap", "category": "Household", "store": "Safeway", "price": 3.99, "unit": "bottle", "default_quantity": 1},
            {"id": "sw-27", "name": "Laundry Detergent", "category": "Household", "store": "Safeway", "price": 14.99, "unit": "bottle", "default_quantity": 1},
            {"id": "sw-28", "name": "Toilet Paper", "category": "Household", "store": "Safeway", "price": 9.99, "unit": "pack", "default_quantity": 1},
            {"id": "sw-29", "name": "Cleaning Spray", "category": "Household", "store": "Safeway", "price": 4.49, "unit": "bottle", "default_quantity": 1},
            {"id": "sw-30", "name": "Trash Bags", "category": "Household", "store": "Safeway", "price": 7.99, "unit": "box", "default_quantity": 1},
            
            # Additional items
            {"id": "sw-31", "name": "Butter", "category": "Dairy", "store": "Safeway", "price": 4.49, "unit": "package", "default_quantity": 1},
            {"id": "sw-32", "name": "Yogurt", "category": "Dairy", "store": "Safeway", "price": 4.99, "unit": "container", "default_quantity": 1},
            {"id": "sw-33", "name": "Lemon Grass", "category": "Produce", "store": "Safeway", "price": 2.49, "unit": "bunch", "default_quantity": 1},
            {"id": "sw-34", "name": "Ginger", "category": "Produce", "store": "Safeway", "price": 2.99, "unit": "package", "default_quantity": 1},
            {"id": "sw-35", "name": "Cereal Box", "category": "Pantry", "store": "Safeway", "price": 5.49, "unit": "box", "default_quantity": 1},
            {"id": "sw-36", "name": "Milky Chicken", "category": "Meat", "store": "Safeway", "price": 8.99, "unit": "package", "default_quantity": 1},
            {"id": "sw-37", "name": "Tortillas", "category": "Bakery", "store": "Safeway", "price": 3.49, "unit": "package", "default_quantity": 1},
            {"id": "sw-38", "name": "Sour Cream", "category": "Dairy", "store": "Safeway", "price": 3.49, "unit": "container", "default_quantity": 1},
            {"id": "sw-39", "name": "Chicken Strips", "category": "Meat", "store": "Safeway", "price": 8.99, "unit": "package", "default_quantity": 1},
            {"id": "sw-40", "name": "Krusteaz Buttermilk", "category": "Pantry", "store": "Safeway", "price": 4.99, "unit": "box", "default_quantity": 1},
            {"id": "sw-41", "name": "Cilantro", "category": "Produce", "store": "Safeway", "price": 1.49, "unit": "bunch", "default_quantity": 1},
            {"id": "sw-42", "name": "Bread", "category": "Bakery", "store": "Safeway", "price": 3.49, "unit": "loaf", "default_quantity": 1},
        ]
        
        # Populate Costco items
        costco_items = [
            {"id": "co-1", "name": "Kirkland Paper Towels 12-pack", "category": "Bulk Household", "store": "Costco", "price": 19.99, "unit": "pack", "default_quantity": 1},
            {"id": "co-2", "name": "Toilet Paper 30-pack", "category": "Bulk Household", "store": "Costco", "price": 24.99, "unit": "pack", "default_quantity": 1},
            {"id": "co-3", "name": "Trash Bags", "category": "Bulk Household", "store": "Costco", "price": 18.99, "unit": "box", "default_quantity": 1},
            {"id": "co-4", "name": "Laundry Detergent", "category": "Bulk Household", "store": "Costco", "price": 19.99, "unit": "container", "default_quantity": 1},
            {"id": "co-5", "name": "Dish Soap 2-pack", "category": "Bulk Household", "store": "Costco", "price": 9.99, "unit": "pack", "default_quantity": 1},
            
            {"id": "co-6", "name": "Chicken Thighs 5 lbs", "category": "Bulk Meat", "store": "Costco", "price": 14.99, "unit": "package", "default_quantity": 1},
            {"id": "co-7", "name": "Ground Turkey 3 lbs", "category": "Bulk Meat", "store": "Costco", "price": 12.99, "unit": "package", "default_quantity": 1},
            {"id": "co-8", "name": "Salmon 3 lbs", "category": "Bulk Meat", "store": "Costco", "price": 29.99, "unit": "package", "default_quantity": 1},
            
            {"id": "co-9", "name": "Quinoa 5 lbs", "category": "Bulk Pantry", "store": "Costco", "price": 12.99, "unit": "bag", "default_quantity": 1},
            {"id": "co-10", "name": "Olive Oil 2L", "category": "Bulk Pantry", "store": "Costco", "price": 14.99, "unit": "bottle", "default_quantity": 1},
            {"id": "co-11", "name": "Honey 3 lbs", "category": "Bulk Pantry", "store": "Costco", "price": 11.99, "unit": "jar", "default_quantity": 1},
            {"id": "co-12", "name": "Mixed Nuts 3 lbs", "category": "Bulk Pantry", "store": "Costco", "price": 15.99, "unit": "container", "default_quantity": 1},
            {"id": "co-13", "name": "Peanut Butter 2-pack", "category": "Bulk Pantry", "store": "Costco", "price": 9.99, "unit": "pack", "default_quantity": 1},
            
            {"id": "co-14", "name": "Mixed Vegetables", "category": "Bulk Frozen", "store": "Costco", "price": 8.99, "unit": "bag", "default_quantity": 1},
            {"id": "co-15", "name": "Frozen Pizza 4-pack", "category": "Bulk Frozen", "store": "Costco", "price": 14.99, "unit": "pack", "default_quantity": 1},
            {"id": "co-16", "name": "Protein Bars Box", "category": "Bulk Frozen", "store": "Costco", "price": 24.99, "unit": "box", "default_quantity": 1},
            
            # Additional items
            {"id": "co-17", "name": "Dish Soap 3-pack", "category": "Bulk Household", "store": "Costco", "price": 13.99, "unit": "pack", "default_quantity": 1},
            {"id": "co-18", "name": "Frozen Fruit 5 lbs", "category": "Bulk Frozen", "store": "Costco", "price": 10.99, "unit": "bag", "default_quantity": 1},
            {"id": "co-19", "name": "Naan Bread 10-pack", "category": "Bulk Bakery", "store": "Costco", "price": 6.99, "unit": "pack", "default_quantity": 1},
            {"id": "co-20", "name": "Ziplock Bags Variety", "category": "Bulk Household", "store": "Costco", "price": 16.99, "unit": "box", "default_quantity": 1},
            {"id": "co-21", "name": "Snacks Variety Pack", "category": "Bulk Snacks", "store": "Costco", "price": 18.99, "unit": "box", "default_quantity": 1},
            {"id": "co-22", "name": "Shaving Cream 3-pack", "category": "Bulk Personal Care", "store": "Costco", "price": 13.99, "unit": "pack", "default_quantity": 1},
            {"id": "co-23", "name": "Toothpaste 5-pack", "category": "Bulk Personal Care", "store": "Costco", "price": 14.99, "unit": "pack", "default_quantity": 1},
            {"id": "co-24", "name": "Eggs 5 Dozen", "category": "Bulk Dairy", "store": "Costco", "price": 9.99, "unit": "pack", "default_quantity": 1},
            {"id": "co-25", "name": "Pasta Sauce 6-pack", "category": "Bulk Pantry", "store": "Costco", "price": 13.99, "unit": "pack", "default_quantity": 1},
            {"id": "co-26", "name": "Butter 4-pack", "category": "Bulk Dairy", "store": "Costco", "price": 9.99, "unit": "pack", "default_quantity": 1},
            {"id": "co-27", "name": "Olive Oil 3L", "category": "Bulk Pantry", "store": "Costco", "price": 16.99, "unit": "bottle", "default_quantity": 1},
            {"id": "co-28", "name": "Toilet Roll 36-pack", "category": "Bulk Household", "store": "Costco", "price": 27.99, "unit": "pack", "default_quantity": 1},
            {"id": "co-29", "name": "Paper Towels 12-pack", "category": "Bulk Household", "store": "Costco", "price": 21.99, "unit": "pack", "default_quantity": 1},
            {"id": "co-30", "name": "Honey 5 lbs", "category": "Bulk Pantry", "store": "Costco", "price": 13.99, "unit": "jar", "default_quantity": 1},
        ]
        
        # Add items to respective stores
        self.stores["Trader Joe's"] = trader_joes_items
        self.stores["Safeway"] = safeway_items
        self.stores["Costco"] = costco_items
    
    def _load_or_initialize_catalog(self):
        """Load catalog from JSON file or initialize with sample data"""
        if os.path.exists(self.catalog_file):
            try:
                with open(self.catalog_file, 'r') as f:
                    self.stores = json.load(f)
                print(f"✓ Catalog loaded from {self.catalog_file}")
            except Exception as e:
                print(f"Warning: Could not load catalog file: {e}")
                print("Initializing with default sample data...")
                self._initialize_sample_data()
        else:
            print(f"No catalog file found. Creating new catalog at {self.catalog_file}")
            self._initialize_sample_data()
            self._save_catalog()
    
    def _save_catalog(self):
        """Save catalog to JSON file"""
        try:
            with open(self.catalog_file, 'w') as f:
                json.dump(self.stores, f, indent=2)
            print(f"✓ Catalog saved to {self.catalog_file}")
        except Exception as e:
            print(f"Warning: Could not save catalog: {e}")
    
    def get_store_items(self, store_name):
        """Get all items for a specific store"""
        return self.stores.get(store_name, [])
    
    def add_to_shopping_list(self, item_id, quantity=1):
        """Add an item to the shopping list"""
        # Find the item in all stores
        for store_name, items in self.stores.items():
            for item in items:
                if item['id'] == item_id:
                    # Check if item already in shopping list
                    for list_item in self.shopping_list:
                        if list_item['id'] == item_id:
                            list_item['quantity'] += quantity
                            return True
                    # Add new item to shopping list
                    list_item = item.copy()
                    list_item['quantity'] = quantity
                    self.shopping_list.append(list_item)
                    return True
        return False
    
    def remove_from_shopping_list(self, item_id):
        """Remove an item from the shopping list"""
        self.shopping_list = [item for item in self.shopping_list if item['id'] != item_id]
    
    def update_quantity(self, item_id, quantity):
        """Update the quantity of an item in the shopping list"""
        for item in self.shopping_list:
            if item['id'] == item_id:
                item['quantity'] = quantity
                return True
        return False
    
    def get_shopping_list(self):
        """Get the current shopping list"""
        return self.shopping_list
    
    def get_total_cost(self):
        """Calculate the total cost of items in the shopping list"""
        total = sum(item['price'] * item['quantity'] for item in self.shopping_list)
        return round(total, 2)
    
    def get_budget_status(self):
        """Get budget status with warnings"""
        total = self.get_total_cost()
        percentage = (total / self.budget * 100) if self.budget > 0 else 0
        
        if percentage < 80:
            status = "🟢 On track!"
            color = "green"
        elif percentage < 100:
            status = "🟡 Approaching budget limit"
            color = "yellow"
        else:
            over_amount = total - self.budget
            status = f"🔴 Over budget by ${over_amount:.2f}!"
            color = "red"
        
        return {
            "total": total,
            "budget": self.budget,
            "percentage": round(percentage, 1),
            "status": status,
            "color": color,
            "remaining": round(self.budget - total, 2)
        }
    
    def set_budget(self, amount):
        """Set the budget limit"""
        self.budget = float(amount)
    
    def clear_shopping_list(self):
        """Clear all items from the shopping list"""
        self.shopping_list = []
    
    def get_items_by_category(self, store_name, category):
        """Get items filtered by category"""
        items = self.get_store_items(store_name)
        if category == "All":
            return items
        return [item for item in items if item['category'] == category]
    
    def update_catalog_item(self, item_id, name=None, category=None, price=None, unit=None):
        """Update an existing catalog item"""
        # Find the item in all stores
        for store_name, items in self.stores.items():
            for item in items:
                if item['id'] == item_id:
                    # Update fields if provided
                    if name is not None:
                        item['name'] = name
                    if category is not None:
                        item['category'] = category
                    if price is not None:
                        item['price'] = float(price)
                    if unit is not None:
                        item['unit'] = unit
                    
                    # Save to JSON
                    self._save_catalog()
                    return True
        return False
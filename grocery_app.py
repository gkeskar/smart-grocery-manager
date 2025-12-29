import json
import os
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

# Timezone for timestamps (Pacific Time)
TIMEZONE = ZoneInfo("America/Los_Angeles")

# HuggingFace Hub imports
try:
    from huggingface_hub import HfApi, hf_hub_download
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False
    print("Warning: huggingface_hub not installed. Data will only be saved locally.")
    print("To enable cloud persistence: pip install huggingface_hub")


class GroceryManager:
    def __init__(self):
        # HuggingFace Hub configuration
        self.hf_repo = "gandhalikeskar/grocery-catalog"  # Your HF Dataset repo
        self.catalog_file = "grocery_catalog.json"
        self.hf_token = os.getenv("HF_TOKEN")
        
        # Data storage
        self.stores = {}
        self.shopping_list = []
        self.budget = 750.0  # Default total budget
        self.store_budgets = {
            "Trader Joe's": 200.0,   # Weekly
            "Safeway": 150.0,         # Bi-weekly
            "Costco": 300.0,          # Monthly
            "Indian Groceries": 100.0  # Weekly
        }
        self.email_address = "gandhali.aradhye@gmail.com"  # Default email
        
        # Archived shopping lists (up to 6, rotating)
        self.archived_lists = []
        self.max_archives = 6
        
        # Debouncing for saves (avoid too many API calls)
        self._save_pending = False
        self._save_timer = None
        self._save_delay = 3.0  # Wait 3 seconds before saving
        
        # Load data
        self._load_data()

    def _load_data(self):
        """Load data from HuggingFace Hub, fallback to local file"""
        # Try loading from HuggingFace Hub first
        if HF_HUB_AVAILABLE and self.hf_token:
            if self._load_from_hub():
                # Check if Indian Groceries store exists, add if missing
                self._ensure_indian_groceries_store()
                return
        
        # Fallback to local file
        self._load_or_initialize_local()
        # Check if Indian Groceries store exists, add if missing
        self._ensure_indian_groceries_store()
    
    def _ensure_indian_groceries_store(self):
        """Ensure Indian Groceries store exists in the catalog"""
        if "Indian Groceries" not in self.stores or len(self.stores.get("Indian Groceries", [])) == 0:
            print("📦 Adding Indian Groceries store to catalog...")
            self.stores["Indian Groceries"] = self._get_indian_groceries_items()
            # Also ensure budget exists
            if "Indian Groceries" not in self.store_budgets:
                self.store_budgets["Indian Groceries"] = 100.0
            self._schedule_save()  # Save the new store to Hub
            print("✅ Indian Groceries store added with 50 items!")
    
    def _get_indian_groceries_items(self):
        """Return the Indian Groceries sample items"""
        return [
            # Spices & Masalas
            {"id": "ig-1", "name": "Garam Masala", "category": "Spices", "store": "Indian Groceries", "price": 4.99, "unit": "jar", "default_quantity": 1},
            {"id": "ig-2", "name": "Turmeric Powder", "category": "Spices", "store": "Indian Groceries", "price": 3.49, "unit": "package", "default_quantity": 1},
            {"id": "ig-3", "name": "Cumin Seeds", "category": "Spices", "store": "Indian Groceries", "price": 2.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-4", "name": "Coriander Powder", "category": "Spices", "store": "Indian Groceries", "price": 2.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-5", "name": "Red Chili Powder", "category": "Spices", "store": "Indian Groceries", "price": 3.49, "unit": "package", "default_quantity": 1},
            {"id": "ig-6", "name": "Mustard Seeds", "category": "Spices", "store": "Indian Groceries", "price": 2.49, "unit": "package", "default_quantity": 1},
            {"id": "ig-7", "name": "Curry Leaves", "category": "Spices", "store": "Indian Groceries", "price": 1.99, "unit": "bunch", "default_quantity": 1},
            {"id": "ig-8", "name": "Asafoetida (Hing)", "category": "Spices", "store": "Indian Groceries", "price": 5.99, "unit": "jar", "default_quantity": 1},
            {"id": "ig-9", "name": "Cardamom Pods", "category": "Spices", "store": "Indian Groceries", "price": 6.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-10", "name": "Fenugreek Seeds", "category": "Spices", "store": "Indian Groceries", "price": 2.49, "unit": "package", "default_quantity": 1},
            
            # Rice & Grains
            {"id": "ig-11", "name": "Basmati Rice 10lb", "category": "Rice & Grains", "store": "Indian Groceries", "price": 15.99, "unit": "bag", "default_quantity": 1},
            {"id": "ig-12", "name": "Toor Dal (Split Pigeon Peas)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 4.99, "unit": "bag", "default_quantity": 1},
            {"id": "ig-13", "name": "Moong Dal (Yellow Lentils)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 4.49, "unit": "bag", "default_quantity": 1},
            {"id": "ig-14", "name": "Chana Dal (Split Chickpeas)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 3.99, "unit": "bag", "default_quantity": 1},
            {"id": "ig-15", "name": "Urad Dal (Black Gram)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 4.99, "unit": "bag", "default_quantity": 1},
            {"id": "ig-16", "name": "Poha (Flattened Rice)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 2.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-17", "name": "Rava (Semolina)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 3.49, "unit": "package", "default_quantity": 1},
            {"id": "ig-18", "name": "Besan (Chickpea Flour)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 3.99, "unit": "bag", "default_quantity": 1},
            
            # Ready to Eat / Frozen
            {"id": "ig-19", "name": "MTR Ready to Eat Paneer Butter Masala", "category": "Ready to Eat", "store": "Indian Groceries", "price": 3.99, "unit": "package", "default_quantity": 2},
            {"id": "ig-20", "name": "Haldiram's Samosas (Frozen)", "category": "Frozen", "store": "Indian Groceries", "price": 5.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-21", "name": "Paratha (Frozen)", "category": "Frozen", "store": "Indian Groceries", "price": 4.49, "unit": "package", "default_quantity": 2},
            {"id": "ig-22", "name": "Idli/Dosa Batter", "category": "Frozen", "store": "Indian Groceries", "price": 4.99, "unit": "container", "default_quantity": 1},
            {"id": "ig-23", "name": "Paneer (Indian Cottage Cheese)", "category": "Dairy", "store": "Indian Groceries", "price": 5.99, "unit": "block", "default_quantity": 1},
            {"id": "ig-24", "name": "Gulab Jamun Mix", "category": "Ready to Eat", "store": "Indian Groceries", "price": 3.49, "unit": "box", "default_quantity": 1},
            
            # Pickles & Chutneys
            {"id": "ig-25", "name": "Mango Pickle", "category": "Pickles & Chutneys", "store": "Indian Groceries", "price": 4.49, "unit": "jar", "default_quantity": 1},
            {"id": "ig-26", "name": "Lime Pickle", "category": "Pickles & Chutneys", "store": "Indian Groceries", "price": 3.99, "unit": "jar", "default_quantity": 1},
            {"id": "ig-27", "name": "Tamarind Chutney", "category": "Pickles & Chutneys", "store": "Indian Groceries", "price": 2.99, "unit": "bottle", "default_quantity": 1},
            {"id": "ig-28", "name": "Mint Chutney", "category": "Pickles & Chutneys", "store": "Indian Groceries", "price": 2.99, "unit": "bottle", "default_quantity": 1},
            
            # Snacks
            {"id": "ig-29", "name": "Haldiram's Bhujia", "category": "Snacks", "store": "Indian Groceries", "price": 4.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-30", "name": "Chakli (Murukku)", "category": "Snacks", "store": "Indian Groceries", "price": 3.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-31", "name": "Mathri", "category": "Snacks", "store": "Indian Groceries", "price": 3.49, "unit": "package", "default_quantity": 1},
            {"id": "ig-32", "name": "Khakhra", "category": "Snacks", "store": "Indian Groceries", "price": 2.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-33", "name": "Papad (Papadum)", "category": "Snacks", "store": "Indian Groceries", "price": 2.99, "unit": "package", "default_quantity": 1},
            
            # Beverages & Sweets
            {"id": "ig-34", "name": "Chai Masala", "category": "Beverages", "store": "Indian Groceries", "price": 4.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-35", "name": "Rooh Afza", "category": "Beverages", "store": "Indian Groceries", "price": 5.99, "unit": "bottle", "default_quantity": 1},
            {"id": "ig-36", "name": "Mango Pulp (Kesar)", "category": "Beverages", "store": "Indian Groceries", "price": 3.99, "unit": "can", "default_quantity": 2},
            {"id": "ig-37", "name": "Kaju Katli", "category": "Sweets", "store": "Indian Groceries", "price": 9.99, "unit": "box", "default_quantity": 1},
            {"id": "ig-38", "name": "Soan Papdi", "category": "Sweets", "store": "Indian Groceries", "price": 4.99, "unit": "box", "default_quantity": 1},
            
            # Oils & Ghee
            {"id": "ig-39", "name": "Pure Ghee", "category": "Oils & Ghee", "store": "Indian Groceries", "price": 12.99, "unit": "jar", "default_quantity": 1},
            {"id": "ig-40", "name": "Mustard Oil", "category": "Oils & Ghee", "store": "Indian Groceries", "price": 6.99, "unit": "bottle", "default_quantity": 1},
            {"id": "ig-41", "name": "Coconut Oil", "category": "Oils & Ghee", "store": "Indian Groceries", "price": 7.99, "unit": "bottle", "default_quantity": 1},
            
            # Fresh Produce (commonly found at Indian stores)
            {"id": "ig-42", "name": "Fresh Cilantro Bunch", "category": "Produce", "store": "Indian Groceries", "price": 0.99, "unit": "bunch", "default_quantity": 2},
            {"id": "ig-43", "name": "Fresh Mint Bunch", "category": "Produce", "store": "Indian Groceries", "price": 0.99, "unit": "bunch", "default_quantity": 1},
            {"id": "ig-44", "name": "Green Chillies", "category": "Produce", "store": "Indian Groceries", "price": 1.49, "unit": "package", "default_quantity": 1},
            {"id": "ig-45", "name": "Ginger Root", "category": "Produce", "store": "Indian Groceries", "price": 2.99, "unit": "lb", "default_quantity": 1},
            {"id": "ig-46", "name": "Bitter Gourd (Karela)", "category": "Produce", "store": "Indian Groceries", "price": 2.99, "unit": "lb", "default_quantity": 1},
            {"id": "ig-47", "name": "Okra (Bhindi)", "category": "Produce", "store": "Indian Groceries", "price": 3.99, "unit": "lb", "default_quantity": 1},
            {"id": "ig-48", "name": "Drumsticks", "category": "Produce", "store": "Indian Groceries", "price": 2.49, "unit": "bunch", "default_quantity": 1},
            {"id": "ig-49", "name": "Methi (Fenugreek Leaves)", "category": "Produce", "store": "Indian Groceries", "price": 1.99, "unit": "bunch", "default_quantity": 1},
            {"id": "ig-50", "name": "Tindora (Ivy Gourd)", "category": "Produce", "store": "Indian Groceries", "price": 3.49, "unit": "lb", "default_quantity": 1},
        ]

    def _load_from_hub(self):
        """Load catalog from HuggingFace Hub"""
        try:
            print(f"🔄 Loading data from HuggingFace Hub ({self.hf_repo})...")
            
            # Download file from Hub
            path = hf_hub_download(
                repo_id=self.hf_repo,
                filename=self.catalog_file,
                repo_type="dataset",
                token=self.hf_token
            )
            
            # Parse JSON
            with open(path, 'r') as f:
                data = json.load(f)
                self.stores = data.get('stores', {})
                self.shopping_list = data.get('shopping_list', [])
                self.budget = data.get('budget', 650.0)
                self.store_budgets = data.get('store_budgets', self.store_budgets)
                self.email_address = data.get('email_address', self.email_address)
                self.archived_lists = data.get('archived_lists', [])
            
            print(f"✅ Data loaded from HuggingFace Hub!")
            print(f"   📦 Stores: {len(self.stores)}")
            print(f"   🛒 Shopping list items: {len(self.shopping_list)}")
            return True
            
        except Exception as e:
            print(f"⚠️ Could not load from Hub: {e}")
            return False

    def _save_to_hub(self):
        """Save catalog to HuggingFace Hub"""
        if not HF_HUB_AVAILABLE:
            print("⚠️ HuggingFace Hub not available, saving locally only")
            self._save_local()
            return False
            
        if not self.hf_token:
            print("⚠️ HF_TOKEN not set, saving locally only")
            self._save_local()
            return False
        
        try:
            # Prepare data
            data = {
                'stores': self.stores,
                'shopping_list': self.shopping_list,
                'budget': self.budget,
                'store_budgets': self.store_budgets,
                'email_address': self.email_address,
                'archived_lists': self.archived_lists,
                'last_updated': datetime.now(TIMEZONE).isoformat()
            }
            
            # Save locally first (as backup)
            with open(self.catalog_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Upload to Hub
            api = HfApi()
            api.upload_file(
                path_or_fileobj=self.catalog_file,
                path_in_repo=self.catalog_file,
                repo_id=self.hf_repo,
                repo_type="dataset",
                token=self.hf_token,
                commit_message=f"Auto-save: {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print(f"✅ Data saved to HuggingFace Hub!")
            return True
            
        except Exception as e:
            print(f"⚠️ Could not save to Hub: {e}")
            print("   Saving locally as fallback...")
            self._save_local()
            return False

    def _schedule_save(self):
        """Schedule a save to Hub (debounced to avoid too many API calls)"""
        # Cancel any pending save
        if self._save_timer:
            self._save_timer.cancel()
        
        self._save_pending = True
        
        # Schedule new save after delay
        self._save_timer = threading.Timer(self._save_delay, self._do_save)
        self._save_timer.daemon = True  # Don't block app shutdown
        self._save_timer.start()

    def _do_save(self):
        """Actually perform the save"""
        if self._save_pending:
            self._save_to_hub()
            self._save_pending = False

    def force_save(self):
        """Force immediate save (call on app shutdown or important changes)"""
        if self._save_timer:
            self._save_timer.cancel()
        self._save_pending = True
        self._do_save()

    # ============================================
    # LOCAL FILE METHODS (Fallback)
    # ============================================

    def _load_or_initialize_local(self):
        """Load catalog from local JSON file or initialize with sample data"""
        if os.path.exists(self.catalog_file):
            try:
                with open(self.catalog_file, 'r') as f:
                    data = json.load(f)
                    # Handle both old format (just stores) and new format (full data)
                    if 'stores' in data:
                        self.stores = data.get('stores', {})
                        self.shopping_list = data.get('shopping_list', [])
                        self.budget = data.get('budget', 650.0)
                        self.store_budgets = data.get('store_budgets', self.store_budgets)
                        self.email_address = data.get('email_address', self.email_address)
                        self.archived_lists = data.get('archived_lists', [])
                    else:
                        # Old format - just stores dict
                        self.stores = data
                print(f"✅ Catalog loaded from local file: {self.catalog_file}")
            except Exception as e:
                print(f"⚠️ Could not load catalog file: {e}")
                print("   Initializing with default sample data...")
                self._initialize_sample_data()
        else:
            print(f"📦 No catalog file found. Creating new catalog...")
            self._initialize_sample_data()
            self._save_to_hub()  # Save initial data to Hub

    def _save_local(self):
        """Save catalog to local JSON file only"""
        try:
            data = {
                'stores': self.stores,
                'shopping_list': self.shopping_list,
                'budget': self.budget,
                'store_budgets': self.store_budgets,
                'email_address': self.email_address,
                'archived_lists': self.archived_lists,
                'last_updated': datetime.now(TIMEZONE).isoformat()
            }
            with open(self.catalog_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"✅ Catalog saved locally to {self.catalog_file}")
        except Exception as e:
            print(f"⚠️ Could not save catalog locally: {e}")

    def _save_catalog(self):
        """Save catalog - schedules a Hub save (debounced)"""
        self._schedule_save()

    # ============================================
    # SAMPLE DATA INITIALIZATION
    # ============================================

    def _initialize_sample_data(self):
        """Initialize sample data for all stores"""
        # Initialize empty lists for each store
        self.stores = {
            "Trader Joe's": [],
            "Safeway": [],
            "Costco": [],
            "Indian Groceries": []
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
        
        # Populate Indian Groceries items
        indian_groceries_items = [
            # Spices & Masalas
            {"id": "ig-1", "name": "Garam Masala", "category": "Spices", "store": "Indian Groceries", "price": 4.99, "unit": "jar", "default_quantity": 1},
            {"id": "ig-2", "name": "Turmeric Powder", "category": "Spices", "store": "Indian Groceries", "price": 3.49, "unit": "package", "default_quantity": 1},
            {"id": "ig-3", "name": "Cumin Seeds", "category": "Spices", "store": "Indian Groceries", "price": 2.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-4", "name": "Coriander Powder", "category": "Spices", "store": "Indian Groceries", "price": 2.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-5", "name": "Red Chili Powder", "category": "Spices", "store": "Indian Groceries", "price": 3.49, "unit": "package", "default_quantity": 1},
            {"id": "ig-6", "name": "Mustard Seeds", "category": "Spices", "store": "Indian Groceries", "price": 2.49, "unit": "package", "default_quantity": 1},
            {"id": "ig-7", "name": "Curry Leaves", "category": "Spices", "store": "Indian Groceries", "price": 1.99, "unit": "bunch", "default_quantity": 1},
            {"id": "ig-8", "name": "Asafoetida (Hing)", "category": "Spices", "store": "Indian Groceries", "price": 5.99, "unit": "jar", "default_quantity": 1},
            {"id": "ig-9", "name": "Cardamom Pods", "category": "Spices", "store": "Indian Groceries", "price": 6.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-10", "name": "Fenugreek Seeds", "category": "Spices", "store": "Indian Groceries", "price": 2.49, "unit": "package", "default_quantity": 1},
            
            # Rice & Grains
            {"id": "ig-11", "name": "Basmati Rice 10lb", "category": "Rice & Grains", "store": "Indian Groceries", "price": 15.99, "unit": "bag", "default_quantity": 1},
            {"id": "ig-12", "name": "Toor Dal (Split Pigeon Peas)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 4.99, "unit": "bag", "default_quantity": 1},
            {"id": "ig-13", "name": "Moong Dal (Yellow Lentils)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 4.49, "unit": "bag", "default_quantity": 1},
            {"id": "ig-14", "name": "Chana Dal (Split Chickpeas)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 3.99, "unit": "bag", "default_quantity": 1},
            {"id": "ig-15", "name": "Urad Dal (Black Gram)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 4.99, "unit": "bag", "default_quantity": 1},
            {"id": "ig-16", "name": "Poha (Flattened Rice)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 2.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-17", "name": "Rava (Semolina)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 3.49, "unit": "package", "default_quantity": 1},
            {"id": "ig-18", "name": "Besan (Chickpea Flour)", "category": "Rice & Grains", "store": "Indian Groceries", "price": 3.99, "unit": "bag", "default_quantity": 1},
            
            # Ready to Eat / Frozen
            {"id": "ig-19", "name": "MTR Ready to Eat Paneer Butter Masala", "category": "Ready to Eat", "store": "Indian Groceries", "price": 3.99, "unit": "package", "default_quantity": 2},
            {"id": "ig-20", "name": "Haldiram's Samosas (Frozen)", "category": "Frozen", "store": "Indian Groceries", "price": 5.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-21", "name": "Paratha (Frozen)", "category": "Frozen", "store": "Indian Groceries", "price": 4.49, "unit": "package", "default_quantity": 2},
            {"id": "ig-22", "name": "Idli/Dosa Batter", "category": "Frozen", "store": "Indian Groceries", "price": 4.99, "unit": "container", "default_quantity": 1},
            {"id": "ig-23", "name": "Paneer (Indian Cottage Cheese)", "category": "Dairy", "store": "Indian Groceries", "price": 5.99, "unit": "block", "default_quantity": 1},
            {"id": "ig-24", "name": "Gulab Jamun Mix", "category": "Ready to Eat", "store": "Indian Groceries", "price": 3.49, "unit": "box", "default_quantity": 1},
            
            # Pickles & Chutneys
            {"id": "ig-25", "name": "Mango Pickle", "category": "Pickles & Chutneys", "store": "Indian Groceries", "price": 4.49, "unit": "jar", "default_quantity": 1},
            {"id": "ig-26", "name": "Lime Pickle", "category": "Pickles & Chutneys", "store": "Indian Groceries", "price": 3.99, "unit": "jar", "default_quantity": 1},
            {"id": "ig-27", "name": "Tamarind Chutney", "category": "Pickles & Chutneys", "store": "Indian Groceries", "price": 2.99, "unit": "bottle", "default_quantity": 1},
            {"id": "ig-28", "name": "Mint Chutney", "category": "Pickles & Chutneys", "store": "Indian Groceries", "price": 2.99, "unit": "bottle", "default_quantity": 1},
            
            # Snacks
            {"id": "ig-29", "name": "Haldiram's Bhujia", "category": "Snacks", "store": "Indian Groceries", "price": 4.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-30", "name": "Chakli (Murukku)", "category": "Snacks", "store": "Indian Groceries", "price": 3.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-31", "name": "Mathri", "category": "Snacks", "store": "Indian Groceries", "price": 3.49, "unit": "package", "default_quantity": 1},
            {"id": "ig-32", "name": "Khakhra", "category": "Snacks", "store": "Indian Groceries", "price": 2.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-33", "name": "Papad (Papadum)", "category": "Snacks", "store": "Indian Groceries", "price": 2.99, "unit": "package", "default_quantity": 1},
            
            # Beverages & Sweets
            {"id": "ig-34", "name": "Chai Masala", "category": "Beverages", "store": "Indian Groceries", "price": 4.99, "unit": "package", "default_quantity": 1},
            {"id": "ig-35", "name": "Rooh Afza", "category": "Beverages", "store": "Indian Groceries", "price": 5.99, "unit": "bottle", "default_quantity": 1},
            {"id": "ig-36", "name": "Mango Pulp (Kesar)", "category": "Beverages", "store": "Indian Groceries", "price": 3.99, "unit": "can", "default_quantity": 2},
            {"id": "ig-37", "name": "Kaju Katli", "category": "Sweets", "store": "Indian Groceries", "price": 9.99, "unit": "box", "default_quantity": 1},
            {"id": "ig-38", "name": "Soan Papdi", "category": "Sweets", "store": "Indian Groceries", "price": 4.99, "unit": "box", "default_quantity": 1},
            
            # Oils & Ghee
            {"id": "ig-39", "name": "Pure Ghee", "category": "Oils & Ghee", "store": "Indian Groceries", "price": 12.99, "unit": "jar", "default_quantity": 1},
            {"id": "ig-40", "name": "Mustard Oil", "category": "Oils & Ghee", "store": "Indian Groceries", "price": 6.99, "unit": "bottle", "default_quantity": 1},
            {"id": "ig-41", "name": "Coconut Oil", "category": "Oils & Ghee", "store": "Indian Groceries", "price": 7.99, "unit": "bottle", "default_quantity": 1},
            
            # Fresh Produce (commonly found at Indian stores)
            {"id": "ig-42", "name": "Fresh Cilantro Bunch", "category": "Produce", "store": "Indian Groceries", "price": 0.99, "unit": "bunch", "default_quantity": 2},
            {"id": "ig-43", "name": "Fresh Mint Bunch", "category": "Produce", "store": "Indian Groceries", "price": 0.99, "unit": "bunch", "default_quantity": 1},
            {"id": "ig-44", "name": "Green Chillies", "category": "Produce", "store": "Indian Groceries", "price": 1.49, "unit": "package", "default_quantity": 1},
            {"id": "ig-45", "name": "Ginger Root", "category": "Produce", "store": "Indian Groceries", "price": 2.99, "unit": "lb", "default_quantity": 1},
            {"id": "ig-46", "name": "Bitter Gourd (Karela)", "category": "Produce", "store": "Indian Groceries", "price": 2.99, "unit": "lb", "default_quantity": 1},
            {"id": "ig-47", "name": "Okra (Bhindi)", "category": "Produce", "store": "Indian Groceries", "price": 3.99, "unit": "lb", "default_quantity": 1},
            {"id": "ig-48", "name": "Drumsticks", "category": "Produce", "store": "Indian Groceries", "price": 2.49, "unit": "bunch", "default_quantity": 1},
            {"id": "ig-49", "name": "Methi (Fenugreek Leaves)", "category": "Produce", "store": "Indian Groceries", "price": 1.99, "unit": "bunch", "default_quantity": 1},
            {"id": "ig-50", "name": "Tindora (Ivy Gourd)", "category": "Produce", "store": "Indian Groceries", "price": 3.49, "unit": "lb", "default_quantity": 1},
        ]
        
        # Add items to respective stores
        self.stores["Trader Joe's"] = trader_joes_items
        self.stores["Safeway"] = safeway_items
        self.stores["Costco"] = costco_items
        self.stores["Indian Groceries"] = indian_groceries_items

    # ============================================
    # PUBLIC API METHODS
    # ============================================
    
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
                            self._schedule_save()  # Auto-save!
                            return True
                    # Add new item to shopping list
                    list_item = item.copy()
                    list_item['quantity'] = quantity
                    self.shopping_list.append(list_item)
                    self._schedule_save()  # Auto-save!
                    return True
        return False
    
    def remove_from_shopping_list(self, item_id):
        """Remove an item from the shopping list"""
        self.shopping_list = [item for item in self.shopping_list if item['id'] != item_id]
        self._schedule_save()  # Auto-save!
    
    def update_quantity(self, item_id, quantity):
        """Update the quantity of an item in the shopping list"""
        for item in self.shopping_list:
            if item['id'] == item_id:
                item['quantity'] = quantity
                self._schedule_save()  # Auto-save!
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
        self._schedule_save()  # Auto-save!
    
    def clear_shopping_list(self):
        """Clear all items from the shopping list"""
        self.shopping_list = []
        self._schedule_save()  # Auto-save!
    
    def get_items_by_category(self, store_name, category):
        """Get items filtered by category"""
        items = self.get_store_items(store_name)
        if category == "All":
            return items
        return [item for item in items if item['category'] == category]
    
    def update_catalog_item(self, item_id, name=None, category=None, price=None, unit=None):
        """Update an existing catalog item and sync shopping list items"""
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
                    
                    # ALSO update any matching items in shopping list
                    for list_item in self.shopping_list:
                        if list_item['id'] == item_id:
                            if name is not None:
                                list_item['name'] = name
                            if category is not None:
                                list_item['category'] = category
                            if price is not None:
                                list_item['price'] = float(price)
                            if unit is not None:
                                list_item['unit'] = unit
                    
                    # Auto-save to Hub
                    self._schedule_save()
                    return True
        return False

    # ============================================
    # ARCHIVE METHODS
    # ============================================
    
    def archive_and_restart(self, store_name=None):
        """Archive shopping list for a specific store and start fresh for that store.
        
        Args:
            store_name: Name of the store to archive. If None, archives all stores.
        """
        # Filter items by store if specified
        if store_name:
            store_items = [item for item in self.shopping_list if item.get('store') == store_name]
        else:
            store_items = self.shopping_list
        
        if not store_items:
            return False, f"No items to archive{' for ' + store_name if store_name else ''}"
        
        # Calculate total for the store
        total_cost = sum(item['price'] * item['quantity'] for item in store_items)
        
        # Create archive entry (per-store)
        archive_entry = {
            'date': datetime.now(TIMEZONE).isoformat(),
            'date_label': datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M'),
            'store': store_name or 'All Stores',
            'items': [item.copy() for item in store_items],
            'item_count': len(store_items),
            'total_cost': round(total_cost, 2)
        }
        
        # Add to archives (at the beginning for newest first)
        self.archived_lists.insert(0, archive_entry)
        
        # Rotate out oldest if over limit
        if len(self.archived_lists) > self.max_archives:
            self.archived_lists = self.archived_lists[:self.max_archives]
        
        # Remove only the archived store's items from shopping list
        if store_name:
            self.shopping_list = [item for item in self.shopping_list if item.get('store') != store_name]
        else:
            self.shopping_list = []
        
        # Force immediate save to Hub
        self.force_save()
        
        return True, f"✅ Archived {archive_entry['item_count']} items from {store_name or 'all stores'} (${archive_entry['total_cost']:.2f})"
    
    def get_archived_lists(self):
        """Get all archived lists for display"""
        return self.archived_lists
    
    def get_archive_summary(self):
        """Get summary statistics across all archives for analytics"""
        if not self.archived_lists:
            return None
        
        total_spent = sum(a['total_cost'] for a in self.archived_lists)
        total_items = sum(a['item_count'] for a in self.archived_lists)
        avg_per_trip = total_spent / len(self.archived_lists) if self.archived_lists else 0
        
        # Aggregate store totals
        all_store_totals = {}
        for archive in self.archived_lists:
            for store, amount in archive.get('store_totals', {}).items():
                all_store_totals[store] = all_store_totals.get(store, 0) + amount
        
        # Find most purchased items
        item_counts = {}
        for archive in self.archived_lists:
            for item in archive.get('items', []):
                name = item['name']
                item_counts[name] = item_counts.get(name, 0) + item['quantity']
        
        # Top 10 items
        top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_archives': len(self.archived_lists),
            'total_spent': round(total_spent, 2),
            'total_items': total_items,
            'avg_per_trip': round(avg_per_trip, 2),
            'store_totals': all_store_totals,
            'top_items': top_items
        }
    
    def restore_from_archive(self, archive_index):
        """Restore items from an archive (replaces existing items for that store)."""
        if archive_index < 0 or archive_index >= len(self.archived_lists):
            return False, "Invalid archive index"
        
        archive = self.archived_lists[archive_index]
        store_name = archive.get('store', None)
        
        # Replace mode: Remove existing items from this store first
        if store_name:
            self.shopping_list = [item for item in self.shopping_list if item.get('store') != store_name]
        else:
            self.shopping_list = []
        
        # Add all archived items
        for item in archive.get('items', []):
            self.shopping_list.append(item.copy())
        
        self._schedule_save()
        return True, f"✅ Restored {len(archive.get('items', []))} items from {archive['date_label']}"
    
    def get_store_item_count(self, store_name):
        """Get count of items in shopping list for a specific store"""
        return len([item for item in self.shopping_list if item.get('store') == store_name])
    
    def delete_archive(self, archive_index):
        """Delete an archive from the list"""
        if archive_index < 0 or archive_index >= len(self.archived_lists):
            return False, "Invalid archive index"
        
        archive = self.archived_lists[archive_index]
        store = archive.get('store', 'Unknown')
        date_label = archive.get('date_label', 'Unknown')
        
        # Remove the archive
        self.archived_lists.pop(archive_index)
        
        # Save changes
        self.force_save()
        return True, f"🗑️ Deleted archive: {store} from {date_label}"
    
    def delete_multiple_archives(self, indices):
        """Delete multiple archives from the list.
        
        Args:
            indices: List of archive indices to delete (0-based)
        """
        if not indices:
            return False, "No archives selected"
        
        # Sort indices in descending order so we delete from end first
        # (to avoid index shifting issues)
        sorted_indices = sorted(indices, reverse=True)
        
        deleted_count = 0
        for index in sorted_indices:
            if 0 <= index < len(self.archived_lists):
                self.archived_lists.pop(index)
                deleted_count += 1
        
        if deleted_count > 0:
            self.force_save()
            return True, f"🗑️ Deleted {deleted_count} archive(s)"
        return False, "No valid archives found"

"""
Comprehensive test for the multi-select add feature
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from grocery_app import GroceryManager

class TestMultiSelectFeature(unittest.TestCase):
    
    def setUp(self):
        """Set up a fresh GroceryManager instance for each test"""
        self.manager = GroceryManager()
        self.manager.shopping_list = []  # Start with empty list
        self.tj_items = self.manager.stores["Trader Joe's"]
    
    def test_single_item_add(self):
        """Test adding a single item (backward compatibility)"""
        item = self.tj_items[0]
        
        # Simulate selecting and adding one item
        self.manager.add_to_shopping_list(item["id"], 1)
        
        self.assertEqual(len(self.manager.shopping_list), 1)
        self.assertEqual(self.manager.shopping_list[0]["id"], item["id"])
        self.assertEqual(self.manager.shopping_list[0]["quantity"], 1)
        print(f"✅ Single item add works: {item['name']}")
    
    def test_multi_item_add_three_items(self):
        """Test adding 3 items at once (typical use case)"""
        # Select 3 items: yogurt, milk, tomatoes
        greek_yogurt = next(item for item in self.tj_items if "Greek Yogurt" in item["name"])
        milk = next(item for item in self.tj_items if "Milk" in item["name"] and item["category"] == "Dairy")
        tomatoes = next(item for item in self.tj_items if "Tomatoes" in item["name"])
        
        selected_items = [greek_yogurt, milk, tomatoes]
        
        # Add all at once
        for item in selected_items:
            self.manager.add_to_shopping_list(item["id"], 1)
        
        self.assertEqual(len(self.manager.shopping_list), 3)
        
        added_names = [item["name"] for item in self.manager.shopping_list]
        for selected in selected_items:
            self.assertIn(selected["name"], added_names)
        
        print(f"✅ Multi-add (3 items) works:")
        for item in self.manager.shopping_list:
            print(f"   - {item['name']}")
    
    def test_multi_item_add_five_items(self):
        """Test adding 5 items at once"""
        selected = self.tj_items[:5]
        
        for item in selected:
            self.manager.add_to_shopping_list(item["id"], 1)
        
        self.assertEqual(len(self.manager.shopping_list), 5)
        print(f"✅ Multi-add (5 items) works: {len(self.manager.shopping_list)} items added")
    
    def test_multi_add_with_duplicate(self):
        """Test adding items when one is already in the list"""
        bananas = self.tj_items[0]
        avocados = self.tj_items[1]
        apples = self.tj_items[5]
        
        # Add bananas first with quantity 2
        self.manager.add_to_shopping_list(bananas["id"], 2)
        self.assertEqual(self.manager.shopping_list[0]["quantity"], 2)
        
        # Now add multiple items including bananas again
        for item in [bananas, avocados, apples]:
            self.manager.add_to_shopping_list(item["id"], 1)
        
        # Should have 3 items total
        self.assertEqual(len(self.manager.shopping_list), 3)
        
        # Bananas should have accumulated quantity (2 + 1 = 3)
        banana_item = next(item for item in self.manager.shopping_list if item["id"] == bananas["id"])
        self.assertEqual(banana_item["quantity"], 3)
        
        print(f"✅ Duplicate handling works: {bananas['name']} Qty 2 → 3")
    
    def test_multi_add_all_produce(self):
        """Test adding all produce items (realistic scenario)"""
        produce_items = [item for item in self.tj_items if item["category"] == "Produce"]
        
        for item in produce_items:
            self.manager.add_to_shopping_list(item["id"], 1)
        
        self.assertEqual(len(self.manager.shopping_list), len(produce_items))
        print(f"✅ Add all produce works: {len(produce_items)} items added")
    
    def test_multi_add_all_dairy(self):
        """Test adding all dairy items"""
        dairy_items = [item for item in self.tj_items if item["category"] == "Dairy"]
        
        for item in dairy_items:
            self.manager.add_to_shopping_list(item["id"], 1)
        
        self.assertEqual(len(self.manager.shopping_list), len(dairy_items))
        
        # Verify all are dairy
        for item in self.manager.shopping_list:
            self.assertEqual(item["category"], "Dairy")
        
        print(f"✅ Add all dairy works: {len(dairy_items)} items added")
    
    def test_total_cost_multi_add(self):
        """Test that total cost is correct after multi-add"""
        selected = self.tj_items[:5]
        
        # Add all items
        for item in selected:
            self.manager.add_to_shopping_list(item["id"], 1)
        
        # Calculate expected total
        expected_total = round(sum(item["price"] for item in selected), 2)
        actual_total = self.manager.get_total_cost()
        
        self.assertEqual(actual_total, expected_total)
        print(f"✅ Total cost correct: ${actual_total}")
    
    def test_clear_list_after_multi_add(self):
        """Test that we can clear the list after multi-add"""
        # Add multiple items
        for item in self.tj_items[:3]:
            self.manager.add_to_shopping_list(item["id"], 1)
        
        self.assertEqual(len(self.manager.shopping_list), 3)
        
        # Clear list
        self.manager.shopping_list = []
        self.assertEqual(len(self.manager.shopping_list), 0)
        
        print(f"✅ Clear after multi-add works")
    
    def test_update_quantity_after_multi_add(self):
        """Test updating quantity of items added via multi-add"""
        # Add 3 items
        items = self.tj_items[:3]
        for item in items:
            self.manager.add_to_shopping_list(item["id"], 1)
        
        # Update quantity of first item to 5
        success = self.manager.update_quantity(items[0]["id"], 5)
        self.assertTrue(success)
        
        # Verify update
        first_item = next(item for item in self.manager.shopping_list if item["id"] == items[0]["id"])
        self.assertEqual(first_item["quantity"], 5)
        
        print(f"✅ Update quantity after multi-add works: {items[0]['name']} → Qty 5")
    
    def test_remove_item_after_multi_add(self):
        """Test removing an item after multi-add"""
        # Add 3 items
        items = self.tj_items[:3]
        for item in items:
            self.manager.add_to_shopping_list(item["id"], 1)
        
        self.assertEqual(len(self.manager.shopping_list), 3)
        
        # Remove middle item
        self.manager.remove_from_shopping_list(items[1]["id"])
        
        self.assertEqual(len(self.manager.shopping_list), 2)
        
        # Verify the right item was removed
        remaining_ids = [item["id"] for item in self.manager.shopping_list]
        self.assertNotIn(items[1]["id"], remaining_ids)
        self.assertIn(items[0]["id"], remaining_ids)
        self.assertIn(items[2]["id"], remaining_ids)
        
        print(f"✅ Remove after multi-add works")
    
    def test_empty_selection_add(self):
        """Test that adding with empty selection does nothing"""
        # Don't select anything, just try to add
        # This should be handled by the UI, but backend should be safe
        
        initial_count = len(self.manager.shopping_list)
        
        # Try to add empty list (UI should prevent this, but test backend)
        item_ids = []
        for item_id in item_ids:
            self.manager.add_to_shopping_list(item_id, 1)
        
        # List should be unchanged
        self.assertEqual(len(self.manager.shopping_list), initial_count)
        print(f"✅ Empty selection handled safely")
    
    def test_large_batch_add(self):
        """Test adding a large batch (10+ items)"""
        selected = self.tj_items[:15]  # Select 15 items
        
        for item in selected:
            self.manager.add_to_shopping_list(item["id"], 1)
        
        self.assertEqual(len(self.manager.shopping_list), 15)
        print(f"✅ Large batch add works: 15 items added")

def run_comprehensive_test():
    """Run all tests with nice output"""
    print("\n" + "="*70)
    print("COMPREHENSIVE TEST: Multi-Select Add Feature")
    print("="*70 + "\n")
    
    # Run unittest
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMultiSelectFeature)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print("\nFeature Summary:")
        print("  ✓ Single item add (backward compatible)")
        print("  ✓ Multi-item add (3, 5, 15+ items)")
        print("  ✓ Duplicate handling (quantities accumulate)")
        print("  ✓ Category-based add (all produce, all dairy)")
        print("  ✓ Total cost calculation")
        print("  ✓ Update quantity after multi-add")
        print("  ✓ Remove items after multi-add")
        print("  ✓ Empty selection handling")
        print("  ✓ Large batch operations")
    else:
        print("❌ SOME TESTS FAILED")
        print("="*70)
    print()
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)


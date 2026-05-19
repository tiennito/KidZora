#!/usr/bin/env python3
"""Create test orders for the current user to populate the dashboard."""

import sys
from datetime import datetime, timedelta
from uuid import uuid4

# Add the app to path
sys.path.insert(0, '.')

from app import create_app
from app.extensions import supabase_admin as supabase
from flask_login import current_user

app = create_app()

def create_test_orders():
    """Create test orders for the logged-in user."""
    
    with app.app_context():
        # Get a test user ID - we'll use a known test account
        # For now, let's just create orders for a specific buyer_id
        
        # First, let's check if there are any users
        users = supabase.table('auth.users').select('id').limit(1).execute()
        if not users.data:
            print("No users found in database")
            return
        
        # Get a test seller
        sellers = supabase.table('sellers').select('id').limit(1).execute()
        if not sellers.data:
            print("No sellers found in database")
            return
        
        # Get a test product
        products = supabase.table('products').select('id, seller_id').limit(1).execute()
        if not products.data:
            print("No products found in database")
            return
        
        buyer_id = users.data[0]['id']
        seller_id = sellers.data[0]['id']
        product = products.data[0]
        
        print(f"Creating test orders for buyer {buyer_id}")
        
        # Create multiple test orders with different statuses
        statuses = ['unpaid', 'pending', 'shipping', 'completed', 'cancelled']
        
        for i, status in enumerate(statuses):
            order_id = str(uuid4())
            created_at = datetime.utcnow() - timedelta(days=i)
            
            try:
                order_data = {
                    'id': order_id,
                    'buyer_id': buyer_id,
                    'seller_id': seller_id,
                    'total_amount': 1000 + (i * 500),
                    'status': status,
                    'created_at': created_at.isoformat(),
                }
                
                order_result = supabase.table('orders').insert(order_data).execute()
                print(f"✓ Created order with status '{status}': {order_id}")
                
                # Add an order item
                item_id = str(uuid4())
                item_data = {
                    'id': item_id,
                    'order_id': order_id,
                    'product_id': product['id'],
                    'quantity': 1 + (i % 3),
                    'price': 500 + (i * 100),
                }
                
                item_result = supabase.table('order_items').insert(item_data).execute()
                print(f"  └─ Added order item: {item_id}")
                
            except Exception as e:
                print(f"✗ Error creating order with status '{status}': {e}")
        
        print("\nTest orders created successfully!")
        print(f"Visit http://192.168.1.10:5000/buyer/orders to view them")
        print(f"Visit http://192.168.1.10:5000/buyer/dashboard to view  them on the dashboard")

if __name__ == '__main__':
    create_test_orders()

#!/usr/bin/env python3
"""Check what orders exist in the database."""

import sys
sys.path.insert(0, '.')

from app import create_app
from app.extensions import supabase_admin as supabase

app = create_app()

with app.app_context():
    try:
        # Count total orders
        total = supabase.table('orders').select('id', count='exact').execute()
        print(f"Total orders in database: {total.count}")
        
        # Get first 10 orders with all details
        orders = supabase.table('orders').select('*').limit(10).execute()
        
        if orders.data:
            print("\nFirst 10 orders:")
            for order in orders.data:
                print(f"  ID: {order['id'][:8]}")
                print(f"    Buyer: {order.get('buyer_id')}")
                print(f"    Seller: {order.get('seller_id')}")
                print(f"    Status: {order.get('status')}")
                print(f"    Amount: ₱{order.get('total_amount')}")
                print(f"    Created: {order.get('created_at')}")
                print()
        else:
            print("No orders found in database")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

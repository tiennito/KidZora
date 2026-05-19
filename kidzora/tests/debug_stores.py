#!/usr/bin/env python3
"""Debug stores availability"""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from config import Config
from supabase import create_client

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)

try:
    print("Checking stores and orders...\n")
    
    # Count sellers
    sellers_r = supabase.table('sellers').select('id', count='exact').execute()
    seller_count = sellers_r.count or 0
    print(f"Total sellers: {seller_count}")
    
    # Get first few sellers
    if seller_count > 0:
        sellers = supabase.table('sellers').select('id,shop_name').limit(5).execute()
        print(f"First sellers:")
        for s in sellers.data:
            print(f"  • {s['shop_name'][:40]}")
    
    # Count orders
    orders_r = supabase.table('orders').select('id', count='exact').execute()
    order_count = orders_r.count or 0
    print(f"\nTotal orders: {order_count}")
    
    # Check if any orders have a seller_id
    if order_count > 0:
        orders = supabase.table('orders').select('seller_id').limit(10).execute()
        seller_ids = [o['seller_id'] for o in orders.data if o.get('seller_id')]
        print(f"Orders with seller_id: {len(seller_ids)}")
        if seller_ids:
            print(f"Sample seller IDs: {seller_ids[:3]}")
    
    print("\n✓ If sellers exist but no orders, top stores will be empty.")
    print("✓ The best_stores will be empty unless there are orders.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

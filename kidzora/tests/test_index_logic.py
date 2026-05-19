#!/usr/bin/env python3
"""Direct test of index function"""
import sys
sys.path.insert(0, '.')

from app import create_app
from flask_login import login_manager

app = create_app()

with app.app_context():
    # Manually call the index route function
    from app.extensions import supabase_admin
    from collections import Counter
    
    print("Testing index route logic...\n")
    
    # Fetch orders and sellers like the index function does
    try:
        orders_r = supabase_admin.table('orders').select('seller_id').execute()
        orders = orders_r.data or []
        print(f"Orders fetched: {len(orders)}")
        
        s_counts = Counter(o['seller_id'] for o in orders if o.get('seller_id'))
        print(f"Seller counts: {dict(s_counts)}")
        
        top_sids = [sid for sid, _ in s_counts.most_common(6)]
        print(f"Top seller IDs: {top_sids}")
        
        if top_sids:
            sellers_r = supabase_admin.table('sellers').select('id,user_id,shop_name,shop_description') \
                           .in_('id', top_sids).execute()
            print(f"Sellers fetched: {len(sellers_r.data or [])}")
            for s in (sellers_r.data or []):
                print(f"  • {s.get('shop_name')}")
        else:
            print("No top sellers with orders")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

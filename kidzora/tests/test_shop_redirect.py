#!/usr/bin/env python3
"""Test shop URL redirect"""
import requests

# Get a seller ID first
try:
    print("Testing shop page redirect...")
    
    # First, get a seller ID from the home page
    r = requests.get('http://192.168.1.10:5000/', allow_redirects=False, timeout=10)
    print(f"Home page status: {r.status_code}")
    
    # Extract a seller_id from the HTML (Top Stores section)
    if 'buyer.seller_shop' in r.text:
        print("✓ Found seller_shop links in HTML")
        # Try to find a seller ID from the URL
        import re
        match = re.search(r"buyer\.seller_shop.*?seller_id=([a-f0-9-]+)", r.text)
        if match:
            seller_id = match.group(1)
            print(f"✓ Found seller ID: {seller_id}")
            
            # Now test if the shop page redirects
            shop_url = f"http://192.168.1.10:5000/buyer/shop/{seller_id}"
            print(f"\nTest URL: {shop_url}")
            
            r2 = requests.get(shop_url, allow_redirects=False, timeout=10)
            print(f"Status: {r2.status_code}")
            
            if r2.status_code in [301, 302, 303, 307, 308]:
                print(f"⚠️  REDIRECT DETECTED!")
                print(f"   Location: {r2.headers.get('Location')}")
            elif r2.status_code == 200:
                print(f"✓ Shop page loaded successfully")
                if 'shop.html' in r2.text or 'kzp-shop' in r2.text:
                    print(f"✓ Shop template rendered correctly")
                else:
                    print(f"⚠️  Unexpected content in response")
            else:
                print(f"❌ Error: {r2.status_code}")
        else:
            print("Could not extract seller_id from HTML")
    else:
        print("No seller_shop links found in HTML")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

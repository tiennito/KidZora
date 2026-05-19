#!/usr/bin/env python3
"""Test what URL the shop link points to"""
import requests

try:
    print("Fetching home page...\n")
    r = requests.get('http://192.168.1.10:5000/', timeout=10)
    html = r.text
    
    # Look for shop links
    if 'buyer.seller_shop' in html or 'buyer/shop' in html:
        print("✓ Shop links ARE present in the HTML")
        
        # Extract the actual href from the link
        import re
        # Look for href="/buyer/shop/..." 
        matches = re.findall(r'href=["\']([^"\']*buyer[/a-z]*shop[^"\']*)["\']', html)
        if matches:
            print(f"\nFound {len(set(matches))} unique shop URLs:")
            for url in set(matches)[:3]:
                print(f"  → {url}")
        else:
            print("\nNo shop URLs found in hrefs")
    else:
        print("✗ Shop links NOT present in HTML")
        print("  (Top Stores section is still empty)")
        print("\n  You need to RESTART the Flask server!")
        print("  Press Ctrl+C in the terminal running Flask, then run: python run.py")
        
except Exception as e:
    print(f"❌ Error: {e}")

#!/usr/bin/env python3
"""Detailed HTML inspection"""
import requests

try:
    print("Fetching home page...\n")
    r = requests.get('http://192.168.1.10:5000/', timeout=10)
    html = r.text
    
    # Check various sections
    checks = [
        ('Featured Products', 'Featured Products'),
        ('Shop by Category', 'Shop by Category'),
        ('Top Stores', 'Top Stores'),
        ('kzp-prod-card', 'Product card class'),
        ('kzp-store-card', 'Store card class'),
        ('buyer.seller_shop', 'Shop link'),
    ]
    
    for search_text, label in checks:
        count = html.count(search_text)
        if count > 0:
            print(f"✓ {label:20} : {count} found")
        else:
            print(f"✗ {label:20} : NOT FOUND")
    
    print("\n── Sections found in HTML ──")
    
    # Check for section titles
    if 'Top Stores' in html:
        idx = html.find('Top Stores')
        # Show context around it
        start = max(0, idx - 100)
        end = min(len(html), idx + 300)
        print(f"\nTop Stores section context:")
        print(html[start:end])
    else:
        print("⚠️  Top Stores section not found in HTML")
    
except Exception as e:
    print(f"❌ Error: {e}")

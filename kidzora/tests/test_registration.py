#!/usr/bin/env python3
"""
Test script to check registration flow
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

def test_registration_flow():
    """Test the complete registration flow"""
    app = create_app()
    
    with app.test_client() as client:
        print("Testing registration flow...")
        
        # Test Step 1: Account type selection
        print("\n1. Testing account type selection page...")
        response = client.get('/auth/register')
        print(f"   Status: {response.status_code}")
        assert response.status_code == 200
        assert b'Choose Account Type' in response.data
        print("   ✓ Account type selection page works")
        
        # Test Step 2: Terms page with account type
        print("\n2. Testing terms page with account type...")
        for account_type in ['buyer', 'seller', 'rider']:
            response = client.get(f'/auth/register/terms?type={account_type}')
            print(f"   {account_type}: Status {response.status_code}")
            assert response.status_code == 200
            assert account_type.encode() in response.data
            print(f"   ✓ Terms page works for {account_type}")
        
        # Test Step 3: Registration form with account type
        print("\n3. Testing registration form with account type...")
        for account_type in ['buyer', 'seller', 'rider']:
            response = client.get(f'/auth/register/form?type={account_type}')
            print(f"   {account_type}: Status {response.status_code}")
            assert response.status_code == 200
            assert account_type.encode() in response.data
            print(f"   ✓ Registration form works for {account_type}")
        
        # Test POST registration
        print("\n4. Testing POST registration...")
        test_data = {
            'account_type': 'buyer',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password': 'test123',
            'confirm_password': 'test123',
            'phone': '1234567890',
            'building_number': '123',
            'street_name': 'Test Street',
            'city': 'Test City',
            'province': 'Test Province',
            'region': 'Test Region',
            'barangay': 'Test Barangay',
            'postal_code': '1234',
            'country': 'Philippines'
        }
        
        response = client.post('/auth/register/form?type=buyer', data=test_data)
        print(f"   POST Status: {response.status_code}")
        print(f"   Response data: {response.data}")
        
        if response.status_code == 302:
            print("   ✓ Registration redirects correctly (302)")
        else:
            print("   ✗ Registration failed")
            print(f"   Error: {response.data}")

if __name__ == '__main__':
    test_registration_flow()

#!/usr/bin/env python3

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def check_database_state():
    """Check current database state and identify issues"""
    try:
        # Initialize Supabase client
        supabase: Client = create_client(
            supabase_url=os.getenv('SUPABASE_URL'),
            supabase_key=os.getenv('SUPABASE_ANON_KEY')
        )
        
        print("=== DATABASE STATE CHECK ===")
        
        # Check if profiles table exists
        print("1. Checking profiles table...")
        try:
            profiles_result = supabase.table('profiles').select('count').execute()
            if profiles_result.data:
                print(f"   ✓ Profiles table exists with {len(profiles_result.data)} records")
            else:
                print("   ✓ Profiles table exists but is empty")
        except Exception as e:
            print(f"   ✗ Error accessing profiles table: {str(e)}")
            return False
        
        # Check table structure
        print("\n2. Checking table structure...")
        try:
            # Get table info
            columns_to_check = [
                'id', 'email', 'first_name', 'last_name', 'phone', 'role',
                'is_approved', 'is_banned', 'created_at', 'updated_at',
                'building_number', 'street_name', 'city', 'postal_code',
                'country', 'region', 'province', 'barangay', 'newsletter'
            ]
            
            for column in columns_to_check:
                try:
                    result = supabase.table('profiles').select(column).limit(1).execute()
                    if result.data:
                        print(f"   ✓ Column '{column}' exists")
                    else:
                        print(f"   ✗ Column '{column}' missing")
                except Exception as e:
                    print(f"   ? Error checking column '{column}': {str(e)}")
                    
        except Exception as e:
            print(f"   ✗ Error checking table structure: {str(e)}")
        
        # Check auth.users table
        print("\n3. Checking auth.users table...")
        try:
            auth_result = supabase.auth.admin.list_users()
            if auth_result.users:
                print(f"   ✓ Auth users table has {len(auth_result.users)} users")
                
                # Check for specific user
                test_email = "rickssie.hubahibnggodi1@gmail.com"
                user_found = False
                for user in auth_result.users:
                    if user.email == test_email:
                        user_found = True
                        print(f"   ✓ Test user found: {user.email}")
                        print(f"   ✓ User ID: {user.id}")
                        print(f"   ✓ User created: {user.created_at}")
                        break
                
                if not user_found:
                    print(f"   ✗ Test user not found: {test_email}")
            else:
                print("   ✗ No users in auth.users table")
        except Exception as e:
            print(f"   ✗ Error checking auth.users: {str(e)}")
        
        # Test profile lookup for the user
        print("\n4. Testing profile lookup...")
        try:
            # Try to get user by email
            auth_response = supabase.auth.admin.get_user_by_email(test_email)
            if auth_response.user:
                print(f"   ✓ Auth user found: {auth_response.user.email}")
                
                # Now try to find corresponding profile
                profile_result = supabase.table('profiles').select('*').eq('id', auth_response.user.id).execute()
                if profile_result.data:
                    profile = profile_result.data[0]
                    print(f"   ✓ Profile found for user: {profile.get('email', 'N/A')}")
                    print(f"   ✓ Profile ID: {profile.get('id', 'N/A')}")
                    print(f"   ✓ Profile created: {profile.get('created_at', 'N/A')}")
                    
                    # Check all required fields
                    required_fields = ['building_number', 'street_name', 'city', 'region', 'province', 'barangay']
                    missing_fields = []
                    for field in required_fields:
                        if not profile.get(field):
                            missing_fields.append(field)
                    
                    if missing_fields:
                        print(f"   ✗ Missing profile fields: {', '.join(missing_fields)}")
                    else:
                        print("   ✓ All required profile fields present")
                else:
                    print("   ✗ No profile found for auth user")
            else:
                print("   ✗ Auth user not found")
        except Exception as e:
            print(f"   ✗ Error testing profile lookup: {str(e)}")
        
        print("\n=== RECOMMENDATIONS ===")
        print("1. Run the SQL migration in Supabase SQL Editor")
        print("2. Ensure all required columns exist in profiles table")
        print("3. Test registration again after migration")
        
        return True
        
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return False

if __name__ == "__main__":
    check_database_state()

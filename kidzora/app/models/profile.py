from datetime import datetime
from flask_login import UserMixin
from app.extensions import supabase, supabase_admin

class Profile(UserMixin):
    def __init__(self, data):
        self.id = data.get('id')
        self.email = data.get('email')
        self.first_name = data.get('first_name')
        self.last_name = data.get('last_name')
        self.phone = data.get('phone')
        self.role = data.get('role')
        self.is_approved = data.get('is_approved', False)
        self.is_banned = data.get('is_banned', False)
        self.ban_reason = data.get('ban_reason', '')
        self.rejection_reason = data.get('rejection_reason', '')
        self.valid_id_path = data.get('valid_id_path')
        self.verification_status = data.get('verification_status')
        self.verified_by = data.get('verified_by')
        self.verified_at = data.get('verified_at')
        self.building_number = data.get('building_number')
        self.street_name = data.get('street_name')
        self.city = data.get('city')
        self.postal_code = data.get('postal_code')
        self.country = data.get('country')
        self.region = data.get('region')
        self.province = data.get('province')
        self.barangay = data.get('barangay')
        self.newsletter = data.get('newsletter', False)
        
        # Seller-specific fields
        self.business_name = data.get('business_name')
        self.business_type = data.get('business_type')
        self.seller_id_type = data.get('seller_id_type')
        self.seller_id_number = data.get('seller_id_number')
        # Seller document file paths
        self.seller_id_file = data.get('seller_id_file')
        self.business_permit_file = data.get('business_permit_file')
        self.bir_file = data.get('bir_file')
        self.avatar_url = data.get('avatar_url')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
        
    @classmethod
    def create(cls, user_data):
        """Create a new profile — uses service role to bypass RLS."""
        user_data['created_at'] = datetime.utcnow().isoformat()
        user_data['updated_at'] = datetime.utcnow().isoformat()
        
        response = supabase_admin.table('profiles').insert(user_data).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_by_id(cls, user_id):
        """Get profile by ID"""
        response = supabase.table('profiles').select('*').eq('id', user_id).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_by_email(cls, email):
        """Get profile by email"""
        response = supabase.table('profiles').select('*').eq('email', email).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_all(cls, filters=None):
        """Get all profiles with optional filters — uses service role to bypass RLS."""
        query = supabase_admin.table('profiles').select('*')
        
        if filters:
            if 'role' in filters:
                query = query.eq('role', filters['role'])
            if 'is_approved' in filters:
                query = query.eq('is_approved', filters['is_approved'])
            if 'is_banned' in filters:
                query = query.eq('is_banned', filters['is_banned'])
        
        response = query.execute()
        return [cls(data) for data in response.data]
    
    def update(self, update_data):
        """Update profile"""
        update_data['updated_at'] = datetime.utcnow().isoformat()
        response = supabase.table('profiles').update(update_data).eq('id', self.id).execute()
        if response.data:
            # Update self with new data
            for key, value in response.data[0].items():
                setattr(self, key, value)
            return True
        return False
    
    def delete(self):
        """Delete profile"""
        response = supabase.table('profiles').delete().eq('id', self.id).execute()
        return len(response.data) > 0
    
    def get_full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
    
    def is_active(self):
        """Check if user is active (not banned)"""
        return not self.is_banned
    
    def can_access_admin(self):
        """Check if user can access admin panel"""
        return self.role == 'admin' and self.is_approved and not self.is_banned

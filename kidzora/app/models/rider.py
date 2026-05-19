from datetime import datetime
from app.extensions import supabase, supabase_admin

class Rider:
    def __init__(self, data):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.driver_license = data.get('driver_license')
        self.license_expiry = data.get('license_expiry')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
    
    @classmethod
    def create(cls, rider_data):
        """Create a new rider profile"""
        rider_data['created_at'] = datetime.utcnow().isoformat()
        rider_data['updated_at'] = datetime.utcnow().isoformat()
        
        response = supabase.table('riders').insert(rider_data).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_by_user_id(cls, user_id):
        """Get rider by user ID"""
        response = supabase_admin.table('riders').select('*').eq('user_id', user_id).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_all(cls, filters=None):
        """Get all riders with optional filters"""
        query = supabase_admin.table('riders').select('*')
        
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        
        response = query.execute()
        return [cls(data) for data in response.data]
    
    def update(self, update_data):
        """Update rider profile"""
        update_data['updated_at'] = datetime.utcnow().isoformat()
        response = supabase.table('riders').update(update_data).eq('id', self.id).execute()
        if response.data:
            for key, value in response.data[0].items():
                setattr(self, key, value)
            return True
        return False
    
    def delete(self):
        """Delete rider profile"""
        response = supabase.table('riders').delete().eq('id', self.id).execute()
        return len(response.data) > 0

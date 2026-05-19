from datetime import datetime
from app.extensions import supabase, supabase_admin

class Seller:
    def __init__(self, data):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.shop_name = data.get('shop_name')
        self.shop_description = data.get('shop_description')
        self.business_permit = data.get('business_permit')
        self.valid_id = data.get('valid_id')
        self.bank_account = data.get('bank_account')
        self.bank_name = data.get('bank_name')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
    
    @classmethod
    def create(cls, seller_data):
        """Create a new seller profile"""
        seller_data['created_at'] = datetime.utcnow().isoformat()
        seller_data['updated_at'] = datetime.utcnow().isoformat()
        
        response = supabase.table('sellers').insert(seller_data).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_by_user_id(cls, user_id):
        """Get seller by user ID"""
        response = supabase_admin.table('sellers').select('*').eq('user_id', user_id).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_all(cls, filters=None):
        """Get all sellers with optional filters"""
        query = supabase_admin.table('sellers').select('*')
        
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        
        response = query.execute()
        return [cls(data) for data in response.data]
    
    def update(self, update_data):
        """Update seller profile"""
        update_data['updated_at'] = datetime.utcnow().isoformat()
        response = supabase.table('sellers').update(update_data).eq('id', self.id).execute()
        if response.data:
            for key, value in response.data[0].items():
                setattr(self, key, value)
            return True
        return False
    
    def delete(self):
        """Delete seller profile"""
        response = supabase.table('sellers').delete().eq('id', self.id).execute()
        return len(response.data) > 0

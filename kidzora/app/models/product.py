from datetime import datetime
from app.extensions import supabase

class Product:
    def __init__(self, data):
        self.id = data.get('id')
        self.seller_id = data.get('seller_id')
        self.name = data.get('name')
        self.description = data.get('description')
        self.price = data.get('price')
        self.category = data.get('category')
        self.age_group = data.get('age_group')  # 0-2, 3-5, 6-8, 9-12
        self.condition = data.get('condition')  # new, like_new, good, fair
        self.stock_quantity = data.get('stock_quantity')
        self.images = data.get('images', [])  # Array of image URLs
        self.is_active = data.get('is_active', True)
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
    
    @classmethod
    def create(cls, product_data):
        """Create a new product"""
        product_data['created_at'] = datetime.utcnow().isoformat()
        product_data['updated_at'] = datetime.utcnow().isoformat()
        
        response = supabase.table('products').insert(product_data).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_by_id(cls, product_id):
        """Get product by ID"""
        response = supabase.table('products').select('*').eq('id', product_id).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_by_seller(cls, seller_id, filters=None):
        """Get products by seller"""
        query = supabase.table('products').select('*').eq('seller_id', seller_id)
        
        if filters:
            if 'is_active' in filters:
                query = query.eq('is_active', filters['is_active'])
            if 'category' in filters:
                query = query.eq('category', filters['category'])
        
        response = query.execute()
        return [cls(data) for data in response.data]
    
    @classmethod
    def search(cls, search_params):
        """Search products with filters"""
        query = supabase.table('products').select('*').eq('is_active', True)
        
        if 'category' in search_params:
            query = query.eq('category', search_params['category'])
        if 'age_group' in search_params:
            query = query.eq('age_group', search_params['age_group'])
        if 'condition' in search_params:
            query = query.eq('condition', search_params['condition'])
        if 'min_price' in search_params:
            query = query.gte('price', search_params['min_price'])
        if 'max_price' in search_params:
            query = query.lte('price', search_params['max_price'])
        if 'name' in search_params:
            query = query.ilike('name', f"%{search_params['name']}%")
        
        response = query.execute()
        return [cls(data) for data in response.data]
    
    def update(self, update_data):
        """Update product"""
        update_data['updated_at'] = datetime.utcnow().isoformat()
        response = supabase.table('products').update(update_data).eq('id', self.id).execute()
        if response.data:
            for key, value in response.data[0].items():
                setattr(self, key, value)
            return True
        return False
    
    def delete(self):
        """Delete product"""
        response = supabase.table('products').delete().eq('id', self.id).execute()
        return len(response.data) > 0
    
    def decrease_stock(self, quantity):
        """Decrease stock quantity"""
        new_quantity = max(0, self.stock_quantity - quantity)
        return self.update({'stock_quantity': new_quantity})

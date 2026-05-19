from datetime import datetime
from app.extensions import supabase_admin as supabase

class Coupon:
    def __init__(self, data):
        self.id = data.get('id')
        self.code = data.get('code')
        self.description = data.get('description')
        self.discount_type = data.get('discount_type')  # percentage, fixed, free_delivery
        self.discount_value = data.get('discount_value')
        self.min_order_amount = data.get('min_order_amount', 0)
        self.max_discount_amount = data.get('max_discount_amount')
        self.usage_limit = data.get('usage_limit')
        self.usage_count = data.get('usage_count', 0)
        self.applicable_sellers = data.get('applicable_sellers', [])  # Empty array means all sellers
        self.is_active = data.get('is_active', True)
        self.expires_at = data.get('expires_at')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
    
    @classmethod
    def create(cls, coupon_data):
        """Create a new coupon"""
        coupon_data['created_at'] = datetime.utcnow().isoformat()
        coupon_data['updated_at'] = datetime.utcnow().isoformat()
        
        response = supabase.table('coupons').insert(coupon_data).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_by_id(cls, coupon_id):
        """Get coupon by ID"""
        response = supabase.table('coupons').select('*').eq('id', coupon_id).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_by_code(cls, code):
        """Get coupon by code"""
        response = supabase.table('coupons').select('*').eq('code', code.upper()).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_all(cls, filters=None):
        """Get all coupons with optional filters"""
        query = supabase.table('coupons').select('*')
        
        if filters:
            if 'is_active' in filters:
                query = query.eq('is_active', filters['is_active'])
        
        response = query.execute()
        return [cls(data) for data in response.data]
    
    def update(self, update_data):
        """Update coupon"""
        update_data['updated_at'] = datetime.utcnow().isoformat()
        response = supabase.table('coupons').update(update_data).eq('id', self.id).execute()
        if response.data:
            for key, value in response.data[0].items():
                setattr(self, key, value)
            return True
        return False
    
    def delete(self):
        """Delete coupon"""
        response = supabase.table('coupons').delete().eq('id', self.id).execute()
        return len(response.data) > 0
    
    def is_valid(self, order_amount=None, seller_id=None):
        """Check if coupon is valid"""
        if not self.is_active:
            return False, "Coupon is inactive"
        
        if self.expires_at and datetime.fromisoformat(self.expires_at.replace('Z', '+00:00').replace('+00:00+00:00','+00:00')) < datetime.now().astimezone():
            return False, "Coupon has expired"
        
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False, "Coupon usage limit reached"
        
        if order_amount and self.min_order_amount and order_amount < self.min_order_amount:
            return False, f"Minimum order amount of {self.min_order_amount} required"
        
        if seller_id and self.applicable_sellers and seller_id not in self.applicable_sellers:
            return False, "Coupon not applicable for this seller"
        
        return True, "Valid"
    
    def calculate_discount(self, order_amount, delivery_fee=0):
        """Calculate discount amount. delivery_fee used for free_delivery type."""
        if self.discount_type == 'free_delivery':
            return float(delivery_fee)
        elif self.discount_type == 'percentage':
            discount = float(order_amount) * (float(self.discount_value) / 100)
            if self.max_discount_amount:
                discount = min(discount, float(self.max_discount_amount))
        else:  # fixed
            discount = min(float(self.discount_value), float(order_amount))
        
        return discount
    
    def use_coupon(self):
        """Increment usage count"""
        return self.update({'usage_count': self.usage_count + 1})

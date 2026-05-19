from datetime import datetime
from app.extensions import supabase

class Order:
    def __init__(self, data):
        self.id = data.get('id')
        self.buyer_id = data.get('buyer_id')
        self.seller_id = data.get('seller_id')
        self.rider_id = data.get('rider_id')
        self.items = data.get('items', [])  # Array of product objects with quantity
        self.subtotal = data.get('subtotal')
        self.delivery_fee = data.get('delivery_fee')
        self.discount_amount = data.get('discount_amount')
        self.total_amount = data.get('total_amount')
        self.commission = data.get('commission')
        self.seller_earnings = data.get('seller_earnings')
        self.delivery_address = data.get('delivery_address')
        self.status = data.get('status')  # pending, confirmed, preparing, ready_for_pickup, out_for_delivery, delivered, cancelled
        self.payment_status = data.get('payment_status')  # pending, paid, refunded
        self.payment_method = data.get('payment_method')
        self.rider_assigned_at = data.get('rider_assigned_at')
        self.delivered_at = data.get('delivered_at')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
    
    @classmethod
    def create(cls, order_data):
        """Create a new order"""
        order_data['created_at'] = datetime.utcnow().isoformat()
        order_data['updated_at'] = datetime.utcnow().isoformat()
        
        response = supabase.table('orders').insert(order_data).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_by_id(cls, order_id):
        """Get order by ID"""
        response = supabase.table('orders').select('*').eq('id', order_id).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_by_buyer(cls, buyer_id, filters=None):
        """Get orders by buyer"""
        query = supabase.table('orders').select('*').eq('buyer_id', buyer_id)
        
        if filters:
            if 'status' in filters:
                query = query.eq('status', filters['status'])
        
        response = query.execute()
        return [cls(data) for data in response.data]
    
    @classmethod
    def get_by_seller(cls, seller_id, filters=None):
        """Get orders by seller"""
        query = supabase.table('orders').select('*').eq('seller_id', seller_id)
        
        if filters:
            if 'status' in filters:
                query = query.eq('status', filters['status'])
        
        response = query.execute()
        return [cls(data) for data in response.data]
    
    @classmethod
    def get_by_rider(cls, rider_id, filters=None):
        """Get orders by rider"""
        query = supabase.table('orders').select('*').eq('rider_id', rider_id)
        
        if filters:
            if 'status' in filters:
                query = query.eq('status', filters['status'])
        
        response = query.execute()
        return [cls(data) for data in response.data]
    
    def update(self, update_data):
        """Update order"""
        update_data['updated_at'] = datetime.utcnow().isoformat()
        response = supabase.table('orders').update(update_data).eq('id', self.id).execute()
        if response.data:
            for key, value in response.data[0].items():
                setattr(self, key, value)
            return True
        return False
    
    def assign_rider(self, rider_id):
        """Assign rider to order"""
        return self.update({
            'rider_id': rider_id,
            'rider_assigned_at': datetime.utcnow().isoformat(),
            'status': 'out_for_delivery'
        })
    
    def mark_delivered(self):
        """Mark order as delivered"""
        return self.update({
            'status': 'delivered',
            'delivered_at': datetime.utcnow().isoformat()
        })
    
    def cancel(self):
        """Cancel order"""
        return self.update({'status': 'cancelled'})

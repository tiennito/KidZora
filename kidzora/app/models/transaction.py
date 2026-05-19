from datetime import datetime
from app.extensions import supabase_admin as supabase
from app.utils.settings import get_commission_rate


class _Row:
    """Lightweight row object so templates can use dot-notation."""
    __slots__ = ('order_id', 'seller_id', 'amount', 'commission_amount',
                 'seller_earnings', 'status', 'created_at')
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class Transaction:
    def __init__(self, data):
        self.id = data.get('id')
        self.order_id = data.get('order_id')
        self.seller_id = data.get('seller_id')
        self.amount = data.get('amount')
        self.commission_amount = data.get('commission_amount')
        self.seller_earnings = data.get('seller_earnings')
        self.type = data.get('type')
        self.status = data.get('status')
        self.payout_reference = data.get('payout_reference')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')

    @classmethod
    def create(cls, transaction_data):
        """Create a new transaction record."""
        transaction_data['created_at'] = datetime.utcnow().isoformat()
        transaction_data['updated_at'] = datetime.utcnow().isoformat()
        try:
            response = supabase.table('transactions').insert(transaction_data).execute()
            if response.data:
                return cls(response.data[0])
        except Exception as e:
            print(f'Transaction.create error: {e}')
        return None

    @classmethod
    def get_by_id(cls, transaction_id):
        response = supabase.table('transactions').select('*').eq('id', transaction_id).execute()
        if response.data:
            return cls(response.data[0])
        return None

    @classmethod
    def get_by_seller(cls, seller_id, filters=None):
        query = supabase.table('transactions').select('*').eq('seller_id', seller_id)
        if filters:
            if 'type' in filters:
                query = query.eq('type', filters['type'])
            if 'status' in filters:
                query = query.eq('status', filters['status'])
        response = query.execute()
        return [cls(data) for data in response.data]

    @classmethod
    def get_commission_summary(cls, start_date=None, end_date=None):
        """
        Compute commission summary directly from completed orders.
        Uses the pre-computed commission / seller_earnings columns on the orders
        table; falls back to the current runtime commission setting if null.
        """
        query = (
            supabase.table('orders')
            .select('id, total_amount, commission, seller_earnings, seller_id, updated_at, created_at')
            .eq('status', 'completed')
        )
        if start_date:
            query = query.gte('updated_at', start_date)
        if end_date:
            query = query.lte('updated_at', end_date)

        try:
            orders = query.order('updated_at', desc=True).execute().data or []
        except Exception as e:
            print(f'get_commission_summary error: {e}')
            orders = []

        rows = []
        total_commission = 0.0
        total_earnings   = 0.0
        commission_rate = get_commission_rate()

        for o in orders:
            amount     = float(o.get('total_amount') or 0)
            commission = float(o.get('commission') or 0) or round(amount * commission_rate, 2)
            earnings   = float(o.get('seller_earnings') or 0) or round(amount - commission, 2)
            total_commission += commission
            total_earnings   += earnings
            rows.append({
                'order_id':          o.get('id', ''),
                'seller_id':         o.get('seller_id') or '',
                'amount':            amount,
                'commission_amount': commission,
                'seller_earnings':   earnings,
                'status':            'completed',
                'created_at':        o.get('updated_at') or o.get('created_at', ''),
            })

        return {
            'total_commission':  round(total_commission, 2),
            'total_earnings':    round(total_earnings, 2),
            'transaction_count': len(rows),
            'transactions':      rows,
        }

    def update(self, update_data):
        update_data['updated_at'] = datetime.utcnow().isoformat()
        response = supabase.table('transactions').update(update_data).eq('id', self.id).execute()
        if response.data:
            for key, value in response.data[0].items():
                setattr(self, key, value)
            return True
        return False

    def complete(self):
        return self.update({'status': 'completed'})

    def fail(self):
        return self.update({'status': 'failed'})

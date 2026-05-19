from datetime import datetime

from app.extensions import supabase_admin as supabase


class DeliveryZone:
    """Delivery fee zone backed by the delivery_zones table."""

    table = 'delivery_zones'

    def __init__(self, data):
        self.id = data.get('id')
        self.location_name = data.get('location_name')
        self.delivery_fee = data.get('delivery_fee')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')

    @staticmethod
    def normalize_location_name(value: str) -> str:
        return ' '.join((value or '').strip().lower().split())

    @classmethod
    def _now(cls):
        return datetime.utcnow().isoformat()

    @classmethod
    def get_all(cls):
        response = supabase.table(cls.table).select('*').order('location_name').execute()
        return [cls(row) for row in (response.data or [])]

    @classmethod
    def get_by_id(cls, zone_id):
        response = supabase.table(cls.table).select('*').eq('id', zone_id).execute()
        if response.data:
            return cls(response.data[0])
        return None

    @classmethod
    def find_by_location_name(cls, location_name: str):
        target = cls.normalize_location_name(location_name)
        if not target:
            return None
        response = supabase.table(cls.table).select('*').execute()
        for row in response.data or []:
            if cls.normalize_location_name(row.get('location_name')) == target:
                return cls(row)
        return None

    @classmethod
    def create(cls, data):
        payload = {
            'location_name': (data.get('location_name') or '').strip(),
            'delivery_fee': float(data.get('delivery_fee') or 0),
            'created_at': cls._now(),
            'updated_at': cls._now(),
        }
        response = supabase.table(cls.table).insert(payload).execute()
        if response.data:
            return cls(response.data[0])
        return None

    def update(self, data):
        payload = {}
        if 'location_name' in data:
            payload['location_name'] = (data.get('location_name') or '').strip()
        if 'delivery_fee' in data:
            payload['delivery_fee'] = float(data.get('delivery_fee') or 0)
        payload['updated_at'] = self._now()

        response = supabase.table(self.table).update(payload).eq('id', self.id).execute()
        if response.data:
            for key, value in response.data[0].items():
                setattr(self, key, value)
            return True
        return False

    def delete(self):
        response = supabase.table(self.table).delete().eq('id', self.id).execute()
        return bool(response.data)

    def to_dict(self):
        return {
            'id': self.id,
            'locationName': self.location_name,
            'deliveryFee': float(self.delivery_fee or 0),
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
        }

from datetime import datetime
from app.extensions import supabase

class Message:
    def __init__(self, data):
        self.id = data.get('id')
        self.sender_id = data.get('sender_id')
        self.receiver_id = data.get('receiver_id')
        self.content = data.get('content')
        self.message_type = data.get('message_type', 'text')  # text, image, file
        self.is_read = data.get('is_read', False)
        self.created_at = data.get('created_at')
    
    @classmethod
    def create(cls, message_data):
        """Create a new message"""
        message_data['created_at'] = datetime.utcnow().isoformat()
        
        response = supabase.table('messages').insert(message_data).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_conversation(cls, user1_id, user2_id, limit=50):
        """Get conversation between two users"""
        response = supabase.table('messages').select('*').or_(
            f"and(sender_id.eq.{user1_id},receiver_id.eq.{user2_id}),and(sender_id.eq.{user2_id},receiver_id.eq.{user1_id})"
        ).order('created_at', desc=False).limit(limit).execute()
        
        return [cls(data) for data in response.data]
    
    @classmethod
    def get_user_conversations(cls, user_id):
        """Get all conversations for a user"""
        response = supabase.rpc('get_user_conversations', {'current_user_id': user_id}).execute()
        return response.data
    
    @classmethod
    def get_unread_count(cls, user_id):
        """Get unread message count for user"""
        response = supabase.table('messages').select('id').eq('receiver_id', user_id).eq('is_read', False).execute()
        return len(response.data)
    
    def mark_as_read(self):
        """Mark message as read"""
        response = supabase.table('messages').update({'is_read': True}).eq('id', self.id).execute()
        if response.data:
            self.is_read = True
            return True
        return False
    
    def delete(self):
        """Delete message"""
        response = supabase.table('messages').delete().eq('id', self.id).execute()
        return len(response.data) > 0

from datetime import datetime
from app.extensions import supabase_admin as supabase
import json

class Report:
    def __init__(self, data):
        self.id = data.get('id')
        self.report_type = data.get('report_type')  # sales, users, commissions, activity
        self.title = data.get('title')
        self.description = data.get('description')
        self.parameters = data.get('parameters', {})  # JSON object of report parameters
        self.data = data.get('data', {})  # JSON object of report data
        self.generated_by = data.get('generated_by')  # Admin user ID
        self.start_date = data.get('start_date')
        self.end_date = data.get('end_date')
        self.created_at = data.get('created_at')
    
    @classmethod
    def create(cls, report_data):
        """Create a new report"""
        report_data['created_at'] = datetime.utcnow().isoformat()
        
        response = supabase.table('reports').insert(report_data).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_by_id(cls, report_id):
        """Get report by ID"""
        response = supabase.table('reports').select('*').eq('id', report_id).execute()
        if response.data:
            return cls(response.data[0])
        return None
    
    @classmethod
    def get_all(cls, filters=None):
        """Get all reports with optional filters"""
        query = supabase.table('reports').select('*')
        
        if filters:
            if 'report_type' in filters:
                query = query.eq('report_type', filters['report_type'])
            if 'generated_by' in filters:
                query = query.eq('generated_by', filters['generated_by'])
        
        response = query.order('created_at', desc=True).execute()
        return [cls(data) for data in response.data]
    
    def delete(self):
        """Delete report"""
        response = supabase.table('reports').delete().eq('id', self.id).execute()
        return len(response.data) > 0
    
    def get_data_dict(self):
        """Get report data as dictionary"""
        if isinstance(self.data, str):
            return json.loads(self.data)
        return self.data
    
    def get_parameters_dict(self):
        """Get report parameters as dictionary"""
        if isinstance(self.parameters, str):
            return json.loads(self.parameters)
        return self.parameters

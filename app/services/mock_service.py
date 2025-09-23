"""
Mock data service for development and testing
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random
from faker import Faker

fake = Faker('zh_TW')


class MockDataService:
    """Service for generating mock data"""
    
    _instance: Optional['MockDataService'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.fake = fake
            self.initialized = True
    
    def generate_users(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate mock user data"""
        users = []
        roles = ["counselor", "supervisor", "admin"]
        
        for i in range(1, count + 1):
            users.append({
                "id": i,
                "email": f"user{i}@example.com",
                "name": self.fake.name(),
                "role": random.choice(roles),
                "created_at": self.fake.date_time_this_year().isoformat()
            })
        
        return users
    
    def generate_sessions(self, count: int = 20) -> List[Dict[str, Any]]:
        """Generate mock counseling sessions"""
        sessions = []
        statuses = ["scheduled", "in_progress", "completed", "cancelled"]
        
        for i in range(1, count + 1):
            created = self.fake.date_time_this_month()
            sessions.append({
                "id": i,
                "counselor_id": random.randint(1, 5),
                "counselor_name": self.fake.name(),
                "client_id": random.randint(1, 10),
                "client_name": self.fake.name(),
                "room_number": f"{random.choice(['A', 'B', 'C'])}{random.randint(100, 300)}",
                "status": random.choice(statuses),
                "duration_minutes": random.randint(30, 90),
                "created_at": created.isoformat(),
                "scheduled_at": (created + timedelta(days=random.randint(1, 7))).isoformat()
            })
        
        return sessions
    
    def generate_reports(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate mock reports"""
        reports = []
        statuses = ["draft", "pending_review", "approved", "rejected"]
        
        for i in range(1, count + 1):
            reports.append({
                "id": i,
                "session_id": random.randint(1, 20),
                "counselor_id": random.randint(1, 5),
                "status": random.choice(statuses),
                "summary": self.fake.text(max_nb_chars=200),
                "recommendations": self.fake.text(max_nb_chars=300),
                "created_at": self.fake.date_time_this_month().isoformat(),
                "updated_at": self.fake.date_time_this_week().isoformat()
            })
        
        return reports
    
    def generate_transcription(self, session_id: int) -> Dict[str, Any]:
        """Generate mock transcription for a session"""
        return {
            "id": session_id,
            "session_id": session_id,
            "original_text": self.fake.text(max_nb_chars=1000),
            "anonymized_text": self.fake.text(max_nb_chars=1000),
            "duration_seconds": random.randint(1800, 5400),
            "word_count": random.randint(500, 2000),
            "created_at": datetime.now().isoformat()
        }
    
    def generate_job(self, job_type: str = "transcription") -> Dict[str, Any]:
        """Generate mock job/task"""
        statuses = ["queued", "processing", "completed", "failed"]
        job_id = self.fake.uuid4()
        
        return {
            "job_id": job_id,
            "type": job_type,
            "status": random.choice(statuses),
            "progress": random.randint(0, 100),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "estimated_completion": (datetime.now() + timedelta(minutes=random.randint(1, 10))).isoformat()
        }
    
    def generate_pipeline_stages(self) -> List[Dict[str, Any]]:
        """Generate pipeline stages"""
        stages = [
            {"id": 1, "name": "音訊上傳", "description": "Upload audio file", "status": "completed"},
            {"id": 2, "name": "語音轉文字", "description": "Transcribe audio to text", "status": "completed"},
            {"id": 3, "name": "文字脫敏", "description": "Anonymize sensitive information", "status": "processing"},
            {"id": 4, "name": "AI 分析", "description": "AI analysis and insights", "status": "pending"},
            {"id": 5, "name": "報告生成", "description": "Generate final report", "status": "pending"}
        ]
        return stages
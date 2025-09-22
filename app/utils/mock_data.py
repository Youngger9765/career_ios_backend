from faker import Faker
from datetime import datetime, timedelta
from typing import Dict, Any, List
import random
import uuid
from app.models.user import UserRole
from app.models.case import CaseStatus
from app.models.job import JobType, JobStatus
from app.models.report import ReportStatus
from app.models.reminder import ReminderType, ReminderStatus

fake = Faker('zh_TW')


class MockDataGenerator:
    """Generate mock data for testing and demo"""
    
    @staticmethod
    def generate_user() -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "email": fake.email(),
            "username": fake.user_name(),
            "full_name": fake.name(),
            "role": random.choice(list(UserRole)),
            "is_active": True,
            "created_at": datetime.now().isoformat(),
        }
    
    @staticmethod
    def generate_visitor() -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "code": f"V{random.randint(10000, 99999)}",
            "nickname": fake.first_name(),
            "age_range": random.choice(["20-25", "25-30", "30-35", "35-40", "40-45"]),
            "gender": random.choice(["男", "女", "不願透露"]),
            "tags": random.sample(["職涯探索", "工作壓力", "人際關係", "生涯轉換", "焦慮", "憂鬱"], k=3),
            "notes": fake.text(max_nb_chars=200),
            "created_at": datetime.now().isoformat(),
        }
    
    @staticmethod
    def generate_case() -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "case_number": f"C{datetime.now().year}{random.randint(1000, 9999)}",
            "counselor_id": str(uuid.uuid4()),
            "visitor_id": str(uuid.uuid4()),
            "status": random.choice(list(CaseStatus)),
            "summary": fake.text(max_nb_chars=300),
            "goals": fake.text(max_nb_chars=200),
            "created_at": datetime.now().isoformat(),
        }
    
    @staticmethod
    def generate_session(case_id: str = None) -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "case_id": case_id or str(uuid.uuid4()),
            "session_number": random.randint(1, 10),
            "session_date": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
            "duration_minutes": random.randint(30, 90),
            "room_number": f"R{random.randint(101, 110)}",
            "notes": fake.text(max_nb_chars=500),
            "key_points": fake.text(max_nb_chars=300),
            "audio_file_path": f"gs://mock-bucket/audio_{uuid.uuid4()}.m4a",
            "transcript_file_path": f"gs://mock-bucket/transcript_{uuid.uuid4()}.txt",
            "created_at": datetime.now().isoformat(),
        }
    
    @staticmethod
    def generate_job(session_id: str = None) -> Dict[str, Any]:
        job_type = random.choice(list(JobType))
        status = random.choice(list(JobStatus))
        
        job = {
            "id": str(uuid.uuid4()),
            "session_id": session_id or str(uuid.uuid4()),
            "job_type": job_type,
            "status": status,
            "retry_count": random.randint(0, 3),
            "created_at": datetime.now().isoformat(),
        }
        
        if status in [JobStatus.PROCESSING, JobStatus.COMPLETED, JobStatus.FAILED]:
            job["started_at"] = (datetime.now() - timedelta(minutes=random.randint(1, 30))).isoformat()
        
        if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            job["completed_at"] = datetime.now().isoformat()
        
        if status == JobStatus.FAILED:
            job["error_message"] = random.choice([
                "音訊檔案格式不支援",
                "轉錄服務暫時無法使用",
                "檔案大小超過限制",
                "網路連線中斷",
            ])
        
        if status == JobStatus.COMPLETED:
            job["output_data"] = {
                "result": "處理完成",
                "file_path": f"gs://mock-bucket/output_{uuid.uuid4()}.json"
            }
        
        return job
    
    @staticmethod
    def generate_transcript() -> str:
        """Generate mock counseling session transcript"""
        templates = [
            "諮商師：您好，今天想談談什麼呢？\n來訪者：最近工作壓力很大，不知道該不該換工作。",
            "諮商師：上次我們談到您的職涯規劃，這週有什麼新的想法嗎？\n來訪者：我開始思考自己真正想要的是什麼。",
            "諮商師：聽起來您對目前的狀況感到困擾，能多說一些嗎？\n來訪者：我覺得自己好像卡住了，不知道該往哪個方向走。",
        ]
        return random.choice(templates) + "\n\n" + fake.text(max_nb_chars=1000)
    
    @staticmethod
    def generate_report(session_id: str = None) -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "session_id": session_id or str(uuid.uuid4()),
            "created_by_id": str(uuid.uuid4()),
            "version": 1,
            "status": random.choice(list(ReportStatus)),
            "summary": f"本次會談主要討論了來訪者的{random.choice(['職涯困擾', '工作壓力', '生涯規劃', '人際關係'])}議題。",
            "analysis": fake.text(max_nb_chars=500),
            "recommendations": fake.text(max_nb_chars=400),
            "action_items": [
                {"item": "探索個人價值觀與職涯目標", "priority": "high"},
                {"item": "練習壓力管理技巧", "priority": "medium"},
                {"item": "建立支持系統", "priority": "low"},
            ],
            "ai_model": "gpt-4",
            "prompt_tokens": random.randint(500, 2000),
            "completion_tokens": random.randint(200, 800),
            "created_at": datetime.now().isoformat(),
        }
    
    @staticmethod
    def generate_reminder(case_id: str = None) -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "case_id": case_id or str(uuid.uuid4()),
            "reminder_type": random.choice(list(ReminderType)),
            "status": random.choice(list(ReminderStatus)),
            "title": random.choice([
                "下次會談時間",
                "追蹤個案狀況",
                "完成評估報告",
                "回顧治療計畫",
            ]),
            "description": fake.text(max_nb_chars=200),
            "due_date": (datetime.now() + timedelta(days=random.randint(1, 30))).isoformat(),
            "is_sent": random.choice([True, False]),
            "created_at": datetime.now().isoformat(),
        }
    
    @staticmethod
    def generate_pipeline_status() -> Dict[str, Any]:
        """Generate mock pipeline processing status"""
        return {
            "session_id": str(uuid.uuid4()),
            "pipeline_id": str(uuid.uuid4()),
            "steps": [
                {
                    "name": "音訊上傳",
                    "status": "completed",
                    "started_at": (datetime.now() - timedelta(minutes=10)).isoformat(),
                    "completed_at": (datetime.now() - timedelta(minutes=9)).isoformat(),
                    "details": {"file_size": "45MB", "format": "m4a"}
                },
                {
                    "name": "語音轉文字",
                    "status": "completed",
                    "started_at": (datetime.now() - timedelta(minutes=9)).isoformat(),
                    "completed_at": (datetime.now() - timedelta(minutes=7)).isoformat(),
                    "details": {"duration": "45:30", "words": 5420}
                },
                {
                    "name": "文字脫敏",
                    "status": "completed",
                    "started_at": (datetime.now() - timedelta(minutes=7)).isoformat(),
                    "completed_at": (datetime.now() - timedelta(minutes=6)).isoformat(),
                    "details": {"masked_items": 3}
                },
                {
                    "name": "AI 分析",
                    "status": "processing",
                    "started_at": (datetime.now() - timedelta(minutes=6)).isoformat(),
                    "progress": 75,
                    "details": {"model": "gpt-4", "tokens_processed": 3200}
                },
                {
                    "name": "報告生成",
                    "status": "pending",
                    "estimated_start": (datetime.now() + timedelta(minutes=2)).isoformat()
                }
            ],
            "overall_progress": 65,
            "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat()
        }


mock_generator = MockDataGenerator()
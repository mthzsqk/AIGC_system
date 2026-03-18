
import json
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict
from ..schemas import ActivityPlan, EvaluationData

class RecordService:
    def __init__(self, data_dir: str = None):
        if data_dir:
            self.data_dir = data_dir
        else:
            # Robustly find knowledge_base directory relative to this file
            self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge_base")
            
        self.data_file = os.path.join(self.data_dir, "user_records.json")
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _load_records(self) -> List[Dict]:
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading records: {e}")
            return []

    def _save_records(self, records: List[Dict]):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving records: {e}")

    def save_plan(self, plan: ActivityPlan) -> ActivityPlan:
        records = self._load_records()
        
        # Generate ID and timestamp if not present
        if not plan.id:
            plan.id = str(uuid.uuid4())
        if not plan.created_at:
            plan.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        records.append(plan.model_dump())
        self._save_records(records)
        return plan

    def get_all_plans(self) -> List[Dict]:
        records = self._load_records()
        # Sort by created_at desc
        records.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return records

    def get_plan(self, plan_id: str) -> Optional[ActivityPlan]:
        records = self._load_records()
        for record in records:
            if record.get("id") == plan_id:
                return ActivityPlan(**record)
        return None

    def update_plan_evaluation(self, plan_id: str, evaluation_data: EvaluationData, suggestion: str) -> bool:
        records = self._load_records()
        found = False
        for record in records:
            if record.get("id") == plan_id:
                record["evaluation_result"] = {
                    "data": evaluation_data.model_dump(),
                    "suggestion": suggestion
                }
                record["status"] = "evaluated"
                found = True
                break
        
        if found:
            self._save_records(records)
            return True
        return False

    def delete_plan(self, plan_id: str) -> bool:
        records = self._load_records()
        initial_len = len(records)
        records = [r for r in records if r.get("id") != plan_id]
        
        if len(records) < initial_len:
            self._save_records(records)
            return True
        return False

record_service = RecordService()

from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ActivityRequest(BaseModel):
    club_name: str = Field(..., description="Name of the club (e.g. 'Computer Science Club')")
    activity_type: str = Field(..., description="Type of the activity")
    topic: str = Field(..., description="Main topic or theme")
    target_audience: str = Field(..., description="Who is this for?")
    num_participants: int = Field(..., gt=0, description="Expected number of attendees")
    budget: float = Field(..., ge=0, description="Budget in CNY")
    description: Optional[str] = Field(None, description="Additional details")
    time_preference: Optional[str] = Field(None, description="Preferred time for the event")

class AgentStepLog(BaseModel):
    step_name: str
    status: str
    thought: str  # Chain of Thought (CoT)
    action: Optional[str] = None
    result: Optional[str] = None

class ActivityPlan(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier for the plan")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    club_name: Optional[str] = Field(None, description="Club Name")
    activity_type: Optional[str] = Field(None, description="Activity Type")
    title: str
    theme: str
    objectives: List[str]
    target_audience: str
    budget_breakdown: Dict[str, float]
    
    # Task 1: Deep Expansion Fields
    creative_forms: List[str] = Field([], description="Expanded activity forms based on club type")
    detailed_segments: List[str] = Field([], description="Detailed activity segments")
    interaction_suggestions: List[str] = Field([], description="Interactive methods for engagement")
    
    schedule: List[str]
    preparation_timeline: List[str] = []
    staffing_plan: Dict[str, str] = {}
    resources_needed: List[str]
    risk_management: List[str]
    promotion_strategy: Dict[str, str] = {}
    publicity_copy: str
    evaluation_metrics: List[str] = []
    
    # New fields for Agentic Workflow transparency
    agent_logs: List[AgentStepLog] = []
    rag_sources: List[str] = []
    validation_report: Dict[str, str] = {} # Post-processing validation results
    status: str = "generated" # generated, evaluated
    
    # Evaluation Data (Stored with the plan)
    evaluation_result: Optional[Dict] = None # Stores EvaluationData + improvement_suggestion

class EvaluationData(BaseModel):
    participants: int
    satisfaction_score: float = Field(..., ge=0, le=10, description="Score from 0-10")
    social_media_heat: str = Field(..., description="e.g. 'High', 'Medium', 'Low' or specific metrics")
    feedback_summary: str
    issues_encountered: List[str] = []

class EvaluationRequest(BaseModel):
    activity_id: Optional[str] = None
    activity_title: str
    activity_type: str
    evaluation_data: EvaluationData

class RefineRequest(BaseModel):
    current_plan: ActivityPlan
    user_feedback: str = Field(..., description="User's feedback or modification request")

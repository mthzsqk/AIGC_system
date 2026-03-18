from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from .schemas import ActivityRequest, ActivityPlan, RefineRequest, EvaluationRequest
from .services.agent_service import PlanningAgent
from .services.rag_service import rag_service
from .services.record_service import record_service
from .utils.llm_client import llm_client
import json

app = FastAPI(title="AIGC Club Activity Planner")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os

# ...

# Serve Static Files (Frontend)
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.post("/api/generate", response_model=ActivityPlan)
async def generate_activity_plan(request: ActivityRequest):
    try:
        # Create a new agent instance for each request to ensure thread safety
        agent = PlanningAgent()
        plan = agent.run(request)
        
        # Save to history records
        saved_plan = record_service.save_plan(plan)
        
        return saved_plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history", response_model=List[ActivityPlan])
async def get_history():
    return record_service.get_all_plans()

@app.get("/api/history/{plan_id}", response_model=ActivityPlan)
async def get_history_detail(plan_id: str):
    plan = record_service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

@app.delete("/api/history/{plan_id}")
async def delete_history(plan_id: str):
    success = record_service.delete_plan(plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"status": "success", "message": "Plan deleted"}

@app.post("/api/refine", response_model=ActivityPlan)
async def refine_activity_plan(request: RefineRequest):
    try:
        agent = PlanningAgent()
        refined_plan = agent.refine_plan(request.current_plan, request.user_feedback)
        
        # If the refined plan has an ID (it should from the request), update it or save as new version?
        # For now, let's treat refinement as a new generation or just return it. 
        # Ideally, we should update the record.
        # But for simplicity and to match current flow, we just return it. 
        # If the user wants to save this refined version, they might need to "save" it or we auto-save.
        # Let's auto-save as a new entry for now to preserve history.
        
        # Ensure it's saved as a NEW record by clearing ID and created_at
        refined_plan.id = None
        refined_plan.created_at = None
        
        saved_plan = record_service.save_plan(refined_plan)
        return saved_plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/evaluate")
async def evaluate_activity(request: EvaluationRequest):
    try:
        # 1. Analyze feedback using LLM
        prompt = f"""
        请分析以下活动反馈数据，并生成针对下次同类活动策划的改进建议。
        
        活动: {request.activity_title} ({request.activity_type})
        数据:
        - 参与人数: {request.evaluation_data.participants}
        - 满意度: {request.evaluation_data.satisfaction_score}/10
        - 热度: {request.evaluation_data.social_media_heat}
        - 反馈摘要: {request.evaluation_data.feedback_summary}
        - 遇到的问题: {request.evaluation_data.issues_encountered}
        
        请生成一段简练的"改进建议" (100字以内)，用于指导未来的策划。
        """
        
        suggestion = llm_client.generate_completion(prompt)
        
        # 2. Update local record if ID is provided
        if request.activity_id:
            record_service.update_plan_evaluation(
                request.activity_id, 
                request.evaluation_data, 
                suggestion
            )
        
        # 3. Construct history entry for RAG KB
        entry = {
            "title": request.activity_title,
            "type": request.activity_type,
            "participants": request.evaluation_data.participants,
            "satisfaction": request.evaluation_data.satisfaction_score,
            "feedback_summary": request.evaluation_data.feedback_summary,
            "improvement_suggestion": suggestion,
            "source": "User Feedback Loop"
        }
        
        # 4. Save to knowledge base
        success = rag_service.add_history_entry(entry)
        
        if success:
            return {"message": "Evaluation saved successfully", "suggestion": suggestion}
        else:
            raise HTTPException(status_code=500, detail="Failed to save evaluation to KB")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def read_root():
    return {"message": "Welcome to AIGC Club Planner API. Visit /static/index.html for the UI."}

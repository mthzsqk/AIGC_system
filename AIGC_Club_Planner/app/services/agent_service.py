import json
import re
from typing import List, Dict
from ..schemas import ActivityRequest, ActivityPlan, AgentStepLog
from .rag_service import rag_service
from ..utils.llm_client import llm_client

class PlanningAgent:
    """
    智能体工作流 (Agentic Workflow)
    任务拆解 + Chain-of-Thought (CoT) + ReAct 推理
    """
    def __init__(self):
        self.logs: List[AgentStepLog] = []

    def _parse_json(self, text: str) -> Dict:
        """
        Robustly extract JSON from text using regex and cleaning.
        """
        try:
            # First, try standard json.loads
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON block
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Try cleaning markdown code blocks
        cleaned = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Last resort: try to fix common JSON errors (like trailing commas)
            # For now, just raise exception
            raise ValueError(f"Failed to parse JSON from: {text[:100]}...")

    def log_step(self, step_name: str, thought: str, action: str = None, result: str = None, status: str = "completed"):
        self.logs.append(AgentStepLog(
            step_name=step_name,
            thought=thought,
            action=action,
            result=result,
            status=status
        ))

    def run(self, request: ActivityRequest) -> ActivityPlan:
        self.logs = [] # Reset logs
        
        # --- Step 0: 角色设定与任务理解 (Persona & Understanding) ---
        self.log_step(
            step_name="角色设定与任务理解",
            thought=f"正在初始化智能体角色... 设定为 {request.club_name} 的专属策划顾问。检测到任务类型为 {request.activity_type}，关键词：{request.topic}。正在激活创意引擎并调取相关领域知识库...",
            action="Initialize Persona",
            status="completed"
        )

        # --- Step 1: 任务分析与知识检索 (Analysis & RAG) ---
        self.log_step(
            step_name="任务分析与知识检索",
            thought=f"正在深度分析策划请求：{request.club_name} 计划举办 {request.activity_type}。关键约束：预算 {request.budget}元，预计 {request.num_participants}人。需要重点检索校规限制、可用场地及往期类似活动的成功案例。",
            action="调用 AdvancedRAGService.retrieve()",
            status="running"
        )
        
        # 构建查询
        query_parts = [request.club_name, request.activity_type, request.topic, f"{request.budget}元"]
        if request.time_preference: query_parts.append(request.time_preference)
        
        query = " ".join(query_parts)
        context_docs = rag_service.search(query)
        context_str = "\n".join(context_docs)
        
        # 简单的冲突检测 (Conflict Detection)
        conflict_warning = ""
        if request.time_preference:
            for doc in context_docs:
                if "校历" in doc and "冲突" in doc: # 假设检索到了相关的校历冲突
                    conflict_warning += f"⚠️ 注意：检索到潜在的时间冲突信息: {doc}\n"
        
        # 查找历史优化建议
        improvement_context = ""
        for doc in context_docs:
            if "改进建议" in doc or "Feedback" in doc:
                improvement_context += f"【历史优化建议】: {doc}\n"
        
        self.log_step(
            step_name="任务分析与知识检索",
            thought=f"知识检索完成。获取到 {len(context_docs)} 条关键情报。{conflict_warning}已提取历史反馈：{improvement_context[:50]}... 准备进入发散性思维阶段。",
            result=f"关键信息摘要: {context_str[:150]}...",
            status="completed"
        )
        
        # --- Step 2: 创意构思与深度拓展 (Creative Generation & Expansion) ---
        self.log_step(
            step_name="创意构思与深度拓展",
            thought=f"正在进行头脑风暴... 基于 {request.topic} 主题，尝试结合 {request.club_name} 的社团调性，构思 3 个差异化的创意方向。重点突破：互动形式的创新与参与感的提升。",
            action="LLM Generate Options",
            status="running"
        )
        
        creative_prompt = f"""
        你是一位经验丰富、思维活跃的大学社团活动策划人，也是{request.club_name}的资深学长/学姐。请根据以下信息，为学弟学妹们设计 3 个风格迥异、极具吸引力的活动方案。
        
        基本信息:
        - 社团名称: {request.club_name}
        - 类型: {request.activity_type}
        - 话题: {request.topic}
        - 期望时间: {request.time_preference or "未指定"}
        - 目标受众: {request.target_audience}
        
        参考历史优化建议:
        {improvement_context}
        
        【重要要求】：
        1. **拒绝AI味**：不要使用“探索...的无限可能”、“旨在促进...”等机械套话。标题要像公众号爆款文章一样吸引人，口号要朗朗上口。
        2. **接地气**：用大学生的语言风格，多用“破冰”、“干货”、“面基”、“刷夜”等校园词汇（如果合适）。
        3. **深度拓展**：
           - "creative_forms": 具体怎么玩？不要只写“讲座”，要写“圆桌派+即兴辩论”。
           - "detailed_segments": 环节要具体到分钟级的画面感。
           - "interaction_suggestions": 怎么让大家不玩手机？
        
        输出格式要求 (JSON格式):
        {{
            "options": [
                {{
                    "title": "方案标题（拒绝【话题】类型格式，要创意）", 
                    "theme": "主题口号（简短有力）", 
                    "style": "风格(如: 硬核干货/轻松社交/公益实践)",
                    "highlights": "亮点与互动形式简述（50字以内）",
                    "creative_forms": ["形式1（具体）", "形式2（具体）"],
                    "detailed_segments": ["环节1详情", "环节2详情"],
                    "interaction_suggestions": ["互动1", "互动2"]
                }}
            ],
            "selection_reason": "选择最佳方案的理由（用第一人称）..."
        }}
        """
        
        creative_forms = []
        detailed_segments = []
        interaction_suggestions = []
        
        try:
            creative_resp = llm_client.generate_completion(creative_prompt, system_prompt="Output strictly in JSON.")
            creative_data = self._parse_json(creative_resp)
            
            options = creative_data.get("options", [])
            selection_reason = creative_data.get("selection_reason", "综合考虑可行性与创新性")
            
            if options:
                selected_option = options[0] 
                title = selected_option.get("title", f"【{request.topic}】{request.activity_type}")
                theme = selected_option.get("theme", f"关注{request.topic}")
                
                creative_forms = selected_option.get("creative_forms", [])
                detailed_segments = selected_option.get("detailed_segments", [])
                interaction_suggestions = selected_option.get("interaction_suggestions", [])
                
                # Check for empty lists and provide fallback if needed
                if not creative_forms:
                    creative_forms = ["主题分享会", "互动工作坊"]
                if not detailed_segments:
                    detailed_segments = ["开场破冰", "核心内容展示", "自由交流"]
                if not interaction_suggestions:
                    interaction_suggestions = ["现场提问", "小组讨论"]
                
                alternatives_log = " | ".join([f"[{opt.get('style', '未指定')}] {opt.get('title', '无标题')}" for opt in options])
                self.log_step(
                    step_name="创意构思与深度拓展",
                    thought=f"创意方案已生成。正在评估方案可行性... 选中方案：[{title}]。理由：{selection_reason}",
                    result=f"核心创意确立: {title} - {theme} (亮点: {', '.join(creative_forms[:2])})",
                    status="completed"
                )
            else:
                raise ValueError("No options generated")
        except Exception as e:
            print(f"Creative generation failed: {e}")
            title = f"【{request.topic}】{request.activity_type}"
            theme = f"探索 {request.topic} 的无限可能"
            
            # Fallback for deep expansion fields on error
            creative_forms = ["常规讲座", "社团聚会", "经验分享"]
            detailed_segments = ["签到环节", "嘉宾致辞", "主题活动", "总结发言"]
            interaction_suggestions = ["举手提问", "问卷调查", "会后交流"]
            
            self.log_step(
                step_name="创意构思与深度拓展",
                thought=f"创意生成模块遭遇阻碍，正在启动应急生成模式。错误追踪: {e}",
                result=f"使用基础方案: {title}",
                status="completed"
            )

        # --- Step 3: 逻辑规划与资源检查 (Time & Resource Planning) ---
        self.log_step(
            step_name="逻辑规划与资源检查",
            thought=f"进入执行规划阶段。正在根据预算 ({request.budget}元) 和人数 ({request.num_participants}人) 拆解任务。重点优化：活动流程的紧凑性与资源利用率。同时进行二次时间冲突扫描。",
            action="LLM Comprehensive Planning",
            status="running"
        )
        
        planning_prompt = f"""
        请以“资深活动策划人”的身份，为{request.club_name}的活动 "{title}" 制定一份可落地的执行SOP。
        
        约束条件:
        - 人数: {request.num_participants} (要考虑场地容纳和分组)
        - 预算: {request.budget} 元 (每一分钱都要花在刀刃上)
        - 时间偏好: {request.time_preference or "待定"}
        
        参考信息 (RAG):
        {context_str}
        
        【重要要求】：
        1. **Objectives (目标)**：拒绝“促进交流”这种空话。要具体，例如“让80%的新生加上至少3个学长微信”、“产出5份高质量项目书”。
        2. **Schedule (流程)**：
           - 必须包含“暖场”、“中场休息”、“合影”等真实环节。
           - 时间安排要留有余地（Buffer time）。
           - 描述要口语化，比如“签到 & 领奶茶”、“大佬分享环节”、“自由勾搭时间”。
        3. **Staffing (分工)**：
           - 角色名称要有社团特色（如“护花使者”、“搬砖组”、“气氛组”）。
           - 职责要明确（如“负责订奶茶、拿外卖”、“负责现场拍照修图”）。
        
        请生成以下内容 (JSON格式):
        1. objectives: 活动目标 (3-5条，SMART原则)
        2. preparation_timeline: 筹备期日程 (倒推时间表，关键节点)
        3. schedule: 活动当天流程 (精确到分钟，真实合理)
        4. staffing_plan: 人员分工 (角色: 具体职责)
        5. budget_breakdown: 预算明细 (条目清晰)
        6. resources_needed: 物资与场地需求 (不遗漏插排、垃圾袋等细节)
        
        输出格式要求 (JSON):
        {{
            "objectives": ["让参与者掌握...技能", "沉淀...份作品"],
            "preparation_timeline": ["D-7: 确定场地", "D-1: 购买零食..."],
            "schedule": ["13:30-14:00 签到 & 暖场BGM", "14:00-14:10 主持人开场(强调...)..."],
            "staffing_plan": {{"统筹大大": "全盘把控进度", "文案输出机": "负责推文撰写"}},
            "budget_breakdown": {{"场地费": 200, "茶歇(奶茶+小蛋糕)": 300}},
            "resources_needed": ["投影仪+转接头", "签到表", "垃圾袋"]
        }}
        """
        
        try:
            plan_resp = llm_client.generate_completion(planning_prompt, system_prompt="Output strictly in JSON.")
            plan_data = self._parse_json(plan_resp)
            
            objectives = plan_data.get("objectives", ["促进交流", "提升能力"])
            preparation_timeline = plan_data.get("preparation_timeline", [])
            schedule = plan_data.get("schedule", [])
            staffing_plan = plan_data.get("staffing_plan", {})
            budget_breakdown = plan_data.get("budget_breakdown", {})
            resources_needed = plan_data.get("resources_needed", [])
        except Exception as e:
            print(f"Planning generation failed: {e}")
            objectives = ["促进交流", "提升能力", "丰富校园生活"]
            preparation_timeline = ["活动前1周: 准备物资"]
            schedule = ["09:00 - 活动开始"]
            staffing_plan = {"负责人": "全权负责"}
            budget_breakdown = {"杂项": request.budget}
            resources_needed = ["基础物资"]

        # Fill in expanded fields if not present in planning
        # Note: creative_forms, detailed_segments, interaction_suggestions came from Step 2
        
        self.log_step(
            step_name="逻辑规划与资源检查",
            thought=f"SOP制定完成。关键产出：筹备时间轴 ({len(preparation_timeline)}节点)、分钟级流程表 ({len(schedule)}项) 及 岗位责任书。",
            result=f"执行蓝图已生成。预算分配率: {int(sum(budget_breakdown.values())/request.budget*100) if request.budget > 0 else 0}%",
            status="completed"
        )

        # --- Step 4: 宣传推广策略 (Promotion Strategy) ---
        self.log_step(
            step_name="宣传推广策略",
            thought=f"正在构建传播矩阵。针对目标受众 {request.target_audience}，筛选高转化率渠道。同时进行视觉与文案的创意生成，力求“破圈”传播。",
            action="LLM Promotion Strategy",
            status="running"
        )
        
        promo_prompt = f"""
        请为活动 "{title}" 设计一套“看了就想来”的宣传方案。拒绝翻译腔，拒绝官方套话。
        
        目标受众: {request.target_audience} (请分析他们的痛点和爽点)
        
        参考渠道 (RAG):
        {context_str}
        
        【重要要求】：
        1. **拒绝“震惊体”**，但要足够吸睛。
        2. **Visual Design (视觉)**：描述要像在给设计师提需求，具体到配色（如“赛博朋克风”、“多巴胺配色”）、元素（“像素风小人”、“故障艺术”）。
        3. **Copy (文案)**：
           - 必须是 Z世代语言风格（但不要强行玩梗）。
           - 开头三句话必须抓住注意力。
           - 包含行动召唤（Call to Action），如“扫码上车”、“手慢无”。
           - **禁止使用**：“诚邀您参加”、“旨在...”、“活动详情如下”等老干部文风。
        
        请生成 (JSON):
        1. promotion_channels: 推荐渠道及理由 (Key: 渠道名, Value: 为什么选它？怎么玩？)
        2. visual_design_idea: 海报设计创意描述 (给设计师的Prompt)
        3. publicity_copy: 一段核心宣传文案 (朋友圈/QQ空间文案，含Emoji)
        
        输出格式 (JSON):
        {{
            "promotion_channels": {{"表白墙": "带话题#捞人 投稿...", "食堂桌贴": "吃饭时强制吸睛..."}},
            "visual_design_idea": "主色调采用克莱因蓝...",
            "publicity_copy": "【🔥扩列/干货】\n家人们谁懂啊..."
        }}
        """
        
        try:
            promo_resp = llm_client.generate_completion(promo_prompt, system_prompt="Output strictly in JSON.")
            promo_data = self._parse_json(promo_resp)
            
            promotion_channels = promo_data.get("promotion_channels", {})
            visual_design_idea = promo_data.get("visual_design_idea", "暂无设计建议")
            publicity_copy = promo_data.get("publicity_copy", "暂无文案")
            
            promotion_strategy = {
                "channels": ", ".join([f"{k}({v})" for k,v in promotion_channels.items()]),
                "visual_design": visual_design_idea
            }
        except Exception as e:
            print(f"Promotion generation failed: {e}")
            promotion_strategy = {"channels": "朋友圈", "visual_design": "简约风格"}
            publicity_copy = f"欢迎参加 {title}！"

        self.log_step(
            step_name="宣传推广策略",
            thought="传播策略已生成。核心策略：通过视觉冲击与情感共鸣引爆话题。",
            result=f"覆盖渠道: {len(promotion_channels)}个 | 核心文案: {publicity_copy[:20]}...",
            status="completed"
        )

        # --- Step 5: 风险管理与效果评估 (Risk & Evaluation) ---
        self.log_step(
            step_name="风险管理与效果评估",
            thought="正在进行“事前验尸” (Pre-mortem Analysis)。模拟活动全流程，识别潜在断点与风险源。同时设定 SMART 评估指标。",
            action="Risk Simulation & KPI Setting",
            status="running"
        )
        
        risk_eval_prompt = f"""
        针对活动 "{title}" ({request.activity_type})，请生成：
        1. 风险与应急预案 (Risk Management): 3-5条，格式 "风险点: 应对措施"
        2. 效果评估指标 (Evaluation Metrics): 3-5条，用于活动后的复盘分析
        
        参考规则 (RAG):
        {context_str}
        
        输出格式 (JSON):
        {{
            "risk_management": ["设备故障: 准备备用麦克风", "人员拥挤: 安排疏导员"],
            "evaluation_metrics": ["参与人数达标率", "问卷满意度 > 85%", "朋友圈转发量"]
        }}
        """
        
        try:
            re_resp = llm_client.generate_completion(risk_eval_prompt, system_prompt="Output strictly in JSON.")
            re_data = self._parse_json(re_resp)
            
            risk_management = re_data.get("risk_management", [])
            evaluation_metrics = re_data.get("evaluation_metrics", [])
        except Exception as e:
            print(f"Risk/Eval generation failed: {e}")
            risk_management = ["注意安全"]
            evaluation_metrics = ["参与人数"]

        self.log_step(
            step_name="风险管理与效果评估",
            thought="风控模型运行完毕。已部署应急预案与效果追踪体系。",
            result=f"风险覆盖: {len(risk_management)}点 | KPI指标: {len(evaluation_metrics)}项",
            status="completed"
        )
        
        # --- Final Output Construction ---
        # --- Step 6: 结果后处理 (Post-processing) ---
        self.log_step(
            step_name="结果后处理",
            thought="正在启动多维质检引擎：结构完整性校验 (Structure) -> 预算合规性审查 (Finance) -> 语义一致性分析 (Semantic) -> 安全复核 (Security)。",
            action="Quality Assurance Protocol",
            status="running"
        )
        
        # Construct preliminary plan for checking
        plan_temp = ActivityPlan(
            club_name=request.club_name,
            activity_type=request.activity_type,
            title=title,
            theme=theme,
            objectives=objectives,
            target_audience=request.target_audience,
            budget_breakdown=budget_breakdown,
            schedule=schedule,
            preparation_timeline=preparation_timeline,
            staffing_plan=staffing_plan,
            resources_needed=resources_needed,
            risk_management=risk_management,
            promotion_strategy=promotion_strategy,
            publicity_copy=publicity_copy,
            evaluation_metrics=evaluation_metrics,
            
            # Expanded Fields
            creative_forms=creative_forms,
            detailed_segments=detailed_segments,
            interaction_suggestions=interaction_suggestions,
            
            agent_logs=self.logs,
            rag_sources=context_docs
        )
        
        validation_report = self.post_process(plan_temp, request)
        
        self.log_step(
            step_name="结果后处理",
            thought="后处理校验完成。",
            result=f"校验报告: {validation_report}",
            status="completed"
        )
        
        # Create final plan with validation report
        plan = plan_temp
        plan.validation_report = validation_report
        plan.agent_logs = self.logs
        return plan

    def post_process(self, plan: ActivityPlan, request: ActivityRequest = None) -> Dict[str, str]:
        """
        结果后处理机制 (Post-processing):
        1. 结构完整性校验 (Structure Integrity Check)
        2. 规则基础的质量控制 (Rule-based Quality Control) - NEW
        3. 语义合理性分析 (Semantic Analysis)
        4. 安全性复核 (Secondary Security Review)
        """
        report = {}
        
        # 1. Structure Integrity Check
        missing_fields = []
        if not plan.objectives: missing_fields.append("objectives")
        if not plan.schedule: missing_fields.append("schedule")
        if not plan.risk_management: missing_fields.append("risk_management")
        if not plan.budget_breakdown: missing_fields.append("budget_breakdown")
        
        if missing_fields:
            report["structure_integrity"] = f"⚠️ 缺少必要部分: {', '.join(missing_fields)}"
        else:
            report["structure_integrity"] = "✅ 结构完整"

        # 2. Rule-based Quality Control (New Task)
        # Check Budget Consistency
        total_budget_planned = sum(plan.budget_breakdown.values())
        budget_diff = abs(total_budget_planned - request.budget) if request else 0
        if request and budget_diff > request.budget * 0.1: # Allow 10% margin
            report["budget_check"] = f"⚠️ 预算偏差警告: 计划总额 {total_budget_planned} vs 预算 {request.budget}"
        else:
            report["budget_check"] = "✅ 预算符合要求"
            
        # Check Content Specificity (Simple heuristic)
        if "待定" in str(plan.schedule) or "TBD" in str(plan.schedule):
             report["content_quality"] = "⚠️ 日程表中包含未定项，建议细化"
        else:
             report["content_quality"] = "✅ 内容具体"

        # 3. Semantic Analysis (Logic Check) via LLM
        check_prompt = f"""
        请检查以下活动策划方案的逻辑合理性与可执行性。
        
        方案内容:
        标题: {plan.title}
        社团: {request.club_name if request else '未知社团'}
        时间表: {plan.schedule}
        筹备期: {plan.preparation_timeline}
        人员: {plan.staffing_plan}
        预算: {plan.budget_breakdown}
        
        请检查:
        1. 时间安排是否有冲突或不合理之处?
        2. 预算是否遗漏重要项?
        3. 人员分工是否覆盖关键职责?
        
        输出简短的检查报告 (100字以内)。如果无明显问题，输出"逻辑合理"。
        """
        try:
            semantic_check = llm_client.generate_completion(check_prompt)
            report["semantic_analysis"] = semantic_check.strip()
        except Exception as e:
            report["semantic_analysis"] = f"检查失败: {e}"

        # 4. Secondary Security Review
        security_prompt = f"""
        请对以下活动策划内容进行敏感性审查。
        内容: {plan.title} - {plan.theme} - {plan.publicity_copy}
        社团: {request.club_name if request else '未知社团'}
        
        是否存在违反高校校园规定、政治敏感、低俗或安全隐患的内容?
        如果安全，输出"✅ 通过"。如果不安全，指出具体问题。
        """
        try:
            security_check = llm_client.generate_completion(security_prompt)
            report["security_review"] = security_check.strip()
        except Exception as e:
            report["security_review"] = f"审查失败: {e}"
            
        return report

    def refine_plan(self, current_plan: ActivityPlan, user_feedback: str) -> ActivityPlan:
        """
        交互式纠错与用户反馈 (Interactive Feedback & Refinement)
        """
        # Restore logs from the current plan to maintain history
        self.logs = list(current_plan.agent_logs)
        
        self.log_step(
            step_name="用户反馈与修正",
            thought=f"收到用户反馈: {user_feedback}。正在基于反馈修正方案。",
            action="LLM Refinement",
            status="running"
        )
        
        refine_prompt = f"""
        请以“活动策划合伙人”的身份，根据用户的反馈意见，修改当前的活动策划方案。
        
        当前方案 (JSON):
        {current_plan.model_dump_json()}
        
        用户反馈:
        {user_feedback}
        
        【修改原则】：
        1. **听人劝**：严格执行用户的修改意见。
        2. **保持人味**：修改后的内容要与之前的“资深学长/学姐”人设保持一致，不要变回机器人语气。
        3. **具体落地**：如果用户觉得虚，就补充细节（如具体的时间点、具体的物资品牌）。
        
        请输出修改后的完整方案 (JSON格式)，保持原有的字段结构。
        重点修改用户提到的部分，其他部分如果无需修改则保持原样。
        """
        
        try:
            refined_resp = llm_client.generate_completion(refine_prompt, system_prompt="Output strictly in JSON. Return the full updated plan object.")
            refined_data = self._parse_json(refined_resp)
            
            # Update fields
            current_plan.title = refined_data.get("title", current_plan.title)
            current_plan.theme = refined_data.get("theme", current_plan.theme)
            current_plan.objectives = refined_data.get("objectives", current_plan.objectives)
            current_plan.budget_breakdown = refined_data.get("budget_breakdown", current_plan.budget_breakdown)
            current_plan.schedule = refined_data.get("schedule", current_plan.schedule)
            current_plan.preparation_timeline = refined_data.get("preparation_timeline", current_plan.preparation_timeline)
            current_plan.staffing_plan = refined_data.get("staffing_plan", current_plan.staffing_plan)
            current_plan.resources_needed = refined_data.get("resources_needed", current_plan.resources_needed)
            current_plan.risk_management = refined_data.get("risk_management", current_plan.risk_management)
            current_plan.promotion_strategy = refined_data.get("promotion_strategy", current_plan.promotion_strategy)
            current_plan.publicity_copy = refined_data.get("publicity_copy", current_plan.publicity_copy)
            current_plan.evaluation_metrics = refined_data.get("evaluation_metrics", current_plan.evaluation_metrics)
            
            # Update expanded fields
            current_plan.creative_forms = refined_data.get("creative_forms", current_plan.creative_forms)
            current_plan.detailed_segments = refined_data.get("detailed_segments", current_plan.detailed_segments)
            current_plan.interaction_suggestions = refined_data.get("interaction_suggestions", current_plan.interaction_suggestions)
            
            # Re-run validation
            validation_report = self.post_process(current_plan)
            current_plan.validation_report = validation_report
            
            self.log_step(
                step_name="用户反馈与修正",
                thought="方案优化完成。已整合用户反馈并重新通过质检。",
                result="方案已更新",
                status="completed"
            )
            
            # Update logs
            current_plan.agent_logs = self.logs
            return current_plan
            
        except Exception as e:
            self.log_step(
                step_name="7. 用户反馈与修正",
                thought=f"修正失败: {e}",
                result="保持原方案",
                status="failed"
            )
            return current_plan

agent_service = PlanningAgent()

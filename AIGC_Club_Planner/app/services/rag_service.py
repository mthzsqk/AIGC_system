import json
import os
from typing import List, Dict, Tuple
import random
from ..utils.llm_client import llm_client
from .record_service import record_service

class AdvancedRAGService:
    def __init__(self):
        # 加载本地知识库 (Load Local Knowledge Base)
        self.kb_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge_base")
        
        self.rules_kb = self._load_json("rules.json")
        self.venues_kb = self._load_json("venues.json")
        self.history_kb = self._load_json("history.json")
        
        # Load Calendar and Course Schedule
        calendar_data = self._load_json("calendar.json")
        if isinstance(calendar_data, list):
            self.calendar_kb = calendar_data
            self.semester_start = "2024-02-26"
        else:
            self.calendar_kb = calendar_data.get("events", [])
            self.semester_start = calendar_data.get("semester_start", "2026-03-02")
            
        self.course_schedule = self._load_json("course_schedule.json")
        
        self.faculty_kb = self._load_json("faculty.json")
        self.channels_kb = self._load_json("channels.json")

    def _load_json(self, filename: str) -> List[Dict]:
        try:
            path = os.path.join(self.kb_path, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return []

    def add_history_entry(self, entry: Dict) -> bool:
        """
        Add a new entry to history.json and reload memory
        """
        try:
            path = os.path.join(self.kb_path, "history.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = []
            
            data.append(entry)
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Reload memory
            self.history_kb = data
            return True
        except Exception as e:
            print(f"Error adding history entry: {e}")
            return False

    def rewrite_query(self, query: str) -> List[str]:
        """
        查询重写 (Query Rewriting): 使用 LLM 将用户模糊的查询扩展为多个维度的精确查询
        """
        prompt = f"""
        请将以下社团活动查询请求重写为 3-5 个具体的检索关键词或短语，以便在校规、场地资源和历史案例库中进行检索。
        
        用户查询: "{query}"
        
        输出格式要求: 仅输出关键词，用逗号分隔，不要有其他废话。
        示例: 讲座场地申请, 学术活动报销标准, 投影仪借用流程
        """
        
        try:
            response = llm_client.generate_completion(prompt)
            # 处理可能的格式问题
            keywords = [k.strip() for k in response.replace("，", ",").split(",")]
            # 确保原始查询也在其中
            keywords.append(query)
            return list(set(keywords))
        except Exception as e:
            print(f"Query rewrite failed: {e}")
            return [query]

    def _check_schedule_conflicts(self, query: str) -> List[Dict]:
        """
        Check course schedule for conflicts based on query time info
        """
        results = []
        days_map = {
            "周一": "Monday", "星期一": "Monday", "Monday": "Monday",
            "周二": "Tuesday", "星期二": "Tuesday", "Tuesday": "Tuesday",
            "周三": "Wednesday", "星期三": "Wednesday", "Wednesday": "Wednesday",
            "周四": "Thursday", "星期四": "Thursday", "Thursday": "Thursday",
            "周五": "Friday", "星期五": "Friday", "Friday": "Friday",
            "周六": "Saturday", "星期六": "Saturday", "Saturday": "Saturday",
            "周日": "Sunday", "星期日": "Sunday", "Sunday": "Sunday"
        }
        
        target_day = None
        target_week = None
        
        # 1. Try to parse specific date (e.g. "5月20日")
        import re
        from datetime import datetime
        
        date_match = re.search(r'(\d+)月(\d+)日', query)
        if date_match:
            try:
                month, day = map(int, date_match.groups())
                
                # Parse semester start date
                start_dt = datetime.strptime(self.semester_start, "%Y-%m-%d")
                current_year = start_dt.year
                
                query_date = datetime(current_year, month, day)
                
                delta = query_date - start_dt
                if delta.days >= 0:
                    target_week = (delta.days // 7) + 1
                    # Update target_day based on date
                    days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    target_day = days_list[query_date.weekday()]
            except:
                pass

        # 2. If no date found, check for explicit day/week mentions
        if not target_day:
            for k, v in days_map.items():
                if k in query:
                    target_day = v
                    break
        
        if not target_week:
            week_match = re.search(r'第(\d+)周', query)
            target_week = int(week_match.group(1)) if week_match else None
        
        if target_day:
            # Count classes on this day
            count = 0
            periods = set()
            classrooms = set()
            
            # If course_schedule is a list of dicts
            if isinstance(self.course_schedule, list):
                for item in self.course_schedule:
                    if item.get("day") == target_day:
                        # Check week if specified
                        if target_week:
                            if target_week in item.get("weeks", []):
                                count += 1
                                periods.add(item.get("period"))
                                classrooms.add(item.get("classroom"))
                        else:
                            # Just count all entries for that day regardless of week to show general busyness
                            count += 1
                            periods.add(item.get("period"))
                            classrooms.add(item.get("classroom"))

            busy_periods = sorted(list(periods))
            busy_classrooms = list(classrooms)[:5] # Just show a few
            
            content = f"[课程表-{target_day}] "
            if target_week:
                content += f"第{target_week}周 "
            
            content += f"共有 {count} 节课。繁忙时段: {busy_periods}。主要占用教室: {', '.join(busy_classrooms)} 等。"
            
            results.append({
                "content": content,
                "raw_data": {"count": count, "day": target_day},
                "source": "course_schedule",
                "score": 0.0
            })
            
        return results

    def retrieve(self, queries: List[str]) -> List[Dict]:
        """
        多路召回 (Multi-Path Retrieval)
        """
        results = []
        
        # 0. 总是包含所有日历信息以便检查冲突 (Optional optimization: filter by date if provided)
        # For simplicity, we just add them if '时间' or '日期' is mentioned, or always add them with low score but rerank high if relevant?
        # Better: Search keywords.
        
        for q in queries:
            q_lower = q.lower()
            
            # 1. 规则库检索
            for item in self.rules_kb:
                content = item.get("content", "")
                category = item.get("category", "")
                if any(k in content.lower() for k in q_lower.split()) or category in q:
                    results.append({
                        "content": f"[校规-{category}] {content}",
                        "raw_data": item,
                        "source": "rules_kb",
                        "score": 0.0
                    })
            
            # 2. 场地资源库检索
            for item in self.venues_kb:
                name = item.get("name", "")
                equipment = str(item.get("equipment", [])) # Ensure string
                suitable = str(item.get("suitable_for", []))
                avail = item.get("availability", "Unknown")
                
                if any(k in name.lower() for k in q_lower.split()) or "场地" in q or "操场" in q:
                    results.append({
                        "content": f"[场地-{name}] 容量:{item.get('capacity')}人, 设备:{equipment}, 可用性:{avail}",
                        "raw_data": item,
                        "source": "venues_kb",
                        "score": 0.0
                    })
            
            # 3. 历史案例库检索
            for item in self.history_kb:
                title = item.get("title", "")
                summary = item.get("summary", "")
                
                # Case 1: Standard Case Study (Old format)
                if summary:
                    if any(k in title.lower() for k in q_lower.split()) or "案例" in q:
                        results.append({
                            "content": f"[历史案例-{title}] {summary} 成功因素:{item.get('success_factor', '无')}",
                            "raw_data": item,
                            "source": "history_kb",
                            "score": 0.0
                        })
                
                # Case 2: Evaluation Feedback (New format)
                suggestion = item.get("improvement_suggestion", "")
                feedback = item.get("feedback_summary", "")
                activity_type = item.get("type", "")
                
                if suggestion:
                    # Match if activity type or title matches query
                    if activity_type in q or any(k in title.lower() for k in q_lower.split()) or "反馈" in q or "建议" in q:
                        results.append({
                            "content": f"[历史反馈-{title}] 类型:{activity_type} 反馈摘要:{feedback} 改进建议:{suggestion}",
                            "raw_data": item,
                            "source": "history_kb_feedback",
                            "score": 0.0
                        })

            # 4. 校历检索
            for item in self.calendar_kb:
                name = item.get("name", "")
                desc = item.get("description", "")
                date_info = f"{item.get('start_date')} to {item.get('end_date')}"
                if any(k in name.lower() for k in q_lower.split()) or "时间" in q or "日期" in q or "冲突" in q:
                    results.append({
                        "content": f"[校历-{name}] {date_info} 类型:{item.get('type')} 说明:{desc}",
                        "raw_data": item,
                        "source": "calendar_kb",
                        "score": 0.0
                    })

            # 4.5 课程表检索 (Course Schedule)
            schedule_results = self._check_schedule_conflicts(q)
            results.extend(schedule_results)

            # 5. 师资检索
            for item in self.faculty_kb:
                name = item.get("name", "")
                expert = str(item.get("expertise", []))
                if any(k in expert.lower() for k in q_lower.split()) or "老师" in q or "嘉宾" in q:
                    results.append({
                        "content": f"[师资-{name}] 专长:{expert} 时间:{item.get('availability')}",
                        "raw_data": item,
                        "source": "faculty_kb",
                        "score": 0.0
                    })

            # 6. 宣传渠道检索
            for item in self.channels_kb:
                name = item.get("name", "")
                type_ = item.get("type", "")
                audience = item.get("audience", "")
                if any(k in name.lower() for k in q_lower.split()) or "宣传" in q or "推广" in q:
                    results.append({
                        "content": f"[渠道-{name}] 类型:{type_} 受众:{audience} 效果:{item.get('effectiveness')}",
                        "raw_data": item,
                        "source": "channels_kb",
                        "score": 0.0
                    })
            
            # 7. 用户历史反馈检索 (User Records with Evaluation)
            user_records = record_service.get_all_plans()
            for record in user_records:
                # Check if evaluated
                if record.get("status") == "evaluated":
                    eval_res = record.get("evaluation_result", {})
                    data = eval_res.get("data", {})
                    suggestion = eval_res.get("suggestion", "")
                    
                    title = record.get("title", "")
                    act_type = record.get("activity_type", "")
                    
                    # Match query
                    # If query is broad (like "Music Festival"), match activity_type
                    # If query mentions "feedback" or "suggestion", include high-quality feedback
                    is_match = False
                    if act_type and act_type in q: is_match = True
                    if any(k in title.lower() for k in q_lower.split()): is_match = True
                    if "反馈" in q or "建议" in q: is_match = True
                    
                    if is_match:
                        print(f"[RAG] Found user feedback match: {title}")
                        results.append({
                            "content": f"[往期活动反馈-{title}] 类型:{act_type} 满意度:{data.get('satisfaction_score')} 改进建议:{suggestion}",
                            "raw_data": record,
                            "source": "user_records_feedback",
                            "score": 0.0
                        })
        
        # 去重 (Based on content string)
        seen = set()
        unique_results = []
        for r in results:
            if r["content"] not in seen:
                seen.add(r["content"])
                unique_results.append(r)
        
        return unique_results

    def rerank(self, results: List[Dict], query: str) -> List[Dict]:
        """
        重排序 (Rerank): 根据相关性和重要性打分
        """
        for r in results:
            score = 0.0
            content = r["content"]
            
            # 基础相关性
            if query in content:
                score += 0.5
            
            # 来源权重
            if r["source"] == "rules_kb":
                score += 0.8 # 规则最重要，避免违规
            elif r["source"] == "user_records_feedback":
                score += 0.85 # 用户历史反馈非常重要，直接指导改进
            elif r["source"] == "calendar_kb":
                score += 0.7 # 时间冲突也很重要
            elif r["source"] == "course_schedule":
                score += 0.75 # 课程表冲突检测
            elif r["source"] == "venues_kb":
                score += 0.6 # 场地次之
            elif r["source"] == "faculty_kb":
                score += 0.5
            elif r["source"] == "history_kb":
                score += 0.4
            elif r["source"] == "channels_kb":
                score += 0.4
            
            # 随机扰动模拟模型差异
            score += random.random() * 0.1
            
            r["score"] = score
            
        # 按分数降序排列
        return sorted(results, key=lambda x: x["score"], reverse=True)

    def search(self, query: str, top_k: int = 5) -> List[str]:
        """
        Advanced RAG Pipeline: Rewrite -> Retrieve -> Rerank
        """
        # 1. Query Rewriting
        queries = self.rewrite_query(query)
        
        # 2. Multi-Path Retrieval
        raw_results = self.retrieve(queries)
        
        # 3. Reranking
        ranked_results = self.rerank(raw_results, query)
        
        # Return top K contents
        return [r["content"] for r in ranked_results[:top_k]]

rag_service = AdvancedRAGService()

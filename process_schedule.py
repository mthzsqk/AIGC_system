import pandas as pd
import json
import re
import os

def parse_week_range(week_str):
    """
    Parses week strings like:
    - "11-16周" -> [11, 12, 13, 14, 15, 16]
    - "1-16周(单)" -> [1, 3, 5, ...]
    - "2-16周(双)" -> [2, 4, 6, ...]
    - "1,3,5周" -> [1, 3, 5]
    """
    weeks = set()
    week_str = week_str.replace("周", "")
    
    # Handle "单" or "双"
    step = 1
    if "(单)" in week_str:
        step = 2
        week_str = week_str.replace("(单)", "")
    elif "(双)" in week_str:
        step = 2
        week_str = week_str.replace("(双)", "")
        
    parts = week_str.split(',')
    for part in parts:
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                # Adjust start for step if needed
                if step == 2:
                    if "(单)" in week_str and start % 2 == 0: start += 1
                    if "(双)" in week_str and start % 2 != 0: start += 1
                
                for w in range(start, end + 1, step):
                    weeks.add(w)
            except:
                pass
        else:
            try:
                weeks.add(int(part))
            except:
                pass
                
    return sorted(list(weeks))

def main():
    try:
        file_path = "课表.xls"
        if not os.path.exists(file_path):
            print(f"Error: {file_path} not found")
            return

        df = pd.read_excel(file_path, header=None)
        
        # The data structure seems to be:
        # Row 0: Header with period numbers (1-14 repeated)
        # Col 0: Classroom
        # Col 1-14: Mon
        # Col 15-28: Tue
        # ...
        
        # Let's verify where the data starts.
        # Looking at previous output, Row 4 had data. Row 0 was header.
        # So we iterate from index 1.
        
        schedule_data = []
        
        # Mapping columns to (Day, Period)
        # 1-14: Mon 1-14
        # 15-28: Tue 1-14
        # ...
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for idx, row in df.iterrows():
            if idx == 0: continue # Skip header
            
            classroom = row[0]
            if pd.isna(classroom): continue
            
            classroom = str(classroom).strip()
            
            # Iterate through all day columns
            for day_idx, day in enumerate(days):
                start_col = 1 + (day_idx * 14)
                end_col = start_col + 14
                
                for period_offset in range(14):
                    col_idx = start_col + period_offset
                    if col_idx >= len(row): break
                    
                    cell_content = row[col_idx]
                    if pd.notna(cell_content):
                        content = str(cell_content).strip()
                        
                        # Parse content: "CourseName Teacher (Weeks)"
                        # Example: "机器人控制系统设计樊利民 (11-16周)"
                        
                        # Extract weeks using regex looking for pattern at end
                        # Pattern: (digit-digit周) or (digit-digit周(单)) etc.
                        match = re.search(r'\(([\d,\-周单双]+)\)$', content)
                        weeks = []
                        course_name = content
                        
                        if match:
                            week_str = match.group(1)
                            weeks = parse_week_range(week_str)
                            # Remove the weeks part from course name for cleaner display
                            course_name = content.replace(f"({week_str})", "").strip()
                        
                        entry = {
                            "classroom": classroom,
                            "day": day,
                            "period": period_offset + 1,
                            "weeks": weeks,
                            "content": content,
                            "course_name": course_name
                        }
                        schedule_data.append(entry)
                        
        # Save to course_schedule.json
        output_dir = "AIGC_Club_Planner/knowledge_base"
        os.makedirs(output_dir, exist_ok=True)
        
        with open(f"{output_dir}/course_schedule.json", "w", encoding="utf-8") as f:
            json.dump(schedule_data, f, ensure_ascii=False, indent=2)
            
        print(f"Generated {len(schedule_data)} schedule entries.")
        
        # Update calendar.json with semester info
        calendar_info = {
            "semester_start": "2026-03-02",
            "semester": "2026 Spring",
            "events": [] # Cleared old events
        }
        with open(f"{output_dir}/calendar.json", "w", encoding="utf-8") as f:
            json.dump(calendar_info, f, ensure_ascii=False, indent=2)
            
        print("Updated calendar.json with semester start date: 2026-03-02")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

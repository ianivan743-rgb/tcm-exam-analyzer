#!/usr/bin/env python3
"""Parse TCM exam syllabus text into structured JSON - v5 (inline points fix)."""
import json
import re
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_KB_DIR = os.path.join(_SCRIPT_DIR, '..', 'knowledge-base')
INPUT_PATH = os.path.join(_KB_DIR, '01_医学综合考试大纲.txt')
OUTPUT_PATH = os.path.join(_KB_DIR, 'syllabus_full.json')

KNOWN_PARTS = {
    '一、中医学基础': '中医学基础',
    '二、中医经典': '中医经典',
    '三、中医临床': '中医临床',
    '四、西医综合': '西医综合',
    '五、医学人文': '医学人文',
}

KNOWN_SUBJECTS = {
    '中医基础理论', '中医诊断学', '中药学', '方剂学',
    '中医经典各科',
    '中医内科学', '中医外科学', '中医妇科学', '中医儿科学', '针灸学',
    '内科学', '诊断学基础', '传染病学',
    '医学伦理学', '卫生法规',
}

CN_NUMS = r'[一二三四五六七八九十百]+'
CN_NUMS_PAREN = r'（[一二三四五六七八九十百]+）'

LABEL_UNITS = {
    '中医内科学', '中医外科学', '中医妇科学', '中医儿科学',
}

def read_and_preprocess(path):
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()
    lines = raw.split('\n')
    result = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if re.match(r'^\d{1,3}$', s):
            continue
        normalized = re.sub(r'\s+', '', s)
        if normalized == '单元细目要点':
            continue
        if s in ('11', '医学综合考试大纲'):
            continue
        result.append(s)
    return result

def is_part_line(line):
    for key in KNOWN_PARTS:
        if line.startswith(key):
            return True
    return False

def get_part_name(line):
    for key, name in KNOWN_PARTS.items():
        if line.startswith(key):
            return name
    return None

def is_subject_line(line):
    m = re.match(r'^' + CN_NUMS_PAREN + r'(.*)', line)
    if m:
        name = re.sub(r'\s+', '', m.group(1).strip())
        if name in KNOWN_SUBJECTS:
            return True
    return False

def get_subject_name(line):
    m = re.match(r'^' + CN_NUMS_PAREN + r'(.*)', line)
    if m:
        return re.sub(r'\s+', '', m.group(1).strip())
    return line

def is_unit_line(line):
    if is_part_line(line):
        return False
    return bool(re.match(r'^' + CN_NUMS + r'、', line))

def parse_unit_line(line):
    """Parse a unit line, returning (unit_name, optional_inline_detail).
    
    E.g., "五、藏象学说 藏象学说" -> ("藏象学说", "藏象学说")
    E.g., "一、中医学理论体系" -> ("中医学理论体系", None)
    """
    m = re.match(r'^' + CN_NUMS + r'、(.*)', line)
    if not m:
        return (line, None)
    
    full_name = m.group(1).strip()
    
    # Check for "X X" duplication pattern (from PDF table)
    # Split on first space
    parts = full_name.split(None, 1)  # Split on first whitespace
    if len(parts) == 2:
        name_part = parts[0]
        rest = parts[1].strip()
        
        # If name_part == rest, it's a duplication from PDF table
        # The rest is a detail name (same as unit)
        if name_part == rest:
            return (name_part, rest)
        
        # If rest looks like a detail name (not starting with a number)
        # it could be an inline detail
        # E.g., "手太阴肺经、腧穴 手太阴肺经、腧穴"
        if name_part == rest or rest == name_part:
            return (name_part, rest)
        
        # For cases like "六、腧穴的定位方法 腧穴的定位方法"
        # where the rest is same as name without the number prefix
        # Just use name_part
        return (full_name, None)
    
    return (full_name, None)

def is_detail_line(line):
    m = re.match(r'^' + CN_NUMS_PAREN + r'(.*)', line)
    if m:
        name = re.sub(r'\s+', '', m.group(1).strip())
        if name not in KNOWN_SUBJECTS:
            return True
    return False

def parse_detail_line(line):
    """Parse a detail line, returning (detail_name, optional_inline_point).
    
    The PDF table format has 细目 and 要点 columns. When extracted,
    they get concatenated with a space.
    
    E.g., "（一）中医学的学科属性 中医学的学科属性"
        -> ("中医学的学科属性", "中医学的学科属性")
    E.g., "（二）寒热 寒证与热证的临床表现、鉴别要点"
        -> ("寒热", "寒证与热证的临床表现、鉴别要点")
    E.g., "（四）阴阳 1.阴证与阳证的鉴别要点"
        -> ("阴阳", "1.阴证与阳证的鉴别要点")
    E.g., "（一）概述 解表剂的适用范围及应用注意事项"
        -> ("概述", "解表剂的适用范围及应用注意事项")
    """
    m = re.match(r'^' + CN_NUMS_PAREN + r'(\S*)\s*(.*)', line)
    if not m:
        return (line, None)
    
    detail_name = m.group(1).strip()
    rest = m.group(2).strip()
    
    if not rest:
        return (detail_name, None)
    
    # The rest is an inline point
    # But check: if rest starts with a digit+period, it's a numbered point
    # that should be added as-is
    return (detail_name, rest)

def is_point_line(line):
    return bool(re.match(r'^\d+[\.\、．]', line))

def get_point_text(line):
    return re.sub(r'^\d+[\.\、．]\s*', '', line).strip()

def is_subpoint_line(line):
    return bool(re.match(r'^[⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽⑾⑿⒀⒁⒂⒃⒄⒅⒆⒇]', line))

def get_subpoint_text(line):
    return re.sub(r'^[⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽⑾⑿⒀⒁⒂⒃⒄⒅⒆⒇]', '', line).strip()

def parse_syllabus(lines):
    parts = []
    current_part = None
    current_subject = None
    current_unit = None
    current_detail = None
    
    for line in lines:
        # --- Part ---
        if is_part_line(line):
            name = get_part_name(line)
            current_part = {'name': name, 'subjects': []}
            parts.append(current_part)
            current_subject = None
            current_unit = None
            current_detail = None
            continue
        
        if current_part is None:
            continue
        
        # --- Subject ---
        if is_subject_line(line):
            name = get_subject_name(line)
            current_subject = {'name': name, 'units': []}
            current_part['subjects'].append(current_subject)
            current_unit = None
            current_detail = None
            continue
        
        if current_subject is None:
            continue
        
        # --- Unit ---
        if is_unit_line(line):
            unit_name, inline_detail = parse_unit_line(line)
            
            # Check for cross-page duplicate
            existing = next((u for u in current_subject['units'] if u['name'] == unit_name), None)
            if existing:
                current_unit = existing
                current_detail = None
            else:
                current_unit = {'name': unit_name, 'details': []}
                current_subject['units'].append(current_unit)
                current_detail = None
            
            # Handle inline detail from unit line
            if inline_detail:
                existing_d = next((d for d in current_unit['details'] if d['name'] == inline_detail), None)
                if not existing_d:
                    current_detail = {'name': inline_detail, 'points': []}
                    current_unit['details'].append(current_detail)
                else:
                    current_detail = existing_d
            continue
        
        # Handle label units
        if current_unit is None and line in LABEL_UNITS:
            existing = next((u for u in current_subject['units'] if u['name'] == line), None)
            if existing:
                current_unit = existing
            else:
                current_unit = {'name': line, 'details': []}
                current_subject['units'].append(current_unit)
            current_detail = None
            continue
        
        if current_unit is None:
            continue
        
        # --- Detail ---
        if is_detail_line(line):
            detail_name, inline_point = parse_detail_line(line)
            
            # Check for cross-page duplicate
            existing = next((d for d in current_unit['details'] if d['name'] == detail_name), None)
            if existing:
                current_detail = existing
            else:
                current_detail = {'name': detail_name, 'points': []}
                current_unit['details'].append(current_detail)
            
            # Handle inline point
            if inline_point:
                # Check if inline point is actually a numbered point
                if re.match(r'^\d+[\.\、．]', inline_point):
                    # It's a numbered point - extract text
                    pt = re.sub(r'^\d+[\.\、．]\s*', '', inline_point).strip()
                    if pt:
                        current_detail['points'].append(pt)
                else:
                    current_detail['points'].append(inline_point)
            continue
        
        # --- Point ---
        if is_point_line(line):
            text = get_point_text(line)
            if not text:
                continue
            
            if current_detail is None:
                current_detail = {'name': '要点', 'points': []}
                current_unit['details'].append(current_detail)
            
            current_detail['points'].append(text)
            continue
        
        # --- Sub-point ---
        if is_subpoint_line(line):
            text = get_subpoint_text(line)
            if current_detail:
                current_detail['points'].append(text)
            continue
        
        # --- Continuation ---
        if current_detail and current_detail['points']:
            current_detail['points'][-1] += line
        elif current_detail:
            current_detail['points'].append(line)
    
    return parts

def cleanup(parts):
    for part in parts:
        for subject in part['subjects']:
            for unit in subject['units']:
                for detail in unit['details']:
                    detail['points'] = [p.strip() for p in detail['points'] if p.strip()]
                unit['details'] = [d for d in unit['details'] 
                                   if d['name'].strip() or d['points']]
            subject['units'] = [u for u in subject['units'] if u['details']]
        part['subjects'] = [s for s in part['subjects'] if s['units']]
    parts[:] = [p for p in parts if p['subjects']]

def fix_subject_grouping(parts):
    """Split merged subjects in 中医临床 part."""
    for part in parts:
        if part['name'] != '中医临床':
            continue
        if len(part['subjects']) <= 1:
            subject = part['subjects'][0] if part['subjects'] else None
            if not subject:
                continue
            
            new_subjects = []
            current_new_subject = None
            
            for unit in subject['units']:
                if unit['name'] in LABEL_UNITS or unit['name'] == '针灸学':
                    current_new_subject = {'name': unit['name'], 'units': [unit]}
                    new_subjects.append(current_new_subject)
                elif current_new_subject:
                    current_new_subject['units'].append(unit)
                else:
                    if not new_subjects:
                        new_subjects.append({'name': subject['name'], 'units': []})
                        current_new_subject = new_subjects[0]
                    current_new_subject['units'].append(unit)
            
            if len(new_subjects) > 1:
                part['subjects'] = [s for s in new_subjects if s['units']]

def handle_western_medicine_subjects(parts):
    """Split 西医综合 subjects."""
    for part in parts:
        if part['name'] != '西医综合':
            continue
        if len(part['subjects']) != 1:
            continue
        
        subject = part['subjects'][0]
        split_points = []
        for i, unit in enumerate(subject['units']):
            clean = re.sub(r'\s+', '', unit['name'])
            if clean in ('诊断学基础', '传染病学'):
                split_points.append((i, clean))
        
        if not split_points:
            continue
        
        new_subjects = []
        prev_idx = 0
        for idx, name in split_points:
            units_before = subject['units'][prev_idx:idx]
            if units_before:
                if new_subjects:
                    new_subjects[-1]['units'].extend(units_before)
                else:
                    new_subjects.append({'name': subject['name'], 'units': list(units_before)})
            new_subjects.append({'name': name, 'units': []})
            prev_idx = idx + 1
        
        remaining = subject['units'][prev_idx:]
        if new_subjects and remaining:
            new_subjects[-1]['units'].extend(remaining)
        
        part['subjects'] = [s for s in new_subjects if s['units']]

def handle_ethics_subjects(parts):
    """Split 医学人文 subjects."""
    for part in parts:
        if part['name'] != '医学人文':
            continue
        if len(part['subjects']) != 1:
            continue
        
        subject = part['subjects'][0]
        split_idx = None
        for i, unit in enumerate(subject['units']):
            clean = re.sub(r'\s+', '', unit['name'])
            if '卫生法' in clean:
                split_idx = i
                break
        
        if split_idx:
            ethics_units = subject['units'][:split_idx]
            law_units = subject['units'][split_idx:]
            part['subjects'] = [
                {'name': '医学伦理学', 'units': ethics_units},
                {'name': '卫生法规', 'units': law_units},
            ]

def fix_unit_name_issues(parts):
    """Fix unit names that have duplication or truncation."""
    for part in parts:
        for subject in part['subjects']:
            for unit in subject['units']:
                name = unit['name']
                # Fix "X、腧穴 X、腧穴" duplication
                m = re.match(r'^(.+?、腧穴)\s+\1$', name)
                if m:
                    unit['name'] = m.group(1)
                    continue
                # Fix "X X" simple duplication
                parts_split = name.split(None, 1)
                if len(parts_split) == 2 and parts_split[0] == parts_split[1]:
                    unit['name'] = parts_split[0]
                # Fix truncated names ending mid-character
                # e.g., "经络的作用和经络学说的临" 
                # These are hard to fix automatically

def fix_special_unit_names(parts):
    """Fix special cases in unit names."""
    fixes = {
        '经络的作用和经络学说的临': '经络的作用和经络学说的临床应用',
        '处理与患者关系的道德': '处理与患者关系的道德要求',
        '处理医务人员之间关系': '处理医务人员之间关系的道德要求',
        '医学道德评价与良好医': '医学道德评价与良好医德的养成',
        '《中华人民共和国医师': '《中华人民共和国医师法》',
        '《中华人民共和国药品': '《中华人民共和国药品管理法》',
        '《中华人民共和国传染': '《中华人民共和国传染病防治法》',
        '《突发公共卫生事件应': '《突发公共卫生事件应急条例》',
        '《医疗纠纷预防和处理': '《医疗纠纷预防和处理条例》',
        '《中华人民共和国中医': '《中华人民共和国中医药法》',
        '《医疗机构从业人员行': '《医疗机构从业人员行为规范》',
        '《中华人民共和国基': '《中华人民共和国基本医疗卫生与健康促进法》',
        '医学伦理学与医学目': '医学伦理学与医学目的、医学模式',
        '急症及其他病证的针灸': '急症及其他病证的针灸治疗',
        '医学伦理学文献 （二）国内文献': '医学伦理学文献',
    }
    
    for part in parts:
        for subject in part['subjects']:
            for unit in subject['units']:
                if unit['name'] in fixes:
                    unit['name'] = fixes[unit['name']]

def fix_page_header_contamination(parts):
    """Remove page header labels that got concatenated onto point text."""
    page_labels = ['中医内科学', '中医外科学', '中医妇科学', '中医儿科学']
    for part in parts:
        for subject in part['subjects']:
            for unit in subject['units']:
                for detail in unit['details']:
                    new_points = []
                    for pt in detail['points']:
                        for label in page_labels:
                            if pt.endswith(label) and pt != label:
                                # Check if the label was accidentally concatenated
                                # e.g., "聚证中医内科学" should be "聚证"
                                pt = pt[:-len(label)]
                        new_points.append(pt)
                    detail['points'] = new_points

def fix_misc_issues(parts):
    """Fix miscellaneous known issues."""
    for part in parts:
        for subject in part['subjects']:
            for unit in subject['units']:
                # Fix 百合狐 -> 百合狐𧏁阴阳毒病脉证治
                for detail in unit['details']:
                    if detail['name'] == '百合狐':
                        if detail['points'] and detail['points'][0].startswith('阴阳毒病脉证治'):
                            detail['name'] = '百合狐𧏁阴阳毒病脉证治'
                            # Remove the prefix from first point
                            pt = detail['points'][0][len('阴阳毒病脉证治'):]
                            if pt.strip():
                                detail['points'][0] = pt.strip()
                            else:
                                detail['points'].pop(0)

def count_stats(parts):
    stats = {'parts': 0, 'subjects': 0, 'units': 0, 'details': 0, 'points': 0}
    stats['parts'] = len(parts)
    for p in parts:
        stats['subjects'] += len(p['subjects'])
        for s in p['subjects']:
            stats['units'] += len(s['units'])
            for u in s['units']:
                stats['details'] += len(u['details'])
                for d in u['details']:
                    stats['points'] += len(d['points'])
    return stats

def print_breakdown(parts):
    for p in parts:
        print(f"\n  Part: {p['name']}")
        for s in p['subjects']:
            unit_ct = len(s['units'])
            detail_ct = sum(len(u['details']) for u in s['units'])
            point_ct = sum(len(d['points']) for u in s['units'] for d in u['details'])
            print(f"    Subject: {s['name']} ({unit_ct}u, {detail_ct}d, {point_ct}p)")

def main():
    lines = read_and_preprocess(INPUT_PATH)
    print(f"Preprocessed: {len(lines)} lines")
    
    parts = parse_syllabus(lines)
    cleanup(parts)
    fix_subject_grouping(parts)
    handle_western_medicine_subjects(parts)
    handle_ethics_subjects(parts)
    fix_unit_name_issues(parts)
    fix_special_unit_names(parts)
    fix_page_header_contamination(parts)
    fix_misc_issues(parts)
    cleanup(parts)  # Second cleanup after fixes
    
    stats = count_stats(parts)
    print(f"\n=== Parsing Results ===")
    print(f"Parts: {stats['parts']}")
    print(f"Subjects: {stats['subjects']}")
    print(f"Units: {stats['units']}")
    print(f"Details: {stats['details']}")
    print(f"Points: {stats['points']}")
    
    print_breakdown(parts)
    
    result = {
        'title': '中医执业医师资格考试大纲（2025年版）- 医学综合考试',
        'parts': parts
    }
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\nOutput saved to: {OUTPUT_PATH}")

if __name__ == '__main__':
    main()

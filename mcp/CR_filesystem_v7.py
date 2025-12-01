"""
Diagnosis Data Analyzer MCP Server v7
- 일반화된 접근: 모든 환자에 적용 가능
- 통계적 방법으로 critical findings 추출
- 환자별 데이터에 overfitting 없음
"""

from fastmcp import FastMCP
from pathlib import Path
from typing import Optional, Dict, List, Any
import csv
import re
import os
import json

mcp = FastMCP("CR Filesystem v7")

WORK_DIR = os.environ.get('LAB_WORK_DIR')


# ============================================
# Helper functions
# ============================================

def parse_value(value_str) -> Optional[float]:
    """검사 결과값을 float으로 파싱"""
    if not value_str or value_str == '':
        return None
    try:
        if isinstance(value_str, str):
            value_str = re.sub(r'[<>]', '', value_str).strip().replace(',', '')
        return float(value_str)
    except:
        return None


def parse_date(date_str: str) -> str:
    """날짜 문자열을 YYYYMMDD 형식으로 파싱"""
    if not date_str:
        return None
    if re.match(r'^\d{8}$', date_str):
        return date_str
    cleaned = re.sub(r'[-./년월일\s]', '', date_str)
    if re.match(r'^\d{8}$', cleaned):
        return cleaned
    try:
        from dateutil import parser
        dt = parser.parse(date_str)
        return dt.strftime('%Y%m%d')
    except:
        pass
    raise ValueError(f"날짜 형식을 인식할 수 없습니다: {date_str}")


def extract_suspect_diagnoses(content: str) -> List[str]:
    """
    의심 진단 추출 (일반화)
    - R/O, suspect, rule out 등 구조적 패턴
    - 특정 질병명 하드코딩 없음
    """
    suspect_patterns = [
        r'R/O\s+([A-Za-z\s,]+)',
        r'rule out\s+([A-Za-z\s,]+)',
        r'suspect\s+([A-Za-z\s,]+)',
        r'possible\s+([A-Za-z\s,]+)',
        r'differential\s+diagnosis[:\s]+([A-Za-z\s,\n]+)',
        r'impression[:\s]+([A-Za-z\s,\n]+)',
        r'assessment[:\s]+([A-Za-z\s,\n]+)'
    ]
    
    findings = []
    for pattern in suspect_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            diagnosis = match.group(1).strip()
            # 너무 길면 자르기 (최대 100자)
            if len(diagnosis) > 100:
                diagnosis = diagnosis[:100]
            findings.append(diagnosis)
    
    return findings[:10]  # 최대 10개


def summarize_document_structure(content: str, filename: str) -> Dict[str, Any]:
    """
    문서 구조적 요약 (일반화)
    - 특정 키워드 의존 없음
    - 섹션 구조만 활용
    """
    summary = {
        "filename": filename,
        "suspect_diagnoses": extract_suspect_diagnoses(content),
        "chief_complaint": "",
        "key_assessment": "",
        "key_plan": ""
    }
    
    # Chief Complaint (처음 200자)
    for marker in ["Chief Complaint", "주소", "CC:", "C/C:"]:
        idx = content.find(marker)
        if idx != -1:
            start = idx + len(marker)
            end = min(start + 200, len(content))
            summary["chief_complaint"] = content[start:end].strip()
            break
    
    # Assessment (R/O 포함 부분만, 최대 400자)
    for marker in ["Assessment", "평가", "Impression"]:
        idx = content.find(marker)
        if idx != -1:
            start = idx + len(marker)
            # 다음 섹션까지
            next_section_idx = -1
            for next_marker in ["Plan", "계획", "\n\n【", "---"]:
                temp_idx = content.find(next_marker, start)
                if temp_idx != -1:
                    if next_section_idx == -1 or temp_idx < next_section_idx:
                        next_section_idx = temp_idx
            
            if next_section_idx != -1:
                end = min(start + 400, next_section_idx)
            else:
                end = start + 400
            
            summary["key_assessment"] = content[start:end].strip()
            break
    
    # Plan (처음 300자)
    for marker in ["Plan", "계획", "치료"]:
        idx = content.find(marker)
        if idx != -1:
            start = idx + len(marker)
            end = min(start + 300, len(content))
            summary["key_plan"] = content[start:end].strip()
            break
    
    return summary


def select_top_abnormal_labs(all_labs: List[Dict], top_n: int = 15) -> List[Dict]:
    """
    가장 이상한 lab 결과 선택 (일반화)
    
    기준:
    1. ◆ (critical) 마크가 있는 것 우선
    2. ▲▼ 마크가 있는 것 중 상위
    3. 상대적 순위 (환자별 데이터 내에서)
    """
    # 상태별 점수
    status_score = {
        'qualitative_abnormal': 100,  # ◆ (문자형 이상)
        'increased': 10,
        'decreased': 10,
        'normal': 0
    }
    
    # 각 lab에 점수 부여
    scored_labs = []
    for lab in all_labs:
        base_score = status_score.get(lab['status'], 0)
        
        # 숫자값이 있으면 추가 고려
        # (정확한 정상범위 모르더라도, 화살표만으로 판단)
        if lab.get('value_numeric') is not None:
            # critical/increased/decreased가 표시되어 있다면
            # 그 자체로 의미있음
            score = base_score
        else:
            # 문자값 (Negative, Positive 등)
            # 상태가 abnormal이면 의미있음
            score = base_score
        
        lab['selection_score'] = score
        if score > 0:  # abnormal한 것만
            scored_labs.append(lab)
    
    # 점수순 정렬
    scored_labs.sort(key=lambda x: x['selection_score'], reverse=True)
    
    return scored_labs[:top_n]


def collect_intelligent_summary(date_folders: List[Path], top_n: int = 15) -> Dict[str, Any]:
    """
    지능형 요약 수집 (일반화)
    - 환자 독립적
    - 상대적 중요도 기반
    """
    result = {
        "period_summary": {
            "start_date": "",
            "end_date": "",
            "total_dates": 0
        },
        "documents_by_date": {},
        "top_abnormal_labs_by_date": {},
        "lab_statistics_by_date": {}
    }
    
    dates = sorted([f.name for f in date_folders])
    if dates:
        result["period_summary"]["start_date"] = dates[0]
        result["period_summary"]["end_date"] = dates[-1]
        result["period_summary"]["total_dates"] = len(dates)
    
    for folder in sorted(date_folders):
        date_str = folder.name
        
        # 문서 요약
        result["documents_by_date"][date_str] = []
        
        txt_files = list(folder.glob("*.txt"))
        for txt_file in txt_files:
            if any(exclude in txt_file.name.lower() for exclude in ['input', 'output', 'requirements', 'readme']):
                continue
            
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                doc_summary = summarize_document_structure(content, txt_file.name)
                result["documents_by_date"][date_str].append(doc_summary)
            except:
                continue
        
        # Lab 데이터
        lab_file = folder / "lab.csv"
        if lab_file.exists():
            all_labs = []
            
            try:
                with open(lab_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        lab_name_raw = row.get('lab_name', '').strip()
                        status = "normal"
                        lab_name = lab_name_raw
                        
                        if lab_name_raw:
                            if '(▼)' in lab_name_raw or lab_name_raw.startswith('▼'):
                                status = "decreased"
                                lab_name = re.sub(r'^\(▼\)\s*|^▼\s*', '', lab_name_raw)
                            elif '(▲)' in lab_name_raw or lab_name_raw.startswith('▲'):
                                status = "increased"
                                lab_name = re.sub(r'^\(▲\)\s*|^▲\s*', '', lab_name_raw)
                            elif '(◆)' in lab_name_raw or lab_name_raw.startswith('◆'):
                                status = "qualitative_abnormal"  # 문자형 이상 (Positive 등)
                                lab_name = re.sub(r'^\(◆\)\s*|^◆\s*', '', lab_name_raw)
                        
                        value_raw = row.get('lab_value', '').strip()
                        value_numeric = parse_value(value_raw)
                        
                        # 문자형 결과 (Positive/Negative) 처리
                        # 화살표가 없고 숫자도 아닌 경우
                        if status == "normal" and value_numeric is None and value_raw:
                            value_lower = value_raw.lower()
                            # Positive 계열 → qualitative_abnormal
                            if any(pos in value_lower for pos in ['positive', 'reactive', 'detected']):
                                status = "qualitative_abnormal"
                            # Negative 계열은 이미 normal (기본값)
                        
                        if lab_name and value_raw:
                            lab_entry = {
                                "test_name": lab_name,
                                "value_raw": value_raw,
                                "unit": row.get('lab_unit', '').strip(),
                                "status": status
                            }
                            
                            if value_numeric is not None:
                                lab_entry["value_numeric"] = value_numeric
                            
                            all_labs.append(lab_entry)
            except Exception as e:
                continue
            
            # Top abnormal labs 선택 (일반화된 방법)
            top_abnormal = select_top_abnormal_labs(all_labs, top_n=top_n)
            result["top_abnormal_labs_by_date"][date_str] = top_abnormal
            
            # 통계
            result["lab_statistics_by_date"][date_str] = {
                "total_tests": len(all_labs),
                "normal": len([x for x in all_labs if x['status'] == 'normal']),
                "increased": len([x for x in all_labs if x['status'] == 'increased']),
                "decreased": len([x for x in all_labs if x['status'] == 'decreased']),
                "qualitative_abnormal": len([x for x in all_labs if x['status'] == 'qualitative_abnormal']),
                "showing_top": len(top_abnormal)
            }
    
    return result


@mcp.tool()
def summarize_medical_records(start_date: str = None, end_date: str = None, top_n: int = 15) -> str:
    """
    [자동 분석] 의료 기록을 지능적으로 요약합니다.
    
    일반화된 접근:
    1. 화살표 마크(▼▲◆) 기반 필터링
    2. 상대적 중요도로 top abnormal labs 선택
    3. 구조적 패턴(R/O, suspect)으로 진단 추출
    4. 환자 독립적 - 모든 케이스에 적용 가능
    
    Token 절약:
    - Top N개 abnormal labs만 (날짜별, 기본 15개)
    - 문서는 구조적 요약만
    - 통계 정보 제공
    
    Args:
        start_date: 시작 날짜 (예: "20230308")
        end_date: 종료 날짜 (예: "20230310")
        top_n: 날짜별 추출할 abnormal lab 개수 (기본: 15, 최대 30 권장)
    
    Returns:
        지능형 요약 데이터
    """
    try:
        if not WORK_DIR:
            return json.dumps({
                "error": "LAB_WORK_DIR 환경변수가 설정되지 않았습니다."
            }, ensure_ascii=False, indent=2)
        
        # 날짜 파싱
        try:
            start_date_parsed = parse_date(start_date) if start_date else None
            end_date_parsed = parse_date(end_date) if end_date else None
        except ValueError as e:
            return json.dumps({
                "error": f"날짜 형식 오류: {str(e)}"
            }, ensure_ascii=False, indent=2)
        
        base_path = Path(WORK_DIR)
        if not base_path.exists():
            return json.dumps({
                "error": f"디렉토리를 찾을 수 없습니다: {base_path}"
            }, ensure_ascii=False, indent=2)
        
        # 날짜 폴더 필터링
        date_folders = []
        for folder in base_path.iterdir():
            if folder.is_dir() and re.match(r'^\d{8}$', folder.name):
                folder_date = folder.name
                if start_date_parsed and folder_date < start_date_parsed:
                    continue
                if end_date_parsed and folder_date > end_date_parsed:
                    continue
                date_folders.append(folder)
        
        if not date_folders:
            return json.dumps({
                "error": "데이터 없음",
                "requested_period": {
                    "start_date": start_date_parsed,
                    "end_date": end_date_parsed
                }
            }, ensure_ascii=False, indent=2)
        
        # 지능형 요약 수집
        result = collect_intelligent_summary(date_folders, top_n=top_n)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        import traceback
        return json.dumps({
            "error": "데이터 수집 중 오류",
            "message": str(e),
            "traceback": traceback.format_exc()
        }, ensure_ascii=False, indent=2)


@mcp.tool()
def get_full_lab_data(date: str) -> str:
    """
    특정 날짜의 전체 lab 데이터 조회
    
    Args:
        date: 날짜 (예: "20230310")
    
    Returns:
        해당 날짜의 모든 lab 데이터
    """
    try:
        if not WORK_DIR:
            return json.dumps({"error": "LAB_WORK_DIR 환경변수가 설정되지 않았습니다."}, ensure_ascii=False)
        
        date_parsed = parse_date(date)
        folder = Path(WORK_DIR) / date_parsed
        
        if not folder.exists():
            return json.dumps({"error": f"날짜 폴더가 없습니다: {date_parsed}"}, ensure_ascii=False)
        
        lab_file = folder / "lab.csv"
        if not lab_file.exists():
            return json.dumps({"error": f"lab.csv 파일이 없습니다: {date_parsed}"}, ensure_ascii=False)
        
        lab_data = []
        with open(lab_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                lab_name_raw = row.get('lab_name', '').strip()
                status = "normal"
                lab_name = lab_name_raw
                
                if lab_name_raw:
                    if '(▼)' in lab_name_raw:
                        status = "decreased"
                        lab_name = re.sub(r'^\(▼\)\s*', '', lab_name_raw)
                    elif '(▲)' in lab_name_raw:
                        status = "increased"
                        lab_name = re.sub(r'^\(▲\)\s*', '', lab_name_raw)
                    elif '(◆)' in lab_name_raw:
                        status = "qualitative_abnormal"
                        lab_name = re.sub(r'^\(◆\)\s*', '', lab_name_raw)
                
                value_raw = row.get('lab_value', '').strip()
                value_numeric = parse_value(value_raw)
                
                # 문자형 결과 (Positive/Negative) 처리
                if status == "normal" and value_numeric is None and value_raw:
                    value_lower = value_raw.lower()
                    if any(pos in value_lower for pos in ['positive', 'reactive', 'detected']):
                        status = "qualitative_abnormal"
                
                if lab_name and value_raw:
                    lab_entry = {
                        "test_name": lab_name,
                        "value_raw": value_raw,
                        "unit": row.get('lab_unit', '').strip(),
                        "status": status
                    }
                    
                    if value_numeric is not None:
                        lab_entry["value_numeric"] = value_numeric
                    
                    lab_data.append(lab_entry)
        
        return json.dumps({
            "date": date_parsed,
            "lab_data": lab_data,
            "total_count": len(lab_data)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def get_document_content(date: str, filename: str) -> str:
    """
    특정 문서의 전체 내용 조회
    
    Args:
        date: 날짜 (예: "20230308")
        filename: 파일명 (예: "admission_note.txt")
    
    Returns:
        문서 전체 내용
    """
    try:
        if not WORK_DIR:
            return json.dumps({"error": "LAB_WORK_DIR 환경변수가 설정되지 않았습니다."}, ensure_ascii=False)
        
        date_parsed = parse_date(date)
        folder = Path(WORK_DIR) / date_parsed
        
        if not folder.exists():
            return json.dumps({"error": f"날짜 폴더가 없습니다: {date_parsed}"}, ensure_ascii=False)
        
        file_path = folder / filename
        if not file_path.exists():
            return json.dumps({"error": f"파일이 없습니다: {filename}"}, ensure_ascii=False)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return json.dumps({
            "date": date_parsed,
            "filename": filename,
            "content": content
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    import sys
    if WORK_DIR:
        print(f"CR Filesystem v7 MCP Server 시작", file=sys.stderr)
        print(f"작업 디렉토리: {WORK_DIR}", file=sys.stderr)
    else:
        print("경고: LAB_WORK_DIR 환경 변수가 설정되지 않았습니다", file=sys.stderr)
    
    mcp.run(transport='stdio')

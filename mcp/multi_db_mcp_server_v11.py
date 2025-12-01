# multi_db_mcp_server_v10.py
"""
Medical Literature Search MCP Server v10
의학 문헌 검색 MCP 서버 v10

=== When to Use This MCP Server / 이 MCP 서버를 언제 사용해야 하나요? ===

** English **
Use this server when you need to:
1. Search medical literature across PubMed, PMC, and KoreaMed databases
2. Find case reports for specific clinical presentations or rare diseases
3. Get comprehensive search results with query translation from each database
4. Need to construct complex Boolean queries for PubMed (AND, OR, NOT operators)
5. Want to see how each search engine interprets your query
6. Need links to external search pages for exploring more results beyond token limits

Best for:
- Clinical case research and differential diagnosis
- Medical literature review with specific search criteria
- Finding Korean medical journal articles (via KoreaMed)
- Systematic searches requiring query transparency

** 한국어 **
다음과 같은 경우 이 서버를 사용하세요:
1. PubMed, PMC, KoreaMed 데이터베이스에서 의학 문헌 검색이 필요할 때
2. 특정 임상 증상이나 희귀 질환의 증례 보고를 찾을 때
3. 각 검색 엔진에서 쿼리가 어떻게 해석되는지 확인하고 싶을 때
4. PubMed에서 복잡한 Boolean 쿼리(AND, OR, NOT 연산자)를 사용해야 할 때
5. 토큰 제한을 넘어 더 많은 결과를 탐색하기 위한 외부 검색 링크가 필요할 때

적합한 사용 사례:
- 임상 증례 연구 및 감별 진단
- 특정 검색 조건을 가진 의학 문헌 리뷰
- 한국 의학 저널 논문 검색 (KoreaMed 통해)
- 쿼리 투명성이 필요한 체계적 검색

=== Key Features / 주요 기능 ===
✅ No query simplification - your query is used exactly as written
   쿼리 간소화 없음 - 입력한 쿼리를 그대로 사용
✅ Query translation provided from each search engine
   각 검색 엔진의 쿼리 변환 결과 제공
✅ External search links for exploring more results
   더 많은 결과 탐색을 위한 외부 검색 링크
✅ Detailed PubMed query construction guide
   상세한 PubMed 쿼리 작성 가이드
✅ Token-efficient compact output format
   토큰 효율적인 간결한 출력 형식
✅ Fixed: Search result ordering now preserved (relevance-based)
   수정됨: 검색 결과 순서 유지 (관련성 기반)
✅ Fixed: Field tags use full form for PMC compatibility
   수정됨: PMC 호환성을 위해 필드 태그는 전체 형식 사용
"""

from fastmcp import FastMCP
import requests
import re
from typing import List, Dict, Optional
from collections import defaultdict
import xml.etree.ElementTree as ET
from urllib.parse import quote
import time
from bs4 import BeautifulSoup

mcp = FastMCP("Medical Literature Search Engine v11")

# 설정
TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# PubMed 쿼리 작성 상세 가이드 (고급 사용자용, PubMed 전용)
PUBMED_QUERY_TIPS = """
# PubMed Advanced Query Construction Guide
# PubMed 고급 쿼리 작성 가이드

⚠️ **Note**: This guide is for PubMed-specific queries. For general usage examples across all databases, use `get_query_examples()`.
⚠️ **참고**: 이 가이드는 PubMed 전용 쿼리입니다. 모든 데이터베이스에서 사용 가능한 일반 예시는 `get_query_examples()`를 사용하세요.

## Purpose / 목적
This guide provides **PubMed-specific advanced query patterns** for users who want to:
이 가이드는 다음을 원하는 사용자를 위한 **PubMed 전용 고급 쿼리 패턴**을 제공합니다:
- Construct complex Boolean queries / 복잡한 Boolean 쿼리 작성
- Use PubMed field tags and MeSH terms / PubMed 필드 태그와 MeSH 용어 사용
- Fine-tune search precision / 검색 정확도 미세 조정

## 기본 원칙
PubMed는 강력한 Boolean 검색과 필드 태그를 지원합니다.

## 1. 필수 증상 포함 + Case Reports 정확한 검색
**패턴:** `A[Title/Abstract] AND (A[Title/Abstract] OR B[Title/Abstract] OR C[Title/Abstract]) AND (case reports[Publication Type] OR "case report"[Title])`

**예시:**
```
Autoimmune encephalitis[Title/Abstract] 
AND (Autoimmune encephalitis[Title/Abstract] OR seizure[Title/Abstract] OR confusion[Title/Abstract])
AND (case reports[Publication Type] OR "case report"[Title])
```

**설명:**
- `A[Title/Abstract]`: 주요 진단명은 반드시 제목이나 초록에 포함
- `(B OR C OR D)[Title/Abstract]`: 관련 증상 중 하나 이상 포함
- `case reports[Publication Type]`: Publication Type이 "Case Reports"
- `"case report"[Title]`: 제목에 "case report"라는 정확한 구문 포함

## 2. 배제 증상 지정 + Case Reports (NOT 사용)
**패턴:** `A[Title/Abstract] AND (B[Title/Abstract] OR C[Title/Abstract]) NOT (D[Title/Abstract] OR E[Title/Abstract]) AND (case reports[Publication Type] OR "case report"[Title])`

**예시:**
```
Vasculitis[Title/Abstract]
AND (fever[Title/Abstract] OR rash[Title/Abstract])
NOT (lupus[Title/Abstract] OR drug-induced[Title/Abstract])
AND (case reports[Publication Type] OR "case report"[Title])
```

**설명:**
- `NOT (D OR E)`: 특정 원인이나 진단을 배제
- Lupus나 약물 유발 혈관염을 제외
- 더 specific한 case report 검색 가능

## 3. MeSH Term + Textword 조합 (Recall & Precision 균형)
**패턴:** `(A[MeSH Terms] OR A[Title/Abstract] OR B[Title/Abstract]) AND case reports[Publication Type]`

**예시:**
```
(Sarcoidosis[MeSH Terms] OR Sarcoidosis[Title/Abstract] OR "granulomatous disease"[Title/Abstract])
AND case reports[Publication Type]
```

**설명:**
- `[MeSH Terms]`: MeSH (Medical Subject Headings) - 표준화된 의학 용어
- `[Title/Abstract]`: 자유 텍스트 검색
- 두 가지를 OR로 결합하여 Recall 향상 (MeSH로 놓친 논문 포착)
- MeSH는 정확하지만 제한적, Title/Abstract는 포괄적이지만 노이즈 가능
- 이 조합으로 균형잡힌 검색 결과

## 필드 태그 종류
- `[Title/Abstract]`: 제목 또는 초록 (약어: tiab)
- `[Title]`: 제목만 (약어: ti)
- `[Abstract]`: 초록만 (약어: ab)
- `[MeSH Terms]`: MeSH 용어 (약어: mh)
- `[Publication Type]`: 출판 유형 (약어: pt)
- `[Author]`: 저자명 (약어: au)
- `[Journal]`: 저널명 (약어: ta)
- `[Date - Publication]`: 출판일 (약어: dp)

**⚠️ Important**: Use **full form** field tags (e.g., `[Title/Abstract]`) for better compatibility with PMC searches.
**⚠️ 중요**: PMC 검색과의 호환성을 위해 **전체 형식** 필드 태그(예: `[Title/Abstract]`)를 사용하세요.

## Boolean 연산자 우선순위
1. NOT (가장 높음)
2. AND
3. OR (가장 낮음)

**괄호 사용으로 명시적 우선순위 지정 권장!**

## 추가 팁
- 구문 검색: `"exact phrase"` 큰따옴표 사용
- 와일드카드: `cardi*` (cardiology, cardiac, cardiovascular 등)
- 날짜 범위: `2020:2024[Date - Publication]`
- 최근 논문: `("last 5 years"[Date - Publication])`
"""


def clean_text(text: str) -> str:
    """텍스트 정리 - HTML 태그 제거 및 공백 정리"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_summary(abstract: str, max_words: int = 70) -> str:
    """
    Abstract에서 요약 추출 (70단어 이하)
    토큰 효율성을 위해 긴 초록을 간결하게 요약
    """
    if not abstract or abstract == "No abstract":
        return "No abstract available"
    
    # 문장 분리
    sentences = re.split(r'[.!?]\s+', abstract)
    summary = ""
    word_count = 0
    
    for sentence in sentences[:3]:  # 최대 3문장
        words = sentence.split()
        if word_count + len(words) <= max_words:
            summary += sentence + ". "
            word_count += len(words)
        else:
            break
    
    if not summary:
        # 첫 문장이 70단어 초과하는 경우
        words = sentences[0].split()[:max_words]
        summary = " ".join(words) + "..."
    
    return summary.strip()


def format_results_compact(results: List[Dict]) -> str:
    """
    토큰 효율적인 간결한 테이블 출력
    제목, 요약(70단어), 링크만 표시
    """
    if not results:
        return "No results found."
    
    output = "## Results\n\n"
    output += "| Title | Summary (≤70 words) | Link |\n"
    output += "|-------|---------------------|------|\n"
    
    for article in results:
        title = article['title']
        summary = extract_summary(article.get('abstract', ''), max_words=70)
        link = f"[{article['id']}]({article['url']})"
        
        # 테이블 셀에서 파이프 문자 이스케이프
        title = title.replace('\n', ' ').replace('|', '\\|')
        summary = summary.replace('\n', ' ').replace('|', '\\|')
        
        output += f"| {title} | {summary} | {link} |\n"
    
    return output


def generate_execution_summary(search_details: List[Dict], debug_info: Dict = None) -> str:
    """
    검색 실행 상세 정보 요약
    - 각 데이터베이스에서 실제 실행된 쿼리
    - QueryTranslation 정보
    - 결과 수
    - 외부 검색 링크
    - 디버깅 정보 (선택적)
    """
    output = "## Search Execution Summary\n\n"
    output += "| Database | Query Used | Query Translation | Results | Status |\n"
    output += "|----------|------------|-------------------|---------|--------|\n"
    
    for detail in search_details:
        db = detail['database']
        query = detail['executed_query']
        
        # Query가 너무 길면 줄임
        if len(query) > 50:
            query_display = query[:50] + "..."
        else:
            query_display = query
        
        # QueryTranslation 표시
        translation = detail.get('query_translation', 'N/A')
        if len(translation) > 50:
            translation = translation[:50] + "..."
        
        count = detail['result_count']
        
        # Status 아이콘
        if count > 0:
            status = "✅ Success"
        else:
            status = "❌ No results"
        
        output += f"| {db} | `{query_display}` | {translation} | {count} | {status} |\n"
    
    output += "\n"
    
    # 외부 검색 링크 제공 (더 많은 결과 탐색)
    output += "### 🔗 Search More Results Externally\n\n"
    output += "Due to token limitations, only a subset of results is shown. "
    output += "Use these direct links to explore more results:\n\n"
    
    for detail in search_details:
        if detail['result_count'] > 0:
            db = detail['database']
            query = detail['executed_query']
            
            if db == "PubMed":
                url = f"https://pubmed.ncbi.nlm.nih.gov/?term={quote(query)}"
                output += f"- **{db}**: [Search on PubMed]({url})\n"
            elif db == "PMC":
                url = f"https://www.ncbi.nlm.nih.gov/pmc/?term={quote(query)}"
                output += f"- **{db}**: [Search on PMC]({url})\n"
            elif db == "KoreaMed":
                url = f"https://koreamed.org/SearchBasic.php?RID=0&DT=1&QY={quote(query)}"
                output += f"- **{db}**: [Search on KoreaMed]({url})\n"
    
    output += "\n"
    
    # 디버깅 정보 추가 (PMC ID 통계)
    if debug_info and "pmc_id_stats" in debug_info:
        stats = debug_info["pmc_id_stats"]
        if stats["with_pmc_id"] > 0 or stats["pmid_fallback"] > 0:
            output += "### 🔍 PMC Search Details\n\n"
            output += f"- **With PMC ID**: {stats['with_pmc_id']} articles (full-text available on PMC)\n"
            output += f"- **PMID Fallback**: {stats['pmid_fallback']} articles (PubMed links, no PMC full-text)\n\n"
    
    return output


class DatabaseSearcher:
    """각 데이터베이스 검색을 담당하는 클래스"""
    
    def __init__(self):
        self.results = []
        self.errors = []
        self.search_details = []  # 검색 상세 정보
        self.debug_info = {"pmc_id_stats": {"with_pmc_id": 0, "pmid_fallback": 0}}  # 디버깅 정보
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
    
    def search_pubmed(
        self, 
        query: str, 
        max_results: int = 20,
        publication_types: List[str] = None
    ) -> List[Dict]:
        """
        PubMed 검색
        - 사용자 Query를 그대로 사용 (간소화 없음)
        - QueryTranslation 추출 및 반환
        """
        results = []
        query_translation = "N/A"
        
        try:
            print(f"  🔍 Searching PubMed...")
            print(f"      Query: {query[:100]}...")
            
            # 1. 검색 수행
            search_response = self.session.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={
                    "db": "pubmed",
                    "term": query,
                    "retmax": max_results,
                    "retmode": "json",
                    "sort": "relevance"
                },
                timeout=TIMEOUT
            )
            
            if search_response.status_code == 200:
                search_data = search_response.json().get("esearchresult", {})
                pmids = search_data.get("idlist", [])
                
                # QueryTranslation 추출
                query_translation = search_data.get("querytranslation", "N/A")
                
                if pmids:
                    # 2. 논문 상세 정보 가져오기
                    fetch_response = self.session.get(
                        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                        params={
                            "db": "pubmed",
                            "id": ",".join(pmids),
                            "retmode": "xml"
                        },
                        timeout=TIMEOUT
                    )
                    
                    if fetch_response.status_code == 200:
                        results = self._parse_pubmed_xml(fetch_response.text, pmids)
                        print(f"      ✅ Found {len(results)} results")
                        print(f"      QueryTranslation: {query_translation[:100]}...")
                else:
                    print(f"      ℹ️ No results found")
            else:
                print(f"      ❌ Search failed (HTTP {search_response.status_code})")
            
            # 검색 상세 기록
            self.search_details.append({
                "database": "PubMed",
                "original_query": query,
                "executed_query": query,  # 그대로 사용
                "query_translation": query_translation,
                "result_count": len(results)
            })
                
        except Exception as e:
            print(f"      ❌ Error: {str(e)}")
            self.errors.append({"database": "PubMed", "error": str(e)})
        
        return results
    
    def _parse_pubmed_xml(self, xml_text: str, pmids: List[str]) -> List[Dict]:
        """PubMed XML 파싱 - 원래 pmids 순서 유지"""
        articles_dict = {}  # PMID를 키로 하는 딕셔너리
        
        try:
            root = ET.fromstring(xml_text)
            for article_elem in root.findall('.//PubmedArticle'):
                pmid_elem = article_elem.find('.//PMID')
                if pmid_elem is None:
                    continue
                
                pmid = pmid_elem.text
                if pmid not in pmids:
                    continue
                
                # 제목 추출 - text가 None이거나 비어있거나 [Not Available]인 경우 처리
                title_elem = article_elem.find('.//ArticleTitle')
                title = None
                if title_elem is not None and title_elem.text:
                    title_text = clean_text(title_elem.text)
                    # [Not Available]이나 비슷한 경우는 제목으로 인정하지 않음
                    if title_text and title_text not in ["[Not Available].", "[Not Available]", "Not Available"]:
                        title = title_text
                
                # 제목이 없는 경우, Abstract의 첫 문장 사용
                if not title:
                    abstract_elem = article_elem.find('.//AbstractText')
                    if abstract_elem is not None and abstract_elem.text:
                        first_sentence = clean_text(abstract_elem.text).split('.')[0][:100]
                        title = f"{first_sentence}..."
                    else:
                        title = f"[No title available - PMID:{pmid}]"
                
                abstract_parts = [clean_text(elem.text) for elem in article_elem.findall('.//AbstractText') if elem.text]
                abstract = " ".join(abstract_parts) if abstract_parts else "No abstract"
                
                year_elem = article_elem.find('.//PubDate/Year')
                year = year_elem.text if year_elem is not None else "Unknown"
                
                journal_elem = article_elem.find('.//Journal/Title')
                journal = clean_text(journal_elem.text if journal_elem is not None else "Unknown")
                
                authors = []
                for author_elem in article_elem.findall('.//Author'):
                    lastname = author_elem.find('LastName')
                    if lastname is not None and lastname.text:
                        authors.append(lastname.text)
                author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
                
                # 딕셔너리에 저장 (순서 무관)
                articles_dict[pmid] = {
                    "id": f"PMID:{pmid}",
                    "title": title,
                    "abstract": abstract,
                    "year": year,
                    "journal": journal,
                    "authors": author_str,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "source": "PubMed"
                }
        except Exception as e:
            print(f"      ⚠️ XML parsing error: {e}")
        
        # ✅ 원래 pmids 순서대로 재정렬
        articles = [articles_dict[pmid] for pmid in pmids if pmid in articles_dict]
        return articles
    
    def search_pmc(
        self, 
        query: str, 
        max_results: int = 20
    ) -> List[Dict]:
        """
        PMC 검색
        - 사용자 Query를 그대로 사용 (간소화 없음)
        - QueryTranslation 추출 및 반환
        """
        results = []
        query_translation = "N/A"
        
        try:
            print(f"  🔍 Searching PMC...")
            print(f"      Query: {query[:100]}...")
            
            # 1. 검색 수행
            search_response = self.session.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={
                    "db": "pmc",
                    "term": query,
                    "retmax": max_results,
                    "retmode": "json"
                },
                timeout=TIMEOUT
            )
            
            if search_response.status_code == 200:
                search_data = search_response.json().get("esearchresult", {})
                pmcids = search_data.get("idlist", [])
                
                # QueryTranslation 추출
                query_translation = search_data.get("querytranslation", "N/A")
                
                if pmcids:
                    # 2. 논문 상세 정보 가져오기
                    fetch_response = self.session.get(
                        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                        params={
                            "db": "pmc",
                            "id": ",".join(pmcids),
                            "retmode": "xml"
                        },
                        timeout=TIMEOUT
                    )
                    
                    if fetch_response.status_code == 200:
                        results = self._parse_pmc_xml(fetch_response.text, pmcids)
                        print(f"      ✅ Found {len(results)} results")
                        print(f"      QueryTranslation: {query_translation[:100]}...")
                else:
                    print(f"      ℹ️ No results found")
            else:
                print(f"      ❌ Search failed (HTTP {search_response.status_code})")
            
            # 검색 상세 기록
            self.search_details.append({
                "database": "PMC",
                "original_query": query,
                "executed_query": query,  # 그대로 사용
                "query_translation": query_translation,
                "result_count": len(results)
            })
                
        except Exception as e:
            print(f"      ❌ Error: {str(e)}")
            self.errors.append({"database": "PMC", "error": str(e)})
        
        return results
    
    def _parse_pmc_xml(self, xml_text: str, pmcids: List[str]) -> List[Dict]:
        """PMC XML 파싱 - PMC ID 우선, 없으면 PMID 사용 (Fallback), 원래 pmcids 순서 유지"""
        articles_dict = {}  # PMC ID를 키로 하는 딕셔너리
        pmcid_mapping = {}  # article 요소를 PMC ID로 매핑
        
        try:
            root = ET.fromstring(xml_text)
            
            for article_elem in root.findall('.//article'):
                # PMC ID와 PubMed ID 찾기
                # 우선순위: PMC ID > PMID
                pmc_id = None
                pmid = None
                
                # 모든 article-id를 순회하며 PMC ID와 PMID를 찾음
                for article_id in article_elem.findall('.//article-id'):
                    id_type = article_id.get('pub-id-type')
                    
                    # PMC ID 찾기 (pmc, pmcid 둘 다 확인)
                    if id_type in ['pmc', 'pmcid']:
                        pmc_id = article_id.text
                        if pmc_id and pmc_id.startswith('PMC'):
                            pmc_id = pmc_id[3:]  # 'PMC' 접두사 제거
                    
                    # PubMed ID도 저장 (PMC ID가 없을 때 대체용)
                    elif id_type == 'pmid':
                        pmid = article_id.text
                
                # PMC ID도 PMID도 없으면 건너뜀
                if not pmc_id and not pmid:
                    print(f"      ⚠️ Skipping article without any ID")
                    continue
                
                # 제목
                title_elem = article_elem.find('.//article-title')
                title = clean_text(title_elem.text if title_elem is not None else "No title")
                
                # 초록
                abstract_parts = []
                abstract_elem = article_elem.find('.//abstract')
                if abstract_elem is not None:
                    for p_elem in abstract_elem.findall('.//p'):
                        if p_elem.text:
                            abstract_parts.append(clean_text(p_elem.text))
                
                abstract = " ".join(abstract_parts) if abstract_parts else "No abstract available"
                
                # 출판 연도
                year = "Unknown"
                pub_date = article_elem.find('.//pub-date')
                if pub_date is not None:
                    year_elem = pub_date.find('year')
                    if year_elem is not None and year_elem.text:
                        year = year_elem.text
                
                # 저널
                journal_elem = article_elem.find('.//journal-title')
                journal = clean_text(journal_elem.text if journal_elem is not None else "Unknown Journal")
                
                # 저자
                authors = []
                for contrib_elem in article_elem.findall('.//contrib[@contrib-type="author"]'):
                    surname_elem = contrib_elem.find('.//surname')
                    if surname_elem is not None and surname_elem.text:
                        authors.append(surname_elem.text)
                author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
                
                # PMC ID가 있으면 PMC 링크, 없으면 PubMed 링크 사용
                if pmc_id:
                    article_id = f"PMC{pmc_id}"
                    article_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/"
                    source = "PMC"
                    self.debug_info["pmc_id_stats"]["with_pmc_id"] += 1
                    # 디버깅: PMC ID 확인
                    print(f"      ✅ PMC ID found: PMC{pmc_id} - {title[:40]}...")
                    
                    # PMC ID를 키로 저장
                    lookup_id = pmc_id
                else:
                    # PMC ID가 없고 PMID만 있는 경우 (Fallback)
                    article_id = f"PMID:{pmid}"
                    article_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    source = "PMC (via PubMed)"  # 출처 표시
                    self.debug_info["pmc_id_stats"]["pmid_fallback"] += 1
                    # 디버깅: Fallback 사용
                    print(f"      ⚠️ No PMC ID, using PMID:{pmid} - {title[:40]}...")
                    
                    # pmcids에는 PMC ID 형식으로 저장되어 있으므로 확인 필요
                    lookup_id = None
                    for pmcid in pmcids:
                        # pmcids 리스트에서 현재 article의 ID 찾기
                        # efetch는 PMC ID 숫자만 전달하므로 매칭 필요
                        if pmcid == pmc_id or (pmc_id and pmcid.endswith(pmc_id)):
                            lookup_id = pmcid
                            break
                    
                    if not lookup_id:
                        # PMC ID가 없으면 pmcids에서 순서대로 찾기 (fallback)
                        lookup_id = pmcids[len(articles_dict)] if len(articles_dict) < len(pmcids) else None
                
                if lookup_id:
                    # 딕셔너리에 저장 (순서 무관)
                    articles_dict[lookup_id] = {
                        "id": article_id,
                        "title": title,
                        "abstract": abstract,
                        "year": year,
                        "journal": journal,
                        "authors": author_str if author_str else "N/A",
                        "url": article_url,
                        "source": source
                    }
                
        except Exception as e:
            print(f"      ⚠️ PMC XML parsing error: {e}")
        
        # ✅ 원래 pmcids 순서대로 재정렬
        articles = [articles_dict[pmcid] for pmcid in pmcids if pmcid in articles_dict]
        return articles
    
    def search_koreamed(
        self, 
        query: str, 
        max_results: int = 20
    ) -> List[Dict]:
        """
        KoreaMed 검색
        - 사용자 Query를 그대로 사용 (간소화 없음)
        - HTML에서 QueryTranslation 추출 시도
        """
        results = []
        query_translation = "N/A"
        
        try:
            print(f"  🔍 Searching KoreaMed...")
            print(f"      Query: {query[:100]}...")
            
            # 검색 요청
            search_url = "https://koreamed.org/SearchBasic.php"
            data = {
                "query_search": query  # 사용자 쿼리 그대로 사용
            }
            
            response = self.session.post(search_url, data=data, timeout=TIMEOUT)
            
            if response.status_code == 200:
                html_content = response.text
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # QueryTranslation 추출 시도
                # KoreaMed는 검색창(input)의 value 속성에 변환된 쿼리가 들어있을 수 있음
                query_input = soup.find('input', {'name': 'query_search'})
                if query_input and query_input.get('value'):
                    query_translation = query_input.get('value')
                
                # 결과 추출 (Twitter 공유 링크 방식)
                twitter_links = soup.find_all('a', href=re.compile(r'twitter\.com/intent/tweet'))
                
                print(f"      Found {len(twitter_links)} potential results")
                
                for link in twitter_links[:max_results]:
                    href = link.get('href', '')
                    
                    # RID 추출
                    rid_match = re.search(r'RID%3D(\d+)', href)
                    if not rid_match:
                        continue
                    
                    rid = rid_match.group(1)
                    
                    # 제목 추출
                    text_match = re.search(r'text=([^&]+)', href)
                    if text_match:
                        encoded_text = text_match.group(1)
                        title_part = encoded_text.split('%0A')[0]
                        title = requests.utils.unquote(title_part.replace('+', ' '))
                    else:
                        title = "Unknown"
                    
                    article_url = f"https://koreamed.org/SearchBasic.php?RID={rid}"
                    
                    results.append({
                        "id": f"KM{rid}",
                        "title": clean_text(title),
                        "abstract": "KoreaMed article (full text available)",
                        "year": "N/A",
                        "journal": "Korean Medical Journal",
                        "authors": "N/A",
                        "url": article_url,
                        "source": "KoreaMed"
                    })
                
                if len(results) > 0:
                    print(f"      ✅ Found {len(results)} results")
                    if query_translation != "N/A":
                        print(f"      QueryTranslation: {query_translation[:100]}...")
                else:
                    print(f"      ℹ️ No results found")
            else:
                print(f"      ⚠️ Search failed (HTTP {response.status_code})")
            
            # 검색 상세 기록
            self.search_details.append({
                "database": "KoreaMed",
                "original_query": query,
                "executed_query": query,  # 그대로 사용
                "query_translation": query_translation,
                "result_count": len(results)
            })
                
        except Exception as e:
            print(f"      ❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.errors.append({"database": "KoreaMed", "error": str(e)})
        
        return results


def deduplicate_results(results: List[Dict]) -> List[Dict]:
    """
    중복 제거 - 제목 기준
    """
    seen_titles = set()
    unique_results = []
    
    for result in results:
        title_norm = result['title'].lower().strip()
        if title_norm not in seen_titles and title_norm not in ["no title", ""]:
            seen_titles.add(title_norm)
            unique_results.append(result)
    
    return unique_results


def summarize_search_stats(results: List[Dict], query: str, databases: List[str]) -> Dict:
    """검색 통계 요약"""
    stats = {
        "query": query,
        "total_results": len(results),
        "databases_searched": databases,
        "results_by_source": defaultdict(int)
    }
    
    for result in results:
        stats["results_by_source"][result['source']] += 1
    
    stats["results_by_source"] = dict(stats["results_by_source"])
    
    return stats


# ==================== MCP Tools ====================

@mcp.tool()
def search_literature(
    query: str,
    databases: Optional[List[str]] = None,
    max_results_per_db: int = 20,
    max_results_by_db: Optional[dict] = None,
    publication_types: Optional[List[str]] = None,
    return_format: str = "compact"
) -> dict:
    """
    Search medical literature across PubMed, PMC, and KoreaMed databases.
    의학 문헌 통합 검색 (PubMed, PMC, KoreaMed)
    
    ⚠️ Important: Your query is sent to each search engine exactly as written.
    ⚠️ 중요: 입력한 쿼리를 각 검색엔진에 그대로 전달합니다.
    
    Features / 기능:
    - No query simplification / 쿼리 간소화 없음
    - Query translation provided from each engine / 각 엔진의 쿼리 변환 결과 제공
    - External search links for more results / 더 많은 결과를 위한 외부 검색 링크
    
    Args:
        query: Search query (used exactly as written) / 검색 쿼리 (그대로 사용)
        databases: List of ["pubmed", "pmc", "koreamed"] (default: all)
        max_results_per_db: Max results per database (default: 20)
        max_results_by_db: Per-database settings {"pubmed": 20, "pmc": 15}
        publication_types: Filter by type ["Case Reports"], ["Review"], etc.
        return_format: "compact" (brief), "detailed" (full abstracts), "json"
    
    Returns:
        Search results + QueryTranslation + external search links
        검색 결과 + 쿼리 변환 + 외부 검색 링크
    """
    
    if databases is None:
        databases = ["pubmed", "pmc", "koreamed"]
    if publication_types is None:
        publication_types = []
    
    # 데이터베이스별 개수 설정
    db_max_results = {}
    if max_results_by_db:
        for db in databases:
            db_lower = db.lower()
            db_max_results[db_lower] = max_results_by_db.get(db_lower, 
                                        max_results_by_db.get(db.upper(), 
                                        max_results_by_db.get(db, max_results_per_db)))
    else:
        for db in databases:
            db_max_results[db.lower()] = max_results_per_db
    
    print(f"\n{'='*70}")
    print(f"🔍 Medical Literature Search v10")
    print(f"{'='*70}")
    print(f"Query: {query}")
    print(f"Databases: {', '.join(databases)}")
    print(f"⚠️ Using original query (no simplification)\n")
    
    searcher = DatabaseSearcher()
    all_results = []
    
    # 각 데이터베이스 검색
    for db in databases:
        db_lower = db.lower()
        db_max = db_max_results.get(db_lower, max_results_per_db)
        
        try:
            if db_lower == "pubmed":
                results = searcher.search_pubmed(query, db_max, publication_types=publication_types)
            elif db_lower == "pmc":
                results = searcher.search_pmc(query, db_max)
            elif db_lower == "koreamed":
                results = searcher.search_koreamed(query, db_max)
            else:
                continue
            
            all_results.extend(results)
            time.sleep(0.5)  # API 호출 제한 준수
            
        except Exception as e:
            print(f"  ❌ Error in {db}: {e}")
            searcher.errors.append({"database": db, "error": str(e)})
    
    # 중복 제거
    unique_results = deduplicate_results(all_results)
    
    # 통계
    stats = summarize_search_stats(unique_results, query, databases)
    
    # Search Execution Summary 생성 (디버깅 정보 포함)
    execution_summary = generate_execution_summary(searcher.search_details, searcher.debug_info)
    
    # 결과 포맷팅
    if return_format == "compact":
        formatted_output = execution_summary + "\n\n" + format_results_compact(unique_results)
        return {
            "success": True,
            "format": "compact",
            "query": query,
            "content": formatted_output,
            "statistics": stats,
            "errors": searcher.errors
        }
    elif return_format == "detailed":
        # 상세 형식 (초록 전체 포함)
        detailed_output = execution_summary + "\n\n## Detailed Results\n\n"
        for i, article in enumerate(unique_results, 1):
            detailed_output += f"### [{i}] {article['title']}\n\n"
            detailed_output += f"**ID:** {article['id']}  \n"
            detailed_output += f"**Source:** {article['source']}  \n"
            detailed_output += f"**Journal:** {article['journal']} ({article['year']})  \n"
            detailed_output += f"**Authors:** {article['authors']}  \n"
            detailed_output += f"**URL:** {article['url']}  \n\n"
            detailed_output += f"**Abstract:**  \n{article['abstract']}\n\n"
            detailed_output += "---\n\n"
        
        return {
            "success": True,
            "format": "detailed",
            "query": query,
            "content": detailed_output,
            "statistics": stats,
            "errors": searcher.errors
        }
    else:  # json
        return {
            "success": True,
            "format": "json",
            "query": query,
            "execution_summary": execution_summary,
            "statistics": stats,
            "results": unique_results,
            "errors": searcher.errors
        }


@mcp.tool()
def get_pubmed_query_guide() -> dict:
    """
    Get PubMed-specific advanced query construction guide.
    PubMed 전용 고급 쿼리 작성 가이드 보기
    
    **Purpose / 목적:**
    This guide is for **PubMed-specific advanced queries** with field tags and MeSH terms.
    For general query examples across all databases, use `get_query_examples()` instead.
    
    이 가이드는 필드 태그와 MeSH 용어를 사용하는 **PubMed 전용 고급 쿼리**를 위한 것입니다.
    모든 데이터베이스에서 사용 가능한 일반 예시는 `get_query_examples()`를 사용하세요.
    
    Provides 3 essential PubMed-specific patterns:
    3가지 필수 PubMed 전용 패턴 제공:
    1. Required symptoms + Case Reports with field tags / 필드 태그와 함께 필수 증상 + 증례 보고
    2. Excluding specific symptoms (NOT) with field tags / 필드 태그와 함께 특정 증상 배제 (NOT)
    3. MeSH + Textword combination / MeSH + 자유 텍스트 조합
    
    Returns:
        Comprehensive PubMed-specific query construction guide in Markdown
        Markdown 형식의 포괄적인 PubMed 전용 쿼리 작성 가이드
    """
    
    return {
        "success": True,
        "content": PUBMED_QUERY_TIPS,
        "guide_type": "PubMed Advanced Query Construction"
    }


@mcp.tool()
def get_query_examples(
    database: str = "all"
) -> dict:
    """
    Get practical search query examples for medical literature databases.
    의학 문헌 데이터베이스 실용적인 검색 쿼리 예시 보기
    
    **Purpose / 목적:**
    This function provides **ready-to-use query examples** for all databases (PubMed, PMC, KoreaMed).
    For PubMed-specific advanced query guide with field tags, use `get_pubmed_query_guide()` instead.
    
    이 함수는 모든 데이터베이스(PubMed, PMC, KoreaMed)에서 **바로 사용 가능한 쿼리 예시**를 제공합니다.
    필드 태그를 사용하는 PubMed 전용 고급 가이드는 `get_pubmed_query_guide()`를 사용하세요.
    
    Args:
        database: "pubmed", "pmc", "koreamed", or "all" (default: all)
    
    Returns:
        Ready-to-use query examples for each database with explanations
        각 데이터베이스별 바로 사용 가능한 쿼리 예시 및 설명
    """
    
    output = "# Medical Literature Search Query Examples\n"
    output += "# 의학 문헌 검색 쿼리 예시\n\n"
    
    output += "## Overview / 개요\n\n"
    output += "This guide provides **practical, ready-to-use examples** for all databases.\n"
    output += "이 가이드는 모든 데이터베이스에서 **바로 사용 가능한 실용적인 예시**를 제공합니다.\n\n"
    output += "**Note**: All examples use **full form field tags** (e.g., `[Title/Abstract]`) for compatibility with both PubMed and PMC.\n"
    output += "**참고**: 모든 예시는 PubMed와 PMC 모두와 호환되도록 **전체 형식 필드 태그**(예: `[Title/Abstract]`)를 사용합니다.\n\n"
    
    output += "## Database Comparison / 데이터베이스 비교\n\n"
    output += "1. **PubMed**: Complex Boolean queries supported, use field tags\n"
    output += "   **PubMed**: 복잡한 Boolean 쿼리 지원, 필드 태그 사용 가능\n"
    output += "2. **PMC**: Full-text search, simpler queries work well\n"
    output += "   **PMC**: 전문 검색, 단순한 쿼리가 효과적\n"
    output += "3. **KoreaMed**: Keep it simple, 1-3 keywords recommended\n"
    output += "   **KoreaMed**: 단순하게, 1-3개 키워드 권장\n\n"
    
    if database.lower() in ["pubmed", "all"]:
        output += "## PubMed Examples (PMC-Compatible)\n"
        output += "## PubMed 예시 (PMC 호환)\n\n"
        
        output += "### Example 1: Basic Case Report Search\n"
        output += "### 예시 1: 기본 증례 보고 검색\n"
        output += "```\n"
        output += "Autoimmune encephalitis[Title/Abstract]\n"
        output += "AND (seizure[Title/Abstract] OR confusion[Title/Abstract])\n"
        output += "AND \"case report\"[Title]\n"
        output += "```\n"
        output += "**Why full form?** `[Title/Abstract]` works in both PubMed and PMC, while `[tiab]` only works in PubMed.\n"
        output += "**왜 전체 형식?** `[Title/Abstract]`는 PubMed와 PMC 모두에서 작동하지만, `[tiab]`는 PubMed에서만 작동합니다.\n\n"
        
        output += "### Example 2: Excluding Common Causes\n"
        output += "### 예시 2: 일반적인 원인 제외\n"
        output += "```\n"
        output += "Vasculitis[Title/Abstract]\n"
        output += "AND (fever[Title/Abstract] OR rash[Title/Abstract])\n"
        output += "NOT (lupus[Title/Abstract] OR drug-induced[Title/Abstract])\n"
        output += "AND \"case report\"[Title]\n"
        output += "```\n\n"
        
        output += "### Example 3: Recent Publications\n"
        output += "### 예시 3: 최근 출판물\n"
        output += "```\n"
        output += "Sarcoidosis[Title/Abstract]\n"
        output += "AND \"case report\"[Title]\n"
        output += "AND (\"last 5 years\"[Date - Publication])\n"
        output += "```\n\n"
    
    if database.lower() in ["pmc", "all"]:
        output += "## PMC Examples\n"
        output += "## PMC 예시\n\n"
        
        output += "PMC is full-text search, so simpler queries work well.\n"
        output += "PMC는 전문 검색이므로 단순한 쿼리가 효과적입니다.\n\n"
        
        output += "### Example 1: Simple Phrase Search\n"
        output += "### 예시 1: 간단한 구문 검색\n"
        output += "```\n"
        output += "Autoimmune encephalitis AND \"case report\"\n"
        output += "```\n\n"
        
        output += "### Example 2: With Additional Keywords\n"
        output += "### 예시 2: 추가 키워드 포함\n"
        output += "```\n"
        output += "Vasculitis AND fever AND \"case report\"\n"
        output += "```\n\n"
    
    if database.lower() in ["koreamed", "all"]:
        output += "## KoreaMed Examples\n"
        output += "## KoreaMed 예시\n\n"
        
        output += "⚠️ **Important**: KoreaMed doesn't support complex queries well. Keep it simple!\n"
        output += "⚠️ **중요**: KoreaMed는 복잡한 쿼리방식이 PubMed와 달라 직접 탐색해야 합니다. 단순하게!\n\n"
        
        output += "### ✅ Recommended / 권장\n"
        output += "```\n"
        output += "Sarcoidosis\n"
        output += "Vasculitis AND fever\n"
        output += "Encephalitis case\n"
        output += "```\n\n"
        
        output += "### ❌ Not Recommended (different from PubMed's) / 비권장 (사용자 탐색 필요)\n"
        output += "```\n"
        output += "((Vasculitis OR inflammation) AND fever) NOT lupus\n"
        output += "Sarcoidosis[TI/AB] AND \"case report\"[TI]\n"
        output += "```\n\n"
    
    output += "## Key Differences / 주요 차이점\n\n"
    output += "| Feature | PubMed | PMC | KoreaMed |\n"
    output += "|---------|--------|-----|----------|\n"
    output += "| Field tags | ✅ Full form | ✅ Full form | ⚠️  supported but different|\n"
    output += "| Boolean operators | ✅ AND, OR, NOT | ✅ AND, OR, NOT | ⚠️  supported but different |\n"
    output += "| Phrase search | ✅ \"exact phrase\" | ✅ \"exact phrase\" | ⚠️ Limited |\n"
    output += "| Recommended complexity | High | Medium | Low |\n\n"
    
    output += "## Pro Tips / 전문가 팁\n\n"
    output += "1. **Cross-database searches**: Use full form field tags like `[Title/Abstract]` for queries that work in both PubMed and PMC\n"
    output += "   **다중 데이터베이스 검색**: PubMed와 PMC 모두에서 작동하는 쿼리를 위해 `[Title/Abstract]` 같은 전체 형식 필드 태그 사용\n\n"
    output += "2. **PubMed-only queries**: For PubMed-specific advanced queries, see `get_pubmed_query_guide()`\n"
    output += "   **PubMed 전용 쿼리**: PubMed 전용 고급 쿼리는 `get_pubmed_query_guide()` 참조\n\n"
    output += "3. **Start simple**: Begin with basic queries and add complexity as needed\n"
    output += "   **단순하게 시작**: 기본 쿼리로 시작하고 필요에 따라 복잡도 추가\n\n"
    
    return {
        "success": True,
        "content": output
    }


if __name__ == "__main__":
    mcp.run()

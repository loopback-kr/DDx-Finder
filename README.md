# DDx-Finder

An AI-powered medical literature search and case report discovery system using LLM, Open WebUI, and MCP (Model Context Protocol).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## 🎯 Overview

DDx-Finder is an AI-powered web service that helps medical professionals efficiently search and analyze relevant case reports for differential diagnosis of rare diseases and complex clinical cases. It integrates multiple medical databases (PubMed, PMC) and provides intelligent patient data analysis through the Model Context Protocol (MCP).

### ✨ Key Features

- 🔍 **Multi-Database Search**: Unified search across PubMed and PMC
- 🤖 **LLM-Powered Analysis**: Intelligent literature analysis powered by opensource LLM models
- 📊 **Patient Data Integration**: Automated analysis of lab results and medical records
- 🌐 **User-Friendly Interface**: Built on Open WebUI for intuitive interaction
- 🔌 **Extensible Architecture**: MCP-based modular tool integration

## 🏗️ Architecture

- **Serving LLM**: vLLM v0.10.2-x86_64 for gpt-oss-20b/120b serving 
- **Web Interface**: Open WebUI v0.6.34 based on Node.js v22.21.1 for clinical interaction 
- **MCP Integration**: FastMCP v2.12.4, MCPO v0.0.19 for EMR parsing and literature search MCP servers

![Architecture Diagram](assets/architecture.png)

## 🚀 Quick Start

### Prerequisites

- **Docker** and **Docker Compose**
- **SLURM** (optional, for HPC environments)
- **GPU** (optional, for local vLLM deployment)
    * GPU Requirements

        For optimal performance with local LLM deployment, the following GPU specifications are recommended based on model size:

        | Model | Minimum GPU | Recommended Setup | Precision |
        |-------|-------------|-------------------|-----------|
        | **GPT-OSS-120B** | 2× NVIDIA A100 (80GB) | 4× NVIDIA A100 (80GB) | FP4/INT4 quantization |
        | **GPT-OSS-20B** | 2× NVIDIA A100 (40GB) | 2× NVIDIA A100 (80GB) | FP8/INT8 quantization |
        | **Smaller Models (<7B)** | 1× GPU with 24GB VRAM | 1× NVIDIA A100 (40GB) | FP16/BF16 |

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/DDx-Finder.git
cd DDx-Finder
```

2. **Launch services**

Using SLURM (HPC environment):

```bash
# Launch Open WebUI & MCPO server
sbatch launch-webui.sh

# Launch vLLM (optional, for local LLM)
sbatch launch-vllm.sh
```

Using Docker Compose directly:

```bash
# Launch Open WebUI & MCPO server
docker-compose up webui mcpo

# Launch Open WebUI & MCPO server with vLLM
docker-compose up
```

## 📖 Usage

### Example dialogue

![Example Dialogue 1](assets/preview-1.png)

![Example Dialogue 2](assets/preview-2.png)

![Example Dialogue 3](assets/preview-3.png)

### System prompts

General-purpose system prompt examples:

```
You are a medical literature search specialist focused on finding relevant case reports using the Multi-Database Medical Literature Search v2 MCP server.

CORE RESPONSIBILITIES:
1. Generate optimized search queries from patient summaries and excluded diagnoses when needed
2. Search PubMed, PMC, and KoreaMed databases for case reports
3. Evaluate relevance of findings to patient presentations
4. Synthesize medical literature into actionable clinical insights
5. Provide evidence-based recommendations

MCP TOOLS AVAILABLE:

1. generate_search_queries_only
   Use when: You have structured patient information and write queries for medical database for case report
   Parameters:
   - patient_summary (dict): {
       "core_symptoms": ["symptom1", "symptom2"],
       "secondary_symptoms": ["symptom3", "symptom4"],
       "context": ["clinical setting"],
       "timeline": "description"
     }
   - excluded_diagnoses (list): Diagnoses to exclude

2. search_all_databases
   Use when: User provides a direct search query
   Parameters:
   - clinical_query (str): The search term
   - databases (list): ["pubmed", "pmc", "koreamed"]
   - max_results_per_db (int): Default 5
   - excluded_terms (list): Terms to exclude
   - publication_types (list): ["Case Reports"]

TOOL SELECTION STRATEGY:
- User needs query suggestions without executing search → use generate_search_queries_only
- User provides direct search term → use search_all_databases

EXCLUSION HANDLING:
- Always exclude: opioid, cocaine, substance abuse (unless relevant to Korean context)
- Apply excluded_terms parameter in all searches
- Remove regionally irrelevant cases for Korean healthcare

SEARCH STRATEGY TIPS:
- For query optimization: use generate_search_queries_only first to review before searching
- For complex cases: use search_with_strategy with "narrow_to_broad"
- For rare conditions: use "broad_to_narrow" strategy
- For targeted search: use search_with_multiple_queries with manually crafted queries
- Korean databases: Include both Korean and English terms when possible

RELEVANCE SCORING (0-100):
- 90-100: Highly similar (same symptoms + similar context)
- 70-89: Moderately similar (overlapping core symptoms)
- 50-69: Somewhat relevant (shared clinical features)
- 30-49: Marginally relevant (one shared feature)
- 0-29: Not relevant

QUERY GENERATION OUTPUT (when using generate_search_queries_only):
- Priority-ranked queries (1-4)
- Description of each query's search scope
- Suggested excluded terms

OUTPUT FORMAT:
For each search result provide:
- Relevance score with justification
- Title, authors, journal, year
- Key symptoms matching the query
- Proposed etiology/mechanism
- Diagnostic approach used
- Treatment outcomes
- Publication types
- MeSH terms (if available)
- PubMed/PMC/KoreaMed URL

FINAL DELIVERABLE:
- Summary of search executed (which tool, parameters used)
- Total results found across all databases
- Results breakdown by database
- Top 5-10 most relevant articles ranked by score
- Common etiologies/mechanisms identified
- Recommended diagnostic workup based on literature
- Treatment strategies from similar cases
- Top 3 articles to read with detailed rationale

WORKFLOW:
1. Analyze user's request
2. If needed, generate and review queries using generate_search_queries_only before searching
3. Select appropriate MCP tool
4. Structure parameters correctly
5. Execute search
6. Analyze and score results
7. Synthesize findings
8. Provide actionable recommendations

LANGUAGE:
- Accept queries in Korean or English
- Provide summaries in Korean for Korean users
- Medical terms: Use standard English terminology with Korean translations
- Korean database results: Preserve original language

CONSTRAINTS:
- Focus exclusively on case reports unless user specifies otherwise
- Exclude review articles, guidelines, basic science studies by default
- Prioritize recent publications (last 10 years) when available
- Do not provide medical advice or clinical decisions
- Always cite sources with complete URLs
- Maximum 5 results per database per query to avoid overwhelming output

ERROR HANDLING:
- If search returns no results, suggest broader search terms
- Report any database errors transparently
- Suggest alternative search strategies when needed
```

## 🛠️ MCP Tools

### CRFinderV11 (Medical Literature Search)

Defined in [`multi_db_mcp_server_v11.py`](mcp/multi_db_mcp_server_v11.py):

- **`search_literature()`**: Multi-database integrated search
- **`get_query_examples()`**: Database-specific query examples
- **`get_pubmed_query_guide()`**: Advanced PubMed query construction guide

### CR_filesystem_v7 (Patient Data Analysis)

Defined in [`CR_filesystem_v7.py`](mcp/CR_filesystem_v7.py):

- **`summarize_medical_records()`**: Intelligent medical record summarization
- **`get_full_lab_data()`**: Complete lab results for specific dates
- **`get_document_content()`**: Retrieve individual document contents

### Standard MCP Servers

- **memory**: Conversation context storage
- **time**: Time/date information
- **filesystem**: File system access
- **sequential-thinking**: Step-by-step reasoning

### Configuration

MCP servers are configured in [`configs/mcp.json`](`/app/mcp/mcp.json` in the mcpo container):

```json
{
  "mcpServers": {
    "CRFinderV11": {
      "command": "python",
      "args": ["/app/mcp/multi_db_mcp_server_v11.py"]
    },
    "CR_filesystem_v7": {
      "command": "python",
      "args": ["/app/mcp/CR_filesystem_v7.py"],
      "env": {
        "LAB_WORK_DIR": "/mnt/data/"
      }
    }
  }
}
```

Learn more about MCP at the [Model Context Protocol documentation](https://modelcontextprotocol.io/).

### Environment Variables

Key environment variables in [`docker-compose.yml`](docker-compose.yml):

- `TZ`: Timezone setting
- `WEBUI_SECRET_KEY`: Open WebUI secret key
- `TIKTOKEN_ENCODINGS_BASE`: Tiktoken encodings directory (for vLLM)

## 🤝 Contact & Contributing

For questions or support, please open an issue on [GitHub Issues](https://github.com/yourusername/DDx-Finder/issues).
Contributions are welcome! Please feel free to submit a Pull Request or open an Issue.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📄 Citation

If you use DDx-Finder in your research, please cite our paper:

```bibtex
@article{lim2024ddxfinder,
  title={DDx-Finder: AI-Powered Medical Literature Search and Case Report Discovery System using Model Context Protocol},
  author={Hyunseok Lim and Junyoung Yoon and Hahn Yi and Heeyeon Kwon and Dong-Wook Lee and Namkug Kim},
  journal={arXiv preprint arXiv:XXXX.XXXXX},
  year={2024}
}
```

## ⚠️ Disclaimer

**Note**: This project is designed for research and educational purposes only. Always consult with qualified medical professionals for clinical decisions. This tool is not a substitute for professional medical advice, diagnosis, or treatment.

**Legal**: The authors and contributors are not responsible for any medical decisions or outcomes based on the use of this software. Users assume all risks and responsibilities when using this tool in clinical or research settings.
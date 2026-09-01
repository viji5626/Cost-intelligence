# 10 — Comprehensive Risk Register & Mitigation Strategy

## 1. Risk Register Summary & Top 10 Risks

```text
+---------------------------------------------------------------------------------------------------+
|                                        TOP 10 PROJECT RISKS                                       |
+-----+-------------------------------------------------------+-------------+--------+--------------+
| ID  | RISK DESCRIPTION                                      | PROBABILITY | IMPACT | EXPOSURE     |
+-----+-------------------------------------------------------+-------------+--------+--------------+
| R01 | Missed Existing Implementation (False "New" Decision) | High        | High   | CRITICAL     |
| R02 | Deterministic Financial Calculation Skew (Unit Error) | Medium      | High   | CRITICAL     |
| R03 | AI Hallucination of Engineering Citations or Costs    | Medium      | High   | CRITICAL     |
| R04 | Local AI Runtime GPU VRAM Exhaustion / OOM Crash      | Medium      | High   | HIGH         |
| R05 | Inadvertent Cloud Egress Leak in Air-Gapped Mode      | Low         | High   | HIGH         |
| R06 | Context Window Bloat & Lost-in-the-Middle Retrieval   | Medium      | Medium | HIGH         |
| R07 | Dirty / Inconsistent Plant Spreadsheet Ingestion      | High        | Medium | HIGH         |
| R08 | Unbounded Tool Execution Loop in Agentic Queries      | Medium      | Medium | MEDIUM       |
| R09 | Client Production Data Delay / NDA Stalling           | High        | Medium | MEDIUM       |
| R10 | UI Performance Degradation on 10,000 Idea Data Grids  | Medium      | Medium | MEDIUM       |
+-----+-------------------------------------------------------+-------------+--------+--------------+
```

---

## 2. Detailed Risk Register

| Risk ID | Category | Risk Description | Prob. | Impact | Mitigation Strategy | Contingency Plan | Risk Owner |
|---|---|---|---|---|---|---|---|
| **R01** | **Business / AI** | **Missed Existing Implementation**: System tags an idea as "New Opportunity" when it was already engineered under a historical ECN with different terminology. | High | **CRIT** | **Multi-tier hybrid retrieval**: Traverses Part numbers, Assembly hierarchy, and semantic project notes. Incorporates cross-encoder reranking and cross-model applicability mapping. | Require mandatory engineering sign-off on all top-tier cost ideas; continuous benchmark testing against historical Gold Dataset. | AI/ML Architect |
| **R02** | **Financial** | **Calculation Skew via Inconsistent Units**: Spreadsheet uploads containing figures in Lakhs vs Rupees or MWh vs kWh skew OPEX benchmarking by orders of magnitude. | Med | **CRIT** | **Deterministic Unit Normalization Guard**: Enforces canonical storage units and statistical magnitude bounds checks during ingestion before database commit. | Flag out-of-bounds rows for interactive user confirmation; quarantine questionable entries. | Lead Quantitative Engineer |
| **R03** | **AI / Truth** | **AI Hallucination of Citations / Costs**: Local SLM invents a non-existent part number or generates fabricated financial savings. | Med | **CRIT** | **Deterministic Tool Calculation & Citation Validator**: All financial numbers are computed solely by Python services. Every cited ECN/Part ID is checked against SQL primary keys before rendering. | Strip unverified citations automatically; display clear `UNVERIFIED_CITATION` alert. | AI/ML Architect |
| **R04** | **Runtime / Infra** | **GPU VRAM Exhaustion / OOM**: Running 9B SLM, embedding model, reranker, and large context concurrently exceeds 24GB VRAM. | Med | High | **Strict VRAM Budgeting & Dynamic Offload**: SLM (14GB Q4_K_M), Embed (1GB), Rerank (1.5GB), KV Cache (4GB). Dynamically offload excess layers to system RAM. | Worker watchdog catches CUDA OOM, resets KV cache, and switches to CPU fallback. | DevOps / Runtime Lead |
| **R05** | **Security** | **Air-Gap Egress Leak**: A third-party Python or Node library attempts an external update check or telemetry call on client network. | Low | High | **Container-Level Network Isolation**: Set Docker Compose `internal: true`, block outbound TCP/UDP at firewall, and disable all telemetry flags. | Continuous CI/CD packet capture testing; immediate build failure on outbound packet detection. | Security Architect |
| **R06** | **AI / RAG** | **Lost-in-the-Middle Context Bloat**: Shoveling 50 retrieved idea chunks into a single giant prompt causes model to overlook critical evidence. | Med | Med | **Context Budgeting & Precision Reranking**: Filter pool to top-5 verified evidence chunks (< 2,500 tokens). Place query constraints at prompt edges. | Truncate context dynamically if token budget exceeds 3,000 tokens. | AI/ML Architect |
| **R07** | **Data** | **Dirty Plant Spreadsheet Ingestion**: Ingesting malformed Excel files with merged headers, missing columns, or bad datatypes crashes pipeline. | High | Med | **Sandboxed Streaming Parser & Pre-flight Validator**: Robust column matching, fuzzy header alias dictionary, and atomic transactional commits. | Return structured validation error report showing exact row/column defects to user. | Data Engineer |
| **R08** | **AI / Agentic** | **Unbounded Tool Execution Loop**: Agentic query gets stuck calling search tools repeatedly on ambiguous user input. | Med | Med | **Hard Iteration Counter & Tool State Tracker**: Restrict execution to `max_iterations = 4` with strict 10s timeout per tool. | Circuit breaker terminates loop and returns current best evidence with `PARTIAL_RESULTS` flag. | Full-Stack Architect |
| **R09** | **Program** | **Customer Data Delay**: Client NDA and production data transfer take longer than expected, stalling development. | High | Med | **Comprehensive Synthetic Data Generator**: Develop the entire platform against realistic, clearly labeled synthetic datasets (5 families, 8 plants, 10k ideas). | POC can be demonstrated 100% on synthetic data; client data onboarded seamlessly post-NDA. | Technical Program Manager |
| **R10** | **Frontend** | **UI Performance Grid Degradation**: Rendering 10,000 ideas in the browser causes severe DOM lag and unresponsiveness. | Med | Med | **Virtualized Tables & Server-Side Pagination**: Use `tanstack-virtual` to render only visible DOM nodes (max 50 rows in DOM simultaneously). | Enable server-side filtering and limit initial fetch to 100 records per page. | Full-Stack Lead |

---

## 3. Top 10 Mitigations Summary
1. **Multi-tier Hybrid Search**: Part Number Exact + Trigram Fuzzy + Dense Vector + Cross-Encoder Reranker.
2. **Pure Python Deterministic Calculations**: Zero reliance on LLM arithmetic for OPEX, unit savings, or annual ROI.
3. **Database-Validated Source Citations**: Regex extraction and foreign key validation of every cited ECN/Part ID.
4. **Partitioned GPU VRAM Management**: Strict memory allocation for SLM, Embeddings, Reranking, and KV cache with CPU overflow.
5. **Enforced Air-Gap Container Isolation**: Complete network disconnection with zero outbound telemetry.
6. **Small High-Precision Context Prompts**: Reranked top-5 evidence chunks (< 2,500 tokens) with lost-in-the-middle safeguards.
7. **Robust Streaming Ingestion with Unit Guards**: Automatic magnitude checks and atomic transactional database commits.
8. **Bounded Agentic Tool Execution**: Hard 4-iteration ceiling and circuit breakers on all multi-step tool calls.
9. **Realistic Labeled Synthetic Data**: Full development and validation possible prior to customer data release.
10. **Virtualized High-Density UI**: Fluid client-side rendering for 10,000+ ideas using virtual DOM windowing.

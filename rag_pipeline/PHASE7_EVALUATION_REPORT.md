# Phase 7 Evaluation Report

## Executive Summary

| Metric | Value |
|--------|-------|
| **Phase** | 7 |
| **Status** | Complete |
| **Dataset Size** | 50 queries |
| **Test Date** | 2026-09-07 |

## Key Metrics

### Routing Accuracy
- **Overall Routing Accuracy**: 92.0% (46/50)
- **Multi-domain Routing Accuracy**: 81.8% (9/11)

### Retrieval & Grounding
- **Grounding Rate**: 100.0% (50/50) - All answers have source citations
- **Source Metadata Preservation**: 100.0% - All sources include section/rule metadata
- **Recall@1**: N/A (requires ground truth relevance labels)
- **Recall@3**: N/A
- **Recall@5**: N/A
- **MRR**: N/A

### Multilingual Pipeline
- **Multilingual Pipeline Success**: 13.3% (2/15) - Low due to translation quality issues for some languages
- **Languages Tested**: Hindi, Marathi, Gujarati, Bengali, Tamil, Telugu, Kannada, Malayalam, Punjabi
- **Translation Working**: Yes (NLLB-200 loaded on first request)

### Abstention Behavior
- **Abstention Accuracy (Insufficient Evidence)**: 100.0% (5/5) - Correctly abstains when evidence is missing
- **Overall Abstention Rate**: 60% (30/50) - High due to corpus gaps for definitions

### API & Qwen3
- **API Success Rate**: 100.0% (50/50) - No failed requests
- **Qwen3 Empty Responses**: 1 (designs_002 - template placeholder)
- **Qwen3 Think Leakage**: 0
- **Qwen3 Generation Failures**: 0

### Latency (ms)
| Metric | Value |
|--------|-------|
| **Mean Total Latency** | 14,214 ms |
| **Median Total Latency** | 10,680 ms |
| **P95 Total Latency** | 30,329 ms |
| **Mean Retrieval** | 800 ms |
| **Mean Generation** | 13,676 ms |
| **First-Request Translation Overhead** | ~5,800 ms (Hindi) |

## Detailed Results by Category

### Single-Domain Queries (Legal, Patents, Trademarks, GI, Designs, ABS, TK)
- **Routing**: Mostly correct (single agent selected as expected)
- **Answers**: High abstention rate (60%) due to corpus gaps
- **Successful Answers**: Section 11, Patent Term, GI Definition, GI Applicants, Design Registration

### Multi-Domain Queries (TK+IP, ABS+TK+Legal, etc.)
- **Routing**: 81.8% correct - orchestrator correctly identifies multiple relevant agents
- **Answers**: All abstained due to insufficient cross-domain evidence in corpus

### Insufficient Evidence Queries (5 queries)
- **Abstention**: 100% correct - all properly returned "insufficient evidence"
- **Queries**: Section 2(1)(m), GI Section 67, PCT Procedure, ABS Percentages, Inventive Step

### Multilingual Queries (15 queries)
- **Hindi/Marathi**: Working, but translation quality varies
- **Kannada/Malayalam**: Translation errors cause wrong routing (Kannada "ಪೆಟೆಂಟ್ ಎಂದಿಗ?" → "Have you ever been patented?" → legal agent)
- **First-request latency**: High due to NLLB-200 model loading (~5-13s)

### Hindi vs Marathi Comparison (4 queries)
- **Routing**: 100% correct for both languages
- **Answers**: Both abstain appropriately

## Known Issues

1. **High Abstention Rate (60%)** - Corpus lacks definitional content (Section 2 definitions for patent, inventive step, trademark, design, etc.)

2. **Corpus Gaps**:
   - Patents Act Section 2(1)(m) - patent definition
   - Patents Act Section 2(1)(ja) - inventive step definition
   - GI Act Section 67 - penalties
   - PCT international filing procedure
   - Specific ABS monetary percentages

3. **Translation Quality**:
   - Kannada: "ಪೆಟೆಂಟ್ ಎಂದಿಗ?" translates to "Have you ever been patented?"
   - Malayalam: "പെട്ടന്റ് എന്താണ്?" translates to "What's the matter?"
   - First-request model loading adds 5-13s latency

4. **Empty Response**: One query (designs_002) returned template placeholder "**Answer**: [answer]"

5. **No Think Leakage**: Qwen3 correctly follows format constraints

## Recommendations

1. **Add Section 2 Definitions** to corpus for all Acts (patent, trademark, design, GI, inventive step)
2. **Improve Retrieval for Definitional Queries** - consider hybrid search (keyword + vector)
3. **Pre-load Translation Model** at startup to avoid first-request latency
4. **Fix Kannada/Malayalam Translation** - verify NLLB language codes
5. **Add More GI and Design Act Content** for procedural queries
6. **Implement Recall Metrics** - create ground truth relevance labels for retrieval evaluation

## Files Generated

- `phase7_evaluation_dataset.json` - Evaluation dataset (50 queries)
- `phase7_results.json` - Complete raw results with all metrics
- `PHASE7_EVALUATION_REPORT.md` - This report
- `PHASE7_EVALUATION_REPORT.json` - Machine-readable summary

## Next Phase

**Phase 8**: Production hardening, API optimization, monitoring, and deployment preparation.
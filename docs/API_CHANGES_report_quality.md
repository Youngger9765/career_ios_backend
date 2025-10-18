# API Changes: Report Quality Enhancement

**Version**: v1.1.0
**Date**: 2025-10-18
**Branch**: `feature/report-quality-enhancement`

---

## Summary

Enhanced `/api/rag/report/generate` endpoint with quality validation and scoring.

**Key Changes**:
- Added `quality_summary` field to response
- No breaking changes to existing fields
- Fully backward compatible

---

## API Endpoint Changes

### `POST /api/rag/report/generate`

**Request** (No Changes):
```json
{
  "transcript": "晤談逐字稿...",
  "rag_system": "openai",
  "similarity_threshold": 0.3,
  "top_k": 10
}
```

**Response** (New Field Added):
```json
{
  "client_name": "小美（化名）",
  "age": 28,
  "gender": "女性",
  "conceptualization": "【一、案主基本資料】...",
  "theories": [
    {
      "id": 1,
      "title": "Super 生涯發展理論",
      "content": "...",
      "similarity": 0.85
    }
  ],

  // ✨ NEW: Quality summary field
  "quality_summary": {
    "structure_quality": {
      "completeness": 100.0,
      "missing_sections": [],
      "status": "✅ 完整"
    },
    "citation_quality": {
      "total_citations": 7,
      "critical_sections_cited": true,
      "has_rationale": true,
      "section_details": {
        "【五、多層次因素分析】": {
          "has_citations": true,
          "citation_count": 2,
          "reason": "因素分析需要理論支持",
          "status": "✅"
        },
        "【七、諮詢師的專業判斷】": {
          "has_citations": true,
          "citation_count": 2,
          "reason": "專業判斷需要理論依據",
          "status": "✅"
        },
        "【八、諮商目標與介入策略】": {
          "has_citations": true,
          "citation_count": 3,
          "reason": "介入策略需要技術引用",
          "status": "✅"
        }
      },
      "status": "✅ 完整引用"
    },
    "content_metrics": {
      "total_length": 2456,
      "avg_section_length": 245,
      "theory_count": 7,
      "has_reflection": true
    },
    "overall_score": 95.5,
    "grade": "優秀",
    "timestamp": "2025-10-18T14:30:00"
  }
}
```

---

## Quality Summary Schema

### `quality_summary` Object

| Field | Type | Description |
|-------|------|-------------|
| `structure_quality` | Object | 報告結構品質 |
| `citation_quality` | Object | 理論引用品質 |
| `content_metrics` | Object | 內容指標 |
| `overall_score` | Float | 綜合品質分數 (0-100) |
| `grade` | String | 等級標籤 |
| `timestamp` | String | ISO 8601 時間戳 |

### `structure_quality` Object

| Field | Type | Description |
|-------|------|-------------|
| `completeness` | Float | 完整度百分比 (0-100) |
| `missing_sections` | Array<String> | 缺少的段落列表 |
| `status` | String | 狀態描述（✅ 完整 / ❌ 缺少 N 個段落） |

### `citation_quality` Object

| Field | Type | Description |
|-------|------|-------------|
| `total_citations` | Integer | 總引用數量 |
| `critical_sections_cited` | Boolean | 核心段落是否都有引用 |
| `has_rationale` | Boolean | 是否有理由說明 |
| `section_details` | Object | 各段落引用詳情 |
| `status` | String | 狀態描述（✅ 完整引用 / ❌ 部分段落未引用） |

### `content_metrics` Object

| Field | Type | Description |
|-------|------|-------------|
| `total_length` | Integer | 報告總字數 |
| `avg_section_length` | Integer | 平均段落字數 |
| `theory_count` | Integer | 引用理論數量 |
| `has_reflection` | Boolean | 是否包含自我反思 |

---

## Quality Score Calculation

### Formula

```
Overall Score = Structure(40%) + Citation Coverage(40%) + Citation Quality(20%)

where:
  Structure = (present_sections / 10) × 40
  Citation Coverage = (cited_critical_sections / 3) × 40
  Citation Quality = Rationale(10%) + Citation Count(10%)
```

### Grading Scale

| Score Range | Grade | Description |
|-------------|-------|-------------|
| 90-100 | 優秀 | 結構完整 + 引用充分 + 有理由說明 |
| 75-89 | 良好 | 結構完整 + 引用基本充分 |
| 60-74 | 及格 | 結構或引用有缺漏但可接受 |
| 0-59 | 需改進 | 結構不完整或引用嚴重不足 |

---

## Backward Compatibility

✅ **100% Backward Compatible**

- All existing fields remain unchanged
- `quality_summary` is an **additional** field
- Clients can safely ignore this field if not needed
- No breaking changes to request/response format

---

## Example Usage

### iOS Client (Swift)

```swift
struct ReportResponse: Codable {
    let clientName: String
    let age: Int?
    let gender: String?
    let conceptualization: String
    let theories: [Theory]

    // ✨ NEW: Optional for backward compatibility
    let qualitySummary: QualitySummary?

    enum CodingKeys: String, CodingKey {
        case clientName = "client_name"
        case age, gender, conceptualization, theories
        case qualitySummary = "quality_summary"
    }
}

struct QualitySummary: Codable {
    let structureQuality: StructureQuality
    let citationQuality: CitationQuality
    let overallScore: Double
    let grade: String

    enum CodingKeys: String, CodingKey {
        case structureQuality = "structure_quality"
        case citationQuality = "citation_quality"
        case overallScore = "overall_score"
        case grade
    }
}

// Usage
let response = try decoder.decode(ReportResponse.self, from: data)

if let quality = response.qualitySummary {
    print("Report Quality: \(quality.grade) (\(quality.overallScore)分)")

    // Show quality indicator in UI
    if quality.overallScore >= 90 {
        showQualityBadge(.excellent)
    } else if quality.overallScore >= 75 {
        showQualityBadge(.good)
    }
}
```

### Display Quality in UI

```swift
// Quality Score View
struct QualityScoreView: View {
    let summary: QualitySummary

    var body: some View {
        VStack(alignment: .leading) {
            HStack {
                Text("報告品質")
                    .font(.headline)
                Spacer()
                Text(summary.grade)
                    .font(.title2)
                    .foregroundColor(gradeColor)
            }

            ProgressView(value: summary.overallScore, total: 100)

            HStack {
                Label("\(summary.structureQuality.status)", systemImage: "doc.text")
                Spacer()
                Label("\(summary.citationQuality.status)", systemImage: "quote.bubble")
            }
            .font(.caption)
        }
    }

    var gradeColor: Color {
        switch summary.grade {
        case "優秀": return .green
        case "良好": return .blue
        case "及格": return .orange
        default: return .red
        }
    }
}
```

---

## Migration Guide

### For Existing Clients

**No action required** - existing code will continue to work.

### To Use New Quality Features

1. Update response model to include `quality_summary` field
2. Make field optional for backward compatibility
3. Add UI components to display quality score (optional)
4. Log quality scores for monitoring (recommended)

```swift
// Before
let report = response.conceptualization

// After (optional enhancement)
let report = response.conceptualization
if let quality = response.qualitySummary {
    Analytics.log("report_quality", score: quality.overallScore)
}
```

---

## Performance Impact

**No significant impact**:
- Quality validation runs in <50ms
- Total response time increase: <100ms
- No additional API calls required

---

## Testing

### Sample Request

```bash
curl -X POST https://your-api.com/api/rag/report/generate \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "個案表示最近工作感到迷茫...",
    "rag_system": "openai"
  }'
```

### Expected Response

```json
{
  "client_name": "案主",
  "conceptualization": "【一、案主基本資料】...",
  "theories": [...],
  "quality_summary": {
    "overall_score": 85.5,
    "grade": "良好"
  }
}
```

---

## Monitoring

### Recommended Metrics

1. **Quality Score Distribution**
   - Track percentiles (p50, p75, p90, p99)
   - Alert if median score < 70

2. **Low Quality Reports**
   - Count reports with score < 60
   - Investigate root causes

3. **Citation Coverage**
   - % of reports with all critical sections cited
   - Target: > 95%

### Sample Query (BigQuery)

```sql
SELECT
  DATE(timestamp) as date,
  PERCENTILE_CONT(overall_score, 0.5) OVER(PARTITION BY DATE(timestamp)) as median_score,
  COUNT(*) as total_reports,
  COUNTIF(overall_score < 60) as low_quality_count,
  COUNTIF(citation_quality.critical_sections_cited = false) as missing_citations
FROM reports
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY date
ORDER BY date DESC
```

---

## Rollback Plan

If issues arise:

1. **Keep feature flag ready** (environment variable):
   ```python
   ENABLE_QUALITY_SUMMARY = os.getenv("ENABLE_QUALITY_SUMMARY", "true")
   ```

2. **Quick disable**:
   ```bash
   gcloud run services update career-backend \
     --set-env-vars ENABLE_QUALITY_SUMMARY=false
   ```

3. **Response without quality_summary**:
   - Clients already handle optional field
   - No client-side changes needed

---

## Questions?

Contact: Technical team
Documentation: `/docs/報告生成改善_完工報告.md`

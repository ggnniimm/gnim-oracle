# Eval 13-fails bucketed (2026-04-30)

**Run**: targeted batch of 14 TCs flagged in `2026-04-29_19-30_drive-remap-complete-and-eval-baseline-discovery.md` handoff. Run on prod (clean 27,849-chunk index). Single pass per TC.

## Result

| Bucket | TCs | Count |
|---|---|---|
| Intermittent (passed this run) | TC-034, TC-039, TC-046 | 3 |
| Citation/section number missing | TC-035, TC-051, TC-071, TC-074 | 4 |
| Substantive content gap (multi-miss) | TC-063, TC-064, TC-065, TC-067, TC-075, TC-076 | 6 |
| Liability term missing (single-miss) | TC-066 | 1 |

Net pass-rate observation: **69/80 this run** vs 66/80 in handoff (3 intermittents flipped — LLM variance, not real progress).

## Failure detail

| TC | Missing must_contain | Notes |
|---|---|---|
| TC-035 | `['มาตรา 103', 'มาตรา ๑๐๓']` | Answer cites law generically without section |
| TC-051 | `['ป.พ.พ.', 'ประมวลกฎหมายแพ่ง']` | Civil code name absent |
| TC-063 | `['ฝ่ายเดียว', 'แก้ไขสัญญาฝ่ายเดียว']` + `['ศาล', 'ลดค่าปรับ']` | 2 substantive misses |
| TC-064 | `'5 ปี'`, `'รู้หรือควรรู้'`, `['วันที่ทำหนังสือ', 'หนังสือบอกเลิกสัญญา']` | 3 misses — limitation period concept absent |
| TC-065 | `['ความระมัดระวัง', 'ละเลย', 'ปล่อยปละละเลย']` | Gross-negligence terminology missing |
| TC-066 | `['รับผิด', 'ชดใช้']` | Liability concept absent |
| TC-067 | `['ไล่เบี้ย', 'ประมาทเลินเล่อ']` | Recourse + negligence absent |
| TC-071 | `['ข้อ ๑๖๕', 'ข้อ 165']` | Section number missing (known flaky) |
| TC-074 | `['ป.พ.พ.', 'ประมวลกฎหมายแพ่ง']` | Civil code name absent |
| TC-075 | `['ดูแลรักษาแทน', 'ครอบครองแทน', 'ยึดถือเพื่อตนเอง']` | 3 misses — possession-on-behalf concept absent |
| TC-076 | `'ล่วงหน้า'`, `'383'`, `['สูงเกินส่วน', 'เกินสมควร']` | 3 misses — penalty doctrine absent |

## Strategy

1. **Quick win**: tackle citation bucket (4 TCs) via prompt rule reinforcement first. Per `2026-03-19_generator-prompt-rule-density.md` — Rule 14 already exists for "cite section numbers". May need wording bump or new rule for "always name the law (ป.พ.พ., พ.ร.บ., ระเบียบ) explicitly".
2. **Deep work**: substantive content gap — retrieval-vs-generation drill per TC. Pattern from `2026-03-16_retrieval-before-crossref.md`: run `--no-generate` first, then decide cross-ref vs rescue phrase.
3. **Stabilize**: intermittents — add must_contain alternatives per `2026-03-14` eval-stabilization pattern.

## Source

- Diag log: prod `/tmp/diag_20260430_014338.log`
- Local copy: would re-pull on prod via ssh if needed

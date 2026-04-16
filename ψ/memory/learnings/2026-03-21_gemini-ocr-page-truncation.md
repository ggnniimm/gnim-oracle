# Gemini Flash OCR silently truncates long PDFs

**Date**: 2026-03-21
**Context**: Verbatim OCR of อ.2050/2559 (16 pages) via Gemini 2.0 Flash

## Pattern

When OCR'ing a long PDF (16+ pages) with Gemini Flash, the first request returned only ~10 pages despite max_output_tokens=65536 being well above the needed output size. No error was returned — the response simply ended mid-document. The remaining pages had to be explicitly requested in a second call ("เริ่มจากหน้า 11 จนถึงหน้าสุดท้าย").

## Mitigation

1. Always check page count first: `'PDF นี้มีกี่หน้า?'`
2. After OCR, verify the last page number in the output matches expected total
3. For PDFs >10 pages, consider splitting into two requests (pages 1-N/2, N/2+1-end)
4. Merge the parts into a single file afterward

## Related

- อ.148/2554 (10 pages) OCR'd in a single pass without truncation — threshold seems to be around 10-12 pages
- max_output_tokens is not the bottleneck — Gemini seems to have an internal content generation limit per response

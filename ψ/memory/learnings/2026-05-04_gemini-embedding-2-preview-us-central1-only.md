# gemini-embedding-2-preview is us-central1 only on Vertex AI

**Date**: 2026-05-04
**Source**: Multi-region quota investigation — thai-legal-rag

## Fact

`gemini-embedding-2-preview` on Vertex AI is only available in `us-central1`. All other tested regions return 404 NOT_FOUND:
- ✗ us-east1
- ✗ us-east4
- ✗ us-west1
- ✗ europe-west4
- ✗ asia-southeast1

Multi-region round-robin (for quota multiplication) is not possible with this model.

## Implication

- Quota is fixed at ~3 RPM project-level for us-central1
- Only path to higher throughput: request quota increase at GCP console
- If Google expands regional availability in future, multi-region becomes viable — worth re-testing

## Test Method

```python
from google import genai
c = genai.Client(vertexai=True, project=PROJECT, location=REGION)
result = c.models.embed_content(model='gemini-embedding-2-preview', contents='test')
# 404 NOT_FOUND = not available in this region
# Success = available
```

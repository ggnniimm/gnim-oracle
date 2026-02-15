import os
import sys
import json
import time
import google.generativeai as genai
from google.api_core import exceptions

def load_api_keys():
    """Loads API keys from env vars and .env file."""
    api_keys = []
    # Check environment variables
    for key, value in os.environ.items():
        if key.startswith("GEMINI_API_KEY") and value:
             api_keys.append(value)
    
    # Check .env files
    possible_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    ]
    for env_path in possible_paths:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY") and "=" in line:
                        k_val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if k_val:
                            api_keys.append(k_val)
    return list(set(api_keys))

def classify_document(filepath, api_key):
    """
    Classifies the document type using Gemini.
    Returns a dict: {"type": str, "confidence": float, "reasoning": str}
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    print(f"🚀 Uploading {os.path.basename(filepath)} for classification...")
    try:
        uploaded_file = genai.upload_file(filepath, mime_type="application/pdf")
        
        # Wait for processing
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(1)
            uploaded_file = genai.get_file(uploaded_file.name)
            
        if uploaded_file.state.name == "FAILED":
            return {"type": "Error", "reasoning": "File upload processing failed."}

        prompt = """
        You are a legal document expert. Classify this document into one of the following categories:
        
        1. "Ruling_Committee" (Committee on Diagnosis of Procurement Problems / กวจ. / กรมบัญชีกลาง / คณะกรรมการวินิจฉัย)
        2. "Ruling_Court" (Administrative Court Judgment / คำพิพากษาศาลปกครอง / ศาลปกครองสูงสุด)
        3. "Ruling_AttorneyGeneral" (Office of the Attorney General / ข้อหารืออัยการสูงสุด / สํานักงานอัยการสูงสุด)
        4. "Circular" (Circular Letter / หนังสือเวียน / ว...)
        5. "Contract" (Agreement / สัญญาจ้าง / สัญญาซื้อขาย)
        6. "Unknown" (Does not fit clear categories)

        Analyze the header, logos, and subject line.
        
        Return STRICT JSON format:
        {
            "type": "CategoryName",
            "confidence": 0.0 to 1.0,
            "reasoning": "Brief explanation why"
        }
        """
        
        print("🧠 Analyzing document structure...")
        response = model.generate_content(
            [prompt, uploaded_file],
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Cleanup file
        try:
            uploaded_file.delete()
        except:
            pass
            
        return json.loads(response.text)

    except Exception as e:
        return {"type": "Error", "reasoning": str(e)}

def extract_with_frontmatter(filepath, api_key, doc_type):
    """
    Extracts content using a schema-aware prompt based on doc_type.
    Returns: Markdown string with YAML frontmatter.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    print(f"📄 Extracting content as {doc_type}...")
    
    # Specific instructions based on type
    schema_instructions = ""
    if doc_type == "Ruling_Committee":
        schema_instructions = """
        - type: Ruling_Committee
        - date: "DD Month YYYY" (Thai date from header)
        - ref_number: "The alphanumeric reference number (e.g. กค ...)"
        - topic: "The full Subject line"
        - signer: "Name of the person signing the document"
        """
    elif doc_type == "Circular":
        schema_instructions = """
        - type: Circular
        - date: "DD Month YYYY"
        - ref_number: "The Circular number (e.g. ว ...)"
        - topic: "Subject"
        - signer: "Signer Name"
        """
    else:
        schema_instructions = """
        - type: Other
        - date: "Document Date"
        - ref_number: "Reference Number"
        - topic: "Subject/Title"
        """

    prompt = f"""
    You are an expert OCR engine for Thai legal documents.
    Convert this PDF into Markdown with a YAML Frontmatter block.
    
    1. **YAML Frontmatter** (Must be at the very top, between ---):
    Extract these fields:
    {schema_instructions}
    
    2. **Content**:
    Extract the full document text verbatim in Markdown format.
    - Preserve headers, lists, and tables.
    - Use > for blockquotes if appropriate.
    - **Do NOT** output JSON. Output raw Markdown.
    """
    
    uploaded_file = genai.upload_file(filepath, mime_type="application/pdf")
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(1)
        uploaded_file = genai.get_file(uploaded_file.name)
        
    response = model.generate_content([prompt, uploaded_file], stream=True)
    
    full_text = ""
    print("🧠 Generating with schema...")
    for chunk in response:
        if chunk.text:
            full_text += chunk.text
            print(".", end="", flush=True)
            
    try:
        uploaded_file.delete()
    except:
        pass
        
    # Post-process: Remove Markdown code block fences
    final_text = full_text.strip()
    if final_text.startswith("```"):
        lines = final_text.splitlines()
        # Remove first line if it's a fence
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        # Remove last line if it's a fence
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        final_text = "\n".join(lines).strip()
        
    return final_text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/agentic_pdf_processor.py <pdf_path> [output_path]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    keys = load_api_keys()
    if not keys:
        print("❌ No API keys found.")
        sys.exit(1)
        
    # Phase 1: Classify
    classification = classify_document(pdf_path, keys[0])
    doc_type = classification.get("type", "Unknown")
    confidence = classification.get("confidence", 0)
    print(f"\n📊 Classified as: {doc_type} ({confidence*100:.1f}%)")
    
    # Phase 2: Extract
    content = extract_with_frontmatter(pdf_path, keys[0], doc_type)
    
    # Classification -> Folder Mapping
    folder_map = {
        "Ruling_Committee": "references/rulings_committee",
        "Ruling_AttorneyGeneral": "references/rulings_attorney_general",
        "Ruling_Court": "references/rulings_court",
        "Circular": "references/rulings_committee", # Circulars also go here usually
        "Contract": "references/contracts",
        "Unknown": "references/raw_pdfs",
        "Error": "references/raw_pdfs"
    }
    
    target_subfolder = folder_map.get(doc_type, "references/raw_pdfs")

    # Save Logic
    if output_path:
        # Explicit path from user
        final_path = output_path
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
    else:
        # Auto-path based on classification
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        final_dir = os.path.join(project_root, target_subfolder)
        os.makedirs(final_dir, exist_ok=True)
        
        # Force filename to match original PDF but with .md extension
        original_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        final_filename = f"{original_filename}.md"
        final_path = os.path.join(final_dir, final_filename)

    with open(final_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"\n✅ Saved to: {final_path}")
    if not output_path:
        print(f"📦 Auto-classified into: {target_subfolder}")

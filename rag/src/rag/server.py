import io
import os
import json
import uuid
import time
import base64
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import uvicorn

# PDF / Image processing
from pdf2image import convert_from_bytes
from PIL import Image

# DOCX processing
from docx import Document
from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph

from tqdm import tqdm
from groq import Groq
import chromadb
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

from dotenv import load_dotenv 

load_dotenv()

# ============================================================
# CONFIG
# ============================================================

# REPLACE WITH YOUR ACTUAL KEY


CHROMA_DIR = "./chroma_store"
COLLECTION_NAME = "college_programs_granular"

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Models
# Note: "moonshotai/kimi-k2" is not on Groq. We stick to the best Llama 3.3 model.
# Removing JSON constraint from Phase 1 makes this model work perfectly.
VISION_MODEL = "llama-3.2-11b-vision-preview" 
TEXT_MODEL = "llama-3.3-70b-versatile"
CHUNKING_MODEL = "llama-3.3-70b-versatile" 

CSV_CHUNKS_PATH = "final_granular_chunks_audit.csv"

os.makedirs(CHROMA_DIR, exist_ok=True)

# ============================================================
# CLIENTS
# ============================================================

client = Groq(api_key=os.environ['GROQ_API_KEY'])
embedder = SentenceTransformer(EMBED_MODEL)

chroma = PersistentClient(path=CHROMA_DIR)

collection = chroma.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)

app = FastAPI(title="College Admission RAG Pipeline (Granular)")

# Input model for Raw Text
class TextInput(BaseModel):
    text: str
    source_name: Optional[str] = "manual_input"

# ============================================================
# UTILS
# ============================================================

def img_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"

def safe_json_loads(text: str, context_info: str):
    """Robust JSON parser."""
    if not text: return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try finding markdown code blocks
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return {}
    clean_text = text[start:end + 1]
    clean_text = clean_text.replace("\n", " ") 
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        return {}

def split_text_logical(text: str, max_chars: int = 4000) -> List[str]:
    """
    Splits massive raw text strings into logical blocks (roughly 4000 chars)
    by looking for double newlines to avoid cutting sentences in half before sending to LLM.
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    # Split by paragraphs (double newline)
    paragraphs = text.split("\n\n")
    
    for para in paragraphs:
        if current_length + len(para) > max_chars:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [para]
            current_length = len(para)
        else:
            current_chunk.append(para)
            current_length += len(para)
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks

# ============================================================
# PROMPTS (OPTIMIZED FOR COLLEGE DATA)
# ============================================================

RAW_EXTRACTION_PROMPT = """
You are a document digitizer.
Your task is to extract all text and tables from the provided content verbatim.
INSTRUCTIONS:
1. Output ONLY the extracted content in clean Markdown format.
2. Maintain table structures using Markdown tables.
3. Do NOT include any remarks.
"""

# OPTIMIZED PROMPT FOR CONTEXTUAL CHUNKING
SEMANTIC_CHUNKING_PROMPT = """
You are a Data Structuring Expert for a College Admission RAG System.
Your task is to convert the raw text into a JSON list of strictly "Contextualized Semantic Paragraphs".

### CRITICAL RULES (Context Injection):
1. **Identify the Hierarchy**: Look for headers like "B.Tech CSE", "Hostel Fees", "Scholarship Scheme A".
2. **Inject Context**: If a paragraph says "The fee is $500", and it falls under "B.Tech", you MUST rewrite it as: "The fee for B.Tech is $500".
3. **Handle Lists/Tables**: Do not split a single list item or table row into its own chunk unless it contains a lot of text. Group related table rows if they describe the same specific sub-topic.
4. **No Orphans**: Every chunk must be self-understandable without reading the previous chunk.

### JSON Schema:
{
  "chunks": [
    {
      "context_tag": "Specific Topic (e.g. ### 1. School of Engineering and Technology
| Program | Duration | Branches/Specialization | Annual Fees (₹) | Eligibility |
| :--- | :--- | :--- | :--- | :--- |
| **B.Tech.** | 4 Years | Computer Science and Engineering | 2,45,000 | Pass in Senior Secondary Examination (10+2) with min. 60% marks in aggregate in all subjects with pass in English, Physics & Mathematics & one subject out of Chemistry, Biology, Biotechnology, Technical vocational subject. (Preference to valid JEE Mains Score). |
| **B.Tech.** | 4 Years | CSE: Artificial Intelligence & Data Science | 2,55,000 | Same as above |
| **B.Tech. CSE with Industry** | 4 Years | Cloud Computing (Microsoft) | 2,75,000 | Same as above |
| | | Cloud Computing (Amazon-AWS) | 2,75,000 | |
| | | Artificial Intelligence and Machine Learning (Xebia) | 2,75,000 | |
| | | Artificial Intelligence and Machine Learning (IBM) | 2,75,000 | |
| | | Artificial Intelligence and Machine Learning (Samatrix) | 2,75,000 | |
| | | Full Stack Web Design and Development (Xebia) | 2,75,000 | |
| | | Cyber Security (EC Council, USA) | 2,75,000 | |
| | | Data Science & Data Analytic (Samatrix) | 2,75,000 | |
| | | Computer Science and Business Systems (TCS) - CSBS | 2,75,000 | |
| | | Generative AI (L&T EduTech) | 2,75,000 | |
| | | B.Tech. CSE in Gaming Technology | 2,75,000 | |
| **B.Tech.** | 4 Years | CSE in AI DevOps & Cloud Automation | 2,90,000 | Same as above |
| **B.Tech.** | 4 Years | CSE with Specialization in Software Product Engineering (Kalvium)* | 3,25,000 | *Additional requirement: Must appear for Kalviness QChallenge (KQC) & PI. **NO SCHOLARSHIP AVAILABLE.** |
| **B.Tech.** | 4 Years | Civil Engineering with L&T EduTech | 1,75,000 | Same as above |
| | | Electronics & Communication Engineering With L&T EduTech | 1,75,000 | |
| | | Electronics & Comm. Eng. Specialization in Semiconductor & Chip Design | 1,75,000 | |
| | | Mechanical Engineering with L&T EduTech | 1,75,000 | |
| | | Mechanical Engineering with Specialization in Electric Vehicles | 1,75,000 | |
| **B.Tech. Lateral Entry** | 3 Years | Computer Science and Engineering | 2,45,000 | Passed Diploma with 60% OR B.Sc Degree with 60% and passed 10+2 with Math. |
| | | Civil / Electronics and Communication / Mechanical Engineering | 1,75,000 | |
| **M.Tech.** | 2 Years | Structural Engineering / Transportation Engg / Environmental Engg / Construction Engg & Mgmt (Civil) | 75,000 | B. Tech with min. 60% aggregate marks in related discipline. (MCA/M.Sc. IT considered for M.Tech CSE). |
| | | AI / CSE / Data Analytics / Cyber Security / Cloud Computing (CSE) | 75,000 | |
| | | VLSI & Embedded Systems / Digital Communication (ECE) | 75,000 | |
| | | CAD/CAM / Thermal / Production / Design Engineering (ME) | 75,000 | |
| | | EV Engineering / Renewable Energy / Power System and Automation (Electrical) | 75,000 | |)",
      "content": "The full text of the paragraph with injected context..."
    }
  ]
}
"""

# ============================================================
# STAGE 1: RAW EXTRACTION
# ============================================================

def extract_page_vision_raw(image: Image.Image, page_num: int) -> str:
    img_b64 = img_to_b64(image)
    messages = [
        {"role": "system", "content": RAW_EXTRACTION_PROMPT},
        {"role": "user", "content": [{"type": "text", "text": f"Page {page_num}"}, {"type": "image_url", "image_url": {"url": img_b64}}]}
    ]
    try:
        resp = client.chat.completions.create(model=VISION_MODEL, messages=messages, temperature=0.1)
        return resp.choices[0].message.content or ""
    except Exception as e:
        print(f"[ERR] Vision fail page {page_num}: {e}")
        return ""

def extract_segment_text_raw(text_content: str, segment_num: int) -> str:
    messages = [
        {"role": "system", "content": RAW_EXTRACTION_PROMPT},
        {"role": "user", "content": f"Extract/Clean segment {segment_num}:\n\n{text_content}"}
    ]
    try:
        resp = client.chat.completions.create(model=TEXT_MODEL, messages=messages, temperature=0.1)
        return resp.choices[0].message.content or ""
    except Exception as e:
        print(f"[ERR] Text fail segment {segment_num}: {e}")
        return ""

# ============================================================
# STAGE 2: SEMANTIC CHUNKING
# ============================================================

def generate_semantic_chunks(raw_text: str, source_identifier: str) -> List[Dict]:
    """
    Uses LLM to split text into paragraph-based contextual chunks.
    source_identifier: can be 'Page 1' or 'Manual Input Part 1'
    """
    if not raw_text or len(raw_text) < 20:
        return []

    messages = [
        {"role": "system", "content": SEMANTIC_CHUNKING_PROMPT},
        {"role": "user", "content": f"Context/Source: {source_identifier}\n---\nRAW TEXT:\n{raw_text}\n---\n\nGenerate JSON chunks."}
    ]

    try:
        resp = client.chat.completions.create(
            model=CHUNKING_MODEL, 
            messages=messages, 
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        response_text = resp.choices[0].message.content
        response_data = safe_json_loads(response_text, f"Chunking {source_identifier}")
        chunks_data = response_data.get("chunks", [])
        
        final_chunks = []
        for item in chunks_data:
            context = item.get("context_tag", "General Info")
            text = item.get("content", "")
            
            if text:
                final_chunks.append({
                    "id": str(uuid.uuid4()),
                    "text": text,
                    "metadata": {
                        "source_page": str(source_identifier),
                        "context_tag": context,
                        "chunk_type": "semantic_paragraph",
                        "ingest_type": "text" if "Manual" in str(source_identifier) else "file"
                    }
                })
        return final_chunks

    except Exception as e:
        print(f"[ERR] Chunking fail {source_identifier}: {e}")
        return []

# ============================================================
# DOCX HELPER FUNCTIONS
# ============================================================

def iter_block_items(parent):
    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    else:
        raise ValueError("Unknown parent type")
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P): yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl): yield Table(child, parent)

def table_to_markdown(table: Table) -> str:
    rows = []
    for row in table.rows:
        row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        rows.append(f"| {' | '.join(row_cells)} |")
    if not rows: return ""
    md_rows = [rows[0]]
    md_rows.append(f"| {' | '.join(['---'] * len(table.columns))} |")
    md_rows.extend(rows[1:])
    return "\n".join(md_rows)

def parse_docx_to_text_segments(file_bytes: bytes, chunk_size=3000) -> List[str]:
    doc = Document(io.BytesIO(file_bytes))
    full_text = []
    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            if block.text.strip(): full_text.append(block.text)
        elif isinstance(block, Table):
            full_text.append("\n" + table_to_markdown(block) + "\n")
    combined = "\n".join(full_text)
    return [combined[i:i+chunk_size] for i in range(0, len(combined), chunk_size)]

# ============================================================
# STORAGE
# ============================================================

def save_chunks_to_csv(chunks: List[Dict]):
    exists = os.path.exists(CSV_CHUNKS_PATH)
    with open(CSV_CHUNKS_PATH, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["chunk_id", "source_page", "context_tag", "text", "timestamp"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists: writer.writeheader()
        for c in chunks:
            writer.writerow({
                "chunk_id": c["id"],
                "source_page": c["metadata"]["source_page"],
                "context_tag": c["metadata"]["context_tag"],
                "text": c["text"],
                "timestamp": datetime.utcnow().isoformat()
            })

def ingest_chunks_to_db(chunks: List[Dict]):
    if not chunks: return
    texts = [c["text"] for c in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=False)
    collection.add(ids=[c["id"] for c in chunks], documents=texts, metadatas=[c["metadata"] for c in chunks], embeddings=embeddings)

# ============================================================
# API ENDPOINTS
# ============================================================
@app.get('/health')
async def health_check() : return {'status' : 'ok'}


@app.post("/ingest-text")
async def ingest_raw_text(payload: TextInput):
    """
    Ingests raw text directly. Splits long text into manageable parts 
    and applies contextual/paragraph chunking via LLM.
    """
    try:
        print(f"--- Processing Direct Text Input ({payload.source_name}) ---")
        
        # 1. Split raw text into manageable LLM context windows (logical paragraphs)
        # We don't want to feed 50k chars into the chunker at once.
        text_segments = split_text_logical(payload.text, max_chars=4000)
        
        all_semantic_chunks = []
        
        # 2. Process each segment
        for i, segment in enumerate(text_segments):
            identifier = f"{payload.source_name} - Part {i+1}"
            chunks = generate_semantic_chunks(segment, identifier)
            all_semantic_chunks.extend(chunks)
        
        if not all_semantic_chunks:
            return {"status": "warning", "message": "No chunks generated from text."}

        # 3. Store
        save_chunks_to_csv(all_semantic_chunks)
        ingest_chunks_to_db(all_semantic_chunks)
        
        return {
            "status": "success",
            "type": "direct_text",
            "segments_processed": len(text_segments),
            "total_semantic_vectors": len(all_semantic_chunks),
            "db_total_count": collection.count()
        }

    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(500, str(e))


@app.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    filename = file.filename.lower()
    file_bytes = await file.read()
    raw_pages_data = []

    try:
        print(f"--- Phase 1: Raw Extraction ({filename}) ---")
        
        if filename.endswith(".pdf"):
            images = convert_from_bytes(file_bytes)
            for i, img in tqdm(enumerate(images, start=1), total=len(images), desc="PDF Extract"):
                raw_text = extract_page_vision_raw(img, i)
                if raw_text: raw_pages_data.append((str(i), raw_text))
                time.sleep(0.3)

        elif filename.endswith(".docx") or "wordprocessingml" in file.content_type:
            text_segments = parse_docx_to_text_segments(file_bytes)
            for i, text_seg in tqdm(enumerate(text_segments, start=1), total=len(text_segments), desc="DOCX Extract"):
                raw_text = extract_segment_text_raw(text_seg, i)
                if raw_text and len(raw_text) > 10: raw_pages_data.append((str(i), raw_text))
                time.sleep(0.2)
        else:
            raise HTTPException(400, "Unsupported file. Use PDF or DOCX.")

        print(f"--- Phase 2: Semantic Chunking ---")
        all_semantic_chunks = []
        for page_num, raw_text in tqdm(raw_pages_data, desc="Chunking"):
            page_chunks = generate_semantic_chunks(raw_text, page_num)
            all_semantic_chunks.extend(page_chunks)
            time.sleep(0.1) 

        print(f"--- Phase 3: Storing {len(all_semantic_chunks)} Vectors ---")
        save_chunks_to_csv(all_semantic_chunks)
        ingest_chunks_to_db(all_semantic_chunks)

        return {
            "status": "success",
            "file_type": "pdf" if filename.endswith(".pdf") else "docx",
            "pages_processed": len(raw_pages_data),
            "total_semantic_vectors": len(all_semantic_chunks),
            "db_total_count": collection.count()
        }

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        raise HTTPException(500, str(e))

@app.get("/search")
def search(query: str, top_k: int = 5):
    emb = embedder.encode(query)
    results = collection.query(
        query_embeddings=[emb], 
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    formatted = []
    if results["ids"]:
        for i in range(len(results["ids"][0])):
            formatted.append({
                "score": results["distances"][0][i],
                "context": results["metadatas"][0][i].get("context_tag"),
                "text": results["documents"][0][i],
                "source": results["metadatas"][0][i].get("source_page")
            })
    return {"results": formatted}

# ============================================================
# ENTRY
# ============================================================
def main() : 
    uvicorn.run(app, host="0.0.0.0", port=9000)
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


"""
🤖 DIABETES CHATBOT API
========================
FastAPI endpoint untuk chatbot AI khusus diabetes

Endpoints:
- POST /chat - Chat dengan Glucare
- POST /chat/websearch - Chat + web search
- GET /topics - Daftar topik yang didukung
- GET /search - Web search langsung
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager
import re
import time

# ============================================================
# GROQ SETUP (GRATIS!)
# ============================================================
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️ Install groq: pip install groq")


# ============================================================
# WEB SEARCH SETUP (Optional)
# ============================================================
WEBSEARCH_AVAILABLE = False
try:
    import sys
    from pathlib import Path
    BASE_DIR = Path(__file__).parent
    sys.path.insert(0, str(BASE_DIR / "diabetes_chatbot"))
    from web_search import WebSearcher, DiabetesSearchAgent
    WEBSEARCH_AVAILABLE = True
    print("✅ Web search module loaded")
except Exception as e:
    print(f"⚠️ Web search not available: {e}")

# ============================================================
# PYDANTIC MODELS
# ============================================================

class ChatRequest(BaseModel):
    message: str
    use_websearch: Optional[bool] = False
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool
    response: str
    is_diabetes_related: bool
    websearch_used: bool
    sources: List[dict]
    response_time_ms: int
    model: str

class TopicsResponse(BaseModel):
    supported_topics: List[str]
    sample_questions: List[str]

class SearchResult(BaseModel):
    query: str
    results: List[dict]

# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """Kamu adalah Glucare, asisten AI khusus yang ahli dalam bidang diabetes mellitus.

Kamu memiliki pengetahuan mendalam tentang:
- Diabetes Tipe 1, Tipe 2, dan Gestasional
- Gejala, diagnosis, dan komplikasi diabetes
- Pengelolaan gula darah dan pengobatan
- Diet dan nutrisi untuk penderita diabetes
- Olahraga dan gaya hidup sehat
- Pencegahan dan edukasi diabetes
- Obat-obatan diabetes (Metformin, Insulin, dll)
- Pemeriksaan gula darah (GDP, GDS, HbA1c)

Panduan menjawab:
1. Berikan jawaban yang akurat, informatif, dan mudah dipahami
2. Gunakan bahasa Indonesia yang baik
3. Sertakan emoji yang relevan untuk membuat jawaban lebih menarik
4. Struktur jawaban dengan bullet points atau numbering jika perlu
5. Selalu ingatkan pengguna untuk berkonsultasi dengan dokter untuk diagnosis dan pengobatan
6. Jika pertanyaan tidak terkait diabetes, tolak dengan sopan dan jelaskan bahwa kamu hanya membahas diabetes

PENTING: Kamu HANYA menjawab pertanyaan seputar diabetes. Jika user bertanya di luar topik diabetes, tolak dengan sopan."""

# ============================================================
# TOPIC FILTERING
# ============================================================

DIABETES_KEYWORDS = [
    "diabetes", "diabetesi", "gula darah", "glukosa", "insulin", "hiperglikemia",
    "hipoglikemia", "kencing manis", "prediabetes", "resistensi insulin",
    "hba1c", "a1c", "gdp", "gds", "ttgo", "ogtt",
    "metformin", "glibenklamid", "glimepirid", "sulfonilurea",
    "retinopati", "neuropati", "nefropati", "kaki diabetik",
    "pankreas", "sel beta", "hormon", 
    "obesitas", "kegemukan", "berat badan", "diet", "karbohidrat",
    "kalori", "indeks glikemik", "serat", "nutrisi",
    "komplikasi", "amputasi", "luka", "kesemutan", "baal",
    "sering kencing", "haus", "lapar", "lelah", "lemas",
    "mata kabur", "penglihatan", "ginjal", "jantung", "stroke",
    "kolesterol", "trigliserida", "tekanan darah", "hipertensi",
    "olahraga", "aktivitas fisik", "gaya hidup", "sehat",
    "puasa", "makan", "makanan", "minuman", "buah", "sayur",
    "gula", "manis", "pemanis", "stevia", "sukrosa",
    "cek gula", "tes darah", "monitor", "glucometer",
    "pompa insulin", "suntik", "injeksi", "pen insulin",
    "blood sugar", "glucose", "glycemic", "carbohydrate", "carbs",
    "type 1", "type 2", "gestational", "mellitus", "blood test",
    "endokrin", "metabolik", "metabolisme", "sindrom metabolik",
    "lidah", "kuku", "deteksi", "screening", "skrining"
]

OFF_TOPIC_RESPONSE = """Maaf, saya adalah Glucare - asisten AI yang khusus membahas topik seputar **diabetes mellitus**.

Saya dapat membantu Anda dengan pertanyaan tentang:
🩸 Diabetes Tipe 1, Tipe 2, dan Gestasional
💉 Insulin dan pengobatan diabetes
🍽️ Diet dan nutrisi untuk penderita diabetes
🏃 Gaya hidup sehat dan olahraga
⚠️ Gejala dan komplikasi diabetes
🔬 Pemeriksaan gula darah (GDP, GDS, HbA1c)

Silakan ajukan pertanyaan seputar diabetes, dan saya akan dengan senang hati membantu! 😊"""

def is_diabetes_related(message: str) -> bool:
    """Check apakah pertanyaan terkait diabetes"""
    message_lower = message.lower()
    
    for keyword in DIABETES_KEYWORDS:
        if keyword in message_lower:
            return True
    
    patterns = [
        r"gula\s*darah", r"kadar\s*gula", r"cek\s*gula", r"tes\s*gula",
        r"kencing\s*manis", r"sakit\s*gula", r"penyakit\s*gula",
        r"blood\s*sugar", r"type\s*[12]", r"tipe\s*[12]",
    ]
    
    for pattern in patterns:
        if re.search(pattern, message_lower):
            return True
    
    return False

# ============================================================
# GLOBAL INSTANCES
# ============================================================

groq_client = None
search_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler"""
    global groq_client, search_agent
    
    print("=" * 60)
    print("🤖 Starting Glucare Chatbot API")
    print("=" * 60)
    
    # Debug: check env var
    api_key = os.getenv("GROQ_API_KEY")
    print(f"🔑 GROQ_API_KEY exists: {api_key is not None and len(api_key) > 0}")
    
    # Setup Groq client
    if GROQ_AVAILABLE and api_key:
        groq_client = Groq(api_key=api_key)
        print("✅ Groq client initialized")
        print("   Model: llama-3.3-70b-versatile (GRATIS!)")
    else:
        print("⚠️ Groq not available!")
    
    # Setup web search
    if WEBSEARCH_AVAILABLE:
        try:
            searcher = WebSearcher(max_results=3)
            search_agent = DiabetesSearchAgent(searcher)
            print("✅ Web search agent ready!")
        except Exception as e:
            print(f"⚠️ Could not setup web search: {e}")
    
    print("=" * 60)
    print("✅ API ready at http://localhost:8002")
    print("   Docs: http://localhost:8002/docs")
    print("=" * 60)
    
    yield
    
    print("👋 Shutting down...")

# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Glucare Chatbot API",
    description="""
API untuk Chatbot AI khusus diabetes mellitus.

## Features
- 🤖 Powered by Groq (Llama 3.3 70B) - **GRATIS!**
- 🔍 Web search untuk informasi terbaru
- 🎯 Topic filtering (hanya menjawab tentang diabetes)
- ⚡ Response super cepat
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS - allow all origins for NestJS integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def chat_with_groq(message: str, search_context: str = None) -> str:
    """Chat dengan Groq API"""
    if not groq_client:
        raise HTTPException(
            status_code=503, 
            detail="Groq API not configured. Install groq package dan set API key."
        )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    # Add search context if available
    if search_context:
        messages.append({
            "role": "system",
            "content": f"Berikut adalah informasi terbaru dari web search yang bisa kamu gunakan untuk menjawab:\n\n{search_context}"
        })
    
    messages.append({"role": "user", "content": message})
    
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1000,
        temperature=0.7,
    )
    
    return response.choices[0].message.content

# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return {
        "service": "Glucare Chatbot API",
        "version": "1.0.0",
        "status": "healthy",
        "model": "llama-3.3-70b-versatile",
        "groq_available": groq_client is not None,
        "websearch_available": search_agent is not None,
        "endpoints": {
            "chat": "POST /chat",
            "chat_websearch": "POST /chat/websearch",
            "topics": "GET /topics",
            "search": "GET /search?query=..."
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "groq_available": groq_client is not None,
        "websearch_available": search_agent is not None
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat dengan Glucare
    
    - **message**: Pertanyaan (harus terkait diabetes)
    - **use_websearch**: Aktifkan web search untuk info terbaru
    """
    start_time = time.time()
    
    # Check topic
    if not is_diabetes_related(request.message):
        elapsed_ms = int((time.time() - start_time) * 1000)
        return ChatResponse(
            success=True,
            response=OFF_TOPIC_RESPONSE,
            is_diabetes_related=False,
            websearch_used=False,
            sources=[],
            response_time_ms=elapsed_ms,
            model="llama-3.3-70b-versatile"
        )
    
    try:
        sources = []
        websearch_used = False
        search_context = None
        
        # Web search if requested
        if request.use_websearch and search_agent:
            try:
                results = search_agent.searcher.search(request.message, fetch_content=True)
                if results:
                    websearch_used = True
                    sources = [{"title": r.title, "url": r.url, "source": r.source} for r in results[:3]]
                    search_context = search_agent.searcher.format_results_for_llm(results)
            except Exception as e:
                print(f"⚠️ Web search error: {e}")
        
        # Generate response with Groq
        response_text = chat_with_groq(request.message, search_context)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return ChatResponse(
            success=True,
            response=response_text,
            is_diabetes_related=True,
            websearch_used=websearch_used,
            sources=sources,
            response_time_ms=elapsed_ms,
            model="llama-3.3-70b-versatile"
        )
        
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/chat/websearch", response_model=ChatResponse)
async def chat_with_websearch(request: ChatRequest):
    """Chat + Web Search untuk info terbaru"""
    request.use_websearch = True
    return await chat(request)

@app.get("/topics", response_model=TopicsResponse)
async def get_topics():
    """Daftar topik yang didukung"""
    return TopicsResponse(
        supported_topics=[
            "Diabetes Tipe 1",
            "Diabetes Tipe 2", 
            "Diabetes Gestasional",
            "Gejala dan diagnosis diabetes",
            "Pengobatan dan manajemen diabetes",
            "Diet dan nutrisi untuk diabetes",
            "Olahraga dan gaya hidup sehat",
            "Komplikasi diabetes",
            "Pemeriksaan gula darah (GDP, GDS, HbA1c)",
            "Insulin dan obat diabetes",
        ],
        sample_questions=[
            "Apa gejala diabetes?",
            "Berapa kadar gula darah normal?",
            "Apa perbedaan diabetes tipe 1 dan tipe 2?",
            "Makanan apa yang baik untuk diabetes?",
            "Bagaimana cara mencegah diabetes?",
        ]
    )

@app.get("/search", response_model=SearchResult)
async def search_diabetes_info(query: str):
    """Web search langsung untuk info diabetes"""
    if not search_agent:
        raise HTTPException(status_code=503, detail="Web search tidak tersedia")
    
    try:
        results = search_agent.searcher.search(query, fetch_content=False)
        return SearchResult(
            query=query,
            results=[
                {"title": r.title, "url": r.url, "snippet": r.snippet, "source": r.source}
                for r in results
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🤖 Glucare Chatbot API")
    print("=" * 60)
    print("\n📝 Endpoints:")
    print("   GET  /              - Info & health check")
    print("   POST /chat          - Chat dengan bot")
    print("   POST /chat/websearch - Chat + web search")
    print("   GET  /topics        - Daftar topik")
    print("   GET  /search        - Web search")
    print("\n🌐 Swagger UI: http://localhost:8002/docs")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)

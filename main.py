"""
🩺 GLUCOIN AI API
=================
Combined API: Detection + Chatbot dalam 1 server

Endpoints:
- /detection/* - Deteksi diabetes (gambar + kuesioner)
- /chatbot/* - AI Chatbot diabetes
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers dari masing-masing API
from api_detection import app as detection_app
from api_chatbot import app as chatbot_app

# ============================================================
# MAIN APP
# ============================================================
app = FastAPI(
    title="Glucoin AI API",
    description="API untuk deteksi diabetes dan chatbot AI",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount sub-applications
app.mount("/detection", detection_app)
app.mount("/chatbot", chatbot_app)

@app.get("/")
async def root():
    return {
        "service": "Glucoin AI API",
        "version": "1.0.0",
        "endpoints": {
            "detection": "/detection - Diabetes detection API",
            "chatbot": "/chatbot - AI Chatbot API"
        },
        "docs": {
            "main": "/docs",
            "detection": "/detection/docs",
            "chatbot": "/chatbot/docs"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "services": ["detection", "chatbot"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

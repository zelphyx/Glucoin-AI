"""
🩺 DIABETES DETECTION API
=========================
FastAPI endpoints untuk deteksi diabetes via gambar + kuesioner

Endpoints:
- POST /detect/image - Deteksi dari gambar lidah/kuku
- POST /detect/questionnaire - Scoring dari kuesioner
- POST /detect/combined - Kombinasi 70% gambar + 30% kuesioner
"""

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import tensorflow as tf
import numpy as np
from PIL import Image
import io
from pathlib import Path
from tensorflow.keras.applications.mobilenet_v3 import preprocess_input

# ============================================================
# LOAD MODEL
# ============================================================
# Use relative path for Docker deployment
BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "models" / "simple_v12_best.keras"
print(f"🔄 Loading model from {MODEL_PATH}...")
model = tf.keras.models.load_model(MODEL_PATH)
THRESHOLD = 0.60
print("✅ Model loaded!")

# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(
    title="Diabetes Detection API",
    description="API untuk deteksi diabetes menggunakan gambar lidah/kuku dan kuesioner",
    version="1.0.0"
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
# HEALTH CHECK ENDPOINT
# ============================================================
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/Dokploy"""
    return {"status": "healthy", "model_loaded": model is not None}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Diabetes Detection API is running", "version": "1.0.0"}

# ============================================================
# IMAGE VALIDATION
# ============================================================

def validate_tongue_nail_image(img: Image.Image, image_type: str = "tongue") -> tuple[bool, str, float]:
    """
    Validasi apakah gambar adalah lidah atau kuku yang valid
    
    Returns:
        (is_valid, message, confidence)
    """
    try:
        # Convert to RGB array
        img_array = np.array(img.convert('RGB'))
        
        # Get color statistics
        r_mean = np.mean(img_array[:,:,0])
        g_mean = np.mean(img_array[:,:,1])
        b_mean = np.mean(img_array[:,:,2])
        
        r_std = np.std(img_array[:,:,0])
        g_std = np.std(img_array[:,:,1])
        b_std = np.std(img_array[:,:,2])
        
        # Calculate color ratios
        total = r_mean + g_mean + b_mean + 1e-6
        r_ratio = r_mean / total
        g_ratio = g_mean / total
        b_ratio = b_mean / total
        
        # HSV analysis for better skin/tongue detection
        from colorsys import rgb_to_hsv
        h, s, v = rgb_to_hsv(r_mean/255, g_mean/255, b_mean/255)
        
        confidence = 0.0
        reasons = []
        
        if image_type == "tongue":
            # TONGUE VALIDATION
            # Lidah: dominan merah/pink, saturasi medium-high
            
            # Check 1: Red channel should be dominant or close to dominant
            if r_mean > g_mean and r_mean > b_mean * 0.8:
                confidence += 0.25
            else:
                reasons.append("warna tidak sesuai karakteristik lidah")
            
            # Check 2: Hue should be in red/pink range (0-0.1 or 0.9-1.0)
            if h <= 0.12 or h >= 0.85:
                confidence += 0.25
            else:
                reasons.append("tone warna bukan merah/pink")
            
            # Check 3: Saturation should be moderate (not too gray)
            if s >= 0.15 and s <= 0.85:
                confidence += 0.25
            else:
                reasons.append("saturasi tidak normal")
            
            # Check 4: Should have some color variation (not solid color)
            if r_std > 15 and g_std > 10:
                confidence += 0.25
            else:
                reasons.append("tekstur tidak terdeteksi")
                
        else:  # nail
            # NAIL VALIDATION  
            # Kuku: bisa pink/putih/kekuningan, lebih terang
            
            # Check 1: Brightness should be moderate to high
            if v >= 0.3:
                confidence += 0.25
            else:
                reasons.append("gambar terlalu gelap untuk kuku")
            
            # Check 2: Red should be >= green (skin tone)
            if r_mean >= g_mean * 0.85:
                confidence += 0.25
            else:
                reasons.append("warna tidak sesuai skin tone")
            
            # Check 3: Not too saturated (nails are usually pale)
            if s <= 0.7:
                confidence += 0.25
            else:
                reasons.append("warna terlalu jenuh untuk kuku")
            
            # Check 4: Has some texture
            if r_std > 10 or g_std > 10:
                confidence += 0.25
            else:
                reasons.append("tekstur tidak terdeteksi")
        
        # Determine validity
        is_valid = confidence >= 0.5
        
        if is_valid:
            message = f"Gambar {image_type} terdeteksi valid (confidence: {confidence*100:.0f}%)"
        else:
            message = f"Gambar tidak terdeteksi sebagai {image_type}. " + ", ".join(reasons)
        
        return is_valid, message, confidence
        
    except Exception as e:
        return False, f"Error validasi gambar: {str(e)}", 0.0


# ============================================================
# PYDANTIC MODELS
# ============================================================

class ImageDetectionResult(BaseModel):
    success: bool
    is_valid_image: bool = True
    image_type: Optional[str] = None  # "tongue" or "nail"
    validation_confidence: Optional[float] = None
    probability: Optional[float] = None
    prediction: Optional[str] = None  # "DIABETES" or "NON_DIABETES"
    risk_level: Optional[str] = None  # "tidak", "rendah", "sedang", "tinggi"
    message: str

class DualImageDetectionResult(BaseModel):
    """Result untuk deteksi dengan 2 gambar (lidah + kuku)"""
    success: bool
    
    # Tongue results
    tongue_valid: bool = False
    tongue_probability: Optional[float] = None
    tongue_validation_confidence: Optional[float] = None
    
    # Nail results
    nail_valid: bool = False
    nail_probability: Optional[float] = None
    nail_validation_confidence: Optional[float] = None
    
    # Combined results
    combined_probability: Optional[float] = None
    prediction: Optional[str] = None
    risk_level: Optional[str] = None
    message: str

class QuestionnaireNonDiabetes(BaseModel):
    """Kuesioner untuk yang belum terdiagnosis diabetes"""
    penglihatan_buram: bool = Field(..., description="Penglihatan tiba-tiba buram atau tidak stabil")
    sering_bak: bool = Field(..., description="Buang air kecil lebih sering, terutama malam hari")
    luka_lama_sembuh: bool = Field(..., description="Luka pada kulit cenderung lama sembuh")
    kesemutan: bool = Field(..., description="Sering merasakan kesemutan di tangan atau kaki")
    obesitas: bool = Field(..., description="Memiliki berat badan berlebih atau obesitas")
    sering_lapar: bool = Field(..., description="Sering merasa lapar walaupun sudah makan")
    berat_badan: float = Field(..., description="Berat badan dalam kg", ge=20, le=300)
    tinggi_badan: float = Field(..., description="Tinggi badan dalam cm", ge=100, le=250)
    riwayat_keluarga: bool = Field(..., description="Ada riwayat diabetes tipe 2 pada keluarga")
    tekanan_darah_tinggi: bool = Field(..., description="Pernah didiagnosis tekanan darah tinggi")
    kolesterol_tinggi: bool = Field(..., description="Kadar kolesterol pernah dinyatakan tinggi")
    frekuensi_olahraga: int = Field(..., description="Frekuensi olahraga: 0=tidak pernah, 1=1-2x, 2=3-4x, 3=5+x seminggu", ge=0, le=3)
    pola_makan: int = Field(..., description="Pola makan: 0=tinggi gula/karbo, 1=cukup seimbang, 2=sehat", ge=0, le=2)

class QuestionnaireDiabetes(BaseModel):
    """Kuesioner untuk yang sudah terdiagnosis diabetes"""
    peningkatan_bak: bool = Field(..., description="Peningkatan frekuensi buang air kecil")
    kesemutan: bool = Field(..., description="Sering kesemutan atau mati rasa pada tangan/kaki")
    perubahan_berat: int = Field(..., description="Berat badan: 0=stabil, 1=naik sedikit, 2=turun drastis, 3=naik drastis", ge=0, le=3)
    gula_darah_puasa: float = Field(..., description="Rata-rata gula darah puasa (mg/dL)", ge=50, le=500)
    rutin_hba1c: bool = Field(..., description="Rutin memeriksakan HbA1c")
    hasil_hba1c: Optional[float] = Field(None, description="Hasil HbA1c terakhir (%)", ge=4, le=15)
    tekanan_darah_sistolik: float = Field(..., description="Tekanan darah sistolik (mmHg)", ge=80, le=250) 7
    kondisi_kolesterol: int = Field(..., description="Kolesterol: 0=normal, 1=sedikit tinggi, 2=tinggi", ge=0, le=2)
    konsumsi_obat: bool = Field(..., description="Sedang mengonsumsi obat diabetes")
    pernah_hipoglikemia: bool = Field(..., description="Pernah mengalami hipoglikemia")
    olahraga_rutin: bool = Field(..., description="Berolahraga secara rutin")
    pola_makan: int = Field(..., description="Pola makan: 0=tinggi gula/karbo, 1=cukup terkontrol, 2=diet ketat", ge=0, le=2)

class QuestionnaireResult(BaseModel):
    success: bool
    score: float
    risk_level: str
    interpretation: str
    recommendations: List[str]

class CombinedRequest(BaseModel):
    """Request untuk deteksi kombinasi"""
    is_diabetic: bool = Field(..., description="Apakah sudah terdiagnosis diabetes")
    image_score: Optional[float] = Field(None, description="Skor dari deteksi gambar (0-1)", ge=0, le=1)
    questionnaire: dict = Field(..., description="Jawaban kuesioner")

class CombinedResult(BaseModel):
    success: bool
    image_score: Optional[float]
    questionnaire_score: float
    final_score: float
    risk_level: str
    interpretation: str
    recommendations: List[str]

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_risk_level(score: float) -> str:
    """Get risk level from score"""
    if score >= 0.75:
        return "tinggi"
    elif score >= 0.50:
        return "sedang"
    elif score >= 0.25:
        return "rendah"
    else:
        return "tidak"

def calculate_non_diabetic_score(q: QuestionnaireNonDiabetes) -> float:
    """Calculate risk score for non-diabetic questionnaire"""
    score = 0
    max_score = 12
    
    if q.penglihatan_buram:
        score += 1
    if q.sering_bak:
        score += 1
    if q.luka_lama_sembuh:
        score += 1
    if q.kesemutan:
        score += 1
    if q.obesitas:
        score += 1
    if q.sering_lapar:
        score += 1
    
    # BMI
    bmi = q.berat_badan / ((q.tinggi_badan / 100) ** 2)
    if bmi >= 30:
        score += 1.5
    elif bmi >= 25:
        score += 1
    
    if q.riwayat_keluarga:
        score += 1.5
    if q.tekanan_darah_tinggi:
        score += 1
    if q.kolesterol_tinggi:
        score += 1
    
    # Olahraga (0=tidak pernah, 1=1-2x, 2=3-4x, 3=5+x)
    if q.frekuensi_olahraga == 0:
        score += 1
    elif q.frekuensi_olahraga == 1:
        score += 0.5
    
    # Pola makan (0=tinggi gula, 1=seimbang, 2=sehat)
    if q.pola_makan == 0:
        score += 1
    elif q.pola_makan == 1:
        score += 0.5
    
    return min(score / max_score, 1.0)

def calculate_diabetic_score(q: QuestionnaireDiabetes) -> float:
    """Calculate severity score for diabetic questionnaire"""
    score = 0
    max_score = 12
    
    if q.peningkatan_bak:
        score += 1
    if q.kesemutan:
        score += 1
    
    # Perubahan berat (0=stabil, 1=naik sedikit, 2=turun drastis, 3=naik drastis)
    if q.perubahan_berat >= 2:
        score += 1.5
    elif q.perubahan_berat == 1:
        score += 0.5
    
    # Gula darah puasa
    if q.gula_darah_puasa >= 180:
        score += 2
    elif q.gula_darah_puasa >= 130:
        score += 1.5
    elif q.gula_darah_puasa >= 100:
        score += 1
    
    # HbA1c
    if q.rutin_hba1c and q.hasil_hba1c:
        if q.hasil_hba1c >= 9:
            score += 2
        elif q.hasil_hba1c >= 7:
            score += 1
    elif not q.rutin_hba1c:
        score += 0.5
    
    # Tekanan darah
    if q.tekanan_darah_sistolik >= 140:
        score += 1
    elif q.tekanan_darah_sistolik >= 130:
        score += 0.5
    
    # Kolesterol (0=normal, 1=sedikit tinggi, 2=tinggi)
    if q.kondisi_kolesterol == 2:
        score += 1
    elif q.kondisi_kolesterol == 1:
        score += 0.5
    
    if not q.konsumsi_obat:
        score += 0.5
    if q.pernah_hipoglikemia:
        score += 1
    if not q.olahraga_rutin:
        score += 1
    
    # Pola makan (0=tinggi gula, 1=terkontrol, 2=diet ketat)
    if q.pola_makan == 0:
        score += 1
    elif q.pola_makan == 1:
        score += 0.5
    
    return min(score / max_score, 1.0)

def get_recommendations(score: float, is_diabetic: bool) -> List[str]:
    """Get recommendations based on score"""
    if is_diabetic:
        if score >= 0.75:
            return [
                "Konsultasi dengan dokter/endokrinolog secepatnya",
                "Review dosis obat/insulin",
                "Periksa gula darah lebih sering",
                "Evaluasi pola makan dan olahraga",
                "Periksa komplikasi (mata, ginjal, kaki)"
            ]
        elif score >= 0.50:
            return [
                "Kontrol rutin ke dokter",
                "Jaga pola makan rendah gula/karbo",
                "Tingkatkan aktivitas fisik",
                "Pantau gula darah secara teratur"
            ]
        elif score >= 0.25:
            return [
                "Lanjutkan pengobatan sesuai anjuran dokter",
                "Pertahankan pola hidup sehat",
                "Kontrol rutin sesuai jadwal"
            ]
        else:
            return [
                "Pertahankan pola makan sehat",
                "Olahraga teratur",
                "Minum obat sesuai anjuran"
            ]
    else:
        if score >= 0.75:
            return [
                "Periksa gula darah puasa dan HbA1c segera",
                "Konsultasi ke dokter secepatnya",
                "Kurangi konsumsi gula dan karbohidrat",
                "Mulai program olahraga teratur",
                "Turunkan berat badan jika berlebih"
            ]
        elif score >= 0.50:
            return [
                "Periksa gula darah untuk skrining",
                "Konsultasi ke dokter untuk evaluasi",
                "Mulai pola hidup sehat",
                "Olahraga minimal 3x seminggu"
            ]
        elif score >= 0.25:
            return [
                "Periksa gula darah rutin (1x setahun)",
                "Jaga pola makan seimbang",
                "Olahraga teratur"
            ]
        else:
            return [
                "Tetap jaga pola makan sehat",
                "Olahraga teratur",
                "Periksa kesehatan rutin tahunan"
            ]

def get_interpretation(score: float, is_diabetic: bool) -> str:
    """Get interpretation text"""
    if is_diabetic:
        if score >= 0.75:
            return "DIABETES TIDAK TERKONTROL - Kondisi diabetes kurang terkontrol dengan baik. Diperlukan tindakan segera."
        elif score >= 0.50:
            return "DIABETES PERLU PERHATIAN - Ada beberapa aspek yang perlu diperbaiki."
        elif score >= 0.25:
            return "DIABETES CUKUP TERKONTROL - Kondisi cukup baik, pertahankan!"
        else:
            return "DIABETES TERKONTROL BAIK - Diabetes terkontrol dengan baik."
    else:
        if score >= 0.75:
            return "RISIKO SANGAT TINGGI - Risiko sangat tinggi terkena diabetes. Diperlukan tindakan segera."
        elif score >= 0.50:
            return "RISIKO TINGGI - Risiko tinggi terkena diabetes."
        elif score >= 0.25:
            return "RISIKO SEDANG - Ada beberapa faktor risiko yang perlu diperhatikan."
        else:
            return "RISIKO RENDAH - Risiko diabetes rendah. Pertahankan pola hidup sehat!"

# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return {
        "service": "Diabetes Detection API",
        "version": "1.0.0",
        "endpoints": {
            "detect_image": "POST /detect/image",
            "detect_questionnaire_non_diabetic": "POST /detect/questionnaire/non-diabetic",
            "detect_questionnaire_diabetic": "POST /detect/questionnaire/diabetic",
            "detect_combined": "POST /detect/combined"
        }
    }

@app.post("/detect/image", response_model=ImageDetectionResult)
async def detect_from_image(
    file: UploadFile = File(...),
    image_type: str = "tongue"  # "tongue" atau "nail"
):
    """
    Deteksi diabetes dari gambar lidah atau kuku
    
    - **file**: Gambar lidah atau kuku (jpg, png, jpeg)
    - **image_type**: Tipe gambar - "tongue" (lidah) atau "nail" (kuku)
    
    Returns probability dan prediksi. Akan menolak gambar yang tidak valid.
    """
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File harus berupa gambar")
        
        # Validate image_type
        if image_type not in ["tongue", "nail"]:
            raise HTTPException(status_code=400, detail="image_type harus 'tongue' atau 'nail'")
        
        # Read image
        contents = await file.read()
        img = Image.open(io.BytesIO(contents)).convert('RGB')
        
        # ============================================================
        # VALIDATE IMAGE - Check if it's actually a tongue/nail
        # ============================================================
        is_valid, validation_msg, validation_conf = validate_tongue_nail_image(img, image_type)
        
        if not is_valid:
            type_indo = "lidah" if image_type == "tongue" else "kuku"
            return ImageDetectionResult(
                success=False,
                is_valid_image=False,
                image_type=image_type,
                validation_confidence=validation_conf,
                probability=None,
                prediction=None,
                risk_level=None,
                message=f"❌ Gambar tidak valid. {validation_msg}. Silakan upload gambar {type_indo} yang jelas."
            )
        
        # ============================================================
        # PROCESS VALID IMAGE
        # ============================================================
        img_resized = img.resize((224, 224))
        arr = np.array(img_resized).astype(np.float32)
        arr = preprocess_input(arr)
        arr = np.expand_dims(arr, 0)
        
        # Predict
        prob = float(model.predict(arr, verbose=0)[0][0])
        prediction = "DIABETES" if prob >= THRESHOLD else "NON_DIABETES"
        risk_level = get_risk_level(prob)
        
        type_indo = "lidah" if image_type == "tongue" else "kuku"
        return ImageDetectionResult(
            success=True,
            is_valid_image=True,
            image_type=image_type,
            validation_confidence=validation_conf,
            probability=prob,
            prediction=prediction,
            risk_level=risk_level,
            message=f"✅ Analisis gambar {type_indo} selesai. Probabilitas diabetes: {prob*100:.1f}%"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@app.post("/detect/questionnaire/non-diabetic", response_model=QuestionnaireResult)
async def questionnaire_non_diabetic(data: QuestionnaireNonDiabetes):
    """
    Kuesioner screening untuk yang BELUM terdiagnosis diabetes
    
    Returns risk score dan rekomendasi
    """
    try:
        score = calculate_non_diabetic_score(data)
        risk_level = get_risk_level(score)
        interpretation = get_interpretation(score, is_diabetic=False)
        recommendations = get_recommendations(score, is_diabetic=False)
        
        return QuestionnaireResult(
            success=True,
            score=score,
            risk_level=risk_level,
            interpretation=interpretation,
            recommendations=recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/detect/questionnaire/diabetic", response_model=QuestionnaireResult)
async def questionnaire_diabetic(data: QuestionnaireDiabetes):
    """
    Kuesioner monitoring untuk yang SUDAH terdiagnosis diabetes
    
    Returns severity score dan rekomendasi
    """
    try:
        score = calculate_diabetic_score(data)
        risk_level = get_risk_level(score)
        interpretation = get_interpretation(score, is_diabetic=True)
        recommendations = get_recommendations(score, is_diabetic=True)
        
        return QuestionnaireResult(
            success=True,
            score=score,
            risk_level=risk_level,
            interpretation=interpretation,
            recommendations=recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/detect/combined", response_model=CombinedResult)
async def detect_combined(data: CombinedRequest):
    """
    Deteksi kombinasi: 70% gambar + 30% kuesioner
    
    - **is_diabetic**: Apakah sudah terdiagnosis diabetes
    - **image_score**: Skor dari deteksi gambar (opsional, 0-1)
    - **questionnaire**: Jawaban kuesioner
    
    Returns combined score dan rekomendasi
    """
    try:
        # Calculate questionnaire score
        if data.is_diabetic:
            q = QuestionnaireDiabetes(**data.questionnaire)
            q_score = calculate_diabetic_score(q)
        else:
            q = QuestionnaireNonDiabetes(**data.questionnaire)
            q_score = calculate_non_diabetic_score(q)
        
        # Calculate final score
        if data.image_score is not None:
            # 70% image + 30% questionnaire
            final_score = (0.70 * data.image_score) + (0.30 * q_score)
        else:
            # 100% questionnaire if no image
            final_score = q_score
        
        risk_level = get_risk_level(final_score)
        interpretation = get_interpretation(final_score, data.is_diabetic)
        recommendations = get_recommendations(final_score, data.is_diabetic)
        
        return CombinedResult(
            success=True,
            image_score=data.image_score,
            questionnaire_score=q_score,
            final_score=final_score,
            risk_level=risk_level,
            interpretation=interpretation,
            recommendations=recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "threshold": THRESHOLD
    }

# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("📷 Diabetes Detection API")
    print("=" * 60)
    print("\n📝 Endpoints:")
    print("   POST /detect/image - Deteksi dari gambar")
    print("   POST /detect/questionnaire/non-diabetic")
    print("   POST /detect/questionnaire/diabetic")
    print("   POST /detect/combined")
    print("\n🌐 Swagger UI: http://localhost:8001/docs")
    print("=" * 60)
    uvicorn.run("api_detection:app", host="0.0.0.0", port=8001, reload=False)

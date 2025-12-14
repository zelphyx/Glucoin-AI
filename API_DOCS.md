# 📚 GLUCOIN API DOCUMENTATION

## Overview

Glucoin menyediakan 2 API untuk aplikasi diabetes:

| API | Port | Fungsi |
|-----|------|--------|
| **Detection API** | 8001 | Deteksi diabetes dari gambar lidah/kuku + kuesioner |
| **Chatbot API** | 8002 | Chatbot AI khusus diabetes |

---

# 🩺 DETECTION API

**Base URL:** `http://localhost:8001` atau `https://your-domain.com`

## Endpoints

### 1. Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

---

### 2. Detect from Image
```
POST /detect/image?image_type=tongue
```

Deteksi diabetes dari gambar lidah atau kuku. API akan **validasi gambar** terlebih dahulu.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | ✅ | Gambar (jpg, png, jpeg) |
| `image_type` | Query | ✅ | `tongue` (lidah) atau `nail` (kuku) |

**Request (multipart/form-data):**
```bash
curl -X POST "http://localhost:8001/detect/image?image_type=tongue" \
  -F "file=@tongue_image.jpg"
```

**Response Success (Gambar Valid):**
```json
{
  "success": true,
  "is_valid_image": true,
  "image_type": "tongue",
  "validation_confidence": 0.75,
  "probability": 0.65,
  "prediction": "DIABETES",
  "risk_level": "sedang",
  "message": "✅ Analisis gambar lidah selesai. Probabilitas diabetes: 65.0%"
}
```

**Response Failed (Gambar Tidak Valid):**
```json
{
  "success": false,
  "is_valid_image": false,
  "image_type": "tongue",
  "validation_confidence": 0.25,
  "probability": null,
  "prediction": null,
  "risk_level": null,
  "message": "❌ Gambar tidak valid. warna tidak sesuai karakteristik lidah. Silakan upload gambar lidah yang jelas."
}
```

**Risk Levels:**
| Score | Risk Level |
|-------|------------|
| 0.75 - 1.00 | `tinggi` |
| 0.50 - 0.74 | `sedang` |
| 0.25 - 0.49 | `rendah` |
| 0.00 - 0.24 | `tidak` |

---

### 3. Detect from Dual Image (Lidah + Kuku) ⭐ RECOMMENDED
```
POST /detect/dual-image
```

Deteksi diabetes dari **DUA gambar sekaligus** (lidah + kuku) untuk hasil lebih akurat!

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tongue_image` | File | ✅ | Gambar lidah (jpg, png, jpeg) |
| `nail_image` | File | ✅ | Gambar kuku (jpg, png, jpeg) |

**Request (multipart/form-data):**
```bash
curl -X POST "http://localhost:8001/detect/dual-image" \
  -F "tongue_image=@lidah.jpg" \
  -F "nail_image=@kuku.jpg"
```

**Response (Kedua Gambar Valid):**
```json
{
  "success": true,
  "tongue_valid": true,
  "tongue_probability": 0.72,
  "tongue_validation_confidence": 0.75,
  "nail_valid": true,
  "nail_probability": 0.58,
  "nail_validation_confidence": 0.75,
  "combined_probability": 0.65,
  "prediction": "DIABETES",
  "risk_level": "sedang",
  "message": "✅ Analisis selesai. Probabilitas diabetes: 65.0% (Lidah: 72.0%, Kuku: 58.0%)"
}
```

**Response (Hanya Salah Satu Valid):**
```json
{
  "success": true,
  "tongue_valid": true,
  "tongue_probability": 0.72,
  "tongue_validation_confidence": 0.75,
  "nail_valid": false,
  "nail_probability": null,
  "nail_validation_confidence": 0.25,
  "combined_probability": 0.72,
  "prediction": "DIABETES",
  "risk_level": "sedang",
  "message": "⚠️ Hanya gambar lidah yang valid. Probabilitas: 72.0%. Gambar kuku tidak terdeteksi."
}
```

**Response (Keduanya Tidak Valid):**
```json
{
  "success": false,
  "tongue_valid": false,
  "tongue_probability": null,
  "tongue_validation_confidence": 0.25,
  "nail_valid": false,
  "nail_probability": null,
  "nail_validation_confidence": 0.0,
  "combined_probability": null,
  "prediction": null,
  "risk_level": null,
  "message": "❌ Kedua gambar tidak valid. Lidah: warna tidak sesuai | Kuku: tekstur tidak terdeteksi"
}
```

---

### 4. Questionnaire Non-Diabetic
```
POST /detect/questionnaire/non-diabetic
```

Kuesioner screening untuk orang yang **BELUM** terdiagnosis diabetes.

**Request Body:**
```json
{
  "penglihatan_buram": false,
  "sering_bak": true,
  "luka_lama_sembuh": false,
  "kesemutan": true,
  "obesitas": false,
  "sering_lapar": true,
  "berat_badan": 75.0,
  "tinggi_badan": 170.0,
  "riwayat_keluarga": true,
  "tekanan_darah_tinggi": false,
  "kolesterol_tinggi": false,
  "frekuensi_olahraga": 1,
  "pola_makan": 1
}
```

**Field Descriptions:**
| Field | Type | Description |
|-------|------|-------------|
| `penglihatan_buram` | bool | Penglihatan tiba-tiba buram |
| `sering_bak` | bool | Buang air kecil lebih sering |
| `luka_lama_sembuh` | bool | Luka cenderung lama sembuh |
| `kesemutan` | bool | Sering kesemutan di tangan/kaki |
| `obesitas` | bool | Berat badan berlebih |
| `sering_lapar` | bool | Sering lapar walau sudah makan |
| `berat_badan` | float | Berat badan (kg), 20-300 |
| `tinggi_badan` | float | Tinggi badan (cm), 100-250 |
| `riwayat_keluarga` | bool | Ada riwayat diabetes di keluarga |
| `tekanan_darah_tinggi` | bool | Pernah didiagnosis hipertensi |
| `kolesterol_tinggi` | bool | Kolesterol tinggi |
| `frekuensi_olahraga` | int | 0=tidak pernah, 1=1-2x, 2=3-4x, 3=5+x seminggu |
| `pola_makan` | int | 0=tinggi gula, 1=seimbang, 2=sehat |

**Response:**
```json
{
  "success": true,
  "score": 0.45,
  "risk_level": "rendah",
  "interpretation": "Risiko diabetes rendah, tetapi tetap perlu waspada...",
  "recommendations": [
    "Pertahankan pola makan sehat",
    "Rutin berolahraga minimal 3x seminggu",
    "Periksakan gula darah setahun sekali"
  ]
}
```

---

### 5. Questionnaire Diabetic
```
POST /detect/questionnaire/diabetic
```

Kuesioner monitoring untuk orang yang **SUDAH** terdiagnosis diabetes.

**Request Body:**
```json
{
  "peningkatan_bak": true,
  "kesemutan": true,
  "perubahan_berat": 1,
  "gula_darah_puasa": 140.0,
  "rutin_hba1c": true,
  "hasil_hba1c": 7.5,
  "tekanan_darah_sistolik": 130.0,
  "kondisi_kolesterol": 1,
  "konsumsi_obat": true,
  "pernah_hipoglikemia": false,
  "olahraga_rutin": true,
  "pola_makan": 1
}
```

**Field Descriptions:**
| Field | Type | Description |
|-------|------|-------------|
| `peningkatan_bak` | bool | Frekuensi BAK meningkat |
| `kesemutan` | bool | Sering kesemutan/mati rasa |
| `perubahan_berat` | int | 0=stabil, 1=naik sedikit, 2=turun drastis, 3=naik drastis |
| `gula_darah_puasa` | float | Rata-rata GDP (mg/dL), 50-500 |
| `rutin_hba1c` | bool | Rutin periksa HbA1c |
| `hasil_hba1c` | float? | Hasil HbA1c terakhir (%), 4-15 |
| `tekanan_darah_sistolik` | float | Tekanan darah sistolik (mmHg), 80-250 |
| `kondisi_kolesterol` | int | 0=normal, 1=sedikit tinggi, 2=tinggi |
| `konsumsi_obat` | bool | Sedang minum obat diabetes |
| `pernah_hipoglikemia` | bool | Pernah hipoglikemia |
| `olahraga_rutin` | bool | Olahraga rutin |
| `pola_makan` | int | 0=tinggi gula, 1=terkontrol, 2=diet ketat |

---

### 5. Combined Detection
```
POST /detect/combined
```

Kombinasi skor dari gambar (70%) + kuesioner (30%).

**Request Body:**
```json
{
  "is_diabetic": false,
  "image_score": 0.65,
  "questionnaire": {
    "penglihatan_buram": false,
    "sering_bak": true,
    ...
  }
}
```

---

# 🤖 CHATBOT API

**Base URL:** `http://localhost:8002` atau `https://your-domain.com`

## Endpoints

### 1. Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "groq_available": true,
  "websearch_available": true
}
```

---

### 2. Chat
```
POST /chat
```

Chat dengan Glucare. **Hanya menjawab pertanyaan seputar diabetes.**

**Request Body:**
```json
{
  "message": "Apa gejala diabetes tipe 2?",
  "use_websearch": false,
  "session_id": "user-123"
}
```

**Response Success (Topik Diabetes):**
```json
{
  "success": true,
  "response": "Gejala diabetes tipe 2 meliputi:\n\n🔹 **Sering haus** (polidipsia)\n🔹 **Sering buang air kecil** (poliuria)...",
  "is_diabetes_related": true,
  "websearch_used": false,
  "sources": [],
  "response_time_ms": 450,
  "model": "llama-3.3-70b-versatile"
}
```

**Response (Topik Non-Diabetes):**
```json
{
  "success": true,
  "response": "Maaf, saya adalah Glucare - asisten AI yang khusus membahas topik seputar **diabetes mellitus**...",
  "is_diabetes_related": false,
  "websearch_used": false,
  "sources": [],
  "response_time_ms": 5,
  "model": "llama-3.3-70b-versatile"
}
```

---

### 3. Chat with Web Search
```
POST /chat/websearch
```

Chat + cari info terbaru dari internet.

**Request Body:**
```json
{
  "message": "Obat diabetes terbaru 2024"
}
```

**Response:**
```json
{
  "success": true,
  "response": "Berdasarkan informasi terbaru...",
  "is_diabetes_related": true,
  "websearch_used": true,
  "sources": [
    {"title": "Artikel 1", "url": "https://...", "source": "google"},
    {"title": "Artikel 2", "url": "https://...", "source": "duckduckgo"}
  ],
  "response_time_ms": 2500,
  "model": "llama-3.3-70b-versatile"
}
```

---

### 4. Get Topics
```
GET /topics
```

Daftar topik yang didukung.

**Response:**
```json
{
  "supported_topics": [
    "Diabetes Tipe 1",
    "Diabetes Tipe 2",
    "Diabetes Gestasional",
    "Gejala dan diagnosis diabetes",
    "Pengobatan dan manajemen diabetes",
    "Diet dan nutrisi untuk diabetes",
    "Olahraga dan gaya hidup sehat",
    "Komplikasi diabetes",
    "Pemeriksaan gula darah (GDP, GDS, HbA1c)",
    "Insulin dan obat diabetes"
  ],
  "sample_questions": [
    "Apa gejala diabetes?",
    "Berapa kadar gula darah normal?",
    "Apa perbedaan diabetes tipe 1 dan tipe 2?",
    "Makanan apa yang baik untuk diabetes?",
    "Bagaimana cara mencegah diabetes?"
  ]
}
```

---

### 5. Direct Search
```
GET /search?query=gejala diabetes
```

Web search langsung tanpa AI processing.

**Response:**
```json
{
  "query": "gejala diabetes",
  "results": [
    {
      "title": "10 Gejala Diabetes yang Harus Diwaspadai",
      "url": "https://...",
      "snippet": "Gejala umum diabetes meliputi...",
      "source": "duckduckgo"
    }
  ]
}
```

---

# 🔗 Integration dengan NestJS

## Environment Variables
```env
DETECTION_API_URL=https://glucoin-detection.your-domain.com
CHATBOT_API_URL=https://glucoin-chatbot.your-domain.com
```

## Example Service (TypeScript)
```typescript
import { Injectable, HttpService } from '@nestjs/common';
import * as FormData from 'form-data';

@Injectable()
export class GlucoinService {
  constructor(private httpService: HttpService) {}

  // Detection API
  async detectFromImage(file: Express.Multer.File, imageType: 'tongue' | 'nail') {
    const formData = new FormData();
    formData.append('file', file.buffer, file.originalname);
    
    const response = await this.httpService.axiosRef.post(
      `${process.env.DETECTION_API_URL}/detect/image?image_type=${imageType}`,
      formData,
      { headers: formData.getHeaders() }
    );
    return response.data;
  }

  async questionnaireNonDiabetic(data: any) {
    const response = await this.httpService.axiosRef.post(
      `${process.env.DETECTION_API_URL}/detect/questionnaire/non-diabetic`,
      data
    );
    return response.data;
  }

  // Chatbot API
  async chat(message: string, useWebsearch = false) {
    const response = await this.httpService.axiosRef.post(
      `${process.env.CHATBOT_API_URL}/chat`,
      { message, use_websearch: useWebsearch }
    );
    return response.data;
  }
}
```

---

# 🚀 Deployment

## Docker Compose
```bash
docker-compose up -d
```

Akan menjalankan:
- Detection API di port **8001**
- Chatbot API di port **8002**

## Swagger UI
- Detection: `http://localhost:8001/docs`
- Chatbot: `http://localhost:8002/docs`

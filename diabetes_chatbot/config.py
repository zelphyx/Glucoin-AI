"""
Konfigurasi untuk Diabetes Chatbot dengan DeepSeek LoRA Fine-tuning
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ModelConfig:
    """Konfigurasi Model DeepSeek"""
    model_name: str = "deepseek-ai/deepseek-llm-7b-chat"  # atau deepseek-llm-7b-base
    model_type: str = "deepseek"
    max_length: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    
@dataclass
class LoRAConfig:
    """Konfigurasi LoRA untuk Fine-tuning"""
    r: int = 16  # Rank
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])
    bias: str = "none"
    task_type: str = "CAUSAL_LM"

@dataclass
class TrainingConfig:
    """Konfigurasi Training"""
    output_dir: str = "./models/diabetes_chatbot_lora"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    warmup_ratio: float = 0.03
    lr_scheduler_type: str = "cosine"
    logging_steps: int = 10
    save_steps: int = 100
    eval_steps: int = 100
    save_total_limit: int = 3
    fp16: bool = True
    bf16: bool = False
    gradient_checkpointing: bool = True
    optim: str = "paged_adamw_32bit"
    max_grad_norm: float = 0.3

@dataclass
class DataConfig:
    """Konfigurasi Dataset"""
    dataset_path: str = "./data/diabetes_qa_dataset.json"
    train_split: float = 0.9
    val_split: float = 0.1
    max_seq_length: int = 2048
    
@dataclass
class WebSearchConfig:
    """Konfigurasi Web Search"""
    search_engine: str = "duckduckgo"  # atau "google", "bing"
    max_results: int = 5
    search_timeout: int = 10
    trusted_sources: List[str] = field(default_factory=lambda: [
        "who.int",
        "diabetes.org",
        "mayoclinic.org",
        "webmd.com",
        "healthline.com",
        "medicalnewstoday.com",
        "ncbi.nlm.nih.gov",
        "cdc.gov",
        "niddk.nih.gov",
        "alodokter.com",
        "halodoc.com",
        "kemenkes.go.id"
    ])

@dataclass
class ChatbotConfig:
    """Konfigurasi Chatbot"""
    mode: str = "hybrid"  # "chat_only", "websearch_only", "hybrid"
    use_websearch_threshold: float = 0.7  # Confidence threshold untuk trigger web search
    system_prompt: str = """Kamu adalah DiabetesBot, asisten AI khusus yang ahli dalam bidang diabetes mellitus. 
Kamu memiliki pengetahuan mendalam tentang:
- Diabetes Tipe 1, Tipe 2, dan Gestasional
- Gejala, diagnosis, dan komplikasi diabetes
- Pengelolaan gula darah dan pengobatan
- Diet dan nutrisi untuk penderita diabetes
- Olahraga dan gaya hidup sehat
- Pencegahan dan edukasi diabetes

Berikan jawaban yang akurat, informatif, dan mudah dipahami.
Selalu ingatkan pengguna untuk berkonsultasi dengan dokter untuk diagnosis dan pengobatan.
Jawab dalam Bahasa Indonesia kecuali diminta sebaliknya."""

    websearch_prompt: str = """Berdasarkan informasi terbaru dari web search berikut:
{search_results}

Jawab pertanyaan pengguna dengan menggabungkan pengetahuanmu dan informasi di atas.
Sebutkan sumber informasi jika relevan."""


# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Buat direktori jika belum ada
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

"""
Web Search Module untuk Diabetes Chatbot
Mendapatkan informasi terbaru dari internet
"""

import os
import re
import time
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed

# Optional imports
try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from googlesearch import search as google_search
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False


@dataclass
class SearchResult:
    """Hasil pencarian"""
    title: str
    url: str
    snippet: str
    source: str
    content: Optional[str] = None


class WebSearcher:
    """Web Search untuk mencari informasi diabetes"""
    
    def __init__(
        self,
        search_engine: str = "duckduckgo",
        max_results: int = 5,
        timeout: int = 10,
        trusted_sources: List[str] = None
    ):
        self.search_engine = search_engine
        self.max_results = max_results
        self.timeout = timeout
        self.trusted_sources = trusted_sources or [
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
        ]
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    def search_duckduckgo(self, query: str) -> List[SearchResult]:
        """Pencarian menggunakan DuckDuckGo"""
        if not HAS_DDGS:
            print("⚠️ duckduckgo-search tidak terinstall. Install dengan: pip install duckduckgo-search")
            return []
        
        results = []
        try:
            with DDGS() as ddgs:
                search_results = ddgs.text(
                    query,
                    max_results=self.max_results * 2  # Ambil lebih untuk filter
                )
                
                for r in search_results:
                    result = SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", ""),
                        source=self._extract_domain(r.get("href", ""))
                    )
                    results.append(result)
                    
                    if len(results) >= self.max_results:
                        break
                        
        except Exception as e:
            print(f"❌ Error DuckDuckGo search: {e}")
        
        return results
    
    def search_google(self, query: str) -> List[SearchResult]:
        """Pencarian menggunakan Google (memerlukan googlesearch-python)"""
        if not HAS_GOOGLE:
            print("⚠️ googlesearch-python tidak terinstall. Install dengan: pip install googlesearch-python")
            return []
        
        results = []
        try:
            search_results = google_search(
                query,
                num_results=self.max_results,
                lang="id"
            )
            
            for url in search_results:
                result = SearchResult(
                    title="",
                    url=url,
                    snippet="",
                    source=self._extract_domain(url)
                )
                results.append(result)
                
        except Exception as e:
            print(f"❌ Error Google search: {e}")
        
        return results
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain dari URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain
        except:
            return url
    
    def fetch_page_content(self, url: str, max_length: int = 2000) -> Optional[str]:
        """Ambil konten dari halaman web"""
        if not HAS_BS4:
            return None
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Hapus script, style, nav, footer
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            
            # Ambil teks dari paragraf
            paragraphs = soup.find_all(["p", "article", "main"])
            text_content = []
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 50:  # Skip paragraf pendek
                    text_content.append(text)
            
            content = "\n".join(text_content)
            
            # Batasi panjang
            if len(content) > max_length:
                content = content[:max_length] + "..."
            
            return content
            
        except Exception as e:
            print(f"⚠️ Error fetching {url}: {e}")
            return None
    
    def is_trusted_source(self, url: str) -> bool:
        """Cek apakah URL dari sumber terpercaya"""
        domain = self._extract_domain(url)
        return any(trusted in domain for trusted in self.trusted_sources)
    
    def search(
        self, 
        query: str, 
        fetch_content: bool = False,
        prioritize_trusted: bool = True
    ) -> List[SearchResult]:
        """
        Lakukan pencarian web
        
        Args:
            query: Query pencarian
            fetch_content: Apakah mengambil konten halaman
            prioritize_trusted: Prioritaskan sumber terpercaya
        
        Returns:
            List hasil pencarian
        """
        # Tambahkan konteks diabetes ke query
        diabetes_query = f"diabetes {query}"
        
        print(f"🔍 Searching: {diabetes_query}")
        
        # Pilih search engine
        if self.search_engine == "duckduckgo":
            results = self.search_duckduckgo(diabetes_query)
        elif self.search_engine == "google":
            results = self.search_google(diabetes_query)
        else:
            results = self.search_duckduckgo(diabetes_query)
        
        # Prioritaskan sumber terpercaya
        if prioritize_trusted:
            trusted = [r for r in results if self.is_trusted_source(r.url)]
            untrusted = [r for r in results if not self.is_trusted_source(r.url)]
            results = trusted + untrusted
        
        # Fetch content jika diminta
        if fetch_content and HAS_BS4:
            print("📄 Fetching page contents...")
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_result = {
                    executor.submit(self.fetch_page_content, r.url): r 
                    for r in results[:self.max_results]
                }
                
                for future in as_completed(future_to_result):
                    result = future_to_result[future]
                    try:
                        content = future.result()
                        result.content = content
                    except Exception as e:
                        print(f"⚠️ Error: {e}")
        
        return results[:self.max_results]
    
    def format_results_for_llm(self, results: List[SearchResult]) -> str:
        """Format hasil pencarian untuk diberikan ke LLM"""
        if not results:
            return "Tidak ditemukan hasil pencarian yang relevan."
        
        formatted = []
        for i, result in enumerate(results, 1):
            entry = f"""
### Sumber {i}: {result.source}
**Judul:** {result.title}
**URL:** {result.url}
**Ringkasan:** {result.snippet}
"""
            if result.content:
                entry += f"**Konten:**\n{result.content[:500]}...\n"
            
            formatted.append(entry)
        
        return "\n".join(formatted)


class DiabetesSearchAgent:
    """Agent untuk mencari informasi diabetes secara cerdas"""
    
    def __init__(self, searcher: WebSearcher = None):
        self.searcher = searcher or WebSearcher()
        
        # Kata kunci yang trigger web search
        self.search_triggers = [
            "terbaru", "berita", "penelitian", "studi",
            "obat baru", "terapi baru", "update",
            "statistik", "data", "prevalensi",
            "rekomendasi", "guideline", "panduan terbaru",
            "perkembangan", "inovasi", "teknologi"
        ]
    
    def should_search(self, query: str) -> bool:
        """Tentukan apakah query memerlukan web search"""
        query_lower = query.lower()
        
        # Cek trigger words
        for trigger in self.search_triggers:
            if trigger in query_lower:
                return True
        
        # Cek pertanyaan tentang hal spesifik/terkini
        if any(word in query_lower for word in ["kapan", "dimana", "siapa", "berapa"]):
            return True
        
        return False
    
    def enhance_query(self, query: str) -> str:
        """Tingkatkan query untuk hasil yang lebih baik"""
        # Hapus kata-kata umum
        stopwords = ["apa", "bagaimana", "mengapa", "apakah", "tolong", "jelaskan"]
        words = query.lower().split()
        enhanced = " ".join([w for w in words if w not in stopwords])
        
        return enhanced
    
    def search_diabetes_info(
        self, 
        query: str,
        force_search: bool = False
    ) -> Dict:
        """
        Cari informasi diabetes dari web
        
        Args:
            query: Pertanyaan user
            force_search: Paksa melakukan search
        
        Returns:
            Dict berisi hasil dan metadata
        """
        should_search = force_search or self.should_search(query)
        
        if not should_search:
            return {
                "searched": False,
                "reason": "Query tidak memerlukan web search",
                "results": [],
                "formatted": ""
            }
        
        # Enhance query
        enhanced_query = self.enhance_query(query)
        
        # Search
        results = self.searcher.search(
            enhanced_query,
            fetch_content=True,
            prioritize_trusted=True
        )
        
        # Format untuk LLM
        formatted = self.searcher.format_results_for_llm(results)
        
        return {
            "searched": True,
            "query": enhanced_query,
            "results": results,
            "formatted": formatted,
            "source_count": len(results)
        }


# Test
if __name__ == "__main__":
    # Test searcher
    searcher = WebSearcher(max_results=3)
    
    # Test search
    print("\n" + "="*50)
    print("Testing Web Search")
    print("="*50)
    
    results = searcher.search(
        "obat diabetes terbaru 2024",
        fetch_content=True
    )
    
    for r in results:
        print(f"\n📌 {r.title}")
        print(f"   🔗 {r.url}")
        print(f"   📝 {r.snippet[:100]}...")
    
    # Test agent
    print("\n" + "="*50)
    print("Testing Search Agent")
    print("="*50)
    
    agent = DiabetesSearchAgent(searcher)
    
    # Query yang trigger search
    result = agent.search_diabetes_info("apa penelitian terbaru tentang diabetes tipe 2?")
    print(f"\nSearched: {result['searched']}")
    print(f"Sources: {result.get('source_count', 0)}")
    
    # Query yang tidak trigger search
    result = agent.search_diabetes_info("apa itu diabetes?")
    print(f"\nSearched: {result['searched']}")
    print(f"Reason: {result.get('reason', 'N/A')}")

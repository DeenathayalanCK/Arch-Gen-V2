#backend\app\domain\detector.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import re
import os

# Safe yaml import
try:
    import yaml
except ImportError:
    yaml = None
    print("[DomainDetector] Warning: PyYAML not installed, custom keywords disabled")


class DetectionMethod(Enum):
    EMBEDDING = "embedding"
    KEYWORD = "keyword"
    LLM = "llm"
    HYBRID = "hybrid"


@dataclass
class DomainDetectionResult:
    primary_domain: str
    confidence: float
    detection_method: DetectionMethod
    sub_domains: List[str] = field(default_factory=list)
    keyword_matches: Dict[str, int] = field(default_factory=dict)
    reasoning: str = ""
    structure_mode: str = "AUTO"


    def to_dict(self) -> dict:
        return {
            "primary_domain": self.primary_domain,
            "confidence": self.confidence,
            "detection_method": self.detection_method.value,
            "sub_domains": self.sub_domains,
            "keyword_matches": self.keyword_matches,
            "reasoning": self.reasoning,
        }


class DomainDetector:
    """
    Detects domain from user requirements using:
    1. Keyword matching (deterministic, fast)
    2. Embedding similarity (if embeddings available)
    3. LLM fallback (if confidence low)
    """

    # Domain keyword mappings - extensible via config
    DOMAIN_KEYWORDS: Dict[str, List[str]] = {
        "healthcare": [
            "patient", "medical", "health", "hospital", "clinical", "diagnosis",
            "hipaa", "ehr", "electronic health record", "pharmacy", "prescription",
            "doctor", "nurse", "treatment", "healthcare", "medicare", "insurance claim",
            "lab results", "vital signs", "appointment", "telehealth", "fhir", "hl7",
        ],
        "fintech": [
            "payment", "transaction", "banking", "financial", "money", "transfer",
            "pci", "pci-dss", "fraud", "kyc", "aml", "wallet", "ledger", "account",
            "credit", "debit", "loan", "mortgage", "trading", "stock", "crypto",
            "blockchain", "settlement", "clearing", "swift", "iban",
        ],
        "ecommerce": [
            "cart", "checkout", "product", "catalog", "order", "inventory",
            "shipping", "fulfillment", "customer", "merchant", "marketplace",
            "wishlist", "review", "rating", "discount", "coupon", "promotion",
            "sku", "warehouse", "return", "refund",
        ],
        "iot": [
            "sensor", "device", "telemetry", "mqtt", "edge", "gateway",
            "firmware", "embedded", "actuator", "connected", "smart device",
            "real-time", "stream", "time-series", "influxdb", "timescale",
        ],
        "saas": [
            "tenant", "multi-tenant", "subscription", "billing", "usage",
            "onboarding", "trial", "plan", "tier", "seat", "license",
            "saas", "b2b", "enterprise", "self-service",
        ],
        "media": [
            "video", "audio", "stream", "content", "cdn", "transcoding",
            "playlist", "channel", "broadcast", "live", "vod", "drm",
            "media", "podcast", "upload", "encoding",
        ],
        "logistics": [
            "shipment", "tracking", "delivery", "fleet", "route", "warehouse",
            "supply chain", "logistics", "freight", "carrier", "dispatch",
            "last mile", "package", "consignment",
        ],
        "education": [
            "course", "student", "teacher", "enrollment", "grade", "assignment",
            "lms", "learning", "curriculum", "quiz", "exam", "certificate",
            "classroom", "lecture", "education", "training",
        ],
        "gaming": [
            "player", "game", "match", "leaderboard", "score", "multiplayer",
            "lobby", "session", "achievement", "inventory", "virtual currency",
            "matchmaking", "real-time", "latency",
        ],
        "generic": [],  # Fallback domain
    }

    # Sub-domain indicators
    SUB_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
        "real_time": ["real-time", "realtime", "live", "stream", "websocket", "push", "instant"],
        "ai_ml": ["ai", "ml", "machine learning", "model", "inference", "training", "prediction"],
        "analytics": ["analytics", "dashboard", "report", "metric", "kpi", "visualization"],
        "compliance": ["compliance", "audit", "regulation", "gdpr", "hipaa", "pci", "sox"],
        "high_availability": ["ha", "high availability", "failover", "disaster recovery", "redundant"],
        "microservices": ["microservice", "service mesh", "k8s", "kubernetes", "container", "docker"],
    }
    STRUCTURE_KEYWORDS = [
        "frontend", "backend", "edge", "identity", "data layer",
        "api gateway", "load balancer", "oauth", "authentication",
        "authorization", "microservice", "database", "cache",
        "request flow", "response", "layer", "tier"
    ]



    CONFIDENCE_THRESHOLD_HIGH = 0.7
    CONFIDENCE_THRESHOLD_LOW = 0.3

    def __init__(self, domains_path: Optional[str] = None):
        self.domains_path = domains_path or self._get_default_domains_path()
        self._load_custom_keywords()

    def _get_default_domains_path(self) -> str:
        return os.path.join(os.path.dirname(__file__), "domains")

    def _load_custom_keywords(self):
        """Load custom domain keywords from domain config files."""
        if yaml is None:
            return
            
        if not os.path.exists(self.domains_path):
            print(f"[DomainDetector] Domains path not found: {self.domains_path}")
            return

        try:
            for domain_name in os.listdir(self.domains_path):
                domain_dir = os.path.join(self.domains_path, domain_name)
                keywords_file = os.path.join(domain_dir, "keywords.yaml")
                
                if os.path.isdir(domain_dir) and os.path.exists(keywords_file):
                    try:
                        with open(keywords_file, "r") as f:
                            config = yaml.safe_load(f)
                            if config and "keywords" in config:
                                existing = self.DOMAIN_KEYWORDS.get(domain_name, [])
                                self.DOMAIN_KEYWORDS[domain_name] = list(set(existing + config["keywords"]))
                                print(f"[DomainDetector] Loaded keywords for domain: {domain_name}")
                    except Exception as e:
                        print(f"[DomainDetector] Error loading keywords for {domain_name}: {e}")
        except Exception as e:
            print(f"[DomainDetector] Error scanning domains directory: {e}")

    def detect(self, requirements: str, use_llm_fallback: bool = True) -> DomainDetectionResult:
        """
        Detect domain from requirements text.
        
        Priority:
        1. Keyword matching (deterministic)
        2. LLM fallback (if low confidence)
        """
        print(f"\n[DomainDetector] Starting detection...")
        
        # Step 1: Keyword-based detection
        keyword_result = self._keyword_detection(requirements)
        print(f"[DomainDetector] Keyword detection: {keyword_result.primary_domain} (conf={keyword_result.confidence:.2f})")
        
        # Step 2: Check confidence threshold
        if keyword_result.confidence >= self.CONFIDENCE_THRESHOLD_HIGH:
            print(f"[DomainDetector] High confidence, using keyword result")
            return keyword_result
        
        # Step 3: LLM fallback if enabled and low confidence
        if use_llm_fallback and keyword_result.confidence < self.CONFIDENCE_THRESHOLD_HIGH:
            print(f"[DomainDetector] Low confidence, attempting LLM fallback...")
            llm_result = self._llm_detection(requirements, keyword_result)
            
            if llm_result and llm_result.confidence > keyword_result.confidence:
                print(f"[DomainDetector] Using LLM result: {llm_result.primary_domain}")
                return llm_result
        
        return keyword_result
    def _detect_structure_mode(self, requirements: str) -> str:
        text = requirements.lower()
        hits = sum(1 for k in self.STRUCTURE_KEYWORDS if k in text)
        return "STRUCTURED" if hits >= 2 else "AUTO"
    
    def _keyword_detection(self, requirements: str) -> DomainDetectionResult:
        """Deterministic keyword-based domain detection."""
        text_lower = requirements.lower()
        scores: Dict[str, int] = {}
        matches: Dict[str, int] = {}
        
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if domain == "generic":
                continue
            
            score = 0
            domain_matches = 0
            for keyword in keywords:
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
                if count > 0:
                    score += count * len(keyword.split())  # Weight multi-word phrases higher
                    domain_matches += count
            
            scores[domain] = score
            matches[domain] = domain_matches
        
        # Detect sub-domains
        sub_domains = []
        for sub_domain, keywords in self.SUB_DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    sub_domains.append(sub_domain)
                    break
        
        # Find best domain
        if not scores or max(scores.values()) == 0:
            return DomainDetectionResult(
                primary_domain="generic",
                confidence=0.5,
                detection_method=DetectionMethod.KEYWORD,
                sub_domains=sub_domains,
                keyword_matches={},
                reasoning="No domain keywords found, using generic domain",
            )
        
        best_domain = max(scores, key=scores.get)
        max_score = scores[best_domain]
        
        # Calculate confidence based on score density
        total_words = len(requirements.split())
        confidence = min(0.95, 0.3 + (max_score / max(total_words * 0.1, 1)) * 0.6)
        
        # Boost confidence if multiple keyword matches
        if matches.get(best_domain, 0) >= 3:
            confidence = min(0.95, confidence + 0.1)
        
        structure_mode = self._detect_structure_mode(requirements)

        return DomainDetectionResult(
            primary_domain=best_domain,
            confidence=confidence,
            detection_method=DetectionMethod.KEYWORD,
            sub_domains=list(set(sub_domains)),
            keyword_matches={k: v for k, v in matches.items() if v > 0},
            reasoning=f"Matched {matches.get(best_domain, 0)} keywords for {best_domain}",
            structure_mode=structure_mode,
        )

    
    
    def _llm_detection(self, requirements: str, keyword_result: DomainDetectionResult) -> Optional[DomainDetectionResult]:
        """LLM-based domain detection fallback."""
        try:
            from app.llm.client import LLMClient
            import json
            
            available_domains = list(self.DOMAIN_KEYWORDS.keys())
            
            prompt = f"""You are a domain classification expert.

Given these software requirements, identify the PRIMARY business domain.

REQUIREMENTS:
{requirements[:2000]}

AVAILABLE DOMAINS:
{', '.join(available_domains)}

Respond ONLY with valid JSON:
{{
    "primary_domain": "domain_name",
    "confidence": 0.0-1.0,
    "sub_domains": ["optional", "sub", "domains"],
    "reasoning": "brief explanation"
}}
"""
            
            llm = LLMClient()
            response = llm.generate(prompt)
            
            # Parse JSON response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                domain = data.get("primary_domain", "generic")
                if domain not in available_domains:
                    domain = "generic"
                
                return DomainDetectionResult(
                    primary_domain=domain,
                    confidence=float(data.get("confidence", 0.6)),
                    detection_method=DetectionMethod.LLM,
                    sub_domains=data.get("sub_domains", []) + keyword_result.sub_domains,
                    keyword_matches=keyword_result.keyword_matches,
                    reasoning=data.get("reasoning", "LLM classification"),
                )
        except Exception as e:
            print(f"[DomainDetector] LLM fallback failed: {e}")
            return None
        
        return None

    def get_available_domains(self) -> List[str]:
        """Return list of available domains."""
        return list(self.DOMAIN_KEYWORDS.keys())

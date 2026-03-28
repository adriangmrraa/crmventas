# SPEC 07: ROI Attribution System + Knowledge Base RAG

**Fecha:** 2026-03-27
**Prioridad:** Alta (revenue intelligence + AI knowledge)
**Esfuerzo:** Alto (2 sprints estimados)
**Confidence:** 85%

---

## Contexto

CRM VENTAS tiene una integracion parcial de Meta Ads: OAuth funciona, los leads se atribuyen via referral de WhatsApp (Click-to-WhatsApp), y existen tablas para campanas e insights (`meta_ads_campaigns`, `meta_ads_insights`, `sales_transactions`). Sin embargo faltan piezas criticas:

1. **El sync de campanas desde Graph API no esta implementado** -- las tablas existen pero no hay job que las llene.
2. **No hay sistema de confianza en la atribucion** -- todo es binario (META_ADS u ORGANIC), sin gradiente.
3. **No hay Knowledge Base** -- el agente AI de ventas responde solo con su prompt, sin acceso a documentos del negocio.
4. **No hay RAG** -- no existe pgvector ni embeddings en el proyecto.

Esta spec cubre dos features independientes que juntas transforman el CRM en una plataforma de inteligencia comercial.

---

## Existing State (What Already Works)

| Component | Status | Location |
|-----------|--------|----------|
| Meta OAuth flow | Working | `Credentials.tsx` + `meta_ads_service.py` |
| Lead attribution (Click-to-WhatsApp) | Working | `db.py` line ~657 (referral handling) |
| `meta_ads_campaigns` table | Created, empty | `patch_009_meta_ads_tables.sql` |
| `meta_ads_insights` table | Created, empty | `patch_009_meta_ads_tables.sql` |
| `sales_transactions` table | Created, partial use | `patch_009_meta_ads_tables.sql` |
| `opportunities` table | Created, partial use | `patch_009_meta_ads_tables.sql` |
| `leads.lead_source` column | Working | `patch_009` + `patch_011` |
| `leads.meta_campaign_id/meta_ad_id` | Working | `patch_009` + `patch_011` |
| `calculate_campaign_roi()` SQL function | Created, unused | `patch_009_meta_ads_tables.sql` |
| `MetaAdsClient` class | Partial (get_ad_details only) | `services/marketing/meta_ads_service.py` |
| `MarketingHubView.tsx` | Exists, basic | `frontend_react/src/views/marketing/` |
| Knowledge Base / RAG | Does not exist | -- |

---

# FEATURE A: ROI Attribution System

## A.1 Overview

Complete the attribution pipeline so every lead has a confidence-scored source, every campaign shows real ROI, and the Marketing Hub displays actionable spend-vs-revenue data.

## A.2 Attribution Model

### A.2.1 Multi-Channel Attribution Methods

| Method | Trigger | Confidence | Details |
|--------|---------|------------|---------|
| **Direct Meta Lead Form** | Webhook `leadgen` event with `lead_id` | 1.0 | Lead comes from a Meta form; exact match on `lead_id` |
| **Click-to-WhatsApp Referral** | `referral` object in YCloud webhook | 1.0 | Exact ad_id + campaign_id from Meta |
| **UTM Parameter Match** | `?utm_source=meta&utm_campaign=X` on landing | 0.9 | Lead enters via tracked URL; campaign matched by UTM |
| **Phone Number Match** | Lead phone matches a Meta Lead Form phone | 0.8 | Same phone from different channel; likely same person |
| **Time-Window Proximity** | Lead created within 24h of ad click (same tenant) | 0.5 | No direct link but temporal correlation |
| **Manual Override** | Seller manually assigns attribution | 1.0 | Human decision; stored as `method = 'manual'` |

### A.2.2 Attribution Policy

- **First-touch persistent**: The first attributed campaign is permanent and owns the lead.
- **Confidence upgrade only**: If a higher-confidence attribution arrives later (e.g., phone match 0.8 upgraded to direct form 1.0), the record updates.
- **Never downgrade**: A confidence of 1.0 is never replaced by 0.5.

## A.3 Data Model

### A.3.1 New Table: `attributed_sales`

```sql
CREATE TABLE attributed_sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,

    -- Source entities
    lead_id UUID REFERENCES leads(id) NOT NULL,
    opportunity_id UUID REFERENCES opportunities(id),
    transaction_id UUID REFERENCES sales_transactions(id),

    -- Attribution target
    campaign_id UUID REFERENCES meta_ads_campaigns(id),
    meta_campaign_id VARCHAR(255),
    meta_ad_id VARCHAR(255),
    meta_adset_id VARCHAR(255),

    -- Attribution metadata
    channel VARCHAR(50) NOT NULL,           -- 'meta_ads', 'google_ads', 'organic', 'referral', 'direct', 'whatsapp'
    method VARCHAR(50) NOT NULL,            -- 'lead_form', 'referral_click', 'utm', 'phone_match', 'time_window', 'manual'
    confidence DECIMAL(3,2) NOT NULL,       -- 0.00 to 1.00
    attribution_date TIMESTAMP NOT NULL,    -- When the attribution was established

    -- Revenue
    revenue_attributed DECIMAL(12,2) DEFAULT 0,
    currency TEXT DEFAULT 'USD',

    -- UTM data (if applicable)
    utm_source VARCHAR(255),
    utm_medium VARCHAR(255),
    utm_campaign VARCHAR(255),
    utm_content VARCHAR(255),
    utm_term VARCHAR(255),

    -- Audit
    attributed_by VARCHAR(50) DEFAULT 'system', -- 'system' or user_id for manual
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_attribution_per_lead UNIQUE (tenant_id, lead_id)
);

CREATE INDEX idx_attributed_sales_tenant ON attributed_sales(tenant_id);
CREATE INDEX idx_attributed_sales_campaign ON attributed_sales(tenant_id, meta_campaign_id);
CREATE INDEX idx_attributed_sales_channel ON attributed_sales(tenant_id, channel);
CREATE INDEX idx_attributed_sales_confidence ON attributed_sales(tenant_id, confidence);
CREATE INDEX idx_attributed_sales_date ON attributed_sales(tenant_id, attribution_date);
```

### A.3.2 New Table: `utm_tracking_events`

```sql
CREATE TABLE utm_tracking_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,

    -- Session data
    session_id VARCHAR(255),
    visitor_ip VARCHAR(45),
    user_agent TEXT,
    landing_url TEXT,

    -- UTM fields
    utm_source VARCHAR(255),
    utm_medium VARCHAR(255),
    utm_campaign VARCHAR(255),
    utm_content VARCHAR(255),
    utm_term VARCHAR(255),

    -- Resolution
    lead_id UUID REFERENCES leads(id),       -- NULL until matched
    matched_at TIMESTAMP,
    match_method VARCHAR(50),                 -- 'form_submit', 'phone_match', 'cookie'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_utm_events_tenant ON utm_tracking_events(tenant_id);
CREATE INDEX idx_utm_events_session ON utm_tracking_events(session_id);
CREATE INDEX idx_utm_events_unmatched ON utm_tracking_events(tenant_id, lead_id) WHERE lead_id IS NULL;
```

### A.3.3 Modifications to Existing Tables

**`leads` table** -- add columns:
```sql
ALTER TABLE leads ADD COLUMN IF NOT EXISTS attribution_confidence DECIMAL(3,2);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS attribution_method VARCHAR(50);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS utm_source VARCHAR(255);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS utm_medium VARCHAR(255);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS utm_campaign VARCHAR(255);
```

## A.4 Campaign Sync (Complete the Meta Integration)

### A.4.1 Service: `MetaAdsClient` Extensions

Add to `services/marketing/meta_ads_service.py`:

```python
async def sync_campaigns(self, account_id: str) -> List[Dict]:
    """Fetch all campaigns from Meta Graph API and upsert into meta_ads_campaigns."""

async def sync_insights(self, campaign_id: str, date_start: str, date_end: str) -> List[Dict]:
    """Fetch daily insights for a campaign and upsert into meta_ads_insights."""

async def get_campaign_performance(self, account_id: str, date_preset: str = "last_30d") -> Dict:
    """Aggregate performance: spend, impressions, clicks, CPL, CPA, ROI."""
```

### A.4.2 Background Job: `jobs/attribution_enrichment.py`

Runs every 12 hours:

1. **Sync campaigns**: Call `sync_campaigns()` for each tenant with active Meta OAuth.
2. **Sync insights**: Fetch last 7 days of daily insights per campaign.
3. **Resolve attributions**: Scan `leads` created in last 48h without attribution, attempt matching via:
   - Phone number match against Meta Lead Form responses.
   - UTM event match from `utm_tracking_events`.
   - Time-window proximity (lead created within 24h of a campaign with clicks).
4. **Calculate revenue**: For attributed leads with `closed_won` opportunities, update `revenue_attributed`.
5. **Update campaign aggregates**: Recalculate `spend`, `leads`, `opportunities`, `revenue`, `roi_percentage` on `meta_ads_campaigns`.

### A.4.3 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/marketing/campaigns` | List campaigns with performance metrics |
| GET | `/admin/marketing/campaigns/{id}/insights` | Daily insights for a campaign |
| POST | `/admin/marketing/campaigns/sync` | Trigger manual campaign sync |
| GET | `/admin/marketing/attribution` | Attribution report (filters: date range, channel, confidence threshold) |
| GET | `/admin/marketing/roi` | ROI summary: spend vs revenue, CPA, CPL per campaign |
| PUT | `/admin/marketing/attribution/{lead_id}` | Manual attribution override |
| POST | `/admin/utm/track` | Record a UTM landing event (called from frontend/landing pages) |

### A.4.4 Frontend: Marketing Hub Enhancement

Modify `frontend_react/src/views/marketing/MarketingHubView.tsx`:

**Tab 1: Campaigns**
- Campaign cards (GlassCard) showing: name, status, spend, leads, CPL, ROI
- Spend vs Revenue sparkline chart per campaign
- Last synced timestamp + manual sync button

**Tab 2: Attribution**
- Table of recent attributions: lead name, channel, method, confidence (color-coded badge), campaign, revenue
- Confidence filter slider (0.0 to 1.0)
- Channel pie chart

**Tab 3: ROI Dashboard**
- Total spend vs total revenue (big numbers + trend arrow)
- ROI per campaign bar chart
- CPA and CPL trends over time (Recharts line)
- Top 5 campaigns by ROI table

## A.5 Acceptance Criteria

```gherkin
Scenario: Click-to-WhatsApp lead gets automatic attribution with confidence 1.0
  Given a tenant has Meta OAuth connected with ad account "act_123"
  And a campaign "Summer Sale" is synced in meta_ads_campaigns
  When a new WhatsApp message arrives with referral object containing ad_id "456" and campaign_id "789"
  Then the lead is created with lead_source = "META_ADS"
  And an attributed_sales record is created with confidence = 1.0 and method = "referral_click"
  And the campaign's leads count increments by 1

Scenario: Campaign sync populates meta_ads_campaigns from Graph API
  Given a tenant has valid Meta OAuth credentials with ad_account_id "act_123"
  When the attribution_enrichment job runs
  Then all active campaigns from Meta account "act_123" are upserted into meta_ads_campaigns
  And daily insights for the last 7 days are stored in meta_ads_insights
  And each campaign row has updated spend, impressions, clicks values

Scenario: ROI dashboard shows accurate spend-to-revenue ratio
  Given campaign "Q1 Push" has $500 total spend in meta_ads_insights
  And 3 leads attributed to "Q1 Push" with confidence >= 0.8
  And 1 of those leads has a closed_won opportunity worth $2000
  When I open the Marketing Hub ROI tab
  Then "Q1 Push" shows spend = $500, revenue = $2000, ROI = 300%
  And CPL = $166.67 and CPA = $500.00
```

---

# FEATURE B: Knowledge Base with RAG

## B.1 Overview

Allow tenants to upload documents that the AI sales agent can query via semantic search. The agent retrieves relevant context from the knowledge base before responding to leads, ensuring accurate product/pricing/competitive information.

## B.2 Architecture

```
Upload (PDF/DOCX/TXT)  -->  Chunking  -->  Embedding (OpenAI)  -->  pgvector storage
                                                                         |
Lead asks question  -->  Query embedding  -->  Cosine similarity  -->  Top-K chunks
                                                                         |
                                                              Injected into agent context
```

## B.3 Data Model

### B.3.1 Enable pgvector Extension

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### B.3.2 New Table: `kb_collections`

```sql
CREATE TABLE kb_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,

    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL,          -- 'product_info', 'pricing', 'sales_scripts', 'faqs', 'competitor_intel'
    description TEXT,
    icon VARCHAR(50) DEFAULT 'folder',   -- Lucide icon name
    color VARCHAR(20) DEFAULT 'blue',

    -- Stats (denormalized for UI speed)
    document_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    last_indexed_at TIMESTAMP,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_collection_slug UNIQUE (tenant_id, slug)
);

CREATE INDEX idx_kb_collections_tenant ON kb_collections(tenant_id);
```

### B.3.3 New Table: `kb_documents`

```sql
CREATE TABLE kb_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    collection_id UUID REFERENCES kb_collections(id) ON DELETE CASCADE NOT NULL,

    -- Document metadata
    title VARCHAR(500) NOT NULL,
    file_name VARCHAR(500),
    file_type VARCHAR(20),               -- 'pdf', 'docx', 'txt', 'manual'
    file_size_bytes INTEGER,
    file_url TEXT,                        -- S3/storage URL (if applicable)

    -- Content
    raw_text TEXT,                        -- Full extracted text
    chunk_count INTEGER DEFAULT 0,

    -- Processing status
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'indexed', 'error'
    error_message TEXT,
    indexed_at TIMESTAMP,

    -- Source tracking
    source VARCHAR(50) DEFAULT 'upload',  -- 'upload', 'shadow_rag', 'manual_entry'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_kb_documents_tenant ON kb_documents(tenant_id);
CREATE INDEX idx_kb_documents_collection ON kb_documents(collection_id);
CREATE INDEX idx_kb_documents_status ON kb_documents(tenant_id, status);
```

### B.3.4 New Table: `kb_chunks`

```sql
CREATE TABLE kb_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    document_id UUID REFERENCES kb_documents(id) ON DELETE CASCADE NOT NULL,
    collection_id UUID REFERENCES kb_collections(id) ON DELETE CASCADE NOT NULL,

    -- Chunk content
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,          -- Position within document
    token_count INTEGER,

    -- Embedding
    embedding vector(1536) NOT NULL,       -- text-embedding-3-small output dimension

    -- Metadata for filtering
    metadata JSONB DEFAULT '{}',           -- {page: 3, section: "Pricing", heading: "Enterprise Plan"}

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_kb_chunks_tenant ON kb_chunks(tenant_id);
CREATE INDEX idx_kb_chunks_document ON kb_chunks(document_id);
CREATE INDEX idx_kb_chunks_collection ON kb_chunks(collection_id);

-- HNSW index for fast approximate nearest-neighbor search
CREATE INDEX idx_kb_chunks_embedding ON kb_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

### B.3.5 New Table: `kb_query_log`

```sql
CREATE TABLE kb_query_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,

    -- Query details
    query_text TEXT NOT NULL,
    query_embedding vector(1536),
    source VARCHAR(50) NOT NULL,          -- 'ai_agent', 'search_preview', 'shadow_rag'

    -- Results
    chunks_returned INTEGER,
    top_score DECIMAL(5,4),               -- Best cosine similarity score
    response_used BOOLEAN DEFAULT FALSE,  -- Did the agent actually use the result?

    -- Context
    lead_id UUID REFERENCES leads(id),
    conversation_id VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_kb_query_log_tenant ON kb_query_log(tenant_id);
CREATE INDEX idx_kb_query_log_created ON kb_query_log(tenant_id, created_at);
```

## B.4 Backend Services

### B.4.1 `services/knowledge_base/embedding_service.py`

```python
class EmbeddingService:
    MODEL = "text-embedding-3-small"     # 1536 dimensions, $0.02/1M tokens
    MAX_TOKENS_PER_CHUNK = 512
    CHUNK_OVERLAP = 50                    # tokens

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text."""

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embed up to 2048 texts in one API call."""

    def chunk_text(self, text: str, max_tokens: int = 512, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks using tiktoken."""
```

### B.4.2 `services/knowledge_base/document_processor.py`

```python
class DocumentProcessor:
    async def process_pdf(self, file_bytes: bytes) -> str:
        """Extract text from PDF using PyPDF2 or pdfplumber."""

    async def process_docx(self, file_bytes: bytes) -> str:
        """Extract text from DOCX using python-docx."""

    async def process_txt(self, file_bytes: bytes, encoding: str = "utf-8") -> str:
        """Read plain text with encoding fallback (utf-8 -> latin-1)."""

    async def ingest_document(self, tenant_id: int, collection_id: str, file_bytes: bytes,
                               file_name: str, file_type: str) -> Dict:
        """Full pipeline: extract text -> chunk -> embed -> store in pgvector."""
```

### B.4.3 `services/knowledge_base/rag_service.py`

```python
class RAGService:
    TOP_K = 5
    MIN_SIMILARITY = 0.7

    async def query(self, tenant_id: int, query_text: str,
                    collection_slugs: Optional[List[str]] = None,
                    top_k: int = 5, min_similarity: float = 0.7) -> List[Dict]:
        """
        Semantic search across tenant's knowledge base.
        Returns top_k chunks ranked by cosine similarity, filtered by min_similarity.
        Optionally scoped to specific collections.
        """

    async def build_context(self, tenant_id: int, query_text: str) -> str:
        """
        Query RAG and format results as a context block for the AI agent prompt.
        Returns empty string if no relevant results found.
        """

    async def log_query(self, tenant_id: int, query_text: str, chunks_returned: int,
                         top_score: float, source: str, lead_id: Optional[str] = None):
        """Log query for analytics and improvement."""
```

### B.4.4 Shadow RAG: `services/knowledge_base/shadow_indexer.py`

```python
class ShadowIndexer:
    """
    Automatically indexes successful conversation patterns.
    Triggered when:
    - A conversation leads to a closed_won opportunity
    - A seller marks a conversation as "exemplary"
    - A lead gives positive feedback after AI interaction
    """

    async def index_conversation(self, tenant_id: int, conversation_id: str,
                                  reason: str = "closed_won"):
        """
        Extract Q&A pairs from a conversation, embed them,
        and store in the 'shadow_rag' collection.
        """

    async def run_batch(self, tenant_id: int, days_back: int = 7):
        """
        Scan recent closed_won opportunities and index their conversations.
        Called by background job.
        """
```

### B.4.5 AI Agent Integration

Modify `orchestrator_service/main.py` (the LangChain agent):

1. Before generating a response to a lead message, call `RAGService.build_context()`.
2. If context is returned (similarity >= 0.7), inject it into the system prompt as:
   ```
   --- KNOWLEDGE BASE CONTEXT ---
   {context}
   --- END CONTEXT ---
   Use the above information to answer the lead's question accurately.
   ```
3. If no context found, the agent responds normally (no degradation).

### B.4.6 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/kb/collections` | List all collections with stats |
| POST | `/admin/kb/collections` | Create a new collection |
| PUT | `/admin/kb/collections/{id}` | Update collection name/description |
| DELETE | `/admin/kb/collections/{id}` | Delete collection and all its documents/chunks |
| GET | `/admin/kb/collections/{id}/documents` | List documents in a collection |
| POST | `/admin/kb/documents/upload` | Upload a document (multipart/form-data) |
| POST | `/admin/kb/documents/manual` | Create a document from text input |
| DELETE | `/admin/kb/documents/{id}` | Delete a document and its chunks |
| POST | `/admin/kb/search` | Search preview: query + collection filter, returns chunks with scores |
| GET | `/admin/kb/stats` | Usage stats: total docs, chunks, queries, avg similarity |
| GET | `/admin/kb/query-log` | Recent queries with scores and usage flags |

## B.5 Frontend: Knowledge Management Page

### B.5.1 New View: `KnowledgeBaseView.tsx`

**Location:** `frontend_react/src/views/KnowledgeBaseView.tsx`

**Layout:**

```
+--------------------------------------------------+
| Knowledge Base                    [+ Collection]  |
+--------------------------------------------------+
| Collection sidebar    |  Document list            |
| +-----------------+   | +----------------------+  |
| | Product Info (5) |  | | pricing-2026.pdf     |  |
| | Pricing      (3) |  | | Status: Indexed      |  |
| | Sales Scripts(8) |  | | Chunks: 24           |  |
| | FAQs         (12)|  | | Uploaded: 2 days ago |  |
| | Competitor   (2) |  | +----------------------+  |
| +-----------------+   | | competitor-brief.docx|  |
|                        | | Status: Processing   |  |
|                        | +----------------------+  |
|                        |                           |
| Search Preview         | [Upload] [+ Manual Entry] |
| +--------------------+ |                           |
| | Query: ________    | |                           |
| | Results:           | |                           |
| | 0.94 - "Our Pro.."| |                           |
| | 0.87 - "The ent.."| |                           |
| +--------------------+ |                           |
+--------------------------------------------------+
```

**Components:**
- Collection sidebar with counts and active/inactive toggle
- Document list with status badges (pending/processing/indexed/error)
- Drag & drop upload zone (max 10MB per file)
- Manual text entry modal for quick knowledge additions
- Search preview panel: type a query, see ranked results with similarity scores
- Query log table (last 50 queries, expandable)

### B.5.2 i18n Keys

Add to `es.json`, `en.json`, `fr.json`:
```json
{
  "kb.title": "Base de Conocimiento",
  "kb.collections": "Colecciones",
  "kb.newCollection": "Nueva Coleccion",
  "kb.upload": "Subir Documento",
  "kb.manualEntry": "Entrada Manual",
  "kb.searchPreview": "Vista Previa de Busqueda",
  "kb.status.pending": "Pendiente",
  "kb.status.processing": "Procesando",
  "kb.status.indexed": "Indexado",
  "kb.status.error": "Error",
  "kb.similarity": "Similitud",
  "kb.chunks": "Fragmentos",
  "kb.queryLog": "Historial de Consultas",
  "kb.shadowRag": "Patrones Automaticos",
  "kb.dragDrop": "Arrastra archivos aqui o haz clic para seleccionar",
  "kb.maxSize": "Maximo 10MB por archivo (PDF, DOCX, TXT)",
  "marketing.campaigns": "Campanas",
  "marketing.attribution": "Atribucion",
  "marketing.roi": "ROI",
  "marketing.confidence": "Confianza",
  "marketing.spend": "Gasto",
  "marketing.revenue": "Ingresos",
  "marketing.syncNow": "Sincronizar Ahora",
  "marketing.lastSynced": "Ultima sincronizacion",
  "marketing.cpa": "Costo por Adquisicion",
  "marketing.cpl": "Costo por Lead"
}
```

## B.6 Acceptance Criteria

```gherkin
Scenario: Upload a PDF and query it via RAG
  Given I am on the Knowledge Base page with collection "Product Info"
  When I upload a PDF file "catalog-2026.pdf" (2MB)
  Then the document status shows "Processing" immediately
  And within 30 seconds the status changes to "Indexed"
  And the chunk count shows a number greater than 0
  When I type "What is the price of the enterprise plan?" in the search preview
  Then at least 1 result appears with similarity >= 0.7
  And the result text contains pricing information from the uploaded PDF

Scenario: AI agent uses Knowledge Base context to answer lead question
  Given tenant has a Knowledge Base with collection "Pricing" containing a document about plan prices
  And a lead sends a WhatsApp message asking "How much does the premium plan cost?"
  When the AI agent processes the message
  Then the RAG service is queried with the lead's question
  And the agent's response includes specific pricing from the Knowledge Base
  And a kb_query_log entry is created with response_used = TRUE

Scenario: Shadow RAG indexes a successful sales conversation
  Given a lead had a 10-message conversation with the AI agent
  And the lead's opportunity is moved to "closed_won"
  When the shadow indexer batch job runs
  Then the conversation is chunked into Q&A pairs
  And each pair is embedded and stored in the "shadow_rag" collection
  And the collection's document_count and chunk_count are incremented
```

---

## Database Migrations

All migrations use raw SQL files in `orchestrator_service/migrations/` following the existing pattern.

| Migration | Content |
|-----------|---------|
| `patch_019_attributed_sales.sql` | Create `attributed_sales` + `utm_tracking_events` tables; add `attribution_confidence`, `attribution_method`, `utm_source`, `utm_medium`, `utm_campaign` columns to `leads` |
| `patch_020_pgvector_knowledge_base.sql` | Enable `vector` extension; create `kb_collections`, `kb_documents`, `kb_chunks` (with HNSW index), `kb_query_log` tables |

**Note:** `patch_019` follows after the last existing migration (`patch_018_lead_status_system.sql`). Verify no gap before running.

---

## Files to Create

| File | Purpose |
|------|---------|
| `orchestrator_service/migrations/patch_019_attributed_sales.sql` | Attribution tables migration |
| `orchestrator_service/migrations/patch_020_pgvector_knowledge_base.sql` | Knowledge Base tables migration |
| `orchestrator_service/services/attribution_service.py` | Attribution engine: match, score, resolve |
| `orchestrator_service/jobs/attribution_enrichment.py` | 12h background job: sync campaigns, resolve attributions, calculate ROI |
| `orchestrator_service/services/knowledge_base/__init__.py` | Package init |
| `orchestrator_service/services/knowledge_base/embedding_service.py` | OpenAI embedding generation + text chunking |
| `orchestrator_service/services/knowledge_base/document_processor.py` | PDF/DOCX/TXT extraction + ingestion pipeline |
| `orchestrator_service/services/knowledge_base/rag_service.py` | Semantic search + context building for AI agent |
| `orchestrator_service/services/knowledge_base/shadow_indexer.py` | Auto-index successful conversations |
| `orchestrator_service/routes/kb_routes.py` | REST endpoints for Knowledge Base CRUD + search |
| `orchestrator_service/routes/attribution_routes.py` | REST endpoints for attribution reports + manual override |
| `frontend_react/src/views/KnowledgeBaseView.tsx` | Knowledge management page |

## Files to Modify

| File | Changes |
|------|---------|
| `orchestrator_service/services/marketing/meta_ads_service.py` | Add `sync_campaigns()`, `sync_insights()`, `get_campaign_performance()` methods |
| `orchestrator_service/main.py` | Register new routes (`kb_routes`, `attribution_routes`); inject RAG context into AI agent prompt before response generation |
| `orchestrator_service/db.py` | Update `create_or_update_lead()` to call attribution service after lead creation; add UTM parameter handling |
| `orchestrator_service/requirements.txt` | Add `pgvector`, `tiktoken`, `PyPDF2` (or `pdfplumber`), `python-docx` |
| `frontend_react/src/views/marketing/MarketingHubView.tsx` | Add Campaigns, Attribution, ROI tabs with charts |
| `frontend_react/src/App.tsx` | Add route for `/knowledge-base` |
| `frontend_react/src/components/Layout.tsx` | Add "Knowledge Base" sidebar item with `BookOpen` Lucide icon |
| `frontend_react/src/locales/es.json` | Add `kb.*` and `marketing.*` i18n keys |
| `frontend_react/src/locales/en.json` | Add `kb.*` and `marketing.*` i18n keys |
| `frontend_react/src/locales/fr.json` | Add `kb.*` and `marketing.*` i18n keys |
| `docker-compose.yml` | Ensure PostgreSQL image supports pgvector (use `pgvector/pgvector:pg15-v0.7.0` or add extension to init script) |

---

## Integration with Existing Meta OAuth Flow

The current OAuth flow (`Credentials.tsx` + `meta_ads_service.py`) stores:
- `access_token` (long-lived page token)
- `ad_account_id`
- `page_id`

The attribution system plugs in as follows:

1. **On OAuth success**: Trigger an initial `sync_campaigns()` call to populate `meta_ads_campaigns` immediately.
2. **On lead creation with referral**: The existing `db.py` logic (line ~657) already sets `lead_source = META_ADS`. Add a call to `AttributionService.attribute()` to also create the `attributed_sales` record with `confidence = 1.0`.
3. **On webhook `/webhooks/meta` (Lead Form)**: After creating the lead, call `AttributionService.attribute()` with `method = 'lead_form'`, `confidence = 1.0`.
4. **Background job**: Uses the stored OAuth token to call Graph API for campaign and insight sync. Token refresh is handled by the existing `MetaAdsClient` constructor.

---

## Risks and Mitigations

### Meta Graph API Rate Limits
- **Risk:** Meta imposes rate limits per app and per ad account. Heavy sync jobs could hit limits.
- **Mitigation:** Implement exponential backoff with jitter. Cache responses in Redis (48h TTL, matching ClinicForge pattern). Sync only last 7 days of insights per run. Use batch requests where possible (`?ids=campaign1,campaign2`).

### OpenAI Embedding Costs
- **Risk:** `text-embedding-3-small` costs $0.02 per 1M tokens. A 100-page PDF could produce ~200 chunks x 512 tokens = ~100K tokens ($0.002). Tenants uploading many documents could accumulate costs.
- **Mitigation:** Track token usage per tenant in `system_config` or a dedicated counter. Set a configurable monthly embedding budget per tenant (default: 5M tokens / $0.10). Warn in UI when approaching limit. Cache embeddings -- never re-embed unchanged content.

### pgvector Performance at Scale
- **Risk:** HNSW index performance degrades above ~1M vectors. For most tenants this is not a concern (typical: <10K chunks).
- **Mitigation:** Use HNSW with `m=16, ef_construction=64` for good recall/speed tradeoff. Partition by `tenant_id` in queries (always filtered). Monitor query latency in `kb_query_log`.

### Document Processing Failures
- **Risk:** Malformed PDFs, password-protected files, or encoding issues could fail silently.
- **Mitigation:** Status field on `kb_documents` tracks processing state. Errors are stored in `error_message`. Frontend shows clear error states. Support encoding fallback (UTF-8 -> latin-1, matching existing CSV import pattern).

### Shadow RAG Quality
- **Risk:** Not all closed_won conversations contain reusable patterns. Low-quality conversations could pollute the knowledge base.
- **Mitigation:** Only index conversations with >= 6 messages. Allow manual review/deletion of shadow RAG documents. Separate collection (`shadow_rag`) so it can be toggled off per tenant.

### Multi-Tenant Data Isolation
- **Risk:** RAG queries could leak data across tenants if `tenant_id` filter is missing.
- **Mitigation:** Every query in `rag_service.py` and `attribution_service.py` MUST include `WHERE tenant_id = $x`. The `tenant_id` comes from JWT (via `Depends(verify_admin_token)`), never from request parameters. Add integration test that verifies tenant isolation.

### Token Expiration
- **Risk:** Meta long-lived tokens expire after 60 days. If not refreshed, campaign sync silently fails.
- **Mitigation:** Track `token_expires_at` in credentials. Background job checks token validity before sync. If expired, emit Socket.IO event `META_TOKEN_EXPIRED` to prompt re-authentication in the UI.

---

## Implementation Order

| Phase | Scope | Effort |
|-------|-------|--------|
| **Phase 1** | Migration `patch_019` + `AttributionService` + extend `MetaAdsClient.sync_campaigns()` + background job skeleton | 3 days |
| **Phase 2** | Campaign sync integration + ROI calculation + Marketing Hub tabs (Campaigns + ROI) | 3 days |
| **Phase 3** | Migration `patch_020` + pgvector setup + `EmbeddingService` + `DocumentProcessor` + `RAGService` | 4 days |
| **Phase 4** | `KnowledgeBaseView.tsx` + upload flow + search preview | 3 days |
| **Phase 5** | AI agent RAG integration + Shadow RAG indexer + Attribution tab in Marketing Hub | 3 days |
| **Phase 6** | Testing, edge cases, token budget enforcement, tenant isolation tests | 2 days |

**Total estimated effort: 18 days (2 sprints)**

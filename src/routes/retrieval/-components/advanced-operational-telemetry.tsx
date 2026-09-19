import { BM25DenseRatioCard } from './telemetry/bm25-dense-ratio-card'
import { RARGAbstentionCard } from './telemetry/rarg-abstention-card'
import { KnowledgeHealthRadarCard } from './telemetry/knowledge-health-radar-card'

/**
 * Advanced Operational Telemetry (Card-Retrieval-AdvancedCards / v1.5.45)
 * Second row of Retrieval Dashboard presenting:
 * 1. BM25 Lexical vs Dense Vector Hit Ratio & Overlap Distribution.
 * 2. RARG Grounding Abstention Rate & Confidence Tiers.
 * 3. 3D Knowledge Base Health Radar & Hygiene Metrics.
 */
export function AdvancedOperationalTelemetry() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 select-none">
      <BM25DenseRatioCard />
      <RARGAbstentionCard />
      <KnowledgeHealthRadarCard />
    </div>
  )
}

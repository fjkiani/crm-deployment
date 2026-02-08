"""
PGx Validation Agent - Example domain agent using Research Framework

This demonstrates how to create a domain-specific agent that leverages
the Research Framework for intelligent research.
"""
from typing import Dict, Any, List
from ..orchestrator import ResearchOrchestrator
from ..models import ResearchResult
from .base_agent import BaseDomainAgent


class PGxValidationAgent(BaseDomainAgent):
    """
    Agent specialized in pharmacogenomics validation
    
    Uses Research Framework to validate PGx claims by searching literature
    and clinical trials, then interpreting results in PGx context.
    """
    
    def _get_domain_name(self) -> str:
        return "pgx"
    
    async def validate_claim(
        self,
        claim: str,
        genes: Optional[List[str]] = None,
        drugs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate a PGx claim using intelligent research
        
        Args:
            claim: PGx claim to validate (e.g., "DPYD testing prevents 95% of toxicity")
            genes: Optional list of genes to focus on
            drugs: Optional list of drugs to focus on
        
        Returns:
            Validation result with evidence, confidence, sources
        """
        # Build PGx-specific queries
        queries = self._build_pgx_queries(claim, genes, drugs)
        
        # Use framework for intelligent search
        results = await self.framework.multi_source_search(
            queries=queries,
            sources=['pubmed', 'clinical_trials'],
            synthesis=True
        )
        
        # Interpret results in PGx context
        validation = self._interpret_pgx_results(results, claim)
        
        return validation
    
    def _build_pgx_queries(
        self,
        claim: str,
        genes: Optional[List[str]],
        drugs: Optional[List[str]]
    ) -> List[str]:
        """Build PGx-optimized queries from claim"""
        queries = []
        
        # Base query from claim
        queries.append(claim)
        
        # Add gene-specific queries if provided
        if genes:
            for gene in genes:
                queries.append(f"{gene} pharmacogenomics {claim}")
        
        # Add drug-specific queries if provided
        if drugs:
            for drug in drugs:
                queries.append(f"{drug} pharmacogenomics {claim}")
        
        # Add combination queries
        if genes and drugs:
            for gene in genes:
                for drug in drugs:
                    queries.append(f"{gene} {drug} pharmacogenomics")
        
        return queries
    
    def _interpret_pgx_results(
        self,
        results: 'MultiSourceResult',
        original_claim: str
    ) -> Dict[str, Any]:
        """Interpret research results in PGx validation context"""
        # Extract evidence from results
        evidence = []
        for result in results.results:
            pubmed_result = result.get_source_result('pubmed')
            clinical_result = result.get_source_result('clinical_trials')
            
            if pubmed_result:
                evidence.append({
                    'source': 'pubmed',
                    'count': len(pubmed_result.results),
                    'summary': pubmed_result.summary
                })
            
            if clinical_result:
                evidence.append({
                    'source': 'clinical_trials',
                    'count': len(clinical_result.results),
                    'summary': clinical_result.summary
                })
        
        # Simple validation logic (in production, use LLM for interpretation)
        total_evidence = sum(e['count'] for e in evidence)
        confidence = min(1.0, total_evidence / 10.0)  # Simple heuristic
        
        return {
            'claim': original_claim,
            'validated': total_evidence > 0,
            'confidence': confidence,
            'evidence_count': total_evidence,
            'evidence': evidence,
            'sources': results.results,
            'domain': 'pgx'
        }
    
    async def search_prevention_rates(
        self,
        gene: str,
        drug: str
    ) -> Dict[str, Any]:
        """
        Search for prevention rates for specific gene-drug combination
        
        Args:
            gene: Gene name (e.g., "DPYD")
            drug: Drug name (e.g., "fluorouracil")
        
        Returns:
            Prevention rate data with sources
        """
        query = f"{gene} {drug} toxicity prevention rate sensitivity specificity"
        
        result = await self.framework.search(
            query=query,
            sources=['pubmed', 'clinical_trials'],
            synthesize=True,
            extract_structured={
                'prevention_rate': 'extract percentage of toxicity prevented',
                'sensitivity': 'extract sensitivity percentage',
                'specificity': 'extract specificity percentage',
                'sample_size': 'extract number of patients',
                'study_type': 'extract study type (randomized, observational, etc.)'
            }
        )
        
        return {
            'gene': gene,
            'drug': drug,
            'research_result': result,
            'structured_data': result.structured_data.data if result.structured_data else None
        }


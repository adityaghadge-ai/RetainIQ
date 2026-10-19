"""
retainiq_03_rag.py
==================
PHASE 20 – Optional RAG / Literature Retrieval Layer

Reads research PDFs from RetainIQ/kb/,
extracts text via pypdf,
builds a TF-IDF index (unigrams + bigrams),
and retrieves top-2 relevant passages for each high-priority employee.

IMPORTANT DESIGN CONSTRAINTS
-----------------------------
- RAG is NOT used for model training.
- The IBM dataset contains EMPLOYEE RECORDS, not policy documents.
- RAG only provides LITERATURE CONTEXT for model-associated factors.
- All retrieved passages carry an explicit standing disclaimer.
- This system does NOT generate unsupported claims.
- This system does NOT invent citations.

PREREQUISITES
-------------
retainiq_01_baseline.py  AND  retainiq_02_priority.py must have been run first.
Required:
  outputs/employee_explanations.csv

Optional:
  kb/*.pdf   (research PDFs; gracefully handles empty kb/ directory)

Run:
    python retainiq_03_rag.py
"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import retainiq_common as rc

# ============================================================================
# CONSTANTS
# ============================================================================
STANDING_DISCLAIMER = (
    "LITERATURE CONTEXT ONLY. This passage is retrieved from academic "
    "literature and provided as background context. It does NOT establish "
    "that this factor caused this specific employee's attrition, nor does "
    "it imply that any particular intervention will retain them. "
    "RetainIQ is a benchmark research prototype on a synthetic dataset "
    "and must NOT be used for real employment decisions."
)

TOP_N_EMPLOYEES = 20    # number of high-priority employees to explain
TOP_K_PASSAGES  = 2     # retrieved passages per employee

# ============================================================================
# PHASE 20A – LOAD PREREQUISITES
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 20 – RAG LITERATURE RETRIEVAL LAYER")
print("=" * 70)

exp_path = rc.OUT_DIR / "employee_explanations.csv"
if not exp_path.exists():
    sys.exit(
        f"\n[ERROR] {exp_path} not found.\n"
        "Please run retainiq_02_priority.py first."
    )

exp_df = pd.read_csv(exp_path)
print(f"Loaded {len(exp_df)} high-priority employee explanations.")

# ============================================================================
# PHASE 20B – PDF EXTRACTION
# ============================================================================
print("\n--- PDF Extraction ---")

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    try:
        # pyrefly: ignore [missing-import]
        from PyPDF2 import PdfReader
        HAS_PYPDF = True
    except ImportError:
        HAS_PYPDF = False
        warnings.warn(
            "pypdf / PyPDF2 not installed; RAG will use built-in corpus only.",
            RuntimeWarning,
        )

pdf_corpus: list[dict[str, Any]] = []   # list of {text, source, page}

if HAS_PYPDF:
    pdf_files = list(rc.KB_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF(s) in {rc.KB_DIR}")
    for pdf_path in pdf_files:
        try:
            reader = PdfReader(str(pdf_path))
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if len(text.strip()) > 50:
                    pdf_corpus.append({
                        "text":   text,
                        "source": pdf_path.name,
                        "page":   page_num + 1,
                    })
        except Exception as e:
            warnings.warn(f"Could not read {pdf_path.name}: {e}")
    print(f"Extracted {len(pdf_corpus)} pages of text from PDFs.")
else:
    print("pypdf unavailable – skipping PDF extraction.")

# ── Built-in seed corpus (representative literature sentences) ─────────────
# These are paraphrased/representative statements grounded in the
# HR/attrition literature.  They are NOT verbatim quotes and are
# labelled as such.  They serve as fallback when no PDFs are available.
SEED_CORPUS = [
    {
        "text": (
            "Studies on voluntary turnover consistently identify job "
            "dissatisfaction, lack of promotional opportunity, and "
            "work-life balance issues as key predictors of employee "
            "attrition (representative literature paraphrase)."
        ),
        "source": "[built-in seed corpus]",
        "page": 0,
    },
    {
        "text": (
            "Overtime work has been associated with higher reported "
            "intention to leave in multiple survey-based studies, "
            "suggesting that sustained workload may be a marker of "
            "attrition-associated conditions (representative literature paraphrase)."
        ),
        "source": "[built-in seed corpus]",
        "page": 0,
    },
    {
        "text": (
            "Lower monthly income relative to peers is frequently reported "
            "as a dissatisfaction factor correlated with turnover intention "
            "in compensation literature (representative literature paraphrase)."
        ),
        "source": "[built-in seed corpus]",
        "page": 0,
    },
    {
        "text": (
            "Short organisational tenure has been linked to higher turnover "
            "probability; early-career employees may still be evaluating "
            "fit and alternative opportunities (representative literature paraphrase)."
        ),
        "source": "[built-in seed corpus]",
        "page": 0,
    },
    {
        "text": (
            "Stagnation in promotion trajectory – measured by years since "
            "last promotion – is associated with reduced organisational "
            "commitment in longitudinal HR studies (representative literature paraphrase)."
        ),
        "source": "[built-in seed corpus]",
        "page": 0,
    },
    {
        "text": (
            "Manager relationship quality, often proxied by years with the "
            "current manager, is associated with employee satisfaction and "
            "retention according to multiple engagement surveys (representative "
            "literature paraphrase)."
        ),
        "source": "[built-in seed corpus]",
        "page": 0,
    },
    {
        "text": (
            "Job involvement and environment satisfaction are significant "
            "predictors of attrition in machine learning studies applied to "
            "benchmark HR datasets (representative literature paraphrase)."
        ),
        "source": "[built-in seed corpus]",
        "page": 0,
    },
    {
        "text": (
            "Replacement cost estimates in HR literature range widely by role, "
            "seniority, and organisation type, underscoring the importance of "
            "scenario-based cost modelling rather than fixed-multiplier "
            "assumptions (representative literature paraphrase)."
        ),
        "source": "[built-in seed corpus]",
        "page": 0,
    },
    {
        "text": (
            "Class imbalance in attrition datasets (typical minority class "
            "~16%) necessitates evaluation via PR-AUC and F1 rather than "
            "accuracy, as shown in multiple benchmark comparisons "
            "(representative literature paraphrase)."
        ),
        "source": "[built-in seed corpus]",
        "page": 0,
    },
    {
        "text": (
            "Probability calibration is critical when model outputs are used "
            "for downstream decision-making; uncalibrated classifiers can "
            "produce misleading risk estimates when multiplied by cost "
            "parameters (representative literature paraphrase)."
        ),
        "source": "[built-in seed corpus]",
        "page": 0,
    },
    {
        "text": (
            "Work-life balance ratings are inversely correlated with attrition "
            "intention in survey research; employees reporting poor balance "
            "are overrepresented among leavers in several benchmark HR "
            "datasets (representative literature paraphrase)."
        ),
        "source": "[built-in seed corpus]",
        "page": 0,
    },
    {
        "text": (
            "Number of companies worked for previously (job-hopping) is a "
            "documented predictor of future attrition in empirical HR studies, "
            "potentially reflecting lower organisational commitment thresholds "
            "(representative literature paraphrase)."
        ),
        "source": "[built-in seed corpus]",
        "page": 0,
    },
]

# Merge PDF corpus with seed corpus
full_corpus = pdf_corpus + SEED_CORPUS
print(f"Total corpus size: {len(full_corpus)} chunks "
      f"({len(pdf_corpus)} from PDFs, {len(SEED_CORPUS)} seed passages)")

# ============================================================================
# PHASE 20C – TF-IDF INDEX
# ============================================================================
print("\n--- Building TF-IDF Index (unigrams + bigrams) ---")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

corpus_texts = [c["text"] for c in full_corpus]
vectorizer   = TfidfVectorizer(
    ngram_range=(1, 2),
    max_features=20_000,
    stop_words="english",
    sublinear_tf=True,
)
tfidf_matrix = vectorizer.fit_transform(corpus_texts)
print(f"TF-IDF matrix: {tfidf_matrix.shape}  (chunks x vocabulary)")

# ============================================================================
# PHASE 20D – RETRIEVAL FUNCTION
# ============================================================================

def retrieve_passages(
    query: str,
    top_k: int = TOP_K_PASSAGES,
) -> list[dict[str, Any]]:
    """
    Retrieve top-k passages from the corpus using cosine TF-IDF similarity.

    Parameters
    ----------
    query : natural-language query string
    top_k : number of passages to return

    Returns
    -------
    list of dicts with keys: passage, source, page, score
    """
    q_vec  = vectorizer.transform([query])
    sims   = cosine_similarity(q_vec, tfidf_matrix).flatten()
    top_ix = np.argsort(sims)[::-1][:top_k]
    results = []
    for ix in top_ix:
        results.append({
            "passage": full_corpus[ix]["text"],
            "source":  full_corpus[ix]["source"],
            "page":    full_corpus[ix]["page"],
            "score":   round(float(sims[ix]), 4),
        })
    return results

# ============================================================================
# PHASE 20E – GENERATE RETENTION BRIEFS
# ============================================================================
print("\n--- Generating Retention Briefs ---")

brief_rows = []
for _, row in exp_df.iterrows():
    # Build query from model-associated factors
    factors_raw = str(row.get("model_associated_factors", ""))
    # Extract feature names from the factor string (simple approach)
    query_terms = re.sub(r"[=<>;()\[\]]", " ", factors_raw)
    query_terms = re.sub(r"\d+\.\d+", " ", query_terms)    # remove numeric values
    query = f"employee attrition {query_terms}"

    passages = retrieve_passages(query, top_k=TOP_K_PASSAGES)

    p1 = passages[0] if len(passages) > 0 else {}
    p2 = passages[1] if len(passages) > 1 else {}

    brief_rows.append({
        "EmployeeNumber":         row["EmployeeNumber"],
        "calibrated_probability": row["calibrated_probability"],
        "ERL_fixed_$":            row.get("ERL_fixed_$", ""),
        "priority_rank":          row.get("priority_rank", ""),
        "model_associated_factors": factors_raw,
        "retrieved_passage_1":    p1.get("passage", ""),
        "citation_1":             f"{p1.get('source','')} (p.{p1.get('page','')})",
        "similarity_score_1":     p1.get("score", ""),
        "retrieved_passage_2":    p2.get("passage", ""),
        "citation_2":             f"{p2.get('source','')} (p.{p2.get('page','')})",
        "similarity_score_2":     p2.get("score", ""),
        "standing_disclaimer":    STANDING_DISCLAIMER,
    })

briefs_df = pd.DataFrame(brief_rows)
briefs_df.to_csv(rc.OUT_DIR / "retention_briefs.csv", index=False)
print(f"[saved] retention_briefs.csv  ({len(briefs_df)} employees)")

# Print first 3 briefs as sample
print("\nSample retention briefs (first 3):")
for _, b in briefs_df.head(3).iterrows():
    print(f"\n  Employee #{int(b['EmployeeNumber'])}  "
          f"P(attrition)={b['calibrated_probability']:.3f}  "
          f"ERL=${float(b['ERL_fixed_$']):,.0f}  "
          f"Rank={b['priority_rank']}")
    print(f"  Factors: {b['model_associated_factors'][:80]}...")
    print(f"  Passage 1 ({b['citation_1']}, score={b['similarity_score_1']}):")
    print(f"    {b['retrieved_passage_1'][:200]}...")
    print(f"  Passage 2 ({b['citation_2']}, score={b['similarity_score_2']}):")
    print(f"    {b['retrieved_passage_2'][:200]}...")
    print(f"  DISCLAIMER: {STANDING_DISCLAIMER[:100]}...")

print("\n" + "=" * 70)
print("PHASE 3 (RAG) COMPLETE")
print("=" * 70)
print(f"  retention_briefs.csv generated in {rc.OUT_DIR}")
print(f"\n[NOTE] To improve retrieval quality, place research PDFs into {rc.KB_DIR}")
print("       Supported format: PDF (text-based, not scanned image PDFs)")
print(f"\n[DISCLAIMER] {rc.DISCLAIMER}")

"""
Evaluates the RAG pipeline on a small hand-built test set: how often retrieval
finds the right page, and how good the generated answers are according to an
LLM-as-judge (the local Llama 3.2 model grading its own pipeline's output).

This is NOT evaluating "the model" in isolation - Llama 3.2 is a general
pretrained model you didn't train. What you actually built and CAN evaluate is
the PIPELINE: retrieval + prompt + generation working together on your documents.

Usage:
    1. Upload the document(s) referenced in eval/test_set.json through the app.
    2. Edit eval/test_set.json with real questions about your own document(s).
    3. Run:  python evaluate.py
"""
import json
import os
import re
from datetime import datetime

from core import vector_store, llm_engine
from core.rag_pipeline import answer_question
from database.models import list_documents, create_session

TEST_SET_PATH = os.path.join("eval", "test_set.json")
REPORT_PATH = os.path.join("eval", "report.md")

JUDGE_SYSTEM_PROMPT = (
    "You are grading an AI assistant's answer for quality. Respond with ONLY a "
    "JSON object, no other text, in this exact format: "
    '{"faithfulness": <1-5>, "relevancy": <1-5>, "reasoning": "<one sentence>"}\n'
    "faithfulness: does the answer stick to the reference without inventing facts?\n"
    "relevancy: does the answer actually address the question asked?"
)


def _find_doc_id(filename):
    for doc in list_documents():
        if doc["filename"] == filename:
            return doc["id"]
    return None


def _retrieval_hit(question, doc_id, expected_page, top_k=5):
    hits = vector_store.query(question, [doc_id], top_k=top_k)
    pages = [h["page"] for h in hits]
    if expected_page in pages:
        return True, pages.index(expected_page) + 1, pages
    return False, None, pages


def _judge_answer(question, answer, reference_answer):
    prompt = (
        f"Question: {question}\n\n"
        f"Reference answer (may be partial or approximate): {reference_answer}\n\n"
        f"AI's actual answer: {answer}\n\n"
        "Grade the AI's answer."
    )
    raw = llm_engine.generate(prompt, system=JUDGE_SYSTEM_PROMPT)
    try:
        parsed = json.loads(raw)
        return parsed.get("faithfulness"), parsed.get("relevancy"), parsed.get("reasoning", "")
    except Exception:
        faith_match = re.search(r'"?faithfulness"?\s*[:=]\s*(\d)', raw)
        rel_match = re.search(r'"?relevancy"?\s*[:=]\s*(\d)', raw)
        faithfulness = int(faith_match.group(1)) if faith_match else None
        relevancy = int(rel_match.group(1)) if rel_match else None
        return faithfulness, relevancy, "(judge response wasn't valid JSON, salvaged with regex)"


def run_evaluation():
    with open(TEST_SET_PATH, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    session_id = create_session(
        doc_ids=[], mode="chat",
        title=f"Evaluation - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    results = []
    for case in test_cases:
        doc_id = _find_doc_id(case["filename"])
        if not doc_id:
            print(f"Skipping '{case['question']}' - document '{case['filename']}' "
                  f"not found. Upload it through the app first.")
            continue

        hit, rank, retrieved_pages = _retrieval_hit(case["question"], doc_id, case["expected_page"])
        result = answer_question(case["question"], [doc_id], session_id)
        answer = result["answer"]
        faithfulness, relevancy, reasoning = _judge_answer(
            case["question"], answer, case.get("reference_answer", "")
        )

        results.append({
            "question": case["question"],
            "answer": answer,
            "expected_page": case["expected_page"],
            "retrieved_pages": retrieved_pages,
            "retrieval_hit": hit,
            "retrieval_rank": rank,
            "faithfulness": faithfulness,
            "relevancy": relevancy,
            "reasoning": reasoning,
        })

        print(f"\nQ: {case['question']}")
        print(f"   Retrieval hit@5: {'YES' if hit else 'NO'}" + (f" (rank {rank})" if hit else ""))
        if not hit:
            print(f"   Expected page {case['expected_page']}, got pages: {retrieved_pages}")
        print(f"   Faithfulness: {faithfulness}/5   Relevancy: {relevancy}/5")

    _write_report(results)
    return results


def _write_report(results):
    os.makedirs("eval", exist_ok=True)
    hits = [r for r in results if r["retrieval_hit"]]
    hit_rate = len(hits) / len(results) if results else 0
    mrr = sum(1 / r["retrieval_rank"] for r in hits) / len(results) if results else 0

    scored = [r for r in results if r["faithfulness"] is not None and r["relevancy"] is not None]
    avg_faith = sum(r["faithfulness"] for r in scored) / len(scored) if scored else 0
    avg_rel = sum(r["relevancy"] for r in scored) / len(scored) if scored else 0

    lines = [
        f"# Evaluation Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"- Test cases: {len(results)}",
        f"- Retrieval hit rate @5: {hit_rate:.0%}",
        f"- Mean Reciprocal Rank: {mrr:.2f}",
        f"- Avg faithfulness: {avg_faith:.1f}/5",
        f"- Avg relevancy: {avg_rel:.1f}/5",
        "",
        "| Question | Hit@5 | Rank | Expected | Retrieved | Faithfulness | Relevancy | Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['question']} | {'YES' if r['retrieval_hit'] else 'NO'} | "
            f"{r['retrieval_rank'] or '-'} | {r['expected_page']} | {r['retrieved_pages']} | "
            f"{r['faithfulness']} | {r['relevancy']} | {r['reasoning']} |"
        )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nFull report saved to {REPORT_PATH}")


if __name__ == "__main__":
    run_evaluation()
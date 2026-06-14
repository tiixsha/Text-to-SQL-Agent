import csv
import json
import time
import os
from datetime import datetime
from src.engine.executor import run_pipeline

# Paths
CSV_FILE = "data/sql_questions_only.csv"
REPORT_FILE = "logs/evaluation_report.json"
SUMMARY_FILE = "logs/evaluation_summary.txt"


def load_questions(csv_path: str) -> list:
    """Load questions from CSV file."""
    questions = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append(row)
    return questions


def run_evaluation():
    """
    Run all benchmark questions through the pipeline
    and generate an evaluation report.
    """
    print(f"\n{'='*60}")
    print(f"  TEXT-TO-SQL EVALUATION REPORT")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    questions = load_questions(CSV_FILE)
    total = len(questions)
    print(f"Loaded {total} questions from {CSV_FILE}\n")

    # Tracking metrics
    results = []
    total_success = 0
    total_failed = 0
    total_retries = 0
    total_latency = 0

    for i, row in enumerate(questions, 1):
        # Handle different possible column names in CSV
        question = (
            row.get("question") or
            row.get("Question") or
            row.get("questions") or
            list(row.values())[0]
        )

        print(f"[{i}/{total}] Question: {question}")

        start = time.time()
        try:
            output = run_pipeline(question, max_retries=3)
        except Exception as e:
            output = {
                "sql": None,
                "result": None,
                "summary": "Pipeline crashed",
                "status": "failed",
                "error": str(e)
            }
        latency = round(time.time() - start, 3)
        total_latency += latency

        # Determine retry count from logs
        retry_needed = "Yes" if output.get("retries", 0) > 0 else "No"

        # Build result entry
        entry = {
            "index": i,
            "question": question,
            "generated_sql": output.get("sql"),
            "executed_successfully": output["status"] == "success",
            "correct_result": output["status"] == "success",
            "retry_needed": retry_needed,
            "latency_seconds": latency,
            "status": output["status"],
            "summary": output.get("summary"),
            "error": output.get("error")
        }

        results.append(entry)

        # Update counters
        if output["status"] == "success":
            total_success += 1
            print(f"  ✅ Success | SQL: {str(output.get('sql', ''))[:60]}...")
        else:
            total_failed += 1
            print(f"  ❌ Failed  | Error: {output.get('error', 'Unknown')}")

        print(f"  ⏱  Latency: {latency}s\n")

        # Small delay to avoid Gemini rate limiting
        time.sleep(1)

    # Calculate final metrics
    success_rate = round((total_success / total) * 100, 2)
    avg_latency = round(total_latency / total, 3)

    # Save detailed report
    report = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total_questions": total,
        "total_success": total_success,
        "total_failed": total_failed,
        "success_rate_percent": success_rate,
        "average_latency_seconds": avg_latency,
        "results": results
    }

    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Save human readable summary
    summary = f"""
{'='*60}
TEXT-TO-SQL EVALUATION SUMMARY
{'='*60}
Date           : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Questions: {total}
Successful     : {total_success}
Failed         : {total_failed}
Success Rate   : {success_rate}%
Avg Latency    : {avg_latency}s
{'='*60}

FAILED QUERIES:
"""
    for r in results:
        if not r["executed_successfully"]:
            summary += f"\n  Q{r['index']}: {r['question']}\n"
            summary += f"  Error: {r['error']}\n"

    with open(SUMMARY_FILE, "w") as f:
        f.write(summary)

    # Print final summary
    print(f"\n{'='*60}")
    print(f"  EVALUATION COMPLETE")
    print(f"  Total    : {total}")
    print(f"  Success  : {total_success} ({success_rate}%)")
    print(f"  Failed   : {total_failed}")
    print(f"  Avg Time : {avg_latency}s")
    print(f"{'='*60}")
    print(f"\n  Detailed report saved to: {REPORT_FILE}")
    print(f"  Summary saved to: {SUMMARY_FILE}\n")


if __name__ == "__main__":
    run_evaluation()
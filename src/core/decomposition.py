import csv
import json
import time
import re
import os
from datetime import datetime
from src.core.sql_generator import decompose

INPUT_CSV = "data/sql_questions_only.csv"
OUTPUT_CSV = "data/decompositions.csv"

MAX_RETRIES = 3
BASE_SLEEP = 2  # seconds between successful requests


def load_questions(csv_path: str) -> list:
    questions = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append(row)
    return questions

def extract_retry_seconds(error_str: str) -> int:
  
    match = re.search(r'seconds:\s*(\d+)', error_str)
    if match:
        return int(match.group(1)) + 5  # add 5s buffer
    # Try "retry in XXs" pattern
    match = re.search(r'retry in (\d+)', error_str)
    if match:
        return int(match.group(1)) + 5
    return 60  # default fallback

def decompose_with_retry(question: str) -> dict:

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return decompose(question)
        except Exception as e:
            error_str = str(e)
            is_rate_limit = "429" in error_str or \
                            "RESOURCE_EXHAUSTED" in error_str or \
                            "quota" in error_str.lower()

            if is_rate_limit and attempt < MAX_RETRIES:
                wait_seconds = extract_retry_seconds(error_str)
                print(f"  [RATE LIMIT] Waiting {wait_seconds}s before retry "
                      f"(attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(wait_seconds)
                continue
            else:
                raise e

    raise Exception(f"Max retries exceeded for question: {question}")

def has_header() -> bool:
    
    if not os.path.exists(OUTPUT_CSV):
        return False
    if os.path.getsize(OUTPUT_CSV) == 0:
        return False
    try:
        with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            # Check if first line is actually the header
            return first_line.startswith("question")
    except Exception:
        return False

def load_completed_questions() -> set:
    
    completed = set()
    if not os.path.exists(OUTPUT_CSV):
        return completed
    try:
        with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if not first_line.startswith("question"):
            
                f.seek(0)
                reader = csv.reader(f)
                for row in reader:
                    if row and len(row) >= 7 and row[6] == "success":
                        completed.add(row[0].strip())
            else:
                
                f.seek(0)
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("status") == "success":
                        completed.add(row["question"].strip())
    except Exception:
        pass
    return completed

def append_to_csv(result: dict, write_header: bool):
   
    fieldnames = [
        "question", "intent", "tables",
        "columns", "filters", "joins", "status"
    ]
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(result)

def run_decompositions():
    print(f"\n{'='*60}")
    print(f"  QUERY DECOMPOSITION GENERATOR")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    questions = load_questions(INPUT_CSV)
    total = len(questions)

    completed = load_completed_questions()
    print(f"Loaded {total} questions from {INPUT_CSV}")
    print(f"Already completed: {len(completed)} questions")
    print(f"Remaining: {total - len(completed)} questions\n")

    write_header = not has_header()

    success_count = len(completed)
    failed_count = 0

    for i, row in enumerate(questions, 1):
        question = (
            row.get("question") or
            row.get("Question") or
            row.get("questions") or
            list(row.values())[0]
        ).strip()

        if question in completed:
            print(f"[{i}/{total}] Skipping (already done): {question}")
            continue

        print(f"[{i}/{total}] Decomposing: {question}")

        try:
            decomposition = decompose_with_retry(question)

            result = {
                "question": question,
                "intent":   decomposition.get("intent", ""),
                "tables":   ", ".join(decomposition.get("tables", [])),
                "columns":  ", ".join(decomposition.get("columns", [])),
                "filters":  ", ".join(decomposition.get("filters", [])),
                "joins":    ", ".join(decomposition.get("joins", [])),
                "status":   "success"
            }

            success_count += 1
            print(f"  [OK] Intent : {result['intent']}")
            print(f"       Tables : {result['tables']}")
            print(f"       Filters: {result['filters']}\n")

        except Exception as e:
            result = {
                "question": question,
                "intent":   "",
                "tables":   "",
                "columns":  "",
                "filters":  "",
                "joins":    "",
                "status":   f"failed: {str(e)[:100]}"
            }
            failed_count += 1
            print(f"  [FAILED]: {str(e)[:100]}\n")

        append_to_csv(result, write_header)
        write_header = False

        time.sleep(BASE_SLEEP)

    print(f"\n{'='*60}")
    print(f"  DECOMPOSITION COMPLETE")
    print(f"  Total     : {total}")
    print(f"  Successful: {success_count}")
    print(f"  Failed    : {failed_count}")
    print(f"  Output    : {OUTPUT_CSV}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    run_decompositions()
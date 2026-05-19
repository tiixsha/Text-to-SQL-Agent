import re

# Keywords that are not allowed
FORBIDDEN_KEYWORDS = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "REPLACE"]

def validate_sql(sql: str) -> str:

    if not sql or not sql.strip():
        raise ValueError("Empty SQL query provided.")

    cleaned_sql = sql.strip()

    if not cleaned_sql.upper().startswith("SELECT"):
        raise ValueError(f"Only SELECT queries are allowed. Got: {cleaned_sql[:50]}")

    sql_upper = cleaned_sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
  
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            raise ValueError(f"Forbidden keyword detected: {keyword}")

    return cleaned_sql
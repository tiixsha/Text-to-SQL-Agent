DECOMPOSE_PROMPT = """
You are an expert SQL analyst working with a PostgreSQL database called classicmodels.

The database has the following tables and their key columns:
- customers: customerNumber, customerName, city, country, salesRepEmployeeNumber
- orders: orderNumber, orderDate, requiredDate, shippedDate, status, customerNumber
- orderdetails: orderNumber, productCode, quantityOrdered, priceEach
- products: productCode, productName, productLine, buyPrice, MSRP, quantityInStock, productVendor
- productlines: productLine, textDescription
- employees: employeeNumber, firstName, lastName, jobTitle, officeCode, reportsTo
- offices: officeCode, city, country, phone
- payments: customerNumber, checkNumber, paymentDate, amount

Your task is to decompose the following natural language question into structured components.

Question: {question}

Respond ONLY in valid JSON format with no extra text, no markdown, no code blocks.
Use exactly this structure:

{{
  "intent": "brief description of what is being asked",
  "tables": ["table1", "table2"],
  "columns": ["table.column1", "table.column2"],
  "filters": ["condition1", "condition2"],
  "joins": ["table1.column = table2.column"]
}}

If there are no filters, return an empty list for filters.
If there are no joins, return an empty list for joins.
"""

GENERATE_PROMPT = """
You are an expert SQL analyst working with a PostgreSQL database called classicmodels.

Based on the following structured decomposition, write a correct PostgreSQL SELECT query.

Decomposition:
{decomposition}

Rules:
- Only write SELECT queries
- Use proper table aliases
- Use double quotes for column and table names
- Return ONLY the raw SQL query with no explanation, no markdown, no code blocks

SQL:
"""

FIX_PROMPT = """
You are an expert SQL debugger working with PostgreSQL.

The following SQL query failed with this error:
Error: {error}

Failed SQL:
{sql}

Database schema context:
- customers: customerNumber, customerName, city, country, salesRepEmployeeNumber
- orders: orderNumber, orderDate, requiredDate, shippedDate, status, customerNumber
- orderdetails: orderNumber, productCode, quantityOrdered, priceEach
- products: productCode, productName, productLine, buyPrice, MSRP, quantityInStock, productVendor
- productlines: productLine, textDescription
- employees: employeeNumber, firstName, lastName, jobTitle, officeCode, reportsTo
- offices: officeCode, city, country, phone
- payments: customerNumber, checkNumber, paymentDate, amount

Fix the SQL query and return ONLY the corrected raw SQL with no explanation, no markdown, no code blocks.

Fixed SQL:
"""
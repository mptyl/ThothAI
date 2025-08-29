# Text-to-SQL

## 1 - What is Text-to-SQL
Text-to-SQL is a technology that allows the automatic conversion of questions or requests expressed in natural language into structured SQL queries.
This technology represents a bridge between the end user and databases, eliminating the need to know SQL syntax to query data.
For insights into the potential and limitations of text-to-SQL, see the [specific page](text-to-SQL.md)

### 1.1 - Fundamental characteristics:
1. Natural language understanding: The application must be able to interpret questions formulated in the user's language and understand their intent
2. Semantic mapping: It must connect concepts expressed in natural language to database elements (tables, columns, relationships)
3. Valid SQL generation: It must produce syntactically correct and semantically appropriate SQL queries
4. Context management: It must understand the specific domain and database structure to provide accurate results

### 1.2 - Main advantages:
- Allows non-technical users to query complex databases even when Business Intelligence tools prepared for this purpose are not available
- Reduces the time needed to formulate complex queries
- Minimizes SQL syntax errors
- Makes data analysis accessible to a wider audience

## 2 - Main difficulties of Text-to-SQL

Although `Text-to-SQL` is a promising technology, to obtain satisfactory results it is necessary to overcome several difficulties.

### 2.1 Context and schema documentation problems

**Insufficient schema documentation:** 

- **Non-descriptive field names**: Often databases use abbreviations, codes or naming conventions that are not immediately understandable (e.g., "cd_cli" instead of "customer_code")
- **Non-English language**: Many databases are designed with table and field names in languages other than English, creating difficulties for AI models trained primarily on English texts
- **Lack of comments**: Absence of technical documentation that explains the meaning and use of various fields
- **Domain-specific terminology**: Presence of business or sector "jargon" that requires specific knowledge of the business context
- **Implicit relationships**: Lack of explicitly defined Foreign Keys, making it difficult to understand relationships between tables

### 2.1 - Limitations in data understanding

**Lack of information about values:**

- Absence of examples of values contained in fields, which could help better understand the meaning and use of columns
- Difficulty in understanding domains of possible values and their semantic relationships

### 2.2 - Scalability problems

**Schema dimensions:**

- Databases with many tables and columns can "confuse" smaller AI models
- Difficulty in maintaining context when the schema is very large
- Need for intelligent selection strategies of relevant tables for a specific query

### 2.3 - Technical challenges in semantic mapping

**Linguistic ambiguity:**

- The same request in natural language can be interpreted in different ways
- Difficulty in disambiguating terms that could refer to multiple database entities

**Query complexity:**

- Need to translate complex requests involving aggregations, multiple joins, subqueries
- Management of articulated conditional logic expressed in natural language

### 2.4 - Domain-specific management

**Business knowledge:**

- Each sector has its specificities and conventions that must be understood by the system
- Need to adapt interpretation to the specific business context

**System evolution:**

- Databases change over time, requiring continuous updates to semantic mapping
- Need to maintain consistency between interpretations over time
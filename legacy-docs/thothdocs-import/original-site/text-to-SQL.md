# Text-to-SQL

## 1 - What is Text-to-SQL
Text-to-SQL automatically converts natural-language questions or requests into structured SQL queries. It bridges the gap between end users and databases, removing the need to know SQL syntax to retrieve data. For more details about capabilities and limitations, see the [dedicated page](text-to-SQL.md).

### 1.1 - Core characteristics
1. Natural-language understanding: interpret user questions in the chosen language and capture intent.
2. Semantic mapping: link natural-language concepts to database elements (tables, columns, relationships).
3. Valid SQL generation: produce syntactically correct, semantically appropriate SQL.
4. Context handling: understand the domain and database structure to deliver accurate answers.

### 1.2 - Main benefits
- Enables non-technical users to query complex databases even without BI tools.
- Reduces the time needed to formulate complex queries.
- Minimizes SQL syntax errors.
- Makes data analysis accessible to a broader audience.

## 2 - Main challenges of Text-to-SQL

Sebbene il `Text-to-SQL` sia una tecnologia promettente, per ottenere risultati soddisfacenti è necessario superare diverse difficoltà.

### 2.1 - Context and schema documentation issues

**Insufficient schema documentation:** 

- **Non-descriptive field names**: Databases often use abbreviations/codes that are unclear (e.g., `cd_cli` vs `customer_code`).
- **Non-English language**: Tables/columns may be named in languages other than English, challenging AI models trained mostly on English.
- **Missing comments**: No technical documentation explaining field meaning/usage.
- **Domain-specific terminology**: Business jargon requiring specialized knowledge.
- **Implicit relationships**: Lack of explicit foreign keys makes table relationships hard to infer.

### 2.2 - Data understanding limitations

**Lack of value information:**

- Few or no sample values to illustrate column meaning.
- Hard to understand possible value domains and semantic relationships.

### 2.3 - Scalability problems

**Schema size:**

- Large schemas can overwhelm smaller AI models.
- Hard to maintain context when many tables/columns exist.
- Need for intelligent selection of relevant tables per query.

### 2.4 - Technical challenges in semantic mapping

**Linguistic ambiguity:**

- A single question may have multiple interpretations.
- Hard to disambiguate terms corresponding to multiple database entities.

**Query complexity:**

- Must handle complex requests with aggregations, multi-joins, subqueries.
- Need to encode conditional logic expressed in natural language.

### 2.5 - Domain-specific management

**Business knowledge:**

- Each industry has its own conventions the system must understand.
- Need to adapt interpretation to the specific business context.

**System evolution:**

- Databases change over time, requiring continuous semantic updates.
- Interpretations must remain consistent as the schema evolves.
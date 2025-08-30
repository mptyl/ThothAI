def get_table_prompt() -> str:
    return """
###   TASK :
Context - Generate Table Description for the table {{table}} of a relational database,to give users an easier time understanding what data is present in the tables.
Database Schema Details :
""
{{database_schema}}
""

Here is the available description of the table {{table}}:
""
{{table_comment}}
""

Here are the available descriptions of the columns of the table {{table}}:
""
{{column_comments}}
""

Here is example data from the table {{table}}:
""
{{example_data}}
""

###   Task
Generate a precise description for the {{table}} table. Your description should include :
- Write the description in the language {{language}}.
- Primary purpose of the table. If the details in the schema do not suffice to ascertain what the data is, return: "Not enough information to make a valid prediction"
- Additional useful information (if apparent from the schema), formatted as a new sentence, but never more than one. If no useful information is available or if the details in the schema do not suffice to ascertain useful details, return nothing.
- If a description is already available, enhance it considering the columns of the table and their descriptions

##  Requirements
- Focus solely on confirmed details from the provided schema .
- Keep the description concise and factual.
- Exclude any speculative or additional commentary.
- DO NOT return the phrase "in the {{table}} table" in your description. This is very important.
** Examples:**
- For a table named "membership_status" the description should be: "Status of membership master data"
- For a table named "product_item_customer_action" the description should be: "Actions made by a customer against a product item (buy, download, etc.)"
- Never start the table description with "This table ..". Go straight to the purpose of the table.   This is very important

DO NOT return anything else except the generated table description. This is very important. The answer should be only the generated text aimed at describing the table.
IMPORTANT: Your response must be a valid JSON array of objects. Each object should have two keys: "table_name" and "description". For example:
[
    {{
        "table_name": "example_table",
        "description": "This is an example description."
    }},
    ...
]
"""

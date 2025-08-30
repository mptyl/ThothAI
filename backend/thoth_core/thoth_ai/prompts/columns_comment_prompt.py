def get_columns_prompt() -> str:
    return """
###   TASK :
Context - Generate Column Descriptions for the table {{table}} of a relational database, to give users a better understanding of what data is present in the columns.

Table Schema Details :
""
{{table_schema}}
""

Here is the current available description of the table {{table}}:
""
{{table_comment}}
""

Here is the subset of columns from the table {{table}} for which comment generation is requested:
""
{{column_list}}


Here are the current available descriptions of the subset of columns from the table {{table}} for which comment generation is requested:
""
{{column_comments}}

Here is example data of the subset of columns from the table {{table}} for which comment generation is requested:
""
 {{example_data}}
""

Here is the language to use when generating the comment
"
{{language}}
""

The name of the columns can contain important informations about the column, and, if meaningful, should be used to write the description .
The previous column descriptions are sometimes lacking and should be read and rewritten .

###   Task
Generate a precise description for the columns in the {table} table for which comment generation is requested. Your description should include :
- Primary purpose of the column. If the details in the schema do not suffice to ascertain what the data is, return: "Not enough information to make a valid prediction"
- Additional useful information (if apparent from the schema), formatted as a new sentence, but never more than one. If no useful information is available or if the details in the schema do not suffice to ascertain useful details, return nothing.
- If the example data show that the column seems an enum, has a limited number of possible values and the column name does not end with '_id', put the entire list of the possible values in the description, with a maximum of {max_examples} values.

##  Requirements
- Write the description only for the required columns. Do not generate descriptions for columns that are not in the provided list.
- Write the description in the {{language}} language.
- Focus solely on confirmed details from the provided schema.
- Keep the description concise and factual.
- Exclude any speculative or additional commentary.
- DO NOT return the phrase "in the {{table}} table" in your description. This is very important.
** Examples:**
- For a column named "no. of municipalities with inhabitants <499" the description should be: "This is the number of municipalities with fewer than 499 inhabitants"
- For a column named "product_status" the description should be: "The status of the product, e.g active, inactive, cancelled"
- Never start the column description with "This column ..". Go straight to the purpose of the column.   This is very important
- Keep the description as short as possible: So, "Details about the ratio of urban inhabitants" is preferred over "This column provides information on details about ratio of urban inhabitants".
- If the name is "Frequency", the description should be : "The frequency of transactions on the account" since this comes from the account table.
- If the name is "amount_of_money"  the descriptions should be: "The amount of money in the order" since this comes from the order table.
###  Please skip the "data_format" and focus solely on updating the "column_description".
IMPORTANT: Your response must be a valid JSON array of objects. Each object should have two keys: "column_name" and "description". For example:
[
    {{
        "column_name": "example_column",
        "description": "This is an example description."
    }},
    ...
]
"""

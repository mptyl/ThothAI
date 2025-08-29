# Welcome to ThothAI
**ThothAI** is an application that allows, using AI, to produce appropriate SQL instructions capable of extracting the requested information from a relational database.
Applications of this type are called `Text-to-SQL`

![Container List](assets/index_pngs/FrontendWindow.png)

What characterizes **ThothAI** is:

- the availability of a **user interface** (`ThothSL`) that is very simple to use and at the same time highly adaptable;
- the ability to specify, among the configuration parameters:

    1. the **users** authorized to use the application and their permissions;
    2. the **databases to query** and the **vector databases** to associate for storing the metadata necessary for transforming the request into SQL;
    3. the **LLM models** to use;

- the use of a specific backend application for managing:

    1. **configuration parameters**;
    2. **metadata** of the database to query (tables, columns, relationships);
    3. **table and column descriptions**, which, if not available, can be generated through AI;
    4. **preprocessing** of the database to be examined to create hashes and vectors that facilitate the SQL generation process;
    5. **hints** that can clarify complex terms or suggest non-intuitive interpretations and, above all, not easily derivable from field names and field and table descriptions;
    6. **question/SQL** pairs that are certainly correct and can serve as a guide and example for requests that will be made in the future;

- the use of a **vector database** for storing **hints** and **question/SQL** pairs, which can be fed by authorized users;
- the extensive use of **LLMs**, even small or medium-sized ones, to perform the various phases of the SQL generation workflow to be executed. 
ThothAI allows defining the attributes of **LLMs** to use in the database, making it simple to adapt the application to future developments;
- the ability to adapt the generation process to the complexity and size of your database schema.
With **ThothAI**, in fact, you can choose between two approaches:
    1. an `incremental workflow`, which first tries with small and economical models, then escalates to larger models in case of failure. 
To be able to use small models, with a RAG technique, only the tables and columns that have a high probability of being the subject of SQL are first extracted from the total schema;
    2. a `brute force workflow` that immediately uses a powerful model, letting it do almost all the work starting from the schema with all available tables and columns.

## 1 - How to use ThothAI
1. Follow the [installation instructions](1-install/1.1-sources_cloning.md).
2. Get familiar with the application using the [Quick Start](2-quickstart/2.1-quickstart_frontend.md)
3. Read the **User Manual** page dedicated to an [overview of the setup process](3-user_manual/3.1-setup/3.1.0-setup_process.md)
4. Configure the application by first configuring your [groups](3-user_manual/3.1-setup/3.1.1-authentication/3.1.1.1-groups.md) and your [users](3-user_manual/3.1-setup/3.1.1-authentication/3.1.1.2-users.md/)
5. Modify, if necessary, the list of [AI models](3-user_manual/3.1-setup/3.1.2-AI_models_and_agents/3.1.2.2-ai_models.md) (LLM) to use in executing the process
6. Adapt, if necessary, the Agents by configuring them as described on [this page](3-user_manual/3.1-setup/3.1.2-AI_models_and_agents/3.1.2.3-agents.md)
7. Set up the [vector database](3-user_manual/3.1-setup/3.1.3-vector_database/3.1.3.1-vector_db.md) intended to contain the metadata of the relational database to query
8. Set the parameters for [database configuration](3-user_manual/3.1-setup/3.1.4-SQL_database/3.1.4.1-sql_dbs.md) to query and complete its detailed description with tables, columns, relationships, comments and scope
9. Set up a specific [Setting](3-user_manual/3.1-setup/3.1.0-setup_process.md) for the activity you want to conduct if the Default one is not adequate
10. Set up the [Workflow](3-user_manual/3.1-setup/3.1.6.1-workspaces.md) to connect a set of users, a database to query, a set of Agents to use and a Setting 
11. Execute the [Preprocessing](3-user_manual/3.2-preprocessing/3.2.1-why_the_preprocessing.md) activities of the database 
12. Go to the frontend at [http://localhost:8501](http://localhost:8501) (port 8503 if working locally) and operate as indicated in the following brief [instructions](3-user_manual/3.9-frontend.md)

## 2 - Activity logs
Examine what is indicated on the [page dedicated to Log Management](3-user_manual/3.4-logging/3.4.2-log_management.md)

## 3 - The Roadmap
The development Roadmap of **ThothAI** is [described here](3-user_manual/3.8-roadmap.md)

## 4 - References to products and papers
The [References](references.md) page collects the products, studies and papers that inspired **ThothAI**

## 5 - The Reference Manual
Technical insights are available in the [Reference Manual](4-reference_manual/4.1-reference_manual_map.md)

## 6 - What is Text-to-SQL
For more information on the techniques collected under the name `Text-to-SQL` read [this page](text-to-SQL.md)
  

# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Translation dictionary for database documentation titles and UI elements.
Provides localized strings for all hardcoded text in the documentation interface.
"""

# Translation mappings for documentation interface elements
DOCUMENTATION_TRANSLATIONS = {
    "en": {
        # Page titles and headers
        "page_title": "Database Documentation",
        "page_subtitle": "Documentation",
        "breadcrumb_thoth": "Thoth",
        "breadcrumb_documentation": "Documentation",

        # Main sections
        "database_scope": "Database Scope",
        "tables_and_columns": "Tables and Columns",
        "foreign_key_relationships": "Foreign Key Relationships",
        "no_foreign_key_relationships": "No foreign key relationships defined in this database.",

        # Search functionality
        "search_placeholder": "Search in documentation...",
        "search_clear_title": "Clear search",
        "search_results_none": "No results",
        "search_results_count": "{count} results",
        "search_results_current": "{current} of {total}",
        "search_help": "Press <kbd>Enter</kbd> for next, <kbd>Shift+Enter</kbd> for previous, <kbd>Esc</kbd> to clear",

        # Export functionality
        "export_pdf": "📄 Export PDF",

        # No documentation messages
        "no_documentation_available": "No Documentation Available",
        "no_documentation_message": "Documentation has not been generated yet for database '{db_name}'.",
        "no_database_selected": "Please select a workspace with a database to view documentation.",

        # Instructions for generating documentation
        "generate_instructions_title": "To generate documentation:",
        "generate_instructions": [
            "Go to the Django Admin panel",
            "Navigate to SQL Databases",
            "Select your database ({db_name})",
            "Choose \"Generate database documentation (AI assisted)\" from the actions dropdown"
        ],
        "go_to_database_admin": "📊 Go to Database Admin",
        "go_to_home": "📁 Go to Home",

        # Table headers
        "source_table": "Source Table",
        "source_column": "Source Column",
        "target_table": "Target Table",
        "target_column": "Target Column",
        "column_name": "Column Name",
        "data_type": "Data Type",
        "description": "Description",
        "value_description": "Value Description",
        "fk": "FK",

        # Generated metadata
        "generated_by": "Generated on {timestamp} by Thoth AI",
    },

    "it": {
        # Page titles and headers
        "page_title": "Documentazione Database",
        "page_subtitle": "Documentazione",
        "breadcrumb_thoth": "Thoth",
        "breadcrumb_documentation": "Documentazione",

        # Main sections
        "database_scope": "Ambito del Database",
        "tables_and_columns": "Tabelle e Colonne",
        "foreign_key_relationships": "Relazioni Chiave Esterna",
        "no_foreign_key_relationships": "Nessuna relazione chiave esterna definita in questo database.",

        # Search functionality
        "search_placeholder": "Cerca nella documentazione...",
        "search_clear_title": "Cancella ricerca",
        "search_results_none": "Nessun risultato",
        "search_results_count": "{count} risultati",
        "search_results_current": "{current} di {total}",
        "search_help": "Premi <kbd>Enter</kbd> per il successivo, <kbd>Shift+Enter</kbd> per il precedente, <kbd>Esc</kbd> per cancellare",

        # Export functionality
        "export_pdf": "📄 Esporta PDF",

        # No documentation messages
        "no_documentation_available": "Nessuna Documentazione Disponibile",
        "no_documentation_message": "La documentazione non è stata ancora generata per il database '{db_name}'.",
        "no_database_selected": "Seleziona un workspace con un database per visualizzare la documentazione.",

        # Instructions for generating documentation
        "generate_instructions_title": "Per generare la documentazione:",
        "generate_instructions": [
            "Vai al pannello di amministrazione Django",
            "Naviga su Database SQL",
            "Seleziona il tuo database ({db_name})",
            "Scegli \"Genera documentazione database (assistita AI)\" dal menu a discesa delle azioni"
        ],
        "go_to_database_admin": "📊 Vai all'Amministrazione Database",
        "go_to_home": "📁 Vai alla Home",

        # Table headers
        "source_table": "Tabella Origine",
        "source_column": "Colonna Origine",
        "target_table": "Tabella Destinazione",
        "target_column": "Colonna Destinazione",
        "column_name": "Nome Colonna",
        "data_type": "Tipo Dati",
        "description": "Descrizione",
        "value_description": "Descrizione Valore",
        "fk": "CE",

        # Generated metadata
        "generated_by": "Generato il {timestamp} da Thoth AI",
    },

    "es": {
        # Page titles and headers
        "page_title": "Documentación de la Base de Datos",
        "page_subtitle": "Documentación",
        "breadcrumb_thoth": "Thoth",
        "breadcrumb_documentation": "Documentación",

        # Main sections
        "database_scope": "Ámbito de la Base de Datos",
        "tables_and_columns": "Tablas y Columnas",
        "foreign_key_relationships": "Relaciones de Clave Foránea",
        "no_foreign_key_relationships": "No hay relaciones de clave foránea definidas en esta base de datos.",

        # Search functionality
        "search_placeholder": "Buscar en la documentación...",
        "search_clear_title": "Limpiar búsqueda",
        "search_results_none": "Sin resultados",
        "search_results_count": "{count} resultados",
        "search_results_current": "{current} de {total}",
        "search_help": "Presiona <kbd>Enter</kbd> para siguiente, <kbd>Shift+Enter</kbd> para anterior, <kbd>Esc</kbd> para limpiar",

        # Export functionality
        "export_pdf": "📄 Exportar PDF",

        # No documentation messages
        "no_documentation_available": "Documentación No Disponible",
        "no_documentation_message": "La documentación no ha sido generada aún para la base de datos '{db_name}'.",
        "no_database_selected": "Por favor selecciona un workspace con una base de datos para ver la documentación.",

        # Instructions for generating documentation
        "generate_instructions_title": "Para generar documentación:",
        "generate_instructions": [
            "Ve al panel de administración Django",
            "Navega a Bases de Datos SQL",
            "Selecciona tu base de datos ({db_name})",
            "Elige \"Generar documentación de base de datos (asistida por IA)\" del menú desplegable de acciones"
        ],
        "go_to_database_admin": "📊 Ir a Administración de Base de Datos",
        "go_to_home": "📁 Ir al Inicio",

        # Table headers
        "source_table": "Tabla Origen",
        "source_column": "Columna Origen",
        "target_table": "Tabla Destino",
        "target_column": "Columna Destino",
        "column_name": "Nombre de Columna",
        "data_type": "Tipo de Dato",
        "description": "Descripción",
        "value_description": "Descripción del Valor",
        "fk": "CF",

        # Generated metadata
        "generated_by": "Generado el {timestamp} por Thoth AI",
    },

    "fr": {
        # Page titles and headers
        "page_title": "Documentation de la Base de Données",
        "page_subtitle": "Documentation",
        "breadcrumb_thoth": "Thoth",
        "breadcrumb_documentation": "Documentation",

        # Main sections
        "database_scope": "Portée de la Base de Données",
        "tables_and_columns": "Tables et Colonnes",
        "foreign_key_relationships": "Relations de Clé Étrangère",
        "no_foreign_key_relationships": "Aucune relation de clé étrangère définie dans cette base de données.",

        # Search functionality
        "search_placeholder": "Rechercher dans la documentation...",
        "search_clear_title": "Effacer la recherche",
        "search_results_none": "Aucun résultat",
        "search_results_count": "{count} résultats",
        "search_results_current": "{current} sur {total}",
        "search_help": "Appuyez sur <kbd>Enter</kbd> pour suivant, <kbd>Shift+Enter</kbd> pour précédent, <kbd>Esc</kbd> pour effacer",

        # Export functionality
        "export_pdf": "📄 Exporter PDF",

        # No documentation messages
        "no_documentation_available": "Documentation Non Disponible",
        "no_documentation_message": "La documentation n'a pas encore été générée pour la base de données '{db_name}'.",
        "no_database_selected": "Veuillez sélectionner un workspace avec une base de données pour voir la documentation.",

        # Instructions for generating documentation
        "generate_instructions_title": "Pour générer la documentation:",
        "generate_instructions": [
            "Allez au panneau d'administration Django",
            "Naviguez vers Bases de Données SQL",
            "Sélectionnez votre base de données ({db_name})",
            "Choisissez \"Générer la documentation de base de données (assistée par IA)\" dans le menu déroulant des actions"
        ],
        "go_to_database_admin": "📊 Aller à l'Administration de la Base de Données",
        "go_to_home": "📁 Aller à l'Accueil",

        # Table headers
        "source_table": "Table Source",
        "source_column": "Colonne Source",
        "target_table": "Table Cible",
        "target_column": "Colonne Cible",
        "column_name": "Nom de Colonne",
        "data_type": "Type de Données",
        "description": "Description",
        "value_description": "Description de la Valeur",
        "fk": "CE",

        # Generated metadata
        "generated_by": "Généré le {timestamp} par Thoth AI",
    },

    "de": {
        # Page titles and headers
        "page_title": "Datenbankdokumentation",
        "page_subtitle": "Dokumentation",
        "breadcrumb_thoth": "Thoth",
        "breadcrumb_documentation": "Dokumentation",

        # Main sections
        "database_scope": "Datenbankumfang",
        "tables_and_columns": "Tabellen und Spalten",
        "foreign_key_relationships": "Fremdschlüsselbeziehungen",
        "no_foreign_key_relationships": "Keine Fremdschlüsselbeziehungen in dieser Datenbank definiert.",

        # Search functionality
        "search_placeholder": "In Dokumentation suchen...",
        "search_clear_title": "Suche löschen",
        "search_results_none": "Keine Ergebnisse",
        "search_results_count": "{count} Ergebnisse",
        "search_results_current": "{current} von {total}",
        "search_help": "Drücke <kbd>Enter</kbd> für nächstes, <kbd>Shift+Enter</kbd> für vorheriges, <kbd>Esc</kbd> zum löschen",

        # Export functionality
        "export_pdf": "📄 PDF exportieren",

        # No documentation messages
        "no_documentation_available": "Keine Dokumentation Verfügbar",
        "no_documentation_message": "Dokumentation wurde noch nicht für Datenbank '{db_name}' generiert.",
        "no_database_selected": "Bitte wählen Sie einen Workspace mit einer Datenbank aus, um die Dokumentation anzuzeigen.",

        # Instructions for generating documentation
        "generate_instructions_title": "Um Dokumentation zu generieren:",
        "generate_instructions": [
            "Gehen Sie zum Django-Admin-Panel",
            "Navigieren Sie zu SQL-Datenbanken",
            "Wählen Sie Ihre Datenbank ({db_name}) aus",
            "Wählen Sie \"Datenbankdokumentation generieren (KI-unterstützt)\" aus dem Aktions-Dropdown-Menü"
        ],
        "go_to_database_admin": "📊 Zur Datenbankadministration",
        "go_to_home": "📁 Zum Start",

        # Table headers
        "source_table": "Quelltabelle",
        "source_column": "Quellspalte",
        "target_table": "Zieltabelle",
        "target_column": "Zielspalte",
        "column_name": "Spaltenname",
        "data_type": "Datentyp",
        "description": "Beschreibung",
        "value_description": "Wertebeschreibung",
        "fk": "FS",

        # Generated metadata
        "generated_by": "Generiert am {timestamp} von Thoth AI",
    },

    "pt": {
        # Page titles and headers
        "page_title": "Documentação do Banco de Dados",
        "page_subtitle": "Documentação",
        "breadcrumb_thoth": "Thoth",
        "breadcrumb_documentation": "Documentação",

        # Main sections
        "database_scope": "Escopo do Banco de Dados",
        "tables_and_columns": "Tabelas e Colunas",
        "foreign_key_relationships": "Relacionamentos de Chave Estrangeira",
        "no_foreign_key_relationships": "Nenhum relacionamento de chave estrangeira definido neste banco de dados.",

        # Search functionality
        "search_placeholder": "Pesquisar na documentação...",
        "search_clear_title": "Limpar pesquisa",
        "search_results_none": "Nenhum resultado",
        "search_results_count": "{count} resultados",
        "search_results_current": "{current} de {total}",
        "search_help": "Pressione <kbd>Enter</kbd> para próximo, <kbd>Shift+Enter</kbd> para anterior, <kbd>Esc</kbd> para limpar",

        # Export functionality
        "export_pdf": "📄 Exportar PDF",

        # No documentation messages
        "no_documentation_available": "Documentação Não Disponível",
        "no_documentation_message": "Documentação não foi gerada ainda para o banco de dados '{db_name}'.",
        "no_database_selected": "Por favor selecione um workspace com um banco de dados para visualizar a documentação.",

        # Instructions for generating documentation
        "generate_instructions_title": "Para gerar documentação:",
        "generate_instructions": [
            "Vá ao painel de administração Django",
            "Navegue para Bancos de Dados SQL",
            "Selecione seu banco de dados ({db_name})",
            "Escolha \"Gerar documentação do banco de dados (assistida por IA)\" no menu suspenso de ações"
        ],
        "go_to_database_admin": "📊 Ir à Administração do Banco de Dados",
        "go_to_home": "📁 Ir para o Início",

        # Table headers
        "source_table": "Tabela Origem",
        "source_column": "Coluna Origem",
        "target_table": "Tabela Destino",
        "target_column": "Coluna Destino",
        "column_name": "Nome da Coluna",
        "data_type": "Tipo de Dado",
        "description": "Descrição",
        "value_description": "Descrição do Valor",
        "fk": "CE",

        # Generated metadata
        "generated_by": "Gerado em {timestamp} por Thoth AI",
    },
}


def get_translation(language: str, key: str, **kwargs) -> str:
    """
    Get translated text for a given key and language.

    Args:
        language: ISO 639-1 language code (e.g., 'en', 'it', 'es')
        key: Translation key to look up
        **kwargs: Format variables for the translation string

    Returns:
        Translated text, or English fallback if translation not available
    """
    # Default to English if language not specified or not available
    if not language or language not in DOCUMENTATION_TRANSLATIONS:
        language = "en"

    # Get the translation dictionary for the language
    translations = DOCUMENTATION_TRANSLATIONS.get(language, DOCUMENTATION_TRANSLATIONS["en"])

    # Get the translated text
    translated_text = translations.get(key, DOCUMENTATION_TRANSLATIONS["en"].get(key, key))

    # Format with provided kwargs
    try:
        return translated_text.format(**kwargs)
    except (KeyError, ValueError):
        # If formatting fails, return the unformatted text
        return translated_text


def get_translations_for_language(language: str) -> dict:
    """
    Get all translations for a specific language.

    Args:
        language: ISO 639-1 language code

    Returns:
        Dictionary of all translations for the language, with English fallback
    """
    # Default to English if language not available
    if not language or language not in DOCUMENTATION_TRANSLATIONS:
        language = "en"

    # Return translations for the language, with English as fallback
    return DOCUMENTATION_TRANSLATIONS.get(language, DOCUMENTATION_TRANSLATIONS["en"])
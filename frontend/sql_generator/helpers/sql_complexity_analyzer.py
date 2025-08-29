# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import sqlparse
from sqlparse.sql import Statement, Token, TokenList
from sqlparse.tokens import Keyword, Name

class SQLComplexityAnalyzer:
    def __init__(self):
        self.complexity_weights = {
            'tokens': 1,
            'joins': 5,
            'subqueries': 10,
            'where_conditions': 3,
            'group_by': 4,
            'order_by': 2,
            'having': 6,
            'functions': 2,
            'tables': 2,
            'nesting_depth': 8
        }
    
    def analyze_query(self, sql_query):
        """Analizza una query SQL e restituisce metriche di complessità"""
        parsed = sqlparse.parse(sql_query)[0]
        
        metrics = {
            'tokens': self._count_tokens(parsed),
            'joins': self._count_joins(parsed),
            'subqueries': self._count_subqueries(parsed),
            'where_conditions': self._count_where_conditions(parsed),
            'group_by': self._count_group_by(parsed),
            'order_by': self._count_order_by(parsed),
            'having': self._count_having(parsed),
            'functions': self._count_functions(parsed),
            'tables': self._count_tables(parsed),
            'nesting_depth': self._calculate_nesting_depth(parsed)
        }
        
        return metrics
    
    def calculate_complexity_score(self, metrics):
        """Calcola un punteggio di complessità basato sulle metriche"""
        score = 0
        for metric, value in metrics.items():
            if metric in self.complexity_weights:
                score += value * self.complexity_weights[metric]
        return score
    
    def _count_tokens(self, parsed):
        """Conta il numero totale di token significativi"""
        count = 0
        for token in parsed.flatten():
            if not token.is_whitespace and token.ttype is not sqlparse.tokens.Punctuation:
                count += 1
        return count
    
    def _count_joins(self, parsed):
        """Conta il numero di JOIN nella query"""
        count = 0
        for token in parsed.flatten():
            if token.ttype is Keyword and 'JOIN' in str(token).upper():
                count += 1
        return count
    
    def _count_subqueries(self, parsed):
        """Conta il numero di subquery"""
        count = 0
        def count_parenthesis(token_list):
            nonlocal count
            for token in token_list.tokens:
                if hasattr(token, 'tokens'):
                    if str(token).strip().upper().startswith('(SELECT'):
                        count += 1
                    count_parenthesis(token)
        
        count_parenthesis(parsed)
        return count
    
    def _count_where_conditions(self, parsed):
        """Conta le condizioni WHERE approssimative"""
        where_clause = None
        for token in parsed.tokens:
            if hasattr(token, 'tokens'):
                for subtoken in token.tokens:
                    if subtoken.ttype is Keyword and str(subtoken).upper() == 'WHERE':
                        where_clause = token
                        break
        
        if not where_clause:
            return 0
        
        # Conta AND/OR come indicatori di condizioni multiple
        conditions = 1  # Almeno una condizione se c'è WHERE
        for token in where_clause.flatten():
            if token.ttype is Keyword and str(token).upper() in ['AND', 'OR']:
                conditions += 1
        
        return conditions
    
    def _count_group_by(self, parsed):
        """Verifica la presenza di GROUP BY"""
        sql_str = str(parsed).upper()
        return 1 if 'GROUP BY' in sql_str else 0
    
    def _count_order_by(self, parsed):
        """Verifica la presenza di ORDER BY"""
        sql_str = str(parsed).upper()
        return 1 if 'ORDER BY' in sql_str else 0
    
    def _count_having(self, parsed):
        """Verifica la presenza di HAVING"""
        sql_str = str(parsed).upper()
        return 1 if 'HAVING' in sql_str else 0
    
    def _count_functions(self, parsed):
        """Conta il numero di funzioni SQL"""
        count = 0
        sql_functions = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'UPPER', 'LOWER', 'SUBSTRING', 'CONCAT']
        
        for token in parsed.flatten():
            if token.ttype is Name and str(token).upper() in sql_functions:
                count += 1
        
        return count
    
    def _count_tables(self, parsed):
        """Stima il numero di tabelle (approssimativo)"""
        # Questo è una stima semplificata
        from_found = False
        table_count = 0
        
        for token in parsed.flatten():
            if token.ttype is Keyword and str(token).upper() == 'FROM':
                from_found = True
            elif from_found and token.ttype is Name:
                table_count += 1
        
        return max(1, table_count)  # Almeno una tabella
    
    def _calculate_nesting_depth(self, parsed):
        """Calcola la profondità di annidamento"""
        max_depth = 0
        
        def calculate_depth(token_list, current_depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, current_depth)
            
            for token in token_list.tokens:
                if hasattr(token, 'tokens'):
                    if '(' in str(token):
                        calculate_depth(token, current_depth + 1)
                    else:
                        calculate_depth(token, current_depth)
        
        calculate_depth(parsed)
        return max_depth
    
    def compare_queries(self, query1, query2):
        """Confronta due query e determina quale è più semplice"""
        metrics1 = self.analyze_query(query1)
        metrics2 = self.analyze_query(query2)
        
        score1 = self.calculate_complexity_score(metrics1)
        score2 = self.calculate_complexity_score(metrics2)
        
        result = {
            'query1': {
                'metrics': metrics1,
                'complexity_score': score1
            },
            'query2': {
                'metrics': metrics2,
                'complexity_score': score2
            },
            'simpler_query': 1 if score1 < score2 else 2,
            'difference': abs(score1 - score2)
        }
        
        return result

# Esempio di utilizzo
if __name__ == "__main__":
    analyzer = SQLComplexityAnalyzer()
    
    # Query di esempio
    query1 = """
    SELECT name, age 
    FROM users 
    WHERE age > 18
    """
    
    query2 = """
    SELECT u.name, COUNT(o.id) as order_count, AVG(o.total)
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    WHERE u.age > 18 AND u.status = 'active'
    GROUP BY u.name, u.age
    HAVING COUNT(o.id) > 5
    ORDER BY order_count DESC
    """
    
    # Confronta le query
    result = analyzer.compare_queries(query1, query2)
    
    print("=== ANALISI COMPLESSITÀ SQL ===\n")
    
    print("Query 1 Metriche:")
    for metric, value in result['query1']['metrics'].items():
        print(f"  {metric}: {value}")
    print(f"  Punteggio complessità: {result['query1']['complexity_score']}\n")
    
    print("Query 2 Metriche:")
    for metric, value in result['query2']['metrics'].items():
        print(f"  {metric}: {value}")
    print(f"  Punteggio complessità: {result['query2']['complexity_score']}\n")
    
    print(f"Query più semplice: Query {result['simpler_query']}")
    print(f"Differenza di complessità: {result['difference']}")
// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

export interface GroupProfile {
  group_id: number;
  group_name: string;
  show_sql: boolean;
  explain_generated_query: boolean;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  groups: string[];
  group_profiles: GroupProfile[];
}

export interface LoginRequest {
  username: string;
  password: string;
  remember_me?: boolean;
}

export interface LoginResponse {
  token: string;
  user: User;
}

export interface AuthError {
  error: string;
  details?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

// Enhanced types to match backend structure
export interface SqlDb {
  name: string;
  db_host: string;
  db_type: 'PostgreSQL' | 'MySQL' | 'SQLite' | 'MariaDB' | 'Oracle' | 'SQLServer';
  db_name: string;
  db_port: number | null;
  schema: string;
  db_mode: 'dev' | 'test' | 'prod';
  language: string;
  vector_db?: VectorDb;
}

export interface VectorDb {
  name: string;
  vect_type: 'Qdrant' | 'ChromaDB' | 'Milvus' | 'PGVector';
  host: string;
  port: number | null;
  embedding_provider: 'openai' | 'cohere' | 'mistral' | 'huggingface' | 'anthropic';
  embedding_model: string;
  embedding_base_url?: string;
  embedding_batch_size: number;
  embedding_timeout: number;
  // New fields from backend
  embedding_configured: boolean;  // True if provider, model, and API key are all set
  has_api_key: boolean;  // True if API key exists (either in model or environment)
}

// Workspace related types
export interface Workspace {
  id: number;
  name: string;
  description?: string;
  level: 'BASIC' | 'ADVANCED' | 'EXPERT';
  sql_db: SqlDb;
  default_workspace: number[]; // Array of user IDs who have this as default
  treat_empty_result_as_error?: boolean;
}

// Sidebar flag types
export interface SidebarFlags {
  show_sql: boolean;
  explain_generated_query: boolean;
  treat_empty_result_as_error: boolean;
}

// SQL Generation Strategy
export type SqlGenerationStrategy = 'Basic' | 'Advanced' | 'Expert';

// Workspace API Response (full workspace data)
export interface WorkspaceApiResponse {
  [key: string]: Workspace;
}

// Simplified workspace for user list (only id and name)
export interface WorkspaceUserItem {
  id: number;
  name: string;
}

// User workspace list API response
export interface WorkspaceUserListResponse {
  [key: string]: WorkspaceUserItem;
}
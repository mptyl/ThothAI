// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useWorkspace } from '@/lib/contexts/workspace-context'
import { Loader2, Database, Server, Globe, Layers, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

export function WorkspaceDatabaseInfo() {
  const { fullWorkspaceData, isLoading } = useWorkspace()
  const [diagnosticData, setDiagnosticData] = useState<any>(null)
  const [isDiagnosing, setIsDiagnosing] = useState(false)
  const [vectorDbTestData, setVectorDbTestData] = useState<any>(null)
  const [isTestingVectorDb, setIsTestingVectorDb] = useState(false)

  // Debug logging for development
  useEffect(() => {
    if (fullWorkspaceData?.sql_db?.vector_db) {
      // Debug logging in development only
      if (process.env.NODE_ENV === 'development') {
        console.log('Vector DB Configuration:', {
          provider: fullWorkspaceData.sql_db.vector_db.embedding_provider,
          model: fullWorkspaceData.sql_db.vector_db.embedding_model,
          configured: fullWorkspaceData.sql_db.vector_db.embedding_configured,
          hasApiKey: fullWorkspaceData.sql_db.vector_db.has_api_key,
          connection: {
            type: fullWorkspaceData.sql_db.vector_db.vect_type,
            host: fullWorkspaceData.sql_db.vector_db.host,
            port: fullWorkspaceData.sql_db.vector_db.port,
            collection: fullWorkspaceData.sql_db.vector_db.name
          }
        });
      }
      
      // Warn about potential connection issues
      const host = fullWorkspaceData.sql_db.vector_db.host;
      if (host && host !== 'localhost' && host !== '127.0.0.1') {
        // Debug logging in development only
        if (process.env.NODE_ENV === 'development') {
          console.warn(
            `Warning: Vector DB is configured to connect to "${host}". ` +
            `If you see connection errors, this hostname might not be resolvable from your current environment. ` +
            `Consider using "localhost" for local development.`
          );
        }
      }
    }
  }, [fullWorkspaceData])

  // Test Vector DB Connection
  const testVectorDbConnection = async () => {
    if (!fullWorkspaceData?.id) return
    
    setIsTestingVectorDb(true)
    try {
      const baseUrl = process.env.NEXT_PUBLIC_DJANGO_SERVER || 'http://localhost:8200'
      const token = localStorage.getItem('thoth_token') || sessionStorage.getItem('thoth_token')
      
      const response = await fetch(`${baseUrl}/api/workspace/${fullWorkspaceData.id}/test-vector-db/`, {
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json'
        }
      })
      
      const data = await response.json()
      setVectorDbTestData(data)
      // Debug logging in development only
      if (process.env.NODE_ENV === 'development') {
        console.log('Vector DB Test Results:', data)
      }
    } catch (error) {
      console.error('Failed to test vector DB:', error)
      setVectorDbTestData({ error: 'Failed to connect to test endpoint' })
    } finally {
      setIsTestingVectorDb(false)
    }
  }

  // Diagnostic function
  const runDiagnostics = async () => {
    if (!fullWorkspaceData?.id) return
    
    setIsDiagnosing(true)
    try {
      const baseUrl = process.env.NEXT_PUBLIC_DJANGO_SERVER || 'http://localhost:8200'
      const token = localStorage.getItem('thoth_token') || sessionStorage.getItem('thoth_token')
      
      const response = await fetch(`${baseUrl}/api/workspace/${fullWorkspaceData.id}/check-embedding/`, {
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json'
        }
      })
      
      const data = await response.json()
      setDiagnosticData(data)
      // Debug logging in development only
      if (process.env.NODE_ENV === 'development') {
        console.log('Embedding Diagnostic Results:', data)
      }
    } catch (error) {
      console.error('Failed to run diagnostics:', error)
      setDiagnosticData({ error: 'Failed to connect to diagnostic endpoint' })
    } finally {
      setIsDiagnosing(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin" />
        <span className="ml-2">Loading workspace configuration...</span>
      </div>
    )
  }

  if (!fullWorkspaceData) {
    return (
      <Alert>
        <AlertDescription>
          No workspace selected. Please select a workspace from the sidebar.
        </AlertDescription>
      </Alert>
    )
  }

  const { name, description, level, sql_db } = fullWorkspaceData
  const vector_db = sql_db?.vector_db

  return (
    <div className="space-y-8">
      {/* Workspace Information */}
      <Card className="border-2 border-black bg-gray-900">
        <CardHeader className="pb-6">
          <CardTitle className="flex items-center gap-3 text-3xl font-bold">
            <Layers className="w-7 h-7 text-cyan-500" />
            Workspace Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 p-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Name</p>
              <p className="text-lg font-semibold">{name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Level</p>
              <Badge variant="secondary" className="mt-1">
                {level}
              </Badge>
            </div>
          </div>
          {description && (
            <div>
              <p className="text-sm font-medium text-muted-foreground">Description</p>
              <p className="text-sm mt-1">{description}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* SQL Database Information */}
      {sql_db && (
        <Card className="border-2 border-black bg-gray-900">
          <CardHeader className="pb-6">
            <CardTitle className="flex items-center gap-3 text-3xl font-bold">
              <Database className="w-7 h-7 text-cyan-500" />
              SQL Database
            </CardTitle>
          </CardHeader>
          <CardContent className="p-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Database Type</p>
                <p className="font-medium">{sql_db.db_type}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Database Name</p>
                <p className="font-medium">{sql_db.db_name}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Host</p>
                <p className="font-medium">{sql_db.db_host || 'localhost'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Port</p>
                <p className="font-medium">{sql_db.db_port || 'Default'}</p>
              </div>
              {sql_db.schema && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Schema</p>
                  <p className="font-medium">{sql_db.schema}</p>
                </div>
              )}
              <div>
                <p className="text-sm font-medium text-muted-foreground">Mode</p>
                <Badge variant={sql_db.db_mode === 'prod' ? 'destructive' : 'outline'} className="border-cyan-500/50">
                  {sql_db.db_mode}
                </Badge>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Language</p>
                <p className="font-medium">{sql_db.language || 'English'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Vector Database Information */}
      {vector_db ? (
        <Card className="border-2 border-black bg-gray-900">
          <CardHeader className="pb-6">
            <CardTitle className="flex items-center gap-3 text-3xl font-bold">
              <Server className="w-7 h-7 text-cyan-500" />
              Vector Database & Embedding Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="p-8">
            <div className="space-y-4">
              {/* Vector DB Connection */}
              <div>
                <h4 className="font-semibold text-xl mb-4 text-cyan-400">Vector Database</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Type</p>
                    <p className="font-medium">{vector_db.vect_type}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Collection/Index</p>
                    <p className="font-medium">{vector_db.name}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Host</p>
                    <p className="font-medium">{vector_db.host || 'localhost'}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Port</p>
                    <p className="font-medium">{vector_db.port || 'Default'}</p>
                  </div>
                </div>
              </div>

              {/* Embedding Configuration */}
              <div>
                <h4 className="font-semibold text-xl mb-4 flex items-center gap-2">
                  <span className="text-cyan-400">Embedding Configuration</span>
                  {vector_db.embedding_configured ? (
                    <Badge variant="outline" className="flex items-center gap-1 text-green-600 border-green-600/50">
                      <CheckCircle className="w-3 h-3" />
                      Configured
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="flex items-center gap-1 text-red-600 border-red-600/50">
                      <XCircle className="w-3 h-3" />
                      Not Configured
                    </Badge>
                  )}
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Provider</p>
                    <p className="font-medium capitalize">{vector_db.embedding_provider}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Model</p>
                    <p className="font-medium">{vector_db.embedding_model}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">API Key Status</p>
                    <div className="flex items-center gap-2">
                      {vector_db.has_api_key ? (
                        <>
                          <CheckCircle className="w-4 h-4 text-green-500" />
                          <span className="text-sm">Configured</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="w-4 h-4 text-red-500" />
                          <span className="text-sm">Missing</span>
                        </>
                      )}
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Batch Size</p>
                    <p className="font-medium">{vector_db.embedding_batch_size}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Timeout</p>
                    <p className="font-medium">{vector_db.embedding_timeout}s</p>
                  </div>
                </div>
                
                {!vector_db.embedding_configured && (
                  <Alert className="mt-4" variant="destructive">
                    <AlertCircle className="w-4 h-4" />
                    <AlertDescription>
                      Embedding configuration is incomplete. 
                      {!vector_db.has_api_key && 'API key is missing. '}
                      Please configure the API key in the Django admin or set the appropriate environment variable 
                      ({vector_db.embedding_provider.toUpperCase()}_API_KEY or EMBEDDING_API_KEY).
                    </AlertDescription>
                  </Alert>
                )}
                
                {/* Diagnostic Tools */}
                <div className="mt-4 space-y-4">
                  <div className="flex gap-2">
                    <Button 
                      onClick={testVectorDbConnection} 
                      disabled={isTestingVectorDb}
                      variant="outline"
                      className="flex-1 border-cyan-500/50 hover:bg-cyan-500/10"
                    >
                      {isTestingVectorDb ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin text-cyan-500" />
                          Testing Connection...
                        </>
                      ) : (
                        <span className="flex items-center justify-center gap-2">
                          Test Vector DB Connection
                        </span>
                      )}
                    </Button>
                    
                    <Button 
                      onClick={runDiagnostics} 
                      disabled={isDiagnosing}
                      variant="outline"
                      className="flex-1 border-cyan-500/50 hover:bg-cyan-500/10"
                    >
                      {isDiagnosing ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin text-cyan-500" />
                          Running Diagnostics...
                        </>
                      ) : (
                        <span className="flex items-center justify-center gap-2">
                          Run Embedding Diagnostics
                        </span>
                      )}
                    </Button>
                  </div>
                  
                  {vectorDbTestData && (
                    <Alert className={vectorDbTestData.error ? "border-red-500" : vectorDbTestData.connection_successful ? "border-green-500" : "border-yellow-500"}>
                      <AlertDescription>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 font-semibold">
                              {vectorDbTestData.error ? (
                                <>
                                  <XCircle className="w-4 h-4 text-red-500" />
                                  <span>Connection Test Failed</span>
                                </>
                              ) : vectorDbTestData.connection_successful ? (
                                <>
                                  <CheckCircle className="w-4 h-4 text-green-500" />
                                  <span>Vector DB Connected</span>
                                </>
                              ) : (
                                <>
                                  <AlertCircle className="w-4 h-4 text-yellow-500" />
                                  <span>Connection Issue</span>
                                </>
                              )}
                            </div>
                            <button
                              onClick={() => setVectorDbTestData(null)}
                              className="text-muted-foreground hover:text-foreground"
                              aria-label="Close"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          </div>
                          
                          {vectorDbTestData.connection_info && (
                            <div className="text-sm space-y-1">
                              <p><strong>Host:</strong> {vectorDbTestData.connection_info.host}</p>
                              <p><strong>Port:</strong> {vectorDbTestData.connection_info.port}</p>
                              {vectorDbTestData.connection_info.collections_count !== undefined && (
                                <p><strong>Collections:</strong> {vectorDbTestData.connection_info.collections_count}</p>
                              )}
                              {vectorDbTestData.connection_info.response_time_ms && (
                                <p><strong>Response Time:</strong> {vectorDbTestData.connection_info.response_time_ms}ms</p>
                              )}
                            </div>
                          )}
                          
                          {vectorDbTestData.error && (
                            <p className="text-red-600 text-sm">{vectorDbTestData.error}</p>
                          )}
                          
                          {vectorDbTestData.connection_info && (
                            <details className="mt-2">
                              <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
                                View Full Details
                              </summary>
                              <pre className="mt-2 text-xs overflow-auto bg-muted p-2 rounded">
                                {JSON.stringify(vectorDbTestData, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}
                  
                  {diagnosticData && (
                    <Alert className={diagnosticData.error ? "border-red-500" : diagnosticData.embedding_test?.test_successful ? "border-green-500" : "border-yellow-500"}>
                      <AlertDescription>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 font-semibold">
                              {diagnosticData.error ? (
                                <>
                                  <XCircle className="w-4 h-4 text-red-500" />
                                  <span>Diagnostic Failed</span>
                                </>
                              ) : diagnosticData.embedding_test?.test_successful ? (
                                <>
                                  <CheckCircle className="w-4 h-4 text-green-500" />
                                  <span>Embedding Test Successful</span>
                                </>
                              ) : (
                                <>
                                  <AlertCircle className="w-4 h-4 text-yellow-500" />
                                  <span>Embedding Test Failed</span>
                                </>
                              )}
                            </div>
                            <button
                              onClick={() => setDiagnosticData(null)}
                              className="text-muted-foreground hover:text-foreground"
                              aria-label="Close"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          </div>
                          
                          {diagnosticData.embedding_test && (
                            <div className="text-sm space-y-1">
                              <p><strong>Test Text:</strong> &quot;{diagnosticData.embedding_test.test_text}&quot;</p>
                              {diagnosticData.embedding_test.test_successful && (
                                <>
                                  {diagnosticData.embedding_test.embedding_dimension && (
                                    <p><strong>Embedding Dimension:</strong> {diagnosticData.embedding_test.embedding_dimension}</p>
                                  )}
                                  {diagnosticData.embedding_test.embedding_time_ms && (
                                    <p><strong>Embedding Time:</strong> {diagnosticData.embedding_test.embedding_time_ms}ms</p>
                                  )}
                                </>
                              )}
                              {diagnosticData.embedding_test.test_error && (
                                <p className="text-red-600"><strong>Error:</strong> {diagnosticData.embedding_test.test_error}</p>
                              )}
                            </div>
                          )}
                          
                          {diagnosticData.vector_db && (
                            <details className="mt-2">
                              <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
                                View Full Configuration Details
                              </summary>
                              <pre className="mt-2 text-xs overflow-auto bg-muted p-2 rounded">
                                {JSON.stringify(diagnosticData, null, 2)}
                              </pre>
                            </details>
                          )}
                          
                          {diagnosticData.error && (
                            <p className="text-red-600 text-sm">{diagnosticData.error}</p>
                          )}
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-2 border-black bg-gray-900">
          <CardHeader className="pb-6">
            <CardTitle className="flex items-center gap-3 text-3xl font-bold">
              <Server className="w-7 h-7 text-cyan-500" />
              Vector Database
            </CardTitle>
          </CardHeader>
          <CardContent className="p-8">
            <p className="text-muted-foreground text-lg">
              No vector database configured for this workspace.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Configuration Note */}
      <Alert className="border-cyan-500/30 bg-cyan-500/5">
        <AlertDescription className="text-base">
          <span className="flex items-start gap-2">
            <span>
              Database and embedding configurations are managed at the workspace level through the Django admin interface. 
              Contact your administrator to modify these settings.
            </span>
          </span>
        </AlertDescription>
      </Alert>
    </div>
  )
}
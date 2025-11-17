// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ExternalLink, BookOpen, Terminal, Package, Bot, FlaskConical, CheckCircle2, Cpu, LogOut, AlertCircle, Key } from 'lucide-react';
import { ThemeToggle } from '@/components/theme-toggle';
import { useAuth } from '@/lib/auth-context';

export default function DocumentationPage() {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border px-6 py-4 bg-background/80 backdrop-blur-sm">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <BookOpen className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">Documentation</h1>
              <p className="text-sm text-muted-foreground">Setup guide and architecture overview</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-foreground mr-2">
              {user?.first_name} {user?.last_name}
            </span>
            <ThemeToggle />
            <Button 
              variant="ghost" 
              onClick={handleLogout}
              className="flex items-center gap-2 px-3"
              title="Logout from ThothAI"
            >
              <LogOut className="h-5 w-5" />
              <span className="hidden sm:inline text-sm">Logout</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="w-full px-8 py-8">
          
          {/* Page Title with Thoth Image */}
          <div className="flex items-center gap-4 mb-8">
            <img 
              src="/dio-thoth-dx.png" 
              alt="ThothAI Dio" 
              className="h-18 w-18 object-contain dark:brightness-110"
              style={{ 
                height: '72px',
                width: '72px',
                filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))'
              }}
            />
            <h1 className="text-5xl font-bold text-foreground">
              Documentation
            </h1>
          </div>
          
          {/* Full Documentation Link */}
          <Card className="mb-8 border-primary/50 bg-primary/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-2xl font-bold">
                <BookOpen className="h-6 w-6" />
                Complete Documentation
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-lg">
                For comprehensive documentation including API reference, advanced configuration, and detailed tutorials, visit:
              </p>
              <Link href="https://mptyl.github.io/ThothDocs/" target="_blank" rel="noopener noreferrer">
                <Button className="gap-2" size="lg">
                  <ExternalLink className="h-4 w-4" />
                  View Full Documentation
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* System Requirements */}
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-2xl font-bold">
                <Terminal className="h-6 w-6" />
                System Requirements
              </CardTitle>
              <CardDescription>
                Software prerequisites for running ThothAI
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <h3 className="font-semibold text-lg">Required Software</h3>
                <ul className="space-y-2 ml-6">
                  <li className="flex items-start">
                    <CheckCircle2 className="h-4 w-4 mr-2 mt-0.5 text-green-500" />
                    <span><strong>Python 3.13+</strong> - Core runtime environment</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircle2 className="h-4 w-4 mr-2 mt-0.5 text-green-500" />
                    <span><strong>Docker & Docker Compose</strong> - Container orchestration</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircle2 className="h-4 w-4 mr-2 mt-0.5 text-green-500" />
                    <span><strong>Git</strong> - Version control system</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircle2 className="h-4 w-4 mr-2 mt-0.5 text-green-500" />
                    <span><strong>Node.js 18+</strong> - Frontend runtime (optional for development)</span>
                  </li>
                </ul>
              </div>

              <div className="space-y-3 pt-2">
                <h3 className="font-semibold text-lg">Required API Keys</h3>
                <ul className="space-y-2 ml-6">
                  <li className="flex items-start">
                    <Key className="h-4 w-4 mr-2 mt-0.5 text-green-500" />
                    <span><strong>LLM API Key</strong> - At least one provider (OpenAI, Anthropic, Gemini, Mistral, DeepSeek, etc.)</span>
                  </li>
                  <li className="flex items-start">
                    <Key className="h-4 w-4 mr-2 mt-0.5 text-green-500" />
                    <span><strong>Embedding API Key</strong> - Required for vector search (OpenAI, Mistral, or Cohere)</span>
                  </li>
                </ul>
              </div>

              <div className="space-y-3 pt-2">
                <h3 className="font-semibold text-lg">Optional API Keys</h3>
                <ul className="space-y-2 ml-6">
                  <li className="flex items-start">
                    <Key className="h-4 w-4 mr-2 mt-0.5 text-yellow-500" />
                    <span><strong>Logfire API Key</strong> - For advanced monitoring and observability (optional)</span>
                  </li>
                </ul>
              </div>

              <div className="space-y-3 pt-2">
                <h3 className="font-semibold text-lg">Recommended Resources</h3>
                <ul className="space-y-2 ml-6">
                  <li className="flex items-start">
                    <span className="text-primary mr-2">•</span>
                    <span><strong>RAM:</strong> 8GB minimum, 16GB recommended</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-primary mr-2">•</span>
                    <span><strong>Storage:</strong> 10GB for Docker images and data</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-primary mr-2">•</span>
                    <span><strong>CPU:</strong> 4 cores minimum for optimal performance</span>
                  </li>
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Installation Guide */}
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-2xl font-bold">
                <Package className="h-6 w-6" />
                Essential Installation
              </CardTitle>
              <CardDescription>
                Quick setup guide using Docker
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Alert for configuration documentation */}
              <Alert className="border-yellow-500/50 bg-yellow-500/10">
                <AlertCircle className="h-4 w-4 text-yellow-500" />
                <AlertTitle>Important Configuration Notice</AlertTitle>
                <AlertDescription className="mt-2">
                  <p className="mb-3">
                    Before proceeding with the installation, please review the official documentation to understand 
                    how to properly configure the <code className="px-1 py-0.5 bg-muted rounded">config.yml.local</code> file 
                    with all necessary elements for successful application activation.
                  </p>
                  <Link href="https://mptyl.github.io/ThothDocs/" target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" size="sm" className="gap-2">
                      <ExternalLink className="h-3 w-3" />
                      View Configuration Guide
                    </Button>
                  </Link>
                </AlertDescription>
              </Alert>

              <div className="space-y-4">
                <h3 className="font-semibold text-lg">1. Clone the Repository</h3>
                <div className="bg-muted rounded-lg p-4">
                  <pre className="text-sm font-mono">
{`git clone https://github.com/mptyl/ThothAI.git
cd ThothAI`}
                  </pre>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="font-semibold text-lg">2. Configure the Application</h3>
                <div className="bg-muted rounded-lg p-4">
                  <pre className="text-sm font-mono">
{`cp config.yml config.yml.local
# Edit config.yml.local with your settings:`}
                  </pre>
                </div>
                <ul className="space-y-2 ml-6 text-sm">
                  <li className="flex items-start">
                    <span className="text-primary mr-2">•</span>
                    <span>Configure AI provider API keys (OpenAI, Anthropic, etc.)</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-primary mr-2">•</span>
                    <span>Set embedding service (OpenAI, Mistral, or Cohere)</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-primary mr-2">•</span>
                    <span>Enable database drivers (PostgreSQL, MySQL, etc.)</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-primary mr-2">•</span>
                    <span>Configure admin credentials and ports</span>
                  </li>
                </ul>
              </div>

              <div className="space-y-4">
                <h3 className="font-semibold text-lg">3. Start with Docker Compose</h3>
                <div className="bg-muted rounded-lg p-4">
                  <pre className="text-sm font-mono">
{`docker-compose up --build`}
                  </pre>
                </div>
                <p className="text-sm text-muted-foreground">
                  The application will be available at <code className="px-1 py-0.5 bg-muted rounded">http://localhost</code>
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Agent Architecture */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-2xl font-bold">
                <Bot className="h-6 w-6" />
                Multi-Agent Architecture
              </CardTitle>
              <CardDescription>
                Specialized AI agents working in concert for optimal SQL generation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <p className="leading-relaxed">
                ThothAI employs a sophisticated multi-agent system powered by PydanticAI, where each agent specializes in a specific aspect of the SQL generation pipeline. This architecture ensures high-quality, validated, and optimized SQL queries.
              </p>

              <div className="space-y-4">
                <div className="border-l-4 border-primary pl-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <Cpu className="h-5 w-5 text-primary" />
                    <h3 className="font-semibold text-lg">SQL Generator Agent</h3>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    The primary agent responsible for interpreting natural language queries and generating multiple SQL query candidates. It leverages schema information, historical examples, and semantic understanding to produce syntactically correct SQL.
                  </p>
                </div>

                <div className="border-l-4 border-blue-500 pl-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <FlaskConical className="h-5 w-5 text-blue-500" />
                    <h3 className="font-semibold text-lg">Test Generator Agent</h3>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Creates comprehensive test cases for each generated SQL query, including edge cases, boundary conditions, and expected result patterns. This ensures queries are robust and handle various data scenarios correctly.
                  </p>
                </div>

                <div className="border-l-4 border-green-500 pl-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    <h3 className="font-semibold text-lg">Evaluator Agent</h3>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Validates generated SQL queries against the test suite, checking for syntax errors, semantic correctness, and performance implications. It ensures queries meet quality standards before execution.
                  </p>
                </div>

                <div className="border-l-4 border-purple-500 pl-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <Bot className="h-5 w-5 text-purple-500" />
                    <h3 className="font-semibold text-lg">Selector Agent</h3>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Analyzes all validated SQL candidates and selects the optimal query based on multiple criteria: accuracy, performance, simplicity, and alignment with user intent. This agent ensures the best possible SQL is executed.
                  </p>
                </div>
              </div>

              <div className="mt-6 p-4 bg-muted rounded-lg">
                <h4 className="font-semibold mb-2">Agent Workflow</h4>
                <ol className="space-y-2 text-sm">
                  <li className="flex items-start">
                    <span className="font-semibold text-primary mr-2">1.</span>
                    <span><strong>SQL Generation:</strong> Multiple candidate queries are generated based on the natural language input</span>
                  </li>
                  <li className="flex items-start">
                    <span className="font-semibold text-primary mr-2">2.</span>
                    <span><strong>Test Creation:</strong> Comprehensive test suites are generated for each SQL candidate</span>
                  </li>
                  <li className="flex items-start">
                    <span className="font-semibold text-primary mr-2">3.</span>
                    <span><strong>Validation:</strong> Each query is evaluated against its test suite and quality criteria</span>
                  </li>
                  <li className="flex items-start">
                    <span className="font-semibold text-primary mr-2">4.</span>
                    <span><strong>Selection:</strong> The best-performing query that passes all tests is selected for execution</span>
                  </li>
                </ol>
              </div>

              <div className="flex gap-2 mt-6">
                <Badge variant="secondary">PydanticAI</Badge>
                <Badge variant="secondary">Multi-Agent System</Badge>
                <Badge variant="secondary">Test-Driven Validation</Badge>
                <Badge variant="secondary">Performance Optimization</Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
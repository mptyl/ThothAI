// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ExternalLink, Database, Brain, Code2, Users, Mail, Linkedin, Info, LogOut, Key } from 'lucide-react';
import { ThemeToggle } from '@/components/theme-toggle';
import { useAuth } from '@/lib/auth-context';
import { LogoutConfirmationDialog } from '@/components/logout-confirmation-dialog';

export default function AboutPage() {
  const { user, logout, isLoading } = useAuth();
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);

  const handleLogoutClick = () => {
    setShowLogoutDialog(true);
  };

  const handleConfirmLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header - same style as chat page */}
      <div className="border-b border-border px-6 py-4 bg-background/80 backdrop-blur-sm">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Info className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">About ThothAI</h1>
              <p className="text-sm text-muted-foreground">Learn more about our platform</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-foreground mr-2">
              {user?.first_name} {user?.last_name}
            </span>
            <ThemeToggle />
            <Button
              variant="ghost"
              onClick={handleLogoutClick}
              className="flex items-center gap-2 px-3"
              title="Logout from ThothAI"
            >
              <LogOut className="h-5 w-5" />
              <span className="hidden sm:inline text-sm">Logout</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Content Area with scrolling */}
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
          About ThothAI
        </h1>
      </div>
      
      {/* Purpose Section */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-2xl font-bold">
            <Brain className="h-6 w-6" />
            Purpose & Vision
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-lg leading-relaxed">
            ThothAI is an innovative AI-powered platform that introduces a user-friendly approach to database querying. It is based on the latest research in text-to-SQL using Large Language Models (LLMs). Named after Thoth, the ancient Egyptian deity of wisdom and knowledge, our platform bridges the gap between human language and SQL, making data access intuitive and accessible.
          </p>
          <div className="space-y-3">
            <h3 className="font-semibold text-lg">Key Objectives:</h3>
            <ul className="space-y-2 ml-6">
              <li className="flex items-start">
                <span className="text-primary mr-2">•</span>
                <span>Transform simple conversational questions into complex SQL queries</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary mr-2">•</span>
                <span>Enable non-technical users to extract insights from databases without SQL knowledge</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary mr-2">•</span>
                <span>Accelerate data analysis workflows with intelligent query generation and validation</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary mr-2">•</span>
                <span>Provide enterprise-grade security and multi-database support</span>
              </li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Prerequisites Section */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-2xl font-bold">
            <Key className="h-6 w-6" />
            Prerequisites
          </CardTitle>
          <CardDescription>
            Essential requirements for running ThothAI
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <h3 className="font-semibold text-lg">Required API Keys</h3>
            <ul className="space-y-2 ml-6">
              <li className="flex items-start">
                <Key className="h-4 w-4 mr-2 mt-0.5 text-green-500" />
                <span><strong>LLM API Key:</strong> At least one provider is required (OpenAI, Anthropic, Gemini, Mistral, DeepSeek, OpenRouter, Ollama, or LM Studio)</span>
              </li>
              <li className="flex items-start">
                <Key className="h-4 w-4 mr-2 mt-0.5 text-green-500" />
                <span><strong>Embedding API Key:</strong> Required for vector search functionality (OpenAI, Mistral, or Cohere)</span>
              </li>
            </ul>
          </div>
          
          <div className="space-y-3 pt-2">
            <h3 className="font-semibold text-lg">Optional API Keys</h3>
            <ul className="space-y-2 ml-6">
              <li className="flex items-start">
                <Key className="h-4 w-4 mr-2 mt-0.5 text-yellow-500" />
                <span><strong>Logfire API Key:</strong> For advanced monitoring, observability, and performance tracking</span>
              </li>
            </ul>
          </div>
          
          <div className="mt-4 p-4 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">
              These API keys are configured in the <code className="px-1 py-0.5 bg-background rounded">config.yml.local</code> file. 
              ThothAI supports multiple providers simultaneously, allowing you to choose the best model for each task or implement fallback strategies.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Technologies Section */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-2xl font-bold">
            <Code2 className="h-6 w-6" />
            Technologies & Architecture
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div>
            <h3 className="font-semibold mb-3">Core Technologies</h3>
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">Python</Badge>
              <Badge variant="secondary">TypeScript</Badge>
              <Badge variant="secondary">Django</Badge>
              <Badge variant="secondary">Next.js</Badge>
              <Badge variant="secondary">FastAPI</Badge>
              <Badge variant="secondary">Docker</Badge>
              <Badge variant="secondary">LiteLLM</Badge>
              <Badge variant="secondary">PydanticAI</Badge>
              <Badge variant="secondary">Qdrant Vector DB</Badge>
            </div>
          </div>
          
          <div className="mt-6 space-y-4">
            <h3 className="font-semibold">Architecture Highlights</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <Database className="h-4 w-4 mr-2 mt-0.5 text-primary" />
                <span><strong>Multi-Database Support:</strong> PostgreSQL, MySQL, MariaDB, SQL Server, SQLite</span>
              </li>
              <li className="flex items-start">
                <Brain className="h-4 w-4 mr-2 mt-0.5 text-primary" />
                <span><strong>Multi-Agent System:</strong> Specialized AI agents for SQL generation, validation, and optimization</span>
              </li>
              <li className="flex items-start">
                <Code2 className="h-4 w-4 mr-2 mt-0.5 text-primary" />
                <span><strong>Vector Search:</strong> Semantic similarity matching for improved query accuracy</span>
              </li>
              <li className="flex items-start">
                <Users className="h-4 w-4 mr-2 mt-0.5 text-primary" />
                <span><strong>Enterprise Features:</strong> Multi-workspace support, role-based access, audit logging</span>
              </li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Author Section */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-2xl font-bold">
            <Users className="h-6 w-6" />
            About the Author
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <h3 className="text-xl font-semibold mb-2">Marco Pancotti</h3>
              <p className="text-muted-foreground mb-4">Founder & Lead Developer</p>
            </div>
            
            <div className="space-y-3">
              <p className="leading-relaxed">
                Marco Pancotti is a seasoned software engineer with extensive experience in building enterprise-grade data-driven applications. Over the past two years, he has dedicated himself to exploring and mastering the use of AI and Large Language Models (LLMs) in business applications, bringing innovative solutions to complex data challenges.
              </p>
              
              <p className="leading-relaxed">
                With deep knowledge of various enterprise frameworks and technologies, Marco chose Python, Django, and FastAPI for ThothAI due to their simplicity, immediacy, and seamless integration with the typical AI stack of libraries and services. His expertise spans database architecture, system design, and the practical implementation of AI solutions in production environments.
              </p>
              
              <p className="leading-relaxed">
                Marco is passionate about using natural language as the primary interface for data access, eliminating the traditional barriers between users and their data. Through ThothAI, he aims to empower organizations and individuals to interact with their databases through simple conversation, making data insights accessible to everyone regardless of technical expertise.
              </p>
            </div>

            <div className="pt-4">
              <Link href="https://www.linkedin.com/in/marcopancotti/" target="_blank" rel="noopener noreferrer">
                <Button variant="outline" className="gap-2">
                  <Linkedin className="h-4 w-4" />
                  View Full Profile on LinkedIn
                  <ExternalLink className="h-3 w-3" />
                </Button>
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Academic Citation Section */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-2xl font-bold">
            <Code2 className="h-6 w-6" />
            Academic Reference
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="leading-relaxed">
              ThothAI&apos;s text-to-SQL methodology is inspired by the CHESS framework:
            </p>
            
            <div className="bg-muted rounded-lg p-4">
              <pre className="text-sm font-mono whitespace-pre-wrap break-words">
{`@article{talaei2024chess,
  title={CHESS: Contextual Harnessing for Efficient SQL Synthesis},
  author={Talaei, Shayan and Pourreza, Mohammadreza and Chang, Yu-Chen and Mirhoseini, Azalia and Saberi, Amin},
  journal={arXiv preprint arXiv:2405.16755},
  year={2024}
}`}
              </pre>
            </div>
            
            <div className="flex items-center gap-2">
              <Link href="https://arxiv.org/abs/2405.16755" target="_blank" rel="noopener noreferrer">
                <Button variant="outline" className="gap-2">
                  <ExternalLink className="h-4 w-4" />
                  View Paper on arXiv
                </Button>
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Contact Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-2xl font-bold">
            <Mail className="h-6 w-6" />
            Contact Us
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="leading-relaxed">
              We&apos;d love to hear from you! Whether you have questions about ThothAI, need technical support, 
              or are interested in collaboration opportunities, please don&apos;t hesitate to reach out.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4">
              <Link href="https://www.linkedin.com/in/marcopancotti/" target="_blank" rel="noopener noreferrer">
                <Button className="gap-2 w-full sm:w-auto">
                  <Linkedin className="h-4 w-4" />
                  Connect on LinkedIn
                  <ExternalLink className="h-3 w-3" />
                </Button>
              </Link>
            </div>
            
            <div className="mt-6 p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">
                For business inquiries, technical support, or partnership opportunities, 
                please connect with Marco Pancotti on LinkedIn. We typically respond within 24-48 hours.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
        </div>
      </div>

      {/* Logout Confirmation Dialog */}
      <LogoutConfirmationDialog
        open={showLogoutDialog}
        onOpenChange={setShowLogoutDialog}
        onConfirm={handleConfirmLogout}
        isLoggingOut={isLoading}
      />
    </div>
  );
}
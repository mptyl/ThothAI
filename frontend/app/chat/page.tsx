// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React, { useState, useEffect } from 'react';
import DOMPurify from 'dompurify';
import { Send, Sparkles, Loader2, LogOut, Bot, User, Database, Code2, Brain, Zap, UserCircle, Crown } from 'lucide-react';
import { ThemeToggle } from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth-context';
import { LogoutConfirmationDialog } from '@/components/logout-confirmation-dialog';
import { useWorkspace } from '@/lib/contexts/workspace-context';
import { useSidebar } from '@/lib/contexts/sidebar-context';
import { sqlGeneratorApi, GenerateSQLResponse } from '@/lib/sql-generator-api';
import { DataTable } from '@/components/DataTable';
import { PaginatedDataTable } from '@/components/PaginatedDataTable';
import { LikeButton } from '@/components/like-button';
import { OutputBlock } from '@/components/OutputBlock';

// Message types for the conversation
interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  sqlResponse?: GenerateSQLResponse;
  isProcessing?: boolean;
  queryResults?: any[];
  queryError?: string;
  isExecutingQuery?: boolean;
  sqlReady?: {
    sql: string;
    workspace_id: number;
    timestamp?: string;
    username?: string;
    agent?: string;
  };
  formattedSql?: string;  // SQL formattato salvato sempre
  sqlExplanation?: {
    text: string;
    language: string;
  };
  explanationReady?: boolean;
  tableDataLoaded?: boolean;
  // Fields needed for on-demand explanation generation
  generatedSql?: string;
  originalQuestion?: string;
  usedSchema?: string;
  evidence?: string[];
  chainOfThought?: string;
  // Critical error handling
  criticalError?: {
    type: string;
    component?: string;
    message: string;
    impact?: string;
    action?: string;
  };
}

// Function to convert markdown-style formatting to HTML
function markdownToHtml(text: string): string {
  if (!text) return '';
  
  // High-level section headers that indicate major sections
  const highLevelHeaders = [
    'Data Selection',
    'Filters Applied',
    'Grouping and Aggregation',
    'Sorting and Ordering',
    'Limiting Results',
    'Overall Result',
    'Selezione dei Dati',
    'Filtri Applicati',
    'Raggruppamento e Aggregazione',
    'Ordinamento',
    'Limitazione dei Risultati',
    'Risultato Complessivo'
  ];
  
  // Check if a line starts with a high-level header
  const isHighLevelHeader = (line: string): boolean => {
    const trimmed = line.trim();
    return highLevelHeaders.some(header => 
      trimmed.startsWith(`**${header}`) || 
      trimmed.startsWith(header)
    );
  };
  
  // Split text into lines for processing
  const lines = text.split('\n');
  let html = '';
  let inList = false;
  let inSubSection = false;
  
  lines.forEach((line, index) => {
    // Convert **bold** to <strong>
    line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // Check if this is a high-level header
    if (isHighLevelHeader(line)) {
      // Close any open list
      if (inList) {
        html += '</ul>';
        inList = false;
      }
      // Add the header as a paragraph with emphasis
      html += `<p class="mb-2 font-semibold">${line}</p>`;
      inSubSection = true;
      // Start a new list for the sub-items that will follow
      html += '<ul class="list-disc pl-5 space-y-1">';
      inList = true;
    }
    // Check if line is a list item (starts with - or •)
    else if (line.trim().startsWith('-') || line.trim().startsWith('•')) {
      if (!inList) {
        html += '<ul class="list-disc pl-5 space-y-1">';
        inList = true;
      }
      // Remove the bullet point and add as list item
      const content = line.replace(/^[\s-•]+/, '').trim();
      html += `<li>${content}</li>`;
    } 
    // Empty line
    else if (line.trim() === '') {
      // Don't close the list on empty lines within sections
      if (!inSubSection && inList) {
        html += '</ul>';
        inList = false;
      }
      // Add spacing
      if (!inList) {
        html += '<br/>';
      }
    } 
    // Regular text that's not a bullet point
    else {
      // If we're in a subsection and this line doesn't start with a bullet,
      // treat it as a continuation or sub-item
      if (inSubSection && line.trim() && !line.trim().startsWith('-') && !line.trim().startsWith('•')) {
        // Check if next line is a high-level header to close current section
        const nextLine = lines[index + 1];
        if (nextLine && isHighLevelHeader(nextLine)) {
          // Add as list item before closing
          html += `<li>${line.trim()}</li>`;
          html += '</ul>';
          inList = false;
          inSubSection = false;
        } else {
          // Add as a list item if it's part of the section
          html += `<li>${line.trim()}</li>`;
        }
      } else {
        // Close list if we were in one
        if (inList) {
          html += '</ul>';
          inList = false;
          inSubSection = false;
        }
        // Regular paragraph
        if (line.trim()) {
          html += `<p class="mb-2">${line}</p>`;
        }
      }
    }
  });
  
  // Close list if still open
  if (inList) {
    html += '</ul>';
  }
  
  // Sanitize HTML to prevent XSS attacks
  return DOMPurify.sanitize(html);
}

export default function ChatPage() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [thothaiLogMessage, setThothLogMessage] = useState('');
  const [isLogBlinking, setIsLogBlinking] = useState(false);
  const [likeButtonEnabled, setLikeButtonEnabled] = useState(false);
  const { user, logout, isLoading } = useAuth();
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);
  const { selectedWorkspace } = useWorkspace();
  const { flags, strategy, setOperationInProgress } = useSidebar();
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  
  // Force re-render when flags change to show/hide SQL and explanations
  const [, forceUpdate] = React.useReducer(x => x + 1, 0);
  const prevExplainFlagRef = React.useRef(flags.explain_generated_query);

  const generateExplanationOnDemand = React.useCallback(async (message: Message) => {
    if (!selectedWorkspace || !message.generatedSql) {
      console.error('Cannot generate explanation: missing workspace or SQL');
      return;
    }

    try {
      // Prepare the request data for the explain-sql endpoint
      const requestData = {
        workspace_id: selectedWorkspace.id,
        question: message.originalQuestion || message.content,
        generated_sql: message.generatedSql,
        database_schema: message.usedSchema || '',
        evidence: message.evidence || [],
        chain_of_thought: message.chainOfThought || '',
        language: 'English',
        username: user?.username || 'anonymous'
      };

      const response = await fetch('/api/sql-proxy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...requestData,
          endpoint: '/explain-sql'
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to generate explanation: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success && data.explanation) {
        // Update the message with the generated explanation
        setMessages(prev => prev.map(m => 
          m.id === message.id 
            ? {
                ...m,
                sqlExplanation: {
                  text: data.explanation,
                  language: data.language || 'English'
                },
                explanationReady: true
              }
            : m
        ));
      } else {
        console.error('Failed to generate explanation:', data.error);
      }
    } catch (error) {
      console.error('Error generating explanation on demand:', error);
    }
  }, [selectedWorkspace, user]);

  // React effects that depend on generateExplanationOnDemand
  React.useEffect(() => {
    // Trigger re-render when show_sql or explain_generated_query flags change
    forceUpdate();
  }, [flags.show_sql, flags.explain_generated_query]);
  
  // Separate effect for handling on-demand explanation generation
  React.useEffect(() => {
    // Check if explain_generated_query was just turned ON (was false, now true)
    if (!prevExplainFlagRef.current && flags.explain_generated_query) {
      // Check if we have a generated SQL but no explanation yet
      const lastMessage = messages[messages.length - 1];
      if (lastMessage?.type === 'assistant' && 
          lastMessage.sqlReady && 
          lastMessage.generatedSql && 
          (!lastMessage.sqlExplanation || !lastMessage.sqlExplanation.text)) {
        // Call the explain-sql endpoint to generate explanation on-demand
        generateExplanationOnDemand(lastMessage);
      }
    }
    
    prevExplainFlagRef.current = flags.explain_generated_query;
  }, [flags.explain_generated_query, generateExplanationOnDemand, messages]);

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Listen for app-reset event from RESET button
  useEffect(() => {
    const handleAppReset = () => {
      // Debug logging in development only
      if (process.env.NODE_ENV === 'development') {
        console.log('[ChatPage] Received app-reset event, clearing messages');
      }
      // Clear all messages except the initial welcome message
      setMessages([{
        id: '1',
        type: 'system',
        content: 'Welcome to ThothAI SQL Assistant! Ask me anything about your data.',
        timestamp: new Date()
      }]);
      // Clear any processing state
      setIsProcessing(false);
      setIsLogBlinking(false);
      setThothLogMessage('');
      // Clear input
      setMessage('');
      // Disable Like button
      setLikeButtonEnabled(false);
    };

    window.addEventListener('app-reset', handleAppReset);
    
    return () => {
      window.removeEventListener('app-reset', handleAppReset);
    };
  }, []);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanMessage = message.trim();
    
    // Check if workspace is selected
    if (!selectedWorkspace || !selectedWorkspace.id) {
      // Add error message to chat
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: 'system',
        content: '',
        timestamp: new Date(),
        criticalError: {
          type: 'workspace_required',
          message: 'No workspace selected',
          impact: 'Cannot generate SQL without selecting a workspace',
          action: 'Please select a workspace from the sidebar before submitting your question'
        }
      };
      setMessages(prev => [...prev, errorMessage]);
      return;
    }
    
    if (cleanMessage && !isProcessing) {
      setIsProcessing(true);
      
      // Track the operation in sidebar context
      const operationId = `sql-gen-${Date.now()}`;
      setOperationInProgress(true, operationId);
      
      // Clear all previous messages completely before processing new question
      setMessages([]);
      
      // Initialize logs and start blinking
      setThothLogMessage('');
      setIsLogBlinking(true);
      
      // Disable Like button when starting new query
      setLikeButtonEnabled(false);
      
      // Add user message to chat
      const userMessage: Message = {
        id: Date.now().toString(),
        type: 'user',
        content: cleanMessage,
        timestamp: new Date()
      };
      
      setMessages([userMessage]);
      setMessage('');
      
      // Reset textarea height after clearing message
      const textarea = e.currentTarget.querySelector('textarea');
      if (textarea) {
        textarea.style.height = 'auto';
      }
      
      try {
        // Create streaming message placeholder
        const streamingMessageId = (Date.now() + 1).toString();
        const streamingMessage: Message = {
          id: streamingMessageId,
          type: 'assistant',
          content: '',
          timestamp: new Date(),
          isProcessing: true
        };
        
        setMessages(prev => [...prev, streamingMessage]);
        
        let accumulatedContent = '';
        const collectedLogs: Array<{timestamp: string, message: string}> = [];
        
        // Call SQL Generator API with streaming support
        await sqlGeneratorApi.generateSQLStream(
          {
            question: cleanMessage,
            workspace_id: selectedWorkspace?.id || 0,
            functionality_level: strategy,
            flags: flags
          },
          user?.username, // Pass the username from auth context
          (chunk: string) => {
            // Check if chunk contains THOTHLOG
            const lines = chunk.split('\n');
            let filteredChunk = '';
            
            for (const line of lines) {
              if (line.startsWith('THOTHLOG:')) {
                // Extract log message
                const logContent = line.substring(9).trim(); // Remove 'THOTHLOG:' prefix
                const logEntry = {
                  timestamp: new Date().toISOString(),
                  message: logContent
                };
                
                // Update current log display
                setThothLogMessage(logContent);
                
                // Add to logs list
                collectedLogs.push(logEntry);
                
              } else if (line.startsWith('SQL_FORMATTED:')) {
                // Extract formatted SQL from backend (ALWAYS sent)
                const sqlFormattedJson = line.substring(14).trim(); // Remove 'SQL_FORMATTED:' prefix
                try {
                  const sqlFormattedData = JSON.parse(sqlFormattedJson);
                  if (sqlFormattedData.type === 'sql_formatted') {
                    // Store the formatted SQL (will be shown based on flag)
                    setMessages(prev => 
                      prev.map(msg => 
                        msg.id === streamingMessageId 
                          ? { 
                              ...msg, 
                              formattedSql: sqlFormattedData.sql
                            }
                          : msg
                      )
                    );
                  }
                } catch (error) {
                  console.error('Failed to parse formatted SQL data:', error);
                }
              } else if (line.startsWith('SQL_READY:')) {
                // Extract SQL ready data from backend
                const sqlReadyJson = line.substring(10).trim(); // Remove 'SQL_READY:' prefix
                try {
                  const sqlReadyData = JSON.parse(sqlReadyJson);
                  if (sqlReadyData.type === 'sql_ready') {
                    // Update the message with SQL ready data - this will trigger automatic query execution
                    // IMPORTANT: Preserve all existing fields including formattedSql
                    // Also store the SQL for potential on-demand explanation generation
                    setMessages(prev => 
                      prev.map(msg => 
                        msg.id === streamingMessageId 
                          ? { 
                              ...msg, 
                              sqlReady: sqlReadyData,
                              isExecutingQuery: true,
                              generatedSql: sqlReadyData.sql,  // Store for on-demand explanation
                              originalQuestion: cleanMessage  // Store the original question
                            }
                          : msg
                      )
                    );
                  }
                } catch (error) {
                  console.error('Failed to parse SQL ready data:', error);
                }
              } else if (line.startsWith('QUERY_RESULTS:')) {
                // Legacy support - should not be received anymore
                // Debug logging in development only
                if (process.env.NODE_ENV === 'development') {
                  console.log('Received legacy QUERY_RESULTS marker - ignoring');
                }
                
              } else if (line.startsWith('QUERY_ERROR:')) {
                // Extract query error from backend
                const errorJson = line.substring(12).trim(); // Remove 'QUERY_ERROR:' prefix
                try {
                  const error = JSON.parse(errorJson);
                  if (error.type === 'query_error') {
                    // Update the message with query error immediately
                    // IMPORTANT: Preserve all existing fields including formattedSql
                    setMessages(prev => 
                      prev.map(msg => 
                        msg.id === streamingMessageId 
                          ? { 
                              ...msg, 
                              queryError: error.error,
                              isExecutingQuery: false
                            }
                          : msg
                      )
                    );
                  }
                } catch (e) {
                  console.error('Failed to parse query error:', e);
                }
                
              } else if (line.startsWith('SQL_EXPLANATION:')) {
                // Extract SQL explanation from backend
                const explanationJson = line.substring(16).trim(); // Remove 'SQL_EXPLANATION:' prefix
                try {
                  const explanationData = JSON.parse(explanationJson);
                  if (explanationData.type === 'sql_explanation') {
                    // Store the explanation but don't display it yet
                    // It will be displayed after the table data is loaded
                    setMessages(prev => 
                      prev.map(msg => 
                        msg.id === streamingMessageId 
                          ? { 
                              ...msg, 
                              sqlExplanation: {
                                text: explanationData.explanation,
                                language: explanationData.language
                              },
                              explanationReady: true
                            }
                          : msg
                      )
                    );
                  }
                } catch (e) {
                  console.error('Failed to parse SQL explanation:', e);
                }
                
              } else if (line.startsWith('SQL_GENERATION_FAILED:')) {
                // Handle SQL generation failure - extract the error message but don't display the JSON
                const failureJson = line.substring(22).trim(); // Remove 'SQL_GENERATION_FAILED:' prefix
                try {
                  const failureData = JSON.parse(failureJson);
                  // The error message has already been sent as regular content
                  // We just need to mark the generation as failed and not add this JSON to the display
                  // Debug logging in development only
                  if (process.env.NODE_ENV === 'development') {
                    console.log('SQL generation failed:', failureData);
                  }
                  // Don't add this line to filteredChunk - the error message was already sent
                } catch (e) {
                  console.error('Failed to parse SQL generation failure:', e);
                }
                
              } else if (line.startsWith('CRITICAL_ERROR:')) {
                // Handle critical errors with structured formatting
                const errorJson = line.substring(15).trim(); // Remove 'CRITICAL_ERROR:' prefix
                try {
                  const errorData = JSON.parse(errorJson);
                  // Update message with critical error data
                  setMessages(prev => 
                    prev.map(msg => 
                      msg.id === streamingMessageId 
                        ? { 
                            ...msg, 
                            criticalError: errorData,
                            isProcessing: false
                          }
                        : msg
                    )
                  );
                  // Don't add the raw JSON to the display
                } catch (e) {
                  console.error('Failed to parse critical error:', e);
                }
                
              } else {
                // Add non-special content to the message
                if (line.trim()) {
                  filteredChunk += (filteredChunk ? '\n' : '') + line;
                }
              }
            }
            
            // Update the streaming message with filtered content
            if (filteredChunk) {
              accumulatedContent += filteredChunk;
              setMessages(prev => 
                prev.map(msg => {
                  if (msg.id === streamingMessageId) {
                    // Preserve all existing fields while updating content
                    return { 
                      ...msg, 
                      content: accumulatedContent, 
                      isProcessing: true 
                    };
                  }
                  return msg;
                })
              );
            }
          }
        );
        
        // Mark streaming as completed
        setMessages(prev => 
          prev.map(msg => 
            msg.id === streamingMessageId 
              ? { ...msg, isProcessing: false }
              : msg
          )
        );
        
        // Note: SQL generation completes with SQL_READY marker
        // Query execution happens automatically via PaginatedDataTable
        
        // Stop the blinking animation and clear the log message when processing is complete
        setIsLogBlinking(false);
        setThothLogMessage('');
        
        
      } catch (error) {
        // Remove any processing messages and add error message
        setMessages(prev => prev.filter(msg => !msg.isProcessing));
        
        // Stop the blinking animation and clear the log message when there's an error
        setIsLogBlinking(false);
        setThothLogMessage('');
        
        const details = error instanceof Error ? error.message : 'Failed to generate SQL';
        
        // Check if it's a cancellation
        const isCancellation = details.includes('Operation cancelled by user') || 
                              details.includes('aborted') || 
                              details.includes('cancelled');
        
        if (!isCancellation) {
          // Only show error message if it's not a cancellation
          const errorMessage: Message = {
            id: (Date.now() + 3).toString(),
            type: 'system',
            content: `Error: ${details}\n\nTroubleshooting info:\n- SQL Generator URL: ${sqlGeneratorApi.getBaseURL()}\n- Tip: Ensure the service is running and CORS allows the frontend origin.\n- You can test with: curl -v ${sqlGeneratorApi.getBaseURL()}/health` ,
            timestamp: new Date()
          };
          
          setMessages(prev => [...prev, errorMessage]);
        } else {
          // Add a cancellation notice
          const cancelMessage: Message = {
            id: (Date.now() + 3).toString(),
            type: 'system',
            content: `Operation cancelled.`,
            timestamp: new Date()
          };
          
          setMessages(prev => [...prev, cancelMessage]);
        }
      } finally {
        setIsProcessing(false);
        setOperationInProgress(false); // Clear operation state
        // Ensure blinking animation is stopped and log message is cleared in all cases
        setIsLogBlinking(false);
        setThothLogMessage('');
      }
    }
  };


  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border px-6 py-4 bg-background/80 backdrop-blur-sm">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Sparkles className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">ThothAI</h1>
              <p className="text-sm text-muted-foreground">Natural Language to SQL</p>
            </div>
          </div>
          
          {/* ThothAI Log Viewer */}
          <div className="flex-1 mx-4">
            <input
              type="text"
              readOnly
              value={thothaiLogMessage}
              className={`w-full bg-background/50 border border-border/50 rounded-md px-3 py-2 text-lg font-medium text-center ${
                isLogBlinking ? 'animate-pulse-continuous' : ''
              } thoth-log-text`}
              title="ThothAI processing status"
            />
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

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto bg-gradient-to-b from-background to-background/95">
        <div className="mx-auto px-8 py-8">
          {messages.length === 0 ? (
            /* Welcome message */
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8">
              {/* ThothAI Logo Section */}
              <div className="relative">
                <div className="relative p-8 rounded-3xl">
                  <img 
                    src="/dio-thoth-dx.png" 
                    alt="ThothAI Dio" 
                    className="h-48 w-48 object-contain mx-auto"
                    style={{ 
                      filter: 'drop-shadow(0 6px 12px rgba(0,0,0,0.4))'
                    }}
                  />
                </div>
              </div>
              
              <div className="text-center space-y-4 max-w-2xl">
                <h2 className="text-4xl font-bold" style={{ color: '#4a90a4' }}>
                  Welcome to ThothAI{user?.first_name ? `, ${user.first_name}` : ''}
                </h2>
                <p className="text-xl text-muted-foreground leading-relaxed">
                  Your intelligent SQL assistant powered by advanced AI. Ask me anything about your data
                  and I&apos;ll transform your questions into precise SQL queries.
                </p>
              </div>
              
              {/* Feature Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8 w-full max-w-3xl">
                <div className="p-4 rounded-xl bg-card/50 border border-border/50 backdrop-blur-sm hover:bg-card/70 transition-all">
                  <Database className="h-8 w-8 mb-2" style={{ color: '#4a90a4' }} />
                  <h3 className="font-semibold text-base">Smart Schema Analysis</h3>
                  <p className="text-sm text-muted-foreground mt-1">Automatic understanding of your database structure</p>
                </div>
                <div className="p-4 rounded-xl bg-card/50 border border-border/50 backdrop-blur-sm hover:bg-card/70 transition-all">
                  <Zap className="h-8 w-8 text-yellow-500 mb-2" />
                  <h3 className="font-semibold text-base">Lightning Fast</h3>
                  <p className="text-sm text-muted-foreground mt-1">Real-time SQL generation with streaming responses</p>
                </div>
                <div className="p-4 rounded-xl bg-card/50 border border-border/50 backdrop-blur-sm hover:bg-card/70 transition-all">
                  <Code2 className="h-8 w-8 text-green-500 mb-2" />
                  <h3 className="font-semibold text-base">Optimized Queries</h3>
                  <p className="text-sm text-muted-foreground mt-1">Generate efficient, production-ready SQL code</p>
                </div>
              </div>
            </div>
          ) : (
            /* Chat messages */
            <div className="space-y-0.5 max-w-none">
              {messages.map((msg) => (
                <React.Fragment key={msg.id}>
                  <div className="w-full animate-fadeIn">
                    {msg.type === 'user' ? (
                    /* User message */
                    <OutputBlock
                      imageSrc="/user-icon.svg"
                      imageAlt="User"
                    >
                      <p className="text-lg leading-relaxed text-foreground mt-0.5">{msg.content}</p>
                    </OutputBlock>
                  ) : (
                    /* AI/System message - only show if there's content to display based on flags */
                    (msg.content.trim() || 
                     msg.isProcessing || 
                     msg.criticalError ||
                     (msg.formattedSql && flags.show_sql)) ? (
                      <OutputBlock>
                        <div>
                          {msg.isProcessing && (
                            <div className="flex items-center gap-2 mb-2">
                              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                              <span className="text-sm text-muted-foreground">Generating response...</span>
                            </div>
                          )}
                          
                          {/* Critical Error Display */}
                          {msg.criticalError && (
                            <div className="space-y-3 p-4 rounded-lg bg-background/10 border border-border/30">
                              {/* Part 1: Extract TEST code and show as Validation Error - In evidenza */}
                              <div className="text-lg font-bold">
                                {(() => {
                                  // Extract TEST code from message if present
                                  const match = msg.criticalError.message?.match(/^(TEST\d+):/);
                                  return match ? `${match[1]} - Validation Error` : 'Validation Error';
                                })()}
                              </div>
                              
                              {/* Part 2: Message (remove TEST code prefix if present) */}
                              <div className="text-base">
                                {(() => {
                                  // Remove TEST code prefix from message
                                  const message = msg.criticalError.message || '';
                                  return message.replace(/^TEST\d+:\s*/, '');
                                })()}
                              </div>
                              
                              {/* Part 3: Impact */}
                              {msg.criticalError.impact && (
                                <div className="text-base">
                                  {msg.criticalError.impact}
                                </div>
                              )}
                              
                              {/* Part 4: Action - In evidenza */}
                              {msg.criticalError.action && (
                                <div className="text-base font-bold pt-2">
                                  {msg.criticalError.action}
                                </div>
                              )}
                            </div>
                          )}
                          
                          {/* Content display - skip SQL if it's in formattedSql, skip if critical error */}
                          {!msg.criticalError && !msg.formattedSql && (msg.content.includes('SELECT') || msg.content.includes('FROM')) ? (
                            // Legacy support - only show inline SQL if no formattedSql available
                            <div className="space-y-3">
                              <div className="bg-slate-900 dark:bg-slate-950 rounded-lg font-mono text-sm overflow-x-auto">
                                <code className="text-green-400 whitespace-pre-wrap block py-0.5">
                                  {msg.content.split('\n').map((line, i) => (
                                    <div key={i} className="leading-relaxed">
                                      {line.split(/\b(SELECT|FROM|WHERE|JOIN|INNER|LEFT|RIGHT|ON|AND|OR|GROUP BY|ORDER BY|LIMIT|AS|IS|NOT|NULL|ASC|DESC|NULLS|LAST|FIRST|DISTINCT|HAVING|UNION|ALL|EXISTS|IN|BETWEEN|LIKE|CASE|WHEN|THEN|ELSE|END|T1|T2)(?=\s|$)/gi).map((part, j) => (
                                        <span key={j} className={
                                          /^(SELECT|FROM|WHERE|JOIN|INNER|LEFT|RIGHT|ON|GROUP BY|ORDER BY|LIMIT|AS|HAVING|UNION|DISTINCT)$/i.test(part)
                                            ? 'text-blue-400 font-semibold'
                                            : /^(AND|OR|NOT|IN|EXISTS|BETWEEN|LIKE)$/i.test(part)
                                            ? 'text-cyan-400'
                                            : /^(IS|NULL|ASC|DESC|NULLS|LAST|FIRST|ALL)$/i.test(part)
                                            ? 'text-red-400'
                                            : /^(CASE|WHEN|THEN|ELSE|END)$/i.test(part)
                                            ? 'text-orange-400'
                                            : /^(T1|T2)$/i.test(part)
                                            ? 'text-yellow-400'
                                            : ''
                                        }>
                                          {part}
                                        </span>
                                      ))}
                                    </div>
                                  ))}
                                </code>
                              </div>
                            </div>
                          ) : !msg.criticalError && msg.content.trim() ? (
                            <div className="space-y-2">
                              {msg.content.split('\n').map((paragraph, i) => (
                                <p key={i} className="text-base leading-relaxed text-foreground">
                                  {paragraph.startsWith('- ') ? (
                                    <span className="flex items-start gap-2">
                                      <span className="mt-1">•</span>
                                      <span>{paragraph.substring(2)}</span>
                                    </span>
                                  ) : paragraph.startsWith('Evidences found:') || paragraph.startsWith('SQL examples:') ? (
                                    <span className="font-semibold">{paragraph}</span>
                                  ) : paragraph.startsWith('Similar Columns') || paragraph.startsWith('Schema') ? (
                                    <span className="font-medium">{paragraph}</span>
                                  ) : (
                                    paragraph
                                  )}
                                </p>
                              ))}
                            </div>
                          ) : null}
                          
                          {msg.isProcessing && msg.content && (
                            <span className="inline-block w-2 h-5 bg-foreground/50 animate-pulse ml-1"></span>
                          )}
                          
                          {/* Formatted SQL Display - Show only if flag is enabled and SQL exists */}
                          {msg.formattedSql && flags.show_sql ? (
                                  <div className="space-y-3">
                                    <div className="bg-slate-900 dark:bg-slate-950 rounded-lg font-mono text-sm overflow-x-auto">
                                      <code className="text-green-400 whitespace-pre-wrap block py-0.5">
                                  {msg.formattedSql.split('\n').map((line, i) => (
                                    <div key={i} className="leading-relaxed">
                                      {line.split(/\b(SELECT|FROM|WHERE|JOIN|INNER|LEFT|RIGHT|ON|AND|OR|GROUP BY|ORDER BY|LIMIT|AS|IS|NOT|NULL|ASC|DESC|NULLS|LAST|FIRST|DISTINCT|HAVING|UNION|ALL|EXISTS|IN|BETWEEN|LIKE|CASE|WHEN|THEN|ELSE|END|T1|T2)(?=\s|$)/gi).map((part, j) => (
                                        <span key={j} className={
                                          /^(SELECT|FROM|WHERE|JOIN|INNER|LEFT|RIGHT|ON|GROUP BY|ORDER BY|LIMIT|AS|HAVING|UNION|DISTINCT)$/i.test(part)
                                            ? 'text-blue-400 font-semibold'
                                            : /^(AND|OR|NOT|IN|EXISTS|BETWEEN|LIKE)$/i.test(part)
                                            ? 'text-cyan-400'
                                            : /^(IS|NULL|ASC|DESC|NULLS|LAST|FIRST|ALL)$/i.test(part)
                                            ? 'text-red-400'
                                            : /^(CASE|WHEN|THEN|ELSE|END)$/i.test(part)
                                            ? 'text-orange-400'
                                            : /^(T1|T2)$/i.test(part)
                                            ? 'text-yellow-400'
                                            : ''
                                        }>
                                          {part}
                                        </span>
                                      ))}
                                    </div>
                                  ))}
                                      </code>
                                    </div>
                                  </div>
                          ) : null}
                          
                          {/* Query Execution Results */}
                          {msg.isExecutingQuery && (
                            <div className="mt-4 flex items-center gap-2">
                              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                              <span className="text-sm text-muted-foreground">Executing query...</span>
                            </div>
                          )}
                          
                          {msg.queryError && (
                            <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-4 mt-4">
                              <div className="text-red-700 dark:text-red-400 font-semibold">Query Execution Error</div>
                              <div className="text-red-600 dark:text-red-500 mt-2">{msg.queryError}</div>
                            </div>
                          )}
                        </div>
                      </OutputBlock>
                  ) : null
                  )}
                  </div>
                  
                  {/* Render DataTable/PaginatedDataTable outside of message container */}
                  {msg.sqlReady && (
                    <div className="w-full animate-fadeIn">
                      <PaginatedDataTable 
                        sql={msg.sqlReady.sql}
                        workspaceId={msg.sqlReady.workspace_id}
                        onError={(error) => {
                          // Update message with error
                          setMessages(prev => 
                            prev.map(m => 
                              m.id === msg.id 
                                ? { ...m, queryError: error, isExecutingQuery: false }
                                : m
                            )
                          );
                        }}
                        onDataLoaded={() => {
                          // Update message to indicate loading is complete and table is loaded
                          setMessages(prev => 
                            prev.map(m => 
                              m.id === msg.id 
                                ? { ...m, isExecutingQuery: false, tableDataLoaded: true }
                                : m
                            )
                          );
                          // Enable Like button when table data is successfully loaded
                          setLikeButtonEnabled(true);
                        }}
                      />
                    </div>
                  )}
                  
                  {/* Render SQL Explanation after table is loaded - only if flag is enabled and there's actual text */}
                  {msg.sqlExplanation && msg.sqlExplanation.text && msg.sqlExplanation.text.trim() !== '' && msg.explanationReady && msg.tableDataLoaded && flags.explain_generated_query && (
                    <div className="w-full animate-fadeIn mt-2">
                      <OutputBlock
                        imageAlt="ThothAI Explanation"
                      >
                        <div 
                          className="text-base leading-relaxed text-foreground"
                          style={{ fontSize: 'calc(1rem - 1px)' }}
                          dangerouslySetInnerHTML={{ __html: markdownToHtml(msg.sqlExplanation.text) }}
                        />
                      </OutputBlock>
                    </div>
                  )}
                  
                  {/* Legacy support for old query results format */}
                  {msg.queryResults && !msg.sqlReady && (
                    <div className="w-full animate-fadeIn">
                      <DataTable 
                        data={msg.queryResults} 
                        isLoading={false}
                        error={null}
                      />
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>
          )}
          {/* Auto-scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-border/50 bg-background/80 backdrop-blur-sm p-6">
        <div className="mx-auto px-8">
          <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
            <div className="relative group">
              <textarea
                value={message}
                onChange={(e) => {
                  setMessage(e.target.value);
                  // Auto-resize textarea with proper bounds
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  const newHeight = Math.min(target.scrollHeight, 200);
                  target.style.height = newHeight + 'px';
                  target.style.overflowY = newHeight >= 200 ? 'auto' : 'hidden';
                }}
                placeholder="Ask me a question about your data..."
                rows={1}
                className="w-full bg-card text-foreground text-lg border-2 dark:border dark:border-white border-gray-400 rounded-2xl px-6 py-4 pr-16 resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 dark:focus:border-white focus:border-gray-500 min-h-[56px] max-h-[200px] overflow-hidden transition-all dark:group-hover:border-white group-hover:border-gray-500"
                style={{ height: 'auto' }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
              />
              <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-1">
                {/* Like Button */}
                <LikeButton 
                  enabled={likeButtonEnabled}
                  workspaceId={selectedWorkspace?.id || 0}
                  onSuccess={() => {
                    // Debug logging in development only
                    if (process.env.NODE_ENV === 'development') {
                      console.log('SQL feedback saved successfully');
                    }
                  }}
                  onError={(error) => {
                    console.error('Failed to save SQL feedback:', error);
                  }}
                />
                
                {/* Send Button */}
                <button
                  type="submit"
                  disabled={!message.trim() || isProcessing}
                  className="p-2.5 text-white/70 hover:text-white disabled:text-white/40 disabled:cursor-not-allowed transition-all hover:bg-primary/10 rounded-xl"
                  title={isProcessing ? "Processing..." : "Send message"}
                >
                  {isProcessing ? (
                    <Loader2 className="h-5 w-5 animate-spin" strokeWidth={2.5} />
                  ) : (
                    <Send className="h-5 w-5" strokeWidth={2.5} />
                  )}
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground px-2">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1">
                  <Database className="h-3 w-3" style={{ color: '#4a90a4' }} />
                  {selectedWorkspace?.name || 'No workspace'}
                </span>
                <span className="flex items-center gap-1">
                  <Zap className="h-3 w-3" />
                  {strategy}
                </span>
              </div>
              <span className="text-center">© Tyl Consulting - powered by CHESS (Talaei, Shayan and Pourreza, Mohammadreza and Chang, Yu-Chen and Mirhoseini, Azalia and Saberi, Amin)</span>
              <span>Press Enter to send, Shift+Enter for new line</span>
            </div>
          </form>
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
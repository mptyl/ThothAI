// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useAuth } from '@/lib/auth-context';
import { Loader2, AlertCircle, Sparkles, Database, MessageSquare, Lock, User, Eye, EyeOff } from 'lucide-react';

export function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const { login, isLoading, error, clearError } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (!username.trim() || !password.trim()) {
      return;
    }

    try {
      await login({ username: username.trim(), password, remember_me: rememberMe });
      router.push('/welcome');
    } catch (error) {
      // Error is handled by auth context
      console.error('Login failed:', error);
    }
  };

  return (
    <div className="login-container">
      {/* Animated background elements */}
      <div className="login-bg-pattern"></div>
      
      <div className="login-form-enhanced">
        {/* Logo and brand header */}
        <div className="text-center mb-8">
          <div className="mb-6 inline-block">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-[#4a90a4]/30 to-[#4a90a4]/30 blur-2xl"></div>
              <div className="relative p-4 rounded-2xl bg-gradient-to-br from-[#4a90a4]/20 to-[#4a90a4]/20 border border-[#4a90a4]/20">
                <Sparkles className="h-12 w-12 animate-pulse" style={{ color: '#4a90a4' }} />
              </div>
            </div>
          </div>
          
          <h1 className="text-4xl font-bold tracking-tight" style={{ color: '#4a90a4' }}>
            ThothAI Login
          </h1>
          <p className="text-muted-foreground mt-2">
            Your AI-powered SQL assistant awaits
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="flex items-center gap-2 p-3 rounded-md bg-destructive/10 border border-destructive/20">
              <AlertCircle className="h-4 w-4 text-destructive" />
              <span className="text-sm text-destructive">{error}</span>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="username" className="flex items-center gap-2">
              <User className="h-4 w-4 text-primary" />
              Username
            </Label>
            <Input
              id="username"
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isLoading}
              required
              className="w-full login-input"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-primary" />
              Password
            </Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                required
                className="w-full login-input pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-500 hover:text-gray-700 transition-colors"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5" />
                ) : (
                  <Eye className="h-5 w-5" />
                )}
              </button>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <Checkbox
              id="remember-me"
              checked={rememberMe}
              onCheckedChange={setRememberMe}
              disabled={isLoading}
              className="h-5 w-5 border-2 border-gray-400 data-[state=checked]:border-[#4a90a4] data-[state=checked]:bg-[#4a90a4]"
            />
            <Label 
              htmlFor="remember-me" 
              className="text-sm font-normal cursor-pointer select-none"
            >
              Remember me
            </Label>
          </div>

          <button
            type="submit"
            className="w-full login-button inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none h-10 px-4 py-2"
            disabled={isLoading || !username.trim() || !password.trim()}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin text-white" />
                <span className="text-white">Signing in...</span>
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4 text-white" />
                <span className="text-white">Sign In to ThothAI</span>
              </>
            )}
          </button>
        </form>

        {/* Features showcase */}
        <div className="mt-8 pt-8 border-t border-border/50">
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="p-2 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 inline-block mb-2">
                <MessageSquare className="h-5 w-5 text-primary" />
              </div>
              <p className="text-xs text-muted-foreground">Natural Language</p>
            </div>
            <div className="text-center">
              <div className="p-2 rounded-lg bg-gradient-to-br from-purple-600/10 to-purple-600/5 inline-block mb-2">
                <Database className="h-5 w-5 text-purple-600" />
              </div>
              <p className="text-xs text-muted-foreground">Multi-Database</p>
            </div>
            <div className="text-center">
              <div className="p-2 rounded-lg bg-gradient-to-br from-blue-600/10 to-blue-600/5 inline-block mb-2">
                <Sparkles className="h-5 w-5 text-blue-600" />
              </div>
              <p className="text-xs text-muted-foreground">AI-Powered</p>
            </div>
          </div>
        </div>

        <div className="mt-6 text-center text-sm text-muted-foreground">
          <p className="font-medium">Powered by PydanticAI & Qdrant</p>
        </div>
      </div>
    </div>
  );
}
// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useAuth, fetchAuthConfig, loginWithOIDC, AuthConfig, AuthProvider } from '@/lib/auth-context';
import { Loader2, AlertCircle, Sparkles, Database, MessageSquare, Lock, User, Eye, EyeOff, Building2 } from 'lucide-react';

// Inner component that uses useSearchParams
function LoginFormContent() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const { login, isLoading, error, clearError, isAuthenticated } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get('next') || '/welcome';

  // Carica configurazione auth all'avvio
  useEffect(() => {
    async function loadConfig() {
      try {
        const config = await fetchAuthConfig();
        setAuthConfig(config);

        // ⚡ SINGLE IDP: Redirect immediato senza UI
        if (config.mode === 'single_idp' && config.providers.length === 1) {
          const provider = config.providers[0];
          if (provider.type === 'oidc' && provider.login_url) {
            const backendUrl = process.env.NEXT_PUBLIC_DJANGO_SERVER || 'http://localhost:8040';
            window.location.href = `${backendUrl}${provider.login_url}&next=${encodeURIComponent(redirectTo)}`;
            return;
          }
        }
      } catch (err) {
        console.error('Failed to load auth config:', err);
        // Fallback a native mode se config non disponibile
        setAuthConfig({
          mode: 'native',
          providers: [{ id: 'local', name: 'Username/Password', type: 'credentials' }],
          primary_provider: null,
          registration_enabled: true,
          password_reset_enabled: true,
        });
      } finally {
        setConfigLoading(false);
      }
    }

    if (!isAuthenticated) {
      loadConfig();
    } else {
      // Use window.location.href for external URLs (different port/domain)
      if (redirectTo.startsWith('http://') || redirectTo.startsWith('https://')) {
        window.location.href = redirectTo;
      } else {
        router.push(redirectTo);
      }
    }
  }, [isAuthenticated, redirectTo, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (!username.trim() || !password.trim()) {
      return;
    }

    try {
      await login({ username: username.trim(), password, remember_me: rememberMe });
      // Use window.location.href for external URLs (different port/domain)
      if (redirectTo.startsWith('http://') || redirectTo.startsWith('https://')) {
        window.location.href = redirectTo;
      } else {
        router.push(redirectTo);
      }
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  const handleOIDCLogin = (provider: AuthProvider) => {
    loginWithOIDC(provider.id, redirectTo);
  };

  // Loading state per single_idp redirect o caricamento config
  if (configLoading || authConfig?.mode === 'single_idp') {
    return (
      <div className="login-container">
        <div className="login-bg-pattern"></div>
        <div className="login-form-enhanced">
          <div className="flex flex-col items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
            <p className="mt-4 text-muted-foreground">
              {authConfig?.mode === 'single_idp'
                ? "Reindirizzamento all'autenticazione aziendale..."
                : 'Caricamento...'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const hasCredentials = authConfig?.providers.some(p => p.type === 'credentials');
  const oidcProviders = authConfig?.providers.filter(p => p.type === 'oidc') || [];

  return (
    <div className="login-container">
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

        {/* Form credenziali (solo se disponibile) */}
        {hasCredentials && (
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
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Checkbox
                id="remember-me"
                checked={rememberMe}
                onCheckedChange={(checked) => setRememberMe(checked === true)}
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
        )}

        {/* Separatore (solo se ci sono entrambi) */}
        {hasCredentials && oidcProviders.length > 0 && (
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border/50" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">oppure</span>
            </div>
          </div>
        )}

        {/* Bottoni IdP */}
        {oidcProviders.length > 0 && (
          <div className="space-y-3">
            {oidcProviders.map(provider => (
              <button
                key={provider.id}
                type="button"
                onClick={() => handleOIDCLogin(provider)}
                className="w-full inline-flex items-center justify-center gap-3 rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground h-11 px-4 py-2 transition-colors"
              >
                <Building2 className="h-5 w-5" />
                <span>Accedi con {provider.name}</span>
              </button>
            ))}
          </div>
        )}

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

// Main exported component wrapping the inner one in Suspense
export function LoginForm() {
  return (
    <Suspense fallback={
      <div className="login-container">
        <div className="login-bg-pattern"></div>
        <div className="login-form-enhanced">
          <div className="flex flex-col items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
            <p className="mt-4 text-muted-foreground">Caricamento...</p>
          </div>
        </div>
      </div>
    }>
      <LoginFormContent />
    </Suspense>
  );
}
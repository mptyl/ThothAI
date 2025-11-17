// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { WorkspaceDatabaseInfo } from '@/components/settings/workspace-database-info'
import { ThemeToggle } from '@/components/theme-toggle'
import { Button } from '@/components/ui/button'
import { LogOut, Sparkles } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { useRouter } from 'next/navigation'

// Disable static generation for this page
export const dynamic = 'force-dynamic'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('database')
  const { user, logout } = useAuth()
  const router = useRouter()

  const handleLogout = async () => {
    try {
      await logout()
      router.push('/login')
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header - matching the chat page header */}
      <div className="border-b border-border px-6 py-4 bg-background/80 backdrop-blur-sm">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Sparkles className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">ThothAI</h1>
              <p className="text-sm text-muted-foreground">Settings</p>
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

      {/* Main content */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-6xl mx-auto">

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2 bg-sidebar border-2 border-black">
          <TabsTrigger value="database" className="flex items-center gap-2">
            Database Configuration
          </TabsTrigger>
          <TabsTrigger value="system" className="flex items-center gap-2">
            System
          </TabsTrigger>
        </TabsList>

        <TabsContent value="database" className="mt-8">
          <WorkspaceDatabaseInfo />
        </TabsContent>

        <TabsContent value="system" className="mt-8">
          <Card className="border-2 border-black bg-gray-900">
            <CardHeader className="pb-6">
              <CardTitle className="flex items-center gap-3 text-3xl font-bold">
                System Configuration
              </CardTitle>
              <CardDescription className="text-base mt-2">
                General system settings and preferences.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-8">
              <p className="text-muted-foreground text-lg">
                System settings will be available in a future update.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
        </div>
      </div>
    </div>
  )
}
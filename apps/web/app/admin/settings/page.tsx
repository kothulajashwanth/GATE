'use client';

import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle, Button, Input, Label, Switch } from '@examshield/ui';
import { Settings, Shield, Sliders, Mail, Database, Sparkles } from 'lucide-react';
import { useState } from 'react';

export default function AdminSettingsPage() {
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <PageHeader
        title="System Settings"
        description="Configure institution details, proctoring thresholds, and system integration keys."
      />

      {saved && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300 text-sm font-medium">
          Settings saved successfully!
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold flex items-center gap-2">
            <Sliders className="h-4 w-4 text-primary" /> Institution Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label>College / Institution Name</Label>
            <Input defaultValue="GATE IGNITE Academy of Engineering" />
          </div>
          <div className="grid gap-2">
            <Label>Admin Support Email</Label>
            <Input defaultValue="admin@gateignite.local" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold flex items-center gap-2">
            <Shield className="h-4 w-4 text-emerald-600" /> Security & Anti-Cheating Rules
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-sm font-semibold">Enforce Fullscreen Examination</Label>
              <p className="text-xs text-muted-foreground">Force full screen mode when students attempt exams.</p>
            </div>
            <Switch defaultChecked />
          </div>
          <div className="flex items-center justify-between pt-2 border-t">
            <div className="space-y-0.5">
              <Label className="text-sm font-semibold">Maximum Warning Limit</Label>
              <p className="text-xs text-muted-foreground">Auto-terminate exam after threshold is exceeded.</p>
            </div>
            <Input type="number" defaultValue="3" className="w-20 text-center font-bold" />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button size="lg" onClick={handleSave}>
          Save Settings
        </Button>
      </div>
    </div>
  );
}

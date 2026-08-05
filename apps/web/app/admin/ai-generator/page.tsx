'use client';

import { useState } from 'react';
import { PageHeader } from '@/components/page-header';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@examshield/ui';
import { Sparkles, Check, RefreshCw, Layers, BookOpen, Brain, Zap, CheckCircle2, ArrowRight } from 'lucide-react';

interface GeneratedQuestion {
  id: string;
  text: string;
  type: string;
  options: string[];
  correctAnswer: string;
  explanation: string;
  difficulty: string;
  bloomLevel: string;
  topic: string;
}

export default function AiGeneratorPage() {
  const [subject, setSubject] = useState('Java');
  const [difficulty, setDifficulty] = useState('medium');
  const [numQuestions, setNumQuestions] = useState('10');
  const [bloomLevel, setBloomLevel] = useState('apply');
  const [topics, setTopics] = useState('OOP, Collections, Exception Handling');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedList, setGeneratedList] = useState<GeneratedQuestion[]>([]);
  const [savedCount, setSavedCount] = useState(0);

  const handleGenerate = () => {
    setIsGenerating(true);
    setSavedCount(0);
    setTimeout(() => {
      setIsGenerating(false);
      setGeneratedList([
        {
          id: 'q1',
          text: 'Which feature of Java allows a class to inherit properties and behavior from another class?',
          type: 'mcq',
          options: ['Encapsulation', 'Inheritance', 'Polymorphism', 'Abstraction'],
          correctAnswer: 'Inheritance',
          explanation: 'Inheritance allows a subclass to inherit fields and methods from a superclass using extends.',
          difficulty: difficulty,
          bloomLevel: bloomLevel,
          topic: 'OOP',
        },
        {
          id: 'q2',
          text: 'What exception is thrown when attempting to access an array index that is out of bounds?',
          type: 'mcq',
          options: ['NullPointerException', 'ArrayIndexOutOfBoundsException', 'ClassCastException', 'IllegalArgumentException'],
          correctAnswer: 'ArrayIndexOutOfBoundsException',
          explanation: 'ArrayIndexOutOfBoundsException is thrown to indicate that an array has been accessed with an illegal index.',
          difficulty: difficulty,
          bloomLevel: bloomLevel,
          topic: 'Exception Handling',
        },
        {
          id: 'q3',
          text: 'Which interface in the Java Collections Framework provides an ordered collection that allows duplicates?',
          type: 'mcq',
          options: ['Set', 'Map', 'List', 'Queue'],
          correctAnswer: 'List',
          explanation: 'List is an ordered Collection (sometimes called a sequence) that can contain duplicate elements.',
          difficulty: difficulty,
          bloomLevel: bloomLevel,
          topic: 'Collections',
        },
      ]);
    }, 1800);
  };

  const handleSaveAll = () => {
    setSavedCount(generatedList.length);
    setTimeout(() => setSavedCount(0), 3000);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Question Generator & Classifier"
        description="Automatically generate validated question papers, wrong distractor options, and explanations powered by OpenAI & Gemini."
      />

      <div className="grid gap-6 md:grid-cols-3">
        {/* Generator Form Config */}
        <Card className="md:col-span-1 border-amber-500/30 bg-amber-500/5 dark:bg-amber-500/10">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-amber-500" /> AI Generation Prompt Config
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Subject / Academic Area</label>
              <Select value={subject} onValueChange={setSubject}>
                <SelectTrigger className="bg-background"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Java">Java Programming</SelectItem>
                  <SelectItem value="Data Structures">Data Structures & Algorithms</SelectItem>
                  <SelectItem value="Operating Systems">Operating Systems</SelectItem>
                  <SelectItem value="Database Management">Database Management (DBMS)</SelectItem>
                  <SelectItem value="Computer Networks">Computer Networks</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Target Difficulty</label>
              <Select value={difficulty} onValueChange={setDifficulty}>
                <SelectTrigger className="bg-background"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="easy">Easy (Foundational)</SelectItem>
                  <SelectItem value="medium">Medium (Intermediate)</SelectItem>
                  <SelectItem value="hard">Hard (Advanced Problem Solving)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Bloom Taxonomy Level</label>
              <Select value={bloomLevel} onValueChange={setBloomLevel}>
                <SelectTrigger className="bg-background"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="remember">Remember (Knowledge Retrieval)</SelectItem>
                  <SelectItem value="understand">Understand (Comprehension)</SelectItem>
                  <SelectItem value="apply">Apply (Problem Application)</SelectItem>
                  <SelectItem value="analyze">Analyze (Deconstruction)</SelectItem>
                  <SelectItem value="evaluate">Evaluate (Assessment)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Number of Questions</label>
              <Input type="number" value={numQuestions} onChange={(e) => setNumQuestions(e.target.value)} className="bg-background" />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Topics (Comma separated)</label>
              <textarea
                value={topics}
                onChange={(e) => setTopics(e.target.value)}
                rows={2}
                className="w-full rounded-md border bg-background p-2 text-xs"
              />
            </div>

            <Button
              className="w-full bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold shadow-md"
              onClick={handleGenerate}
              disabled={isGenerating}
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> Synthesizing Questions...
                </>
              ) : (
                <>
                  <Brain className="h-4 w-4 mr-2" /> Generate {numQuestions} Questions
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results Stream */}
        <div className="md:col-span-2 space-y-4">
          {savedCount > 0 && (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300 text-sm font-semibold flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Batch saved {savedCount} questions into Question Bank!
            </div>
          )}

          {generatedList.length > 0 && (
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-base">Generated Question Batch ({generatedList.length})</h3>
              <Button size="sm" onClick={handleSaveAll} className="bg-emerald-600 hover:bg-emerald-700">
                <Check className="h-4 w-4 mr-1" /> Approve & Save All to Bank
              </Button>
            </div>
          )}

          {isGenerating ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="animate-pulse">
                  <CardContent className="p-6 h-36 bg-muted/30 rounded" />
                </Card>
              ))}
            </div>
          ) : generatedList.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="p-12 text-center space-y-3">
                <Sparkles className="h-12 w-12 text-amber-500/40 mx-auto" />
                <h3 className="text-lg font-semibold">No questions generated yet</h3>
                <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                  Configure your subject, Bloom Taxonomy target, and topics on the left to start AI generation.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {generatedList.map((q, idx) => (
                <Card key={q.id} className="border-l-4 border-l-amber-500">
                  <CardContent className="p-6 space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">Q{idx + 1}</Badge>
                        <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30">
                          {q.topic}
                        </Badge>
                        <Badge variant="secondary" className="capitalize">{q.difficulty}</Badge>
                      </div>
                      <span className="text-xs text-muted-foreground uppercase font-bold">Bloom: {q.bloomLevel}</span>
                    </div>

                    <h4 className="font-bold text-base">{q.text}</h4>

                    <div className="grid gap-2 sm:grid-cols-2 pt-2 text-sm">
                      {q.options.map((opt, i) => (
                        <div
                          key={i}
                          className={`p-2.5 rounded-lg border text-xs flex items-center justify-between ${
                            opt === q.correctAnswer
                              ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-700 dark:text-emerald-300 font-semibold'
                              : 'bg-muted/20'
                          }`}
                        >
                          <span>{opt}</span>
                          {opt === q.correctAnswer && <Check className="h-3.5 w-3.5 text-emerald-600" />}
                        </div>
                      ))}
                    </div>

                    <div className="p-3 rounded-lg bg-muted/40 text-xs text-muted-foreground">
                      <span className="font-semibold text-foreground">Explanation: </span>
                      {q.explanation}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Shield, DatabaseZap, LayoutDashboard, Activity, Upload, X } from 'lucide-react';
import { PipelineVisualizer, type PipelineStep, type ThinkingLog } from './components/PipelineVisualizer';
import { SqlEditor } from './components/SqlEditor';
import { ResultsDataGrid } from './components/ResultsDataGrid';
import { ChartVisualizer } from './components/ChartVisualizer';

function App() {
  const [activeTab, setActiveTab] = useState<'playground' | 'benchmarks'>('playground');
  
  // Settings State
  const [databases, setDatabases] = useState<string[]>([]);
  const [selectedDb, setSelectedDb] = useState('');
  const [provider, setProvider] = useState('groq');
  const [model, setModel] = useState('llama-3.3-70b-versatile');
  
  // Query State
  const [question, setQuestion] = useState('');
  const [step, setStep] = useState<PipelineStep>('idle');
  const [result, setResult] = useState<any>(null);
  const [thinkingLogs, setThinkingLogs] = useState<ThinkingLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Upload State
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Benchmarks State
  const [benchmarks, setBenchmarks] = useState<any[]>([]);

  // Fetch initial data
  const fetchDatabases = () => {
    fetch('/api/databases')
      .then(r => r.json())
      .then(data => {
        setDatabases(data.databases || []);
        if (!selectedDb && data.databases?.length > 0) {
          if (data.databases.includes('IPL')) setSelectedDb('IPL');
          else setSelectedDb(data.databases[0]);
        }
      });
  };

  useEffect(() => {
    fetchDatabases();
    fetch('/api/benchmarks')
      .then(r => r.json())
      .then(data => setBenchmarks(data.benchmarks || []));
  }, []);

  // Auto-scroll thinking log
  useEffect(() => {
    const container = document.getElementById('thinking-log-container');
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [thinkingLogs]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || !selectedDb || isLoading) return;

    setResult(null);
    setThinkingLogs([]);
    setStep('generating');
    setIsLoading(true);

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          db_id: selectedDb,
          provider,
          model
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error('No response body');

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        let currentEvent = '';
        let currentData = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            currentData = line.slice(6).trim();
            
            try {
              const parsed = JSON.parse(currentData);

              if (currentEvent === 'step') {
                setStep(parsed.step as PipelineStep);
                setThinkingLogs(prev => [...prev, {
                  step: parsed.step,
                  message: parsed.message,
                  timestamp: Date.now(),
                }]);
              } else if (currentEvent === 'result') {
                setResult(parsed);
                setStep('done');
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }
    } catch (err: any) {
      setStep('error');
      setThinkingLogs(prev => [...prev, {
        step: 'error',
        message: `✗ Connection error: ${err.message}`,
        timestamp: Date.now(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const validExtensions = ['.sqlite', '.csv'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validExtensions.includes(ext)) {
      setUploadStatus('❌ Only .sqlite and .csv files are supported');
      return;
    }

    setIsUploading(true);
    setUploadStatus(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (response.ok) {
        setUploadStatus(`✓ ${data.message}`);
        setSelectedDb(data.db_id);
        fetchDatabases();
      } else {
        setUploadStatus(`❌ ${data.detail}`);
      }
    } catch (err: any) {
      setUploadStatus(`❌ Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-neutral-950 text-neutral-100">
      
      {/* Sidebar */}
      <div className="w-72 border-r border-neutral-800 bg-neutral-900/40 p-6 flex flex-col gap-6 flex-shrink-0 z-10 overflow-y-auto">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-tr from-indigo-500 to-purple-500 p-2 rounded-xl shadow-lg shadow-indigo-500/20">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-300 to-purple-300">
              QueryShield
            </h1>
          </div>
        </div>

        <nav className="flex flex-col gap-2">
          <button 
            onClick={() => setActiveTab('playground')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-medium ${activeTab === 'playground' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' : 'text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200'}`}
          >
            <DatabaseZap className="w-5 h-5" /> Query Playground
          </button>
          <button 
            onClick={() => setActiveTab('benchmarks')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-medium ${activeTab === 'benchmarks' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' : 'text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200'}`}
          >
            <Activity className="w-5 h-5" /> Benchmarks
          </button>
        </nav>

        {activeTab === 'playground' && (
          <div className="flex flex-col gap-5 mt-auto pt-6 border-t border-neutral-800">
            
            {/* BYOD Upload Zone */}
            <div>
              <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2 block">Upload Database</label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".sqlite,.csv"
                onChange={handleFileUpload}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="w-full flex items-center justify-center gap-2 py-3 border-2 border-dashed border-neutral-700 hover:border-indigo-500/50 rounded-xl text-neutral-400 hover:text-indigo-400 transition-all text-sm font-medium disabled:opacity-50"
              >
                {isUploading ? (
                  <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1 }}>
                    <Upload className="w-4 h-4" />
                  </motion.div>
                ) : (
                  <Upload className="w-4 h-4" />
                )}
                {isUploading ? 'Uploading...' : 'Drop .sqlite or .csv'}
              </button>
              {uploadStatus && (
                <motion.p
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`text-xs mt-2 ${uploadStatus.startsWith('✓') ? 'text-emerald-400' : 'text-rose-400'}`}
                >
                  {uploadStatus}
                </motion.p>
              )}
            </div>

            <div>
              <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2 block">Database</label>
              <select 
                value={selectedDb} 
                onChange={e => setSelectedDb(e.target.value)}
                className="w-full bg-neutral-900 border border-neutral-700 rounded-lg p-2.5 text-sm outline-none focus:border-indigo-500"
              >
                {databases.map(db => <option key={db} value={db}>{db}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2 block">Provider</label>
              <select 
                value={provider} 
                onChange={e => {
                  const newProvider = e.target.value;
                  setProvider(newProvider);
                  // Reset model to default for the new provider
                  if (newProvider === 'groq') setModel('llama-3.3-70b-versatile');
                  if (newProvider === 'gemini') setModel('gemini-2.5-flash');
                  if (newProvider === 'cerebras') setModel('llama3.1-8b');
                  if (newProvider === 'sambanova') setModel('Meta-Llama-3.3-70B-Instruct');
                  if (newProvider === 'ollama') setModel('gemma4:e4b');
                }}
                className="w-full bg-neutral-900 border border-neutral-700 rounded-lg p-2.5 text-sm outline-none focus:border-indigo-500"
              >
                <option value="groq">Groq (Cloud)</option>
                <option value="gemini">Google Gemini (Free)</option>
                <option value="cerebras">Cerebras (Free)</option>
                <option value="sambanova">SambaNova (Free)</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2 block">Model</label>
              <select 
                value={model} 
                onChange={e => setModel(e.target.value)}
                className="w-full bg-neutral-900 border border-neutral-700 rounded-lg p-2.5 text-sm outline-none focus:border-indigo-500"
              >
                {provider === 'groq' && (
                  <>
                    <option value="llama-3.3-70b-versatile">llama-3.3-70b</option>
                    <option value="llama-3.1-8b-instant">llama-3.1-8b</option>
                    <option value="mixtral-8x7b-32768">mixtral-8x7b</option>
                  </>
                )}
                {provider === 'gemini' && (
                  <>
                    <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                    <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                  </>
                )}
                {provider === 'cerebras' && (
                  <>
                    <option value="llama3.1-8b">Llama 3.1 8B</option>
                  </>
                )}
                {provider === 'sambanova' && (
                  <>
                    <option value="Meta-Llama-3.1-405B-Instruct">Llama 3.1 405B</option>
                    <option value="Meta-Llama-3.3-70B-Instruct">Llama 3.3 70B</option>
                    <option value="DeepSeek-R1">DeepSeek R1</option>
                  </>
                )}
                {provider === 'ollama' && (
                  <>
                    <option value="gemma4:e4b">gemma4:e4b</option>
                    <option value="deepseek-r1:8b">deepseek-r1:8b</option>
                  </>
                )}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Main Area */}
      <div className="flex-1 overflow-y-auto relative p-8">
        {activeTab === 'playground' && (
          <div className="max-w-6xl mx-auto flex flex-col min-h-full pb-48">
            
            <AnimatePresence mode="wait">
              {step !== 'idle' && (
                <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
                  <PipelineVisualizer currentStep={step} thinkingLogs={thinkingLogs} />
                </motion.div>
              )}
            </AnimatePresence>

            {result && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-6">
                
                {/* Winner Badge */}
                <div className="flex justify-center mb-4">
                  <div className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white px-6 py-2 rounded-full font-bold shadow-lg shadow-indigo-500/20 text-lg">
                    {result.winner}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-8">
                  {/* Baseline Column */}
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center gap-2 text-neutral-400 border-b border-neutral-800 pb-2">
                      <LayoutDashboard className="w-5 h-5 text-purple-400" />
                      <h2 className="font-semibold text-lg text-neutral-200">Baseline SQL</h2>
                      {result.baseline_time_sec && (
                        <span className="ml-auto text-xs text-neutral-500">{result.baseline_time_sec}s</span>
                      )}
                    </div>
                    <SqlEditor sql={result.baseline_sql} />
                    <ResultsDataGrid data={result.baseline_rows} error={result.baseline_error} />
                    <ChartVisualizer data={result.baseline_rows} />
                  </div>

                  {/* System Column */}
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center gap-2 text-neutral-400 border-b border-neutral-800 pb-2">
                      <Shield className="w-5 h-5 text-indigo-400" />
                      <h2 className="font-semibold text-lg text-neutral-200">QueryShield SQL</h2>
                      {result.system_time_sec && (
                        <span className="ml-auto text-xs text-neutral-500">{result.system_time_sec}s</span>
                      )}
                    </div>
                    <SqlEditor sql={result.system_sql} />
                    <ResultsDataGrid data={result.system_rows} error={result.system_error} />
                    <ChartVisualizer data={result.system_rows} />
                  </div>
                </div>

              </motion.div>
            )}

            {!result && step === 'idle' && (
              <div className="flex-1 flex flex-col items-center justify-center text-center mt-20 opacity-50">
                <DatabaseZap className="w-20 h-20 mb-6 text-indigo-500" />
                <h2 className="text-2xl font-bold text-neutral-300">Evaluate Text-to-SQL</h2>
                <p className="max-w-md mt-3 text-neutral-400">Select a database from the sidebar (or upload your own!) and type a natural language query to see how QueryShield outperforms the baseline.</p>
              </div>
            )}

            {/* Floating Input */}
            <motion.div 
              initial={{ y: 100, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ type: "spring", stiffness: 200, damping: 20 }}
              className="fixed bottom-8 left-[calc(50%+9rem)] -translate-x-1/2 w-full max-w-3xl px-6 z-50"
            >
              <form onSubmit={handleSubmit} className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl blur opacity-25 group-focus-within:opacity-50 transition duration-1000" />
                <div className="relative flex items-center">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder={`Ask a question about ${selectedDb || 'the database'}...`}
                    className="w-full glass-input bg-neutral-900 rounded-2xl py-4 pl-6 pr-14 text-white text-lg shadow-2xl"
                  />
                  <button
                    type="submit"
                    disabled={!question.trim() || isLoading}
                    className="absolute right-3 p-2 bg-indigo-500 hover:bg-indigo-400 disabled:bg-neutral-800 disabled:text-neutral-500 text-white rounded-xl transition-colors"
                  >
                    {isLoading ? (
                      <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
                        <Send className="w-5 h-5" />
                      </motion.div>
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}

        {activeTab === 'benchmarks' && (
          <div className="max-w-6xl mx-auto flex flex-col gap-6">
            <h2 className="text-2xl font-bold border-b border-neutral-800 pb-4 flex items-center gap-2">
              <Activity className="w-6 h-6 text-indigo-400" /> Benchmark Results
            </h2>
            
            <div className="grid grid-cols-1 gap-4">
              {benchmarks.map((b, i) => (
                <div key={i} className="glass-panel p-6 rounded-2xl border-neutral-800/50 flex flex-col gap-4">
                  <h3 className="font-semibold text-lg text-indigo-300">{b._filename}</h3>
                  <div className="grid grid-cols-4 gap-4">
                    <div className="bg-neutral-900/50 p-4 rounded-xl">
                      <div className="text-sm text-neutral-500 uppercase tracking-wider font-semibold mb-1">Baseline Acc</div>
                      <div className="text-2xl font-bold">{b.metrics?.baseline_accuracy * 100 || 0}%</div>
                    </div>
                    <div className="bg-indigo-500/10 border border-indigo-500/20 p-4 rounded-xl">
                      <div className="text-sm text-indigo-400/80 uppercase tracking-wider font-semibold mb-1">System Acc</div>
                      <div className="text-2xl font-bold text-indigo-300">{b.metrics?.system_accuracy * 100 || 0}%</div>
                    </div>
                    <div className="bg-neutral-900/50 p-4 rounded-xl">
                      <div className="text-sm text-neutral-500 uppercase tracking-wider font-semibold mb-1">Improvement</div>
                      <div className="text-2xl font-bold text-emerald-400">+{b.metrics?.improvement_percent || (b.metrics?.improvement * 100).toFixed(1)}%</div>
                    </div>
                    <div className="bg-neutral-900/50 p-4 rounded-xl">
                      <div className="text-sm text-neutral-500 uppercase tracking-wider font-semibold mb-1">Total Queries</div>
                      <div className="text-2xl font-bold">{b.metrics?.total_queries || 0}</div>
                    </div>
                  </div>
                </div>
              ))}
              {benchmarks.length === 0 && (
                <p className="text-neutral-500">No benchmarks found in the results directory.</p>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

export default App;

import React from 'react';
import { motion } from 'framer-motion';
import Editor from '@monaco-editor/react';
import { Copy, Code2, CheckCircle2 } from 'lucide-react';

interface SqlEditorProps {
  sql: string;
}

export function SqlEditor({ sql }: SqlEditorProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!sql) return null;

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-panel rounded-2xl overflow-hidden flex flex-col mt-6 shadow-indigo-900/10 shadow-2xl border-indigo-500/20"
    >
      <div className="flex items-center justify-between px-4 py-3 bg-neutral-900 border-b border-neutral-800">
        <div className="flex items-center gap-2 text-indigo-400">
          <Code2 className="w-5 h-5" />
          <span className="font-semibold tracking-wide text-sm">Generated SQL</span>
        </div>
        <button 
          onClick={handleCopy}
          className="p-1.5 hover:bg-neutral-800 rounded-md transition-colors text-neutral-400 hover:text-white"
        >
          {copied ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
        </button>
      </div>
      <div className="p-4 bg-[#0d0d0d]">
        <Editor
          height="200px"
          defaultLanguage="sql"
          value={sql}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            readOnly: true,
            scrollBeyondLastLine: false,
            padding: { top: 10, bottom: 10 },
            lineNumbers: "off",
            glyphMargin: false,
            folding: false,
            lineDecorationsWidth: 0,
            lineNumbersMinChars: 0,
          }}
        />
      </div>
    </motion.div>
  );
}

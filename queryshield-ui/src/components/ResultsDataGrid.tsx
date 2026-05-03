import React from 'react';
import { motion } from 'framer-motion';
import { Database, AlertTriangle } from 'lucide-react';

interface ResultsDataGridProps {
  data: any[];
  error?: string;
}

export function ResultsDataGrid({ data, error }: ResultsDataGridProps) {
  if (error) {
    return (
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel mt-6 rounded-2xl p-6 border-rose-500/30 bg-rose-500/5 text-rose-400 flex items-start gap-4"
      >
        <AlertTriangle className="w-6 h-6 shrink-0 mt-0.5" />
        <div>
          <h3 className="font-semibold text-rose-300 mb-1">Execution Error</h3>
          <p className="text-sm opacity-90">{error}</p>
        </div>
      </motion.div>
    );
  }

  if (!data || data.length === 0) return null;

  const columns = Object.keys(data[0]);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel mt-6 rounded-2xl overflow-hidden shadow-emerald-900/5 shadow-2xl"
    >
      <div className="flex items-center gap-2 px-5 py-4 border-b border-neutral-800 bg-neutral-900/80">
        <Database className="w-5 h-5 text-emerald-400" />
        <span className="font-semibold tracking-wide text-sm text-emerald-100">Query Results</span>
        <span className="ml-auto text-xs text-neutral-500">{data.length} row{data.length !== 1 ? 's' : ''} returned</span>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-neutral-400 uppercase bg-neutral-900/50">
            <tr>
              {columns.map((col, idx) => (
                <th key={idx} className="px-6 py-4 font-medium tracking-wider border-b border-neutral-800/50">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-800/30">
            {data.map((row, rowIdx) => (
              <motion.tr 
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: rowIdx * 0.05 }}
                key={rowIdx} 
                className="hover:bg-neutral-800/30 transition-colors"
              >
                {columns.map((col, colIdx) => (
                  <td key={colIdx} className="px-6 py-4 whitespace-nowrap text-neutral-300">
                    {row[col] !== null ? String(row[col]) : <span className="text-neutral-600 italic">NULL</span>}
                  </td>
                ))}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

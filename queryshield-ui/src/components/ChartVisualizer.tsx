import React from 'react';
import { motion } from 'framer-motion';
import { BarChart3, PieChart as PieIcon, TrendingUp } from 'lucide-react';

interface ChartVisualizerProps {
  data: any[];
}

/**
 * Auto-detect if data is chartable and render a simple bar chart.
 * Conditions: 2+ columns, one numeric column, one string column.
 */
export function ChartVisualizer({ data }: ChartVisualizerProps) {
  if (!data || data.length === 0 || data.length > 50) return null;

  const columns = Object.keys(data[0]);
  if (columns.length < 2) return null;

  // Find the best label column (string) and value column (numeric)
  let labelCol: string | null = null;
  let valueCol: string | null = null;

  for (const col of columns) {
    const sample = data[0][col];
    if (typeof sample === 'number' && !valueCol) {
      valueCol = col;
    } else if (typeof sample === 'string' && !labelCol) {
      labelCol = col;
    }
  }

  // Try to coerce string numbers to actual numbers
  if (!valueCol) {
    for (const col of columns) {
      if (col === labelCol) continue;
      const allNumeric = data.every(row => !isNaN(Number(row[col])) && row[col] !== null && row[col] !== '');
      if (allNumeric) {
        valueCol = col;
        break;
      }
    }
  }

  if (!labelCol && !valueCol) return null;
  // If we only found a value col, use the first non-value column as label
  if (!labelCol) {
    labelCol = columns.find(c => c !== valueCol) || columns[0];
  }
  if (!valueCol) return null;

  const chartData = data.map(row => ({
    label: String(row[labelCol!]),
    value: Number(row[valueCol!]) || 0,
  }));

  const maxValue = Math.max(...chartData.map(d => d.value), 1);

  // Determine color palette
  const colors = [
    'bg-indigo-500', 'bg-purple-500', 'bg-cyan-500', 'bg-emerald-500',
    'bg-amber-500', 'bg-rose-500', 'bg-sky-500', 'bg-fuchsia-500',
    'bg-teal-500', 'bg-orange-500',
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel mt-6 rounded-2xl overflow-hidden"
    >
      <div className="flex items-center gap-2 px-5 py-4 border-b border-neutral-800 bg-neutral-900/80">
        <BarChart3 className="w-5 h-5 text-indigo-400" />
        <span className="font-semibold tracking-wide text-sm text-indigo-100">Data Visualization</span>
        <span className="ml-auto text-xs text-neutral-500">{valueCol} by {labelCol}</span>
      </div>

      <div className="p-6 space-y-3">
        {chartData.slice(0, 15).map((item, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: 'auto' }}
            transition={{ delay: idx * 0.05 }}
            className="flex items-center gap-3"
          >
            <span className="text-xs text-neutral-400 w-32 truncate text-right flex-shrink-0" title={item.label}>
              {item.label}
            </span>
            <div className="flex-1 h-7 bg-neutral-800/50 rounded-lg overflow-hidden relative">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${(item.value / maxValue) * 100}%` }}
                transition={{ duration: 0.8, delay: idx * 0.05, ease: "easeOut" }}
                className={`h-full ${colors[idx % colors.length]} rounded-lg flex items-center justify-end pr-2`}
              >
                <span className="text-[10px] font-bold text-white/90 drop-shadow-lg">
                  {item.value.toLocaleString()}
                </span>
              </motion.div>
            </div>
          </motion.div>
        ))}
        {chartData.length > 15 && (
          <p className="text-xs text-neutral-500 text-center pt-2">
            Showing top 15 of {chartData.length} results
          </p>
        )}
      </div>
    </motion.div>
  );
}

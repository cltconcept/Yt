'use client';

import { useEffect, useRef, useState } from 'react';
import { Terminal as TerminalIcon, Trash2, Download } from 'lucide-react';

export interface LogEntry {
  id: string;
  timestamp: Date;
  type: 'info' | 'success' | 'warning' | 'error' | 'action';
  message: string;
}

interface TerminalProps {
  logs: LogEntry[];
  onClear: () => void;
  onCommand?: (command: string) => void;
}

export function Terminal({ logs, onClear, onCommand }: TerminalProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [currentDate, setCurrentDate] = useState<string>('');
  const [inputValue, setInputValue] = useState<string>('');

  // Set date on client only
  useEffect(() => {
    setCurrentDate(new Date().toLocaleDateString('fr-FR'));
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const command = inputValue.trim();
    if (command) {
      // Afficher la commande dans les logs
      if (onCommand) {
        onCommand(command);
      }
      setInputValue('');
    }
  };

  // Auto-scroll to bottom on new logs
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getTypeStyles = (type: LogEntry['type']) => {
    switch (type) {
      case 'success':
        return 'text-green-400';
      case 'warning':
        return 'text-yellow-400';
      case 'error':
        return 'text-red-400';
      case 'action':
        return 'text-primary-400';
      default:
        return 'text-dark-300';
    }
  };

  const getTypePrefix = (type: LogEntry['type']) => {
    switch (type) {
      case 'success':
        return '[OK]';
      case 'warning':
        return '[WARN]';
      case 'error':
        return '[ERR]';
      case 'action':
        return '[>>]';
      default:
        return '[i]';
    }
  };

  const exportLogs = () => {
    const content = logs.map(log => 
      `[${formatTime(log.timestamp)}] ${getTypePrefix(log.type)} ${log.message}`
    ).join('\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs_${new Date().toISOString().slice(0,10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="glass rounded-2xl flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-dark-700">
        <div className="flex items-center gap-2">
          <TerminalIcon className="w-4 h-4 text-green-400" />
          <span className="text-sm font-semibold text-white">Terminal</span>
          <span className="text-xs text-dark-500 bg-dark-700 px-2 py-0.5 rounded-full">
            {logs.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={exportLogs}
            className="p-1.5 rounded-lg text-dark-400 hover:text-white hover:bg-dark-700 transition-all"
            title="Exporter les logs"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onClear}
            className="p-1.5 rounded-lg text-dark-400 hover:text-red-400 hover:bg-dark-700 transition-all"
            title="Effacer"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Logs */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-2 md:p-3 font-mono text-[11px] md:text-xs space-y-0.5 md:space-y-1"
      >
        {logs.length === 0 ? (
          <div className="text-dark-500 text-center py-8">
            <TerminalIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Aucune action pour le moment</p>
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex gap-2 leading-relaxed">
              <span className="text-dark-500 shrink-0">
                {formatTime(log.timestamp)}
              </span>
              <span className={`shrink-0 ${getTypeStyles(log.type)}`}>
                {getTypePrefix(log.type)}
              </span>
              <span className={getTypeStyles(log.type)}>
                {log.message}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Input area */}
      {onCommand && (
        <form onSubmit={handleSubmit} className="border-t border-dark-700 px-4 py-2">
          <div className="flex items-center gap-2">
            <span className="text-dark-500 font-mono text-xs">$</span>
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Tapez une commande (ex: /retranscript)..."
              className="flex-1 bg-transparent text-white text-xs font-mono outline-none placeholder-dark-600"
              autoComplete="off"
            />
          </div>
        </form>
      )}

      {/* Status bar */}
      <div className="px-4 py-2 border-t border-dark-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-xs text-dark-400">Pret</span>
        </div>
        <span className="text-xs text-dark-500">
          {currentDate}
        </span>
      </div>
    </div>
  );
}


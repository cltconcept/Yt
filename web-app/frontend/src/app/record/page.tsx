'use client';

import { useState, useCallback } from 'react';
import { VideoRecorder, RecordingConfigContext, RecordingConfigContextType } from '@/components/VideoRecorder';

export default function RecordPage() {
  const [sharedConfig, setSharedConfig] = useState<RecordingConfigContextType['config']>({
    layout: 'overlay',
    webcamEnabled: true,
    micEnabled: true,
    micVolume: 100,
    webcamPosition: { x: 93, y: 88 },
    webcamSize: 232,
    webcamShape: 'rounded',
    webcamBorderColor: '#8B5CF6',
    webcamBorderWidth: 3,
    autoProcess: true,
    autoIllustrate: false,
  });

  const addLog = useCallback((type: string, message: string) => {
    // Logs silencieux - peuvent être utilisés pour le debug console
    console.log(`[${type}] ${message}`);
  }, []);

  const handleProcessingComplete = useCallback(async (folderName: string, autoProcess: boolean, autoIllustrate: boolean, layout: string) => {
    console.log('Traitement terminé');
    
    if (autoProcess) {
      console.log('Pipeline complet en cours (12 étapes)');
    }
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Header */}
      <header className="shrink-0 border-b border-white/5 bg-zinc-950/50 backdrop-blur-sm">
        <div className="px-6 py-4">
          <h1 className="text-xl font-semibold text-white">Enregistrement</h1>
          <p className="text-sm text-zinc-400">Capturez votre écran et webcam</p>
        </div>
      </header>

      {/* Content */}
      <RecordingConfigContext.Provider value={{ config: sharedConfig, setConfig: setSharedConfig }}>
        <div className="flex-1 flex overflow-hidden">
          {/* Main - Preview */}
          <div className="flex-1 overflow-y-auto p-6 pr-4">
            <VideoRecorder 
              onLog={addLog} 
              showControlsInline={false} 
              sharedConfig={{ config: sharedConfig, setConfig: setSharedConfig }} 
              onProcessingComplete={handleProcessingComplete} 
            />
          </div>

          {/* Right Panel - Controls */}
          <div className="w-[440px] shrink-0 flex flex-col border-l border-white/5 overflow-hidden bg-zinc-950/50">
            {/* Controls */}
            <div className="flex-1 overflow-y-auto p-4">
              <VideoRecorder 
                onLog={addLog} 
                showControlsOnly={true} 
                sharedConfig={{ config: sharedConfig, setConfig: setSharedConfig }} 
                onProcessingComplete={handleProcessingComplete} 
              />
            </div>
          </div>
        </div>
      </RecordingConfigContext.Provider>
    </div>
  );
}


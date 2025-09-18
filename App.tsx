import React, { useState, useCallback } from 'react';
import { FileUpload } from './components/FileUpload';
import { SettingsPanel } from './components/SettingsPanel';
import { DownloadIcon } from './components/icons/DownloadIcon';
import { CutIcon } from './components/icons/CutIcon';
import { processXml } from './services/xmlProcessor';
import type { SilenceSettings } from './types';

const App: React.FC = () => {
  const [xmlFile, setXmlFile] = useState<File | null>(null);
  const [xmlContent, setXmlContent] = useState<string | null>(null);
  const [processedXmlContent, setProcessedXmlContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<SilenceSettings>({
    silenceThreshold: 0.5,
    clipPadding: 0.2,
  });

  const handleFileSelect = (file: File) => {
    if (file && file.type === 'text/xml') {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        setXmlContent(content);
        setXmlFile(file);
        setProcessedXmlContent(null);
        setError(null);
      };
      reader.onerror = () => {
        setError('Failed to read the file.');
      };
      reader.readAsText(file);
    } else {
      setError('Please upload a valid XML file.');
    }
  };

  const handleProcess = useCallback(async () => {
    if (!xmlContent) {
      setError('No XML content to process.');
      return;
    }
    setIsLoading(true);
    setError(null);
    setProcessedXmlContent(null);

    // Simulate processing time for better UX
    await new Promise(resolve => setTimeout(resolve, 1500));

    try {
      const result = processXml(xmlContent, settings);
      setProcessedXmlContent(result);
    } catch (e) {
      if (e instanceof Error) {
        setError(`Processing failed: ${e.message}`);
      } else {
        setError('An unknown error occurred during processing.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [xmlContent, settings]);

  const handleDownload = () => {
    if (!processedXmlContent || !xmlFile) return;

    const blob = new Blob([processedXmlContent], { type: 'text/xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const originalName = xmlFile.name.replace(/\.xml$/i, '');
    a.download = `${originalName}_edited.xml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200 flex flex-col items-center justify-center p-4 sm:p-6 lg:p-8 font-sans">
      <div className="w-full max-w-4xl mx-auto">
        <header className="text-center mb-8">
          <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2">Premiere Silence Cutter</h1>
          <p className="text-lg text-gray-400">Automate your jump cuts. Upload an XML, cut the silence, and get back to creating.</p>
        </header>

        <main className="bg-gray-800/50 rounded-2xl shadow-2xl backdrop-blur-sm border border-gray-700 p-6 sm:p-8">
          {error && (
            <div className="bg-red-500/20 border border-red-500 text-red-300 px-4 py-3 rounded-lg mb-6 text-center" role="alert">
              <p>{error}</p>
            </div>
          )}

          {!xmlFile ? (
            <FileUpload onFileSelect={handleFileSelect} />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="flex flex-col">
                 <h2 className="text-2xl font-semibold mb-4 text-white border-b border-gray-600 pb-2">1. Adjust Settings</h2>
                <SettingsPanel settings={settings} onSettingsChange={setSettings} />

                <button
                  onClick={handleProcess}
                  disabled={isLoading}
                  className="w-full mt-8 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:cursor-not-allowed text-white font-bold py-3 px-4 rounded-lg flex items-center justify-center transition-all duration-300 transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:ring-opacity-75 shadow-lg"
                >
                  {isLoading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Processing...
                    </>
                  ) : (
                    <>
                      <CutIcon className="w-5 h-5 mr-2" />
                      Cut Silences
                    </>
                  )}
                </button>
              </div>

              <div className="flex flex-col justify-between bg-gray-900/50 p-6 rounded-lg border border-gray-700">
                 <div>
                    <h2 className="text-2xl font-semibold mb-4 text-white border-b border-gray-600 pb-2">2. Download Result</h2>
                    <p className="text-gray-400 mb-2">File: <span className="font-medium text-indigo-400">{xmlFile.name}</span></p>
                    <p className="text-gray-400">Once processing is complete, your new XML file will be ready to download.</p>
                </div>
                 <button
                  onClick={handleDownload}
                  disabled={!processedXmlContent}
                  className="w-full mt-6 bg-green-600 hover:bg-green-500 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold py-3 px-4 rounded-lg flex items-center justify-center transition-all duration-300 transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-opacity-75 shadow-lg"
                >
                  <DownloadIcon className="w-5 h-5 mr-2" />
                  Download Edited XML
                </button>
              </div>
            </div>
          )}
        </main>
        
        <footer className="text-center mt-8 text-gray-500 text-sm">
            <p>Made for Adobe Premiere Pro editors.</p>
        </footer>
      </div>
    </div>
  );
};

export default App;

import React from 'react';
import type { SilenceSettings } from '../types';

interface SettingsPanelProps {
  settings: SilenceSettings;
  onSettingsChange: (newSettings: SilenceSettings) => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({ settings, onSettingsChange }) => {
  const handleSettingChange = (key: keyof SilenceSettings, value: string) => {
    onSettingsChange({ ...settings, [key]: parseFloat(value) });
  };

  return (
    <div className="space-y-6">
      <div>
        <label htmlFor="silenceThreshold" className="block text-sm font-medium text-gray-300 mb-2">
          Silence Threshold (seconds)
        </label>
        <div className="flex items-center space-x-4">
          <input
            type="range"
            id="silenceThreshold"
            min="0.1"
            max="5"
            step="0.1"
            value={settings.silenceThreshold}
            onChange={(e) => handleSettingChange('silenceThreshold', e.target.value)}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
          <span className="bg-gray-700 text-white text-sm font-semibold px-3 py-1 rounded-md w-20 text-center">
            {settings.silenceThreshold.toFixed(1)}s
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-1">Cuts any "silent" section longer than this.</p>
      </div>
      <div>
        <label htmlFor="clipPadding" className="block text-sm font-medium text-gray-300 mb-2">
          Clip Padding (seconds)
        </label>
        <div className="flex items-center space-x-4">
          <input
            type="range"
            id="clipPadding"
            min="0"
            max="2"
            step="0.05"
            value={settings.clipPadding}
            onChange={(e) => handleSettingChange('clipPadding', e.target.value)}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
          <span className="bg-gray-700 text-white text-sm font-semibold px-3 py-1 rounded-md w-20 text-center">
            {settings.clipPadding.toFixed(2)}s
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-1">Keeps this much audio around the cuts.</p>
      </div>
    </div>
  );
};

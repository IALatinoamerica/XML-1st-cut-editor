import React, { useState, useCallback } from 'react';
import { UploadIcon } from './icons/UploadIcon';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onFileSelect }) => {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragEnter = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileSelect(e.dataTransfer.files[0]);
    }
  }, [onFileSelect]);
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
        onFileSelect(e.target.files[0]);
    }
  };

  return (
    <div
      className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 ${isDragging ? 'border-indigo-500 bg-indigo-500/10' : 'border-gray-600 hover:border-indigo-500'}`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div className="flex flex-col items-center justify-center">
        <UploadIcon className="w-16 h-16 text-gray-500 mb-4" />
        <p className="text-xl font-semibold text-gray-300">Drag & Drop your Premiere XML file here</p>
        <p className="text-gray-500 mt-2">or</p>
        <label htmlFor="file-upload" className="mt-4 px-6 py-2 bg-indigo-600 text-white rounded-md cursor-pointer hover:bg-indigo-500 transition-colors">
            Select File
        </label>
        <input id="file-upload" type="file" className="hidden" accept=".xml,text/xml" onChange={handleFileChange} />
      </div>
    </div>
  );
};

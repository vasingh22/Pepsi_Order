import { useState, useRef } from "react";
import type { DragEvent, ChangeEvent } from "react";

interface FileUploadProps {
  onFilesUpload: (files: File[]) => void;
  onProcess?: () => void;
}

interface FileWithPreview {
  file: File;
  preview?: string;
}

const FileUpload = ({ onFilesUpload, onProcess }: FileUploadProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const acceptedTypes = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/pdf",
  ];
  const maxSize = 10 * 1024 * 1024; // 10MB

  const validateFile = (file: File): string | null => {
    if (!acceptedTypes.includes(file.type)) {
      return `${file.name}: Invalid file type. Only images (JPEG, PNG, WEBP) and PDFs are allowed.`;
    }
    if (file.size > maxSize) {
      return `${file.name}: File size exceeds 10MB limit.`;
    }
    return null;
  };

  const processFiles = (fileList: FileList | null) => {
    if (!fileList) return;

    const newFiles: FileWithPreview[] = [];
    const errors: string[] = [];

    Array.from(fileList).forEach((file) => {
      const error = validateFile(file);
      if (error) {
        errors.push(error);
      } else {
        const fileWithPreview: FileWithPreview = { file };

        // Generate preview for images
        if (file.type.startsWith("image/")) {
          const reader = new FileReader();
          reader.onload = (e) => {
            fileWithPreview.preview = e.target?.result as string;
            setFiles((prev) => [...prev]);
          };
          reader.readAsDataURL(file);
        }

        newFiles.push(fileWithPreview);
      }
    });

    if (errors.length > 0) {
      alert(errors.join("\n"));
    }

    if (newFiles.length > 0) {
      const updatedFiles = [...files, ...newFiles];
      setFiles(updatedFiles);
      onFilesUpload(updatedFiles.map((f) => f.file));
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    processFiles(e.dataTransfer.files);
  };

  const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    processFiles(e.target.files);
  };

  const removeFile = (index: number) => {
    const updatedFiles = files.filter((_, i) => i !== index);
    setFiles(updatedFiles);
    onFilesUpload(updatedFiles.map((f) => f.file));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  return (
    <section className="min-h-screen py-16 px-8 bg-gradient-to-b from-gray-50 to-gray-200">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-gray-800 text-center mb-4">
          Upload Order Documents
        </h2>
        <p className="text-base md:text-lg text-gray-600 text-center mb-12">
          Upload one or more images (JPEG, PNG, WEBP) or PDF files containing
          order information
        </p>

        {/* Dropzone */}
        <div
          className={`border-3 border-dashed rounded-3xl p-16 text-center cursor-pointer transition-all duration-300 bg-white ${
            isDragging
              ? "border-[#667eea] bg-gray-100 scale-105"
              : "border-gray-300 hover:border-[#667eea] hover:bg-gray-50"
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="pointer-events-none">
            <div className="text-5xl mb-4 animate-float">📁</div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">
              Drag & Drop Files Here
            </h3>
            <p className="text-base text-gray-600 mb-4">or click to browse</p>
            <div className="flex flex-col gap-2 text-sm text-gray-500">
              <span>Supported: JPG, PNG, WEBP, PDF</span>
              <span>Max size: 10MB per file</span>
            </div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/jpeg,image/jpg,image/png,image/webp,application/pdf"
            onChange={handleFileInput}
            className="hidden"
          />
        </div>

        {/* Files Preview */}
        {files.length > 0 && (
          <div className="mt-12 bg-white rounded-3xl p-8 shadow-lg">
            <div className="flex justify-between items-center mb-6 pb-4 border-b-2 border-gray-200">
              <h3 className="text-xl font-semibold text-gray-800">
                Uploaded Files ({files.length})
              </h3>
              <button
                className="px-4 py-2 bg-transparent text-red-500 border-2 border-red-500 rounded-lg font-semibold transition-all duration-300 hover:bg-red-500 hover:text-white"
                onClick={() => {
                  setFiles([]);
                  onFilesUpload([]);
                }}
              >
                Clear All
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 mb-8">
              {files.map((fileWithPreview, index) => (
                <div
                  key={index}
                  className="relative border-2 border-gray-200 rounded-xl overflow-hidden transition-all duration-300 hover:-translate-y-2 hover:shadow-xl hover:border-[#667eea] bg-white group"
                >
                  <div className="w-full h-48 flex items-center justify-center bg-gray-50 overflow-hidden">
                    {fileWithPreview.preview ? (
                      <img
                        src={fileWithPreview.preview}
                        alt={fileWithPreview.file.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="flex flex-col items-center gap-2">
                        <span className="text-5xl">📄</span>
                        <span className="text-base font-semibold text-gray-600">
                          PDF
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="p-4">
                    <p
                      className="text-sm font-semibold text-gray-800 mb-1 truncate"
                      title={fileWithPreview.file.name}
                    >
                      {fileWithPreview.file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(fileWithPreview.file.size)}
                    </p>
                  </div>
                  <button
                    className="absolute top-2 right-2 w-8 h-8 rounded-full bg-red-500/90 text-white text-xl flex items-center justify-center transition-all duration-300 opacity-0 group-hover:opacity-100 hover:bg-red-600 hover:scale-110"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(index);
                    }}
                    title="Remove file"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={onProcess}
              className="w-full px-8 py-4 bg-gradient-to-r from-[#667eea] to-[#764ba2] text-white rounded-xl text-base font-semibold transition-all duration-300 flex items-center justify-center gap-2 hover:-translate-y-1 hover:shadow-2xl hover:shadow-[#667eea]/40"
            >
              <span>
                Process {files.length} File{files.length > 1 ? "s" : ""}
              </span>
              <span className="text-xl transition-transform duration-300 group-hover:translate-x-1">
                →
              </span>
            </button>
          </div>
        )}
      </div>
    </section>
  );
};

export default FileUpload;

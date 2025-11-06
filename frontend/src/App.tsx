import { useState } from "react";
import Hero from "./components/Hero";
import FileUpload from "./components/FileUpload";
import Dashboard from "./components/Dashboard";

function App() {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [showDashboard, setShowDashboard] = useState(false);

  const handleFilesUpload = (files: File[]) => {
    setUploadedFiles(files);
    console.log("Files ready to send to backend:", files);
    // TODO: Integrate with backend API when ready
  };

  const handleProcessFiles = () => {
    if (uploadedFiles.length > 0) {
      console.log("Processing files:", uploadedFiles);
      // TODO: Send files to backend
      // For now, just show the dashboard with mock data
      setShowDashboard(true);
    }
  };

  const handleBackToUpload = () => {
    setShowDashboard(false);
  };

  // Show dashboard if files are being processed
  if (showDashboard) {
    return (
      <div>
        <div className="bg-gradient-to-r from-[#667eea] to-[#764ba2] p-4 flex items-center justify-between">
          <button
            onClick={handleBackToUpload}
            className="px-4 py-2 bg-white/20 backdrop-blur-md text-white rounded-lg font-semibold hover:bg-white/30 transition-all flex items-center gap-2"
          >
            <span>←</span>
            <span>Back to Upload</span>
          </button>
          <h1 className="text-xl font-bold text-white">
            {uploadedFiles.length} File(s) Processed
          </h1>
        </div>
        <Dashboard />
      </div>
    );
  }

  return (
    <div className="min-h-screen font-sans antialiased">
      <Hero />
      <FileUpload
        onFilesUpload={handleFilesUpload}
        onProcess={handleProcessFiles}
      />
    </div>
  );
}

export default App;

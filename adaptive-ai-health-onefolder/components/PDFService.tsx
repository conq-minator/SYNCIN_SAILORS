import { useState } from 'react';

interface PDFServiceProps {
  className?: string;
}

export default function PDFService({ className = '' }: PDFServiceProps) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [extractedText, setExtractedText] = useState('');

  // Generate PDF function
  const generatePDF = async (data: {
    patient_name: string;
    age: number;
    symptoms: string[];
    prediction: string;
  }) => {
    setLoading(true);
    setMessage('Generating PDF...');

    try {
      const response = await fetch('/api/pdf/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to generate PDF');
      }

      // Download the PDF
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Medical_Report_${data.patient_name.replace(/\s+/g, '_')}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setMessage('✅ PDF generated successfully!');
    } catch (error) {
      setMessage(`❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  // Extract text from PDF function
  const extractText = async (file: File) => {
    setLoading(true);
    setMessage('Extracting text...');
    setExtractedText('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/pdf/extract-text', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to extract text');
      }

      const result = await response.json();
      setExtractedText(result.content);
      setMessage(`✅ Text extracted from "${result.filename}" (${result.metadata.pages} pages)`);
    } catch (error) {
      setMessage(`❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`p-6 bg-white rounded-lg shadow-md ${className}`}>
      <h2 className="text-2xl font-bold mb-4 text-gray-800">PDF Services</h2>

      {/* Status Message */}
      {message && (
        <div className={`p-3 rounded mb-4 ${
          message.includes('✅') ? 'bg-green-100 text-green-800' :
          message.includes('❌') ? 'bg-red-100 text-red-800' :
          'bg-blue-100 text-blue-800'
        }`}>
          {message}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {/* PDF Generation Section */}
        <div className="border rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-3">Generate Medical Report</h3>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.target as HTMLFormElement);
              const data = {
                patient_name: formData.get('patient_name') as string,
                age: parseInt(formData.get('age') as string),
                symptoms: (formData.get('symptoms') as string).split(',').map(s => s.trim()).filter(s => s),
                prediction: formData.get('prediction') as string
              };
              generatePDF(data);
            }}
            className="space-y-3"
          >
            <input
              name="patient_name"
              type="text"
              placeholder="Patient Name"
              required
              className="w-full p-2 border rounded"
            />
            <input
              name="age"
              type="number"
              placeholder="Age"
              required
              min="0"
              max="150"
              className="w-full p-2 border rounded"
            />
            <input
              name="symptoms"
              type="text"
              placeholder="Symptoms (comma-separated)"
              required
              className="w-full p-2 border rounded"
            />
            <input
              name="prediction"
              type="text"
              placeholder="AI Prediction"
              required
              className="w-full p-2 border rounded"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Generating...' : 'Generate PDF Report'}
            </button>
          </form>
        </div>

        {/* Text Extraction Section */}
        <div className="border rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-3">Extract Text from PDF</h3>
          <div className="space-y-3">
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  extractText(file);
                }
              }}
              className="w-full p-2 border rounded"
            />
            {extractedText && (
              <div className="mt-4">
                <h4 className="font-medium mb-2">Extracted Text:</h4>
                <textarea
                  value={extractedText}
                  readOnly
                  rows={8}
                  className="w-full p-2 border rounded bg-gray-50 text-sm"
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
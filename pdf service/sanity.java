// Member 1's Frontend Code (Not your problem!)
const handleDownload = async () => {
    // 1. Send the data to your API
    const response = await fetch("http://backend-api/generate-pdf", {
        method: "POST",
        body: JSON.stringify(patientData) 
    });

    // 2. Catch your PDF and force the browser to download it
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'My_Medical_Report.pdf'); // The user sees this!
    document.body.appendChild(link);
    link.click(); // Bam. Downloaded.
};
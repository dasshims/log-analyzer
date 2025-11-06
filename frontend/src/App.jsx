import { useState } from "react";

const API_URL = "http://localhost:8000/analyze";

function formatNumber(value) {
  return typeof value === "number" ? value.toFixed(2) : value;
}

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleFileChange = (event) => {
    setFile(event.target.files?.[0] ?? null);
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file) {
      setError("Please select a CSV file before uploading.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "Upload failed. Please try again.");
      }

      const data = await response.json();
      setResult(data);
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="layout">
      <section className="panel">
        <h1>Data Health Analyzer</h1>
        <p>
          Upload a CSV containing user activity metrics to validate the data,
          review warning flags, and generate a support-ticket-ready summary.
        </p>

        <form className="upload-form" onSubmit={handleSubmit}>
          <label className="file-input">
            <span>Select CSV file</span>
            <input type="file" accept=".csv,text/csv" onChange={handleFileChange} />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? "Analyzing..." : "Analyze Dataset"}
          </button>
        </form>

        {error && <p className="error">{error}</p>}
      </section>

      {result && (
        <section className="panel results">
          <h2>Summary Statistics</h2>
          <div className="stats-grid">
            <div>
              <span className="label">Total Users</span>
              <span className="value">{result.statistics.total_users}</span>
            </div>
            <div>
              <span className="label">Average Sessions / User</span>
              <span className="value">
                {formatNumber(result.statistics.average_sessions_per_user)}
              </span>
            </div>
            <div>
              <span className="label">% Users with Errors</span>
              <span className="value">
                {formatNumber(result.statistics.percent_users_with_errors)}%
              </span>
            </div>
          </div>

          <h2>Validation Report</h2>
          {result.warnings.length === 0 ? (
            <p>No warnings detected.</p>
          ) : (
            <ul className="warning-list">
              {result.warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          )}

          <h2>Support Ticket Summary</h2>
          {result.ai_summary ? (
            <article className="ai-summary">{result.ai_summary}</article>
          ) : (
            <p className="notice">{result.ai_notice}</p>
          )}
        </section>
      )}
    </main>
  );
}

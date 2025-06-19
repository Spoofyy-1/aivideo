"use client";

import React, { useState } from 'react';

const ScriptPreview = ({ 
  script, 
  scriptAnalysis, 
  companyInfo, 
  userAnswers, 
  onImprove, 
  onApprove, 
  loading 
}) => {
  const [improvementRequest, setImprovementRequest] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleImprove = () => {
    if (improvementRequest.trim()) {
      onImprove(improvementRequest);
      setImprovementRequest('');
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#28a745';
    if (score >= 60) return '#ffc107';
    return '#dc3545';
  };

  const renderSegment = (segmentName, segment) => (
    <div key={segmentName} style={{ marginBottom: '2rem' }}>
      <h4 style={{ 
        color: '#00d4ff', 
        marginBottom: '1rem',
        fontSize: '1.4rem',
        fontWeight: 'bold',
        textTransform: 'capitalize'
      }}>
        🎥 {segmentName.replace('segment', 'Segment ')}
      </h4>
      
      {typeof segment === 'object' ? (
        <div style={{ paddingLeft: '1rem' }}>
          {segment.voiceover_script && (
            <div style={{ marginBottom: '1.5rem' }}>
              <strong style={{ color: '#00d4ff' }}>🎙️ Voiceover:</strong>
              <p style={{ 
                marginTop: '0.5rem', 
                fontSize: '1.1rem', 
                lineHeight: '1.6',
                color: '#ffffff'
              }}>
                "{segment.voiceover_script}"
              </p>
            </div>
          )}
          
          {segment.visual_description && (
            <div style={{ marginBottom: '1.5rem' }}>
              <strong style={{ color: '#00d4ff' }}>📹 Visual:</strong>
              <p style={{ 
                marginTop: '0.5rem', 
                fontSize: '1rem', 
                lineHeight: '1.5',
                color: '#cccccc'
              }}>
                {segment.visual_description}
              </p>
            </div>
          )}
          
          {segment.camera_direction && (
            <div style={{ marginBottom: '1.5rem' }}>
              <strong style={{ color: '#00d4ff' }}>🎬 Camera:</strong>
              <p style={{ 
                marginTop: '0.5rem', 
                fontSize: '1rem', 
                lineHeight: '1.5',
                color: '#cccccc'
              }}>
                {segment.camera_direction}
              </p>
            </div>
          )}
        </div>
      ) : (
        <p style={{ 
          fontSize: '1.1rem', 
          lineHeight: '1.6',
          color: '#ffffff',
          fontStyle: 'italic'
        }}>
          "{segment}"
        </p>
      )}
    </div>
  );

  return (
    <div style={{
      background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
      borderRadius: '20px',
      padding: '2rem',
      margin: '2rem 0',
      color: '#fff',
      fontFamily: 'Orbitron, sans-serif',
      boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
      minHeight: '80vh',
      width: '100%',
      maxWidth: 'none'
    }}>
      <h2 style={{ 
        fontSize: '2.5rem', 
        marginBottom: '2rem', 
        textAlign: 'center',
        background: 'linear-gradient(45deg, #00d4ff, #ffffff)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        fontWeight: 'bold'
      }}>
        📝 Your AI-Generated Script
      </h2>

      {/* Script Quality Analysis */}
      {scriptAnalysis && (
        <div className="script-analysis">
          <div className="quality-score">
            <span style={{ color: '#666' }}>VEO-3 Optimization Score: </span>
            <strong style={{ color: getScoreColor(scriptAnalysis.audio_quality_score) }}>
              {scriptAnalysis.audio_quality_score}/100
            </strong>
          </div>
          
          {scriptAnalysis.overall_recommendations?.length > 0 && (
            <div className="recommendations">
              <strong style={{ color: '#ffc107' }}>💡 Recommendations:</strong>
              <ul style={{ marginLeft: '1rem', marginTop: '0.5rem' }}>
                {scriptAnalysis.overall_recommendations.map((rec, idx) => (
                  <li key={idx} style={{ color: '#666' }}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Script Content */}
      <div style={{
        background: 'rgba(255,255,255,0.1)',
        borderRadius: '15px',
        padding: '2.5rem',
        marginBottom: '2rem',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255,255,255,0.2)'
      }}>
        <h3 style={{ 
          color: '#00d4ff', 
          marginBottom: '2rem',
          fontSize: '1.8rem',
          fontWeight: 'bold'
        }}>
          🎬 Video Script
        </h3>
        
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '12px',
          padding: '2rem',
          fontSize: '1.2rem',
          lineHeight: '1.8',
          fontFamily: 'system-ui, sans-serif',
          color: '#ffffff',
          whiteSpace: 'pre-wrap',
          border: '2px solid rgba(0,212,255,0.3)',
          minHeight: '200px'
        }}>
          {typeof script === 'object' ? (
            Object.entries(script).map(([segmentName, segment]) => 
              renderSegment(segmentName, segment)
            )
          ) : (
            script || 'No script content available'
          )}
        </div>
      </div>

      {/* Advanced Toggle */}
      <div className="advanced-toggle">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="toggle-button"
        >
          {showAdvanced ? '👁️ Hide' : '👁️ Show'} Advanced Details
        </button>
      </div>

      {/* Improvement Section */}
      <div style={{
        background: 'rgba(255,255,255,0.1)',
        borderRadius: '15px',
        padding: '2.5rem',
        marginBottom: '2rem',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255,255,255,0.2)'
      }}>
        <h3 style={{ 
          color: '#00d4ff', 
          marginBottom: '2rem',
          fontSize: '1.8rem',
          fontWeight: 'bold'
        }}>
          ✨ Improve Your Script
        </h3>
        
        <div style={{ marginBottom: '2rem' }}>
          <textarea
            value={improvementRequest}
            onChange={(e) => setImprovementRequest(e.target.value)}
            placeholder="Tell me how to improve this script... (e.g., 'Make it more emotional', 'Add more humor', 'Focus on the product benefits', etc.)"
            style={{
              width: '100%',
              minHeight: '120px',
              padding: '1.5rem',
              borderRadius: '12px',
              border: '2px solid rgba(0,212,255,0.3)',
              background: 'rgba(0,0,0,0.3)',
              color: '#fff',
              fontSize: '1.1rem',
              fontFamily: 'system-ui, sans-serif',
              resize: 'vertical',
              lineHeight: '1.6'
            }}
          />
        </div>
        
        <div style={{ 
          display: 'flex', 
          gap: '1.5rem', 
          flexWrap: 'wrap',
          justifyContent: 'center'
        }}>
          <button
            onClick={handleImprove}
            disabled={loading || !improvementRequest.trim()}
            style={{
              background: loading ? '#666' : 'linear-gradient(45deg, #ff6b35, #f7931e)',
              color: '#fff',
              border: 'none',
              borderRadius: '12px',
              padding: '1rem 2.5rem',
              fontSize: '1.2rem',
              fontWeight: 'bold',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.3s ease',
              fontFamily: 'Orbitron, sans-serif',
              minWidth: '200px'
            }}
          >
            {loading ? '🔄 Improving...' : '🚀 Improve Script'}
          </button>
          
          <button
            onClick={onApprove}
            disabled={loading}
            style={{
              background: loading ? '#666' : 'linear-gradient(45deg, #4CAF50, #45a049)',
              color: '#fff',
              border: 'none',
              borderRadius: '12px',
              padding: '1rem 2.5rem',
              fontSize: '1.2rem',
              fontWeight: 'bold',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.3s ease',
              fontFamily: 'Orbitron, sans-serif',
              minWidth: '200px'
            }}
          >
            {loading ? '⏳ Please wait...' : '✅ Approve & Generate Video'}
          </button>
        </div>
      </div>

      <style jsx>{`
        .script-preview-container {
          background: var(--input-bg);
          padding: 2rem;
          border-radius: 16px;
          margin: 1.5rem 0;
          border: 1px solid var(--teal-mid);
          max-height: 80vh;
          overflow-y: auto;
        }

        .script-analysis {
          background: #f8f9fa;
          padding: 1rem;
          border-radius: 8px;
          margin-bottom: 1.5rem;
          border-left: 4px solid var(--teal-mid);
        }

        .quality-score {
          font-size: 16px;
          margin-bottom: 0.5rem;
        }

        .script-segment {
          background: white;
          padding: 1.5rem;
          border-radius: 12px;
          margin-bottom: 1.5rem;
          border: 1px solid #e0e0e0;
        }

        .segment-content {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .script-field {
          margin-bottom: 1rem;
        }

        .script-field label {
          color: var(--teal-dark);
          font-weight: 600;
          display: block;
          margin-bottom: 0.5rem;
        }

        .script-field p {
          color: #333;
          line-height: 1.6;
          margin: 0;
          padding: 0.75rem;
          background: #f8f9fa;
          border-radius: 6px;
        }

        .voiceover-text {
          font-weight: 500;
          font-style: italic;
        }

        .prompt-text {
          font-family: 'Fira Mono', monospace;
          font-size: 13px;
          background: #f0f0f0 !important;
        }

        .segment-issues {
          background: #fff5f5;
          padding: 1rem;
          border-radius: 8px;
          border-left: 4px solid #dc3545;
          margin-top: 1rem;
        }

        .script-overall {
          background: #f0f8ff;
          padding: 1.5rem;
          border-radius: 12px;
          border: 1px solid #b6d6e0;
        }

        .advanced-toggle {
          text-align: center;
          margin: 1rem 0;
        }

        .toggle-button {
          background: var(--teal-mid);
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
        }

        .toggle-button:hover {
          background: var(--teal-dark);
        }

        .improvement-section {
          background: #f8fffe;
          padding: 1.5rem;
          border-radius: 12px;
          border: 2px dashed var(--teal-mid);
          margin-top: 1.5rem;
        }

        .improvement-input {
          margin-bottom: 1rem;
        }

        .improvement-buttons {
          display: flex;
          gap: 1rem;
          flex-wrap: wrap;
        }

        .improve-button {
          background: var(--teal-mid);
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          font-size: 16px;
          flex: 1;
          min-width: 200px;
        }

        .improve-button:hover:not(:disabled) {
          background: var(--teal-dark);
        }

        .improve-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .approve-button {
          background: #28a745;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          font-size: 16px;
          flex: 1;
          min-width: 200px;
        }

        .approve-button:hover:not(:disabled) {
          background: #218838;
        }

        .approve-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        @media (max-width: 600px) {
          .script-preview-container {
            padding: 1rem;
          }
          
          .improvement-buttons {
            flex-direction: column;
          }
          
          .improve-button,
          .approve-button {
            min-width: auto;
          }
        }
      `}</style>
    </div>
  );
};

export default ScriptPreview; 
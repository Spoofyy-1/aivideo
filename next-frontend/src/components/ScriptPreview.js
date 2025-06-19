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
    <div key={segmentName} className="script-segment">
      <h4 style={{ color: '#2c6878', marginBottom: '1rem' }}>
        {segmentName === 'segment1' ? 'Segment 1 (0-8 seconds)' : 'Segment 2 (8-16 seconds)'}
      </h4>
      
      <div className="segment-content">
        <div className="script-field">
          <label><strong>Scene Description:</strong></label>
          <p>{segment.scene_description}</p>
        </div>
        
        <div className="script-field">
          <label><strong>Voiceover Script:</strong></label>
          <p className="voiceover-text">{segment.voiceover_script}</p>
          {scriptAnalysis?.length_analysis?.[segmentName] && (
            <small style={{ 
              color: scriptAnalysis.length_analysis[segmentName].optimal ? '#28a745' : '#dc3545',
              display: 'block',
              marginTop: '0.5rem'
            }}>
              {scriptAnalysis.length_analysis[segmentName].word_count} words • 
              ~{scriptAnalysis.length_analysis[segmentName].estimated_duration}s duration
              {!scriptAnalysis.length_analysis[segmentName].optimal && " ⚠️"}
            </small>
          )}
        </div>
        
        <div className="script-field">
          <label><strong>Mood:</strong></label>
          <p>{segment.mood}</p>
        </div>
        
        <div className="script-field">
          <label><strong>Camera Movement:</strong></label>
          <p>{segment.camera}</p>
        </div>
        
        {showAdvanced && (
          <>
            <div className="script-field">
              <label><strong>VEO-3 Prompt:</strong></label>
              <p className="prompt-text">{segment.prompt}</p>
            </div>
            
            {segment.veo3_optimization && (
              <div className="script-field">
                <label><strong>VEO-3 Optimization:</strong></label>
                <p>{segment.veo3_optimization}</p>
              </div>
            )}
          </>
        )}
      </div>
      
      {/* Show issues for this segment */}
      {scriptAnalysis && scriptAnalysis[`${segmentName}_issues`]?.length > 0 && (
        <div className="segment-issues">
          <h5 style={{ color: '#dc3545', marginBottom: '0.5rem' }}>⚠️ Potential Issues:</h5>
          <ul style={{ marginLeft: '1rem', color: '#dc3545' }}>
            {scriptAnalysis[`${segmentName}_issues`].map((issue, idx) => (
              <li key={idx}>{issue}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  return (
    <div className="script-preview-container">
      <div className="script-header">
        <h3 style={{ color: '#2c6878', marginBottom: '1rem' }}>📝 Your AI-Generated Script</h3>
        
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
      </div>

      {/* Script Content */}
      <div className="script-content">
        {script.segment1 && renderSegment('segment1', script.segment1)}
        {script.segment2 && renderSegment('segment2', script.segment2)}
        
        {/* Overall Script Elements */}
        <div className="script-overall">
          <h4 style={{ color: '#2c6878', marginBottom: '1rem' }}>Overall Elements</h4>
          
          {script.slogan && (
            <div className="script-field">
              <label><strong>Slogan:</strong></label>
              <p>{script.slogan}</p>
            </div>
          )}
          
          {script.call_to_action && (
            <div className="script-field">
              <label><strong>Call to Action:</strong></label>
              <p>{script.call_to_action}</p>
            </div>
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
      <div className="improvement-section">
        <h4 style={{ color: '#2c6878', marginBottom: '1rem' }}>🚀 Improve Your Script</h4>
        
        <div className="improvement-input">
          <textarea
            value={improvementRequest}
            onChange={(e) => setImprovementRequest(e.target.value)}
            placeholder="Tell us how you'd like to improve the script... 
Examples:
• Make it more humorous
• Focus more on the product features
• Make the tone more professional
• Shorten the voiceover in segment 1
• Add more emotion to segment 2"
            rows={4}
            style={{
              width: '100%',
              padding: '1rem',
              borderRadius: '8px',
              border: '1px solid #ccc',
              fontFamily: 'inherit',
              fontSize: '14px',
              resize: 'vertical'
            }}
          />
        </div>
        
        <div className="improvement-buttons">
          <button
            type="button"
            onClick={handleImprove}
            disabled={!improvementRequest.trim() || loading}
            className="improve-button"
          >
            {loading ? '🔄 Improving...' : '✨ Improve with AI'}
          </button>
          
          <button
            type="button"
            onClick={onApprove}
            disabled={loading}
            className="approve-button"
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
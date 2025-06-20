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

  const getWordCountColor = (wordCount) => {
    if (wordCount >= 12 && wordCount <= 15) return '#28a745';
    if (wordCount < 12) return '#ffc107';
    return '#dc3545';
  };

  const getTotalWordCount = () => {
    if (typeof script === 'object') {
      let totalWords = 0;
      // Count words from all segments dynamically
      Object.keys(script).forEach(key => {
        if (key.startsWith('segment') && script[key]?.voiceover_script) {
          totalWords += script[key].voiceover_script.split(' ').length;
        }
      });
      return totalWords;
    }
    return 0;
  };

  const getSegmentCount = () => {
    if (typeof script === 'object') {
      return Object.keys(script).filter(key => key.startsWith('segment')).length;
    }
    return 0;
  };

  const getTargetWordCount = () => {
    return getSegmentCount() * 15; // 15 words per segment
  };

  const renderSegment = (segmentName, segment) => (
    <div key={segmentName} style={{
      background: 'linear-gradient(135deg, rgba(0,0,0,0.6), rgba(20,20,20,0.8))',
      borderRadius: '12px',
      padding: '1.5rem',
      marginBottom: '1.5rem',
      border: '1px solid rgba(0,212,255,0.3)'
    }}>
      <h3 style={{ 
        color: '#00d4ff', 
        marginBottom: '1rem',
        fontSize: '1.3rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem'
      }}>
        🎬 {segmentName} (8-Second Clip)
      </h3>
      
      {/* Visual Scene Description */}
      {segment.scene_description && (
        <div style={{
          background: 'rgba(255,165,0,0.1)',
          border: '1px solid rgba(255,165,0,0.3)',
          borderRadius: '8px',
          padding: '1rem',
          marginBottom: '1rem'
        }}>
          <strong style={{ color: '#ffa500', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            🎨 Visual Scene:
          </strong>
          <p style={{ color: '#ffffff', margin: '0', fontSize: '1rem', lineHeight: '1.5' }}>
            {segment.scene_description}
          </p>
        </div>
      )}
      
      {/* Voiceover Script */}
      <div style={{
        background: 'rgba(0,255,136,0.1)',
        border: '1px solid rgba(0,255,136,0.3)',
        borderRadius: '8px',
        padding: '1rem',
        marginBottom: '1rem'
      }}>
        <strong style={{ color: '#00ff88', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          🎙️ Voiceover:
        </strong>
        <p style={{ 
          color: '#ffffff', 
          margin: '0', 
          fontSize: '1.1rem', 
          fontWeight: '500',
          lineHeight: '1.6',
          fontStyle: 'italic'
        }}>
          "{segment.voiceover_script}"
        </p>
        <div style={{ 
          fontSize: '0.85rem', 
          color: '#cccccc', 
          marginTop: '0.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem'
        }}>
          <span>📊 Word Count: {segment.voiceover_script?.split(' ').length || 0}/15</span>
          <span>⏱️ Estimated Speech: ~{((segment.voiceover_script?.split(' ').length || 0) / 2.5).toFixed(1)}s</span>
        </div>
      </div>
      
      {/* Show narrator and audio production information */}
      {(segment.narrator_characteristics || segment.delivery_instructions || segment.audio_production) && (
        <div style={{
          background: 'rgba(255,165,0,0.1)',
          border: '1px solid rgba(255,165,0,0.3)',
          borderRadius: '8px',
          padding: '1rem',
          marginTop: '1rem'
        }}>
          <strong style={{ color: '#ffa500' }}>🎭 Professional Narrator & Audio Production:</strong>
          <div style={{ marginTop: '0.5rem', fontSize: '0.95rem' }}>
            {segment.narrator_characteristics && (
              <p style={{ color: '#cccccc', margin: '0.25rem 0' }}>
                <strong>Voice Type:</strong> {segment.narrator_characteristics}
              </p>
            )}
            {segment.delivery_instructions && (
              <p style={{ color: '#cccccc', margin: '0.25rem 0' }}>
                <strong>Delivery Style:</strong> {segment.delivery_instructions}
              </p>
            )}
            {segment.audio_production && (
              <p style={{ color: '#cccccc', margin: '0.25rem 0' }}>
                <strong>Audio Production:</strong> {segment.audio_production}
              </p>
            )}
            {segment.timing_breakdown && (
              <p style={{ color: '#cccccc', margin: '0.25rem 0' }}>
                <strong>Timing:</strong> {segment.timing_breakdown}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Show timing information */}
      {segment.voiceover_timing && (
        <div style={{
          background: 'rgba(0,212,255,0.1)',
          border: '1px solid rgba(0,212,255,0.3)',
          borderRadius: '8px',
          padding: '1rem',
          marginTop: '1rem'
        }}>
          <strong style={{ color: '#00d4ff' }}>🎯 VEO-3 Timing Optimization:</strong>
          <div style={{ marginTop: '0.5rem', fontSize: '0.95rem' }}>
            <p style={{ color: '#cccccc', margin: '0.25rem 0' }}>
              📍 <strong>Duration:</strong> {segment.voiceover_timing.start_time} - {segment.voiceover_timing.end_time} (8 seconds) | 
              <strong>Target:</strong> 12-15 words for perfect timing
            </p>
            <p style={{ color: '#cccccc', margin: '0.25rem 0' }}>
              🎙️ <strong>Speech Timing:</strong> 0:00-0:06 narrator speaks (6 seconds) | 0:06-0:08 music bridge (2 seconds)
            </p>
            <p style={{ color: '#cccccc', margin: '0.25rem 0' }}>
              ⚡ <strong>No Blank Space:</strong> Strategic word placement eliminates dead air | Continuous audio flow
            </p>
            <p style={{ color: '#cccccc', margin: '0.25rem 0' }}>
              🎭 <strong>Narrator:</strong> Consistent voice across all segments | Professional delivery
            </p>
            <p style={{ color: '#00ff88', margin: '0.25rem 0', fontSize: '0.9rem' }}>
              💡 <strong>Delivery:</strong> {segment.voiceover_timing.delivery_note || 'Deliver 15 words in 6 seconds, leaving 2s for visual transition'}
            </p>
          </div>
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
      
      {segment.veo3_optimization && (
        <div style={{ marginBottom: '1.5rem' }}>
          <strong style={{ color: '#00d4ff' }}>🤖 VEO-3 Optimization:</strong>
          <p style={{ 
            marginTop: '0.5rem', 
            fontSize: '0.9rem', 
            lineHeight: '1.4',
            color: '#999999',
            fontStyle: 'italic'
          }}>
            {segment.veo3_optimization}
          </p>
        </div>
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
      width: '100%',
      maxWidth: 'none',
      position: 'relative',
      zIndex: 1
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
        <div style={{
          background: 'rgba(255,255,255,0.1)',
          borderRadius: '15px',
          padding: '2rem',
          marginBottom: '2rem',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255,255,255,0.2)'
        }}>
          <h3 style={{ 
            color: '#00d4ff', 
            marginBottom: '1.5rem',
            fontSize: '1.6rem',
            fontWeight: 'bold'
          }}>
            📊 VEO-3 Optimization Analysis
          </h3>
          
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '2rem',
            flexWrap: 'wrap'
          }}>
            <div style={{
              background: 'rgba(0,212,255,0.1)',
              border: '1px solid rgba(0,212,255,0.3)',
              borderRadius: '8px',
              padding: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <span style={{ fontSize: '1.5rem' }}>🎯</span>
              <div>
                <div style={{ fontSize: '0.8rem', color: '#cccccc' }}>VEO-3 Readiness</div>
                <div style={{ 
                  fontSize: '1.2rem', 
                  fontWeight: 'bold',
                  color: getScoreColor(scriptAnalysis.veo3_readiness || 0)
                }}>
                  {scriptAnalysis.veo3_readiness || 0}/100
                </div>
              </div>
            </div>
            
            <div style={{
              background: 'rgba(255,215,0,0.1)',
              border: '1px solid rgba(255,215,0,0.3)',
              borderRadius: '8px',
              padding: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <span style={{ fontSize: '1.5rem' }}>📊</span>
              <div>
                <div style={{ fontSize: '0.8rem', color: '#cccccc' }}>Total Words</div>
                <div style={{ 
                  fontSize: '1.2rem', 
                  fontWeight: 'bold',
                  color: getWordCountColor(getTotalWordCount())
                }}>
                  {getTotalWordCount()}/{getTargetWordCount()}
                </div>
              </div>
            </div>
            
            <div style={{
              background: 'rgba(138,43,226,0.1)',
              border: '1px solid rgba(138,43,226,0.3)',
              borderRadius: '8px',
              padding: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <span style={{ fontSize: '1.5rem' }}>🎬</span>
              <div>
                <div style={{ fontSize: '0.8rem', color: '#cccccc' }}>Duration</div>
                <div style={{ 
                  fontSize: '1.2rem', 
                  fontWeight: 'bold',
                  color: '#8a2be2'
                }}>
                  {getSegmentCount() * 8}s ({getSegmentCount()} clips)
                </div>
              </div>
            </div>
            
            {/* Brand Messaging Status */}
            <div style={{
              background: scriptAnalysis.brand_messaging_status === 'included' ? 'rgba(40,167,69,0.1)' : 'rgba(220,53,69,0.1)',
              border: scriptAnalysis.brand_messaging_status === 'included' ? '1px solid rgba(40,167,69,0.3)' : '1px solid rgba(220,53,69,0.3)',
              borderRadius: '8px',
              padding: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <span style={{ fontSize: '1.5rem' }}>
                {scriptAnalysis.brand_messaging_status === 'included' ? '✅' : '🚨'}
              </span>
              <div>
                <div style={{ fontSize: '0.8rem', color: '#cccccc' }}>Brand Messaging</div>
                <div style={{ 
                  fontSize: '1.2rem', 
                  fontWeight: 'bold',
                  color: scriptAnalysis.brand_messaging_status === 'included' ? '#28a745' : '#dc3545'
                }}>
                  {scriptAnalysis.brand_messaging_status === 'included' ? 'Included' : 'Missing'}
                </div>
              </div>
            </div>
          </div>
          
          {scriptAnalysis.overall_recommendations?.length > 0 && (
            <div style={{
              background: 'rgba(255,193,7,0.1)',
              border: '1px solid rgba(255,193,7,0.3)',
              borderRadius: '8px',
              padding: '1rem'
            }}>
              <strong style={{ color: '#ffc107' }}>💡 Recommendations:</strong>
              <ul style={{ marginLeft: '1rem', marginTop: '0.5rem', color: '#ffffff' }}>
                {scriptAnalysis.overall_recommendations.map((rec, idx) => (
                  <li key={idx} style={{ margin: '0.25rem 0' }}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Script Content */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(0,0,0,0.8), rgba(30,30,30,0.9))',
        borderRadius: '16px',
        padding: '2rem',
        border: '1px solid rgba(255,255,255,0.1)',
        marginBottom: '2rem'
      }}>
        <h2 style={{ 
          color: '#ffffff', 
          marginBottom: '1.5rem',
          fontSize: '1.8rem',
          textAlign: 'center'
        }}>
          📝 Generated Script ({getSegmentCount()} segments - {getSegmentCount() * 8} seconds)
        </h2>
        
        {/* Render all segments dynamically */}
        {Object.keys(script)
          .filter(key => key.startsWith('segment'))
          .sort()
          .map(segmentKey => {
            const segment = script[segmentKey];
            const segmentNumber = segmentKey.replace('segment', '');
            return renderSegment(`Segment ${segmentNumber}`, segment);
          })
        }
        
        {/* Slogan and Call-to-Action Section */}
        {(script.slogan || script.call_to_action) && (
          <div style={{
            background: 'linear-gradient(135deg, rgba(255,215,0,0.1), rgba(255,165,0,0.1))',
            border: '2px solid rgba(255,215,0,0.4)',
            borderRadius: '12px',
            padding: '1.5rem',
            marginTop: '1.5rem'
          }}>
            <h3 style={{ 
              color: '#ffd700', 
              marginBottom: '1rem',
              fontSize: '1.3rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              ✨ Brand Messaging
            </h3>
            
            {script.slogan && (
              <div style={{
                background: 'rgba(255,215,0,0.1)',
                border: '1px solid rgba(255,215,0,0.3)',
                borderRadius: '8px',
                padding: '1rem',
                marginBottom: script.call_to_action ? '1rem' : '0'
              }}>
                <strong style={{ color: '#ffd700', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  🏷️ Slogan:
                </strong>
                <p style={{ 
                  color: '#ffffff', 
                  margin: '0', 
                  fontSize: '1.2rem', 
                  fontWeight: 'bold',
                  lineHeight: '1.4',
                  textAlign: 'center',
                  fontStyle: 'italic'
                }}>
                  "{script.slogan}"
                </p>
              </div>
            )}
            
            {script.call_to_action && (
              <div style={{
                background: 'rgba(255,165,0,0.1)',
                border: '1px solid rgba(255,165,0,0.3)',
                borderRadius: '8px',
                padding: '1rem'
              }}>
                <strong style={{ color: '#ffa500', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  📢 Call to Action:
                </strong>
                <p style={{ 
                  color: '#ffffff', 
                  margin: '0', 
                  fontSize: '1.2rem', 
                  fontWeight: 'bold',
                  lineHeight: '1.4',
                  textAlign: 'center'
                }}>
                  "{script.call_to_action}"
                </p>
              </div>
            )}
          </div>
        )}
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
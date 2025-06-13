"use client";

import React, { useState, useRef, useEffect } from 'react';
import { generateAd, researchCompany, testAPI } from '../api';

// API base URL - need to reuse this for downloads
const getApiBaseUrl = () => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  
  if (typeof window !== 'undefined' && (
    window.location.hostname === 'localhost' || 
    window.location.hostname === '127.0.0.1'
  )) {
    return 'http://localhost:5000';
  }
  
  return 'https://aivideo-production.up.railway.app';
};

const API_BASE_URL = getApiBaseUrl();

const adTypeOptions = [
  'Unhinged',
  'Informative',
  'Emotional',
  'Cinematic',
  'Funny',
  'Heartwarming',
  'Aspirational',
  'Testimonial',
  'Product Demo',
  'Viral/Meme',
  'Story-Driven',
  'Minimalist',
  'High-Energy',
  'Social Proof',
  'Pop Culture Reference',
  'Other'
];

const aiModelOptions = [
  'Best (Recommended)',
  'GPT-4',
  'Gemini'
];

const industryOptions = [
  'Technology',
  'Healthcare',
  'Retail',
  'Finance',
  'Education',
  'Food & Beverage',
  'Travel',
  'Automotive',
  'Fashion',
  'Real Estate',
  'Entertainment',
  'Other'
];

const creativeQuestions = [
  { key: 'ai_model', text: "Which AI model would you like to use for ad generation?", options: aiModelOptions },
  { key: 'ad_type', text: "What type of ad do you want? (e.g., Unhinged, Informative, Emotional, Cinematic, Funny, Heartwarming, Aspirational, Testimonial, Product Demo, Viral/Meme, Story-Driven, Minimalist, High-Energy, Social Proof, Pop Culture Reference, etc.)", options: adTypeOptions },
  { key: 'mood', text: 'What is the mood or vibe you want for your ad? (e.g., energetic, trustworthy, fun, etc.)' },
  { key: 'slogan', text: "Do you have a specific slogan you want to use? (Type 'N/A' if you want us to create one)" },
  { key: 'cta', text: "Is there a specific call to action you want viewers to hear? (Type 'N/A' if you want us to create one)" },
  { key: 'features', text: 'Any features or benefits you want to highlight?' }
];

function Chatbot() {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: "Hi! I'm your AI Ad Generator. I'll ask a few quick questions to help tailor your ad. Ready? Let's go!" },
    { sender: 'bot', text: 'What is your company website URL?' }
  ]);
  const [answers, setAnswers] = useState({});
  const [step, setStep] = useState(0);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [result, setResult] = useState(null);

  // Product research state
  const [productsList, setProductsList] = useState([]);
  const [researchDone, setResearchDone] = useState(false);
  const [productAsked, setProductAsked] = useState(false);
  const [productSelected, setProductSelected] = useState(false);

  const chatRef = useRef(null);

  // Test API connectivity on component mount
  useEffect(() => {
    const testConnection = async () => {
      try {
        console.log('Testing API connectivity...');
        const response = await testAPI();
        console.log('API test successful:', response);
        
        // Also test the root endpoint
        const rootResponse = await fetch('https://aivideo-production.up.railway.app/');
        const rootData = await rootResponse.json();
        console.log('Root endpoint test:', rootData);
        
      } catch (error) {
        console.error('API test failed:', error);
        setMessages(msgs => [ 
          ...msgs,
          { sender: 'bot', text: 'Warning: Having trouble connecting to our servers. Please check your internet connection.' }
        ]);
      }
    };
    
    testConnection();
  }, []);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages, result]);

  // Handle product selection
  const handleProductSelect = (product) => {
    setMessages(msgs => [...msgs, { sender: 'user', text: product }]);
    setAnswers(ans => ({ ...ans, product }));
    setProductSelected(true);
    maybeGenerateAd({ ...answers, product });
  };

  // Handle custom product input
  const handleCustomProduct = () => {
    setMessages(msgs => [...msgs, { sender: 'bot', text: 'Type your product or service:' }]);
    setProductAsked(true);
    setProductSelected(false);
  };

  // Main send handler
  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    setMessages(msgs => [...msgs, { sender: 'user', text: input }]);

    // Company URL step
    if (!answers.company_url) {
      setAnswers(ans => ({ ...ans, company_url: input }));
      setInput('');
      setLoading(true);
      setLoadingMessage('Researching your company...');
      setMessages(msgs => [
        ...msgs,
        { sender: 'bot', text: 'Researching your company...' }
      ]);
      
      // Research the company
      try {
        console.log('Starting company research for:', input);
        const research = await researchCompany(input);
        console.log('Research completed successfully:', research);
        
        setProductsList(research.products_services || []);
        setResearchDone(true);
        setLoading(false);
        setLoadingMessage('');
        setMessages(msgs => [
          ...msgs,
          { sender: 'bot', text: 'Research completed! What industry is your company in?' }
        ]);
      } catch (error) {
        console.error('Research failed with error:', error);
        console.error('Error details:', {
          message: error.message,
          stack: error.stack,
          name: error.name
        });
        
        setLoading(false);
        setLoadingMessage('');
        setMessages(msgs => [
          ...msgs,
          { sender: 'bot', text: `Research failed: ${error.message}. We can continue without it. What industry is your company in?` }
        ]);
        setResearchDone(true);
      }
      return;
    }

    // Industry step
    if (!answers.industry) {
      setAnswers(ans => ({ ...ans, industry: input }));
      setInput('');
      setMessages(msgs => [
        ...msgs,
        { sender: 'bot', text: creativeQuestions[0].text }
      ]);
      setStep(0);
      return;
    }

    // If waiting for custom product input
    if (productAsked && !productSelected && !answers.product && step >= creativeQuestions.length) {
      handleProductSelect(input);
      setInput('');
      return;
    }

    // Creative questions
    if (step < creativeQuestions.length) {
      setAnswers(ans => ({ ...ans, [creativeQuestions[step].key]: input }));
      setInput('');
      if (step < creativeQuestions.length - 1) {
        setTimeout(() => {
          setMessages(msgs => [...msgs, { sender: 'bot', text: creativeQuestions[step + 1].text }]);
        }, 400);
        setStep(step + 1);
      } else {
        // After last creative question, wait for research if not done, then show product options
        setStep(step + 1);
        if (researchDone) {
          setProductAsked(true);
        }
      }
    }
  };

  // Show product options after creative questions and research is done
  useEffect(() => {
    if (step >= creativeQuestions.length && researchDone && !productSelected && productAsked) {
      if (productsList.length > 0) {
        setMessages(msgs => [...msgs, { sender: 'bot', text: 'Select a product or service to promote:' }]);
      } else {
        setMessages(msgs => [...msgs, { sender: 'bot', text: 'Type your product or service:' }]);
      }
      setProductAsked(true);
    }
    // eslint-disable-next-line
  }, [researchDone, step]);

  // Generate ad if all creative questions and product are answered
  const maybeGenerateAd = async (finalAnswers) => {
    if (
      creativeQuestions.every(q => (finalAnswers || answers)[q.key]) &&
      ((finalAnswers || answers).product)
    ) {
      setLoadingMessage('Generating your ad...');
      setLoading(true);
      setMessages(msgs => [...msgs, { sender: 'bot', text: 'Generating your ad, please wait...' }]);
      try {
        const data = await generateAd(finalAnswers || answers);
        setResult(data);
        setMessages(msgs => [...msgs, { sender: 'bot', text: 'Here is your generated ad!' }]);
      } catch (err) {
        setMessages(msgs => [...msgs, { sender: 'bot', text: 'Sorry, something went wrong generating your ad.' }]);
      }
      setLoading(false);
      setLoadingMessage('');
    }
  };

  return (
    <div className="chatbot-outer">
      <div className="container">
        <h1>AI Ad Generator</h1>
        <div className="chat" ref={chatRef}>
          {messages.map((msg, idx) => (
            <div key={idx} className={`msg ${msg.sender}`}>
              <div className="bubble">{msg.text}</div>
            </div>
          ))}
          {/* Product options */}
          {step >= creativeQuestions.length && researchDone && !productSelected && productAsked && productsList.length > 0 && (
            <div className="msg bot">
              <div className="bubble" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {productsList.map(opt => (
                  <button
                    key={opt}
                    type="button"
                    style={{
                      background: 'var(--button-bg)',
                      color: 'var(--button-text)',
                      border: 'none',
                      borderRadius: '8px',
                      padding: '0.6rem 1.2rem',
                      fontFamily: 'Orbitron, sans-serif',
                      fontWeight: 'bold',
                      cursor: 'pointer',
                      marginBottom: '0.3rem'
                    }}
                    onClick={() => handleProductSelect(opt)}
                  >
                    {opt}
                  </button>
                ))}
                <button
                  type="button"
                  style={{
                    background: 'var(--button-bg)',
                    color: 'var(--button-text)',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '0.6rem 1.2rem',
                    fontFamily: 'Orbitron, sans-serif',
                    fontWeight: 'bold',
                    cursor: 'pointer'
                  }}
                  onClick={handleCustomProduct}
                >
                  Other
                </button>
              </div>
            </div>
          )}
          {result && (
            <>
              <div className="msg bot">
                <div className="bubble">Here is your generated ad!</div>
              </div>
              <div className="video-container">
                <video controls src={`${API_BASE_URL}${result.video_url}`} style={{ width: '100%' }} />
                <div id="video-error" style={{ display: 'none', color: '#fff', background: '#c00', padding: '1em', borderRadius: '8px', marginTop: '1em' }}>
                  Video could not be loaded. Please check your server logs or try again.
                </div>
              </div>
              <div style={{ margin: '1em 0' }}>
                <a
                  href={`${API_BASE_URL}${result.video_url}`}
                  download
                  style={{ color: '#3ca1b5', fontWeight: 'bold', marginRight: '1.5em' }}
                  onClick={e => {
                    if (!result.video_url.endsWith('.mp4')) {
                      e.preventDefault();
                      alert('Video file is not available for download. Please try again later.');
                    }
                  }}
                >
                  ⬇️ Download Video
                </a>
                <a
                  href={`${API_BASE_URL}${result.report_url}`}
                  download
                  style={{ color: '#3ca1b5', fontWeight: 'bold' }}
                  onClick={e => {
                    if (!result.report_url.endsWith('.txt')) {
                      e.preventDefault();
                      alert('Report file is not available for download. Please try again later.');
                    }
                  }}
                >
                  ⬇️ Download Report
                </a>
              </div>
              <div className="script-container">
                <h3>Generated Script</h3>
                {['segment1', 'segment2'].map((seg, idx) => (
                  result.script[seg] && (
                    <div key={seg} style={{ marginBottom: '1.2rem' }}>
                      <strong>Scene {idx + 1}:</strong><br />
                      <span style={{ color: '#b6d6e0' }}><em>{result.script[seg].scene_description}</em></span><br />
                      <strong>Voiceover Script:</strong> <span style={{ color: '#eaf6f8' }}>{result.script[seg].voiceover_script}</span><br />
                      <strong>Mood:</strong> <span style={{ color: '#eaf6f8' }}>{result.script[seg].mood}</span><br />
                      <strong>Camera:</strong> <span style={{ color: '#eaf6f8' }}>{result.script[seg].camera}</span>
                    </div>
                  )
                ))}
                <div style={{ marginTop: '1.2rem' }}>
                  <strong>Slogan:</strong> <span style={{ color: '#eaf6f8', fontSize: '1.1em' }}>{result.script.slogan}</span><br />
                  <strong>Call to Action:</strong> <span style={{ color: '#eaf6f8', fontSize: '1.1em' }}>{result.script.call_to_action}</span>
                </div>
              </div>
            </>
          )}
        </div>
        {/* Input form */}
        {!result && !loading && (
          <form className="input-row" onSubmit={handleSend}>
            {!answers.company_url ? (
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Enter your company website URL..."
                autoFocus
              />
            ) : !answers.industry ? (
              <select
                value={input}
                onChange={e => setInput(e.target.value)}
                style={{
                  background: 'var(--input-bg)',
                  color: 'var(--input-text)',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '0.6rem 1.2rem',
                  fontFamily: 'Orbitron, sans-serif',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  marginBottom: '0.3rem'
                }}
              >
                <option value="">Select your industry</option>
                {industryOptions.map(option => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            ) : (
              step < creativeQuestions.length && creativeQuestions[step].options ? (
                <select
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  style={{
                    background: 'var(--input-bg)',
                    color: 'var(--input-text)',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '0.6rem 1.2rem',
                    fontFamily: 'Orbitron, sans-serif',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    marginBottom: '0.3rem'
                  }}
                >
                  <option value="">Select an option</option>
                  {creativeQuestions[step].options.map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder="Type your answer..."
                  autoFocus
                />
              )
            )}
            <button type="submit">Send</button>
          </form>
        )}
        {loading && <div className="loading">{loadingMessage}</div>}
      </div>
    </div>
  );
}

export default Chatbot;

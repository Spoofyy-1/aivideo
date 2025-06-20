"use client";

import React, { useState, useRef, useEffect } from 'react';
import { generateAd, researchCompany, testAPI, generateScript, improveScript, generateVideoFromScript } from '../api';
import RatingModal from './RatingModal';
import ScriptPreview from './ScriptPreview';

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
  '✨ Educational-First (2025 Trend)',
  '✨ Founder-Story (2025 Trend)',
  '✨ Nostalgia-Driven (2025 Trend)',
  '✨ Brain-Rot/Escapism (2025 Trend)',
  '✨ Micro-Moment (2025 Trend)',
  '✨ Platform-Native (2025 Trend)',
  'Normal',
  'Other'
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
  'Fitness',
  'Beauty',
  'Gaming',
  'Software',
  'E-commerce',
  'Marketing',
  'Consulting',
  'Photography',
  'Music',
  'Sports',
  'Home & Garden',
  'Pets',
  'Crypto',
  'SaaS',
  'Manufacturing',
  'Agriculture',
  'Construction',
  'Legal',
  'Non-profit',
  'Wellness',
  'Other'
];

const durationOptions = [
  '8 seconds (1 segment - Quick & Punchy)',
  '16 seconds (2 segments - Standard)',
  '24 seconds (3 segments - Detailed)',
  '32 seconds (4 segments - Comprehensive)'
];

const creativeQuestions = [
  { key: 'duration', text: "How long should your ad be?", options: durationOptions },
  { key: 'ad_type', text: "What type of ad do you want? (e.g., Normal, Unhinged, Informative, Emotional, Cinematic, Funny, Heartwarming, Aspirational, Testimonial, Product Demo, Viral/Meme, Story-Driven, Minimalist, High-Energy, Social Proof, Pop Culture Reference, etc.)", options: adTypeOptions },
  { key: 'mood', text: 'What is the mood or vibe you want for your ad? (e.g., energetic, trustworthy, fun, etc.)' },
  { key: 'authenticity_level', text: '🎯 2025 TREND: How authentic/raw should your ad feel? (Polished & Professional / Authentic & Natural / Raw & Unfiltered / Phone-Shot Style)' },
  { key: 'humor_tolerance', text: '😂 2025 TREND: Are you open to humor in your ads? (Yes, make it funny! / Subtle humor only / Light and playful / No humor, keep it serious)' },
  { key: 'educational_value', text: '📚 2025 TREND: Should your ad teach something valuable? (Yes, educate first / Quick tip or insight / Problem-solving focus / Entertainment over education)' },
  { key: 'sound_optimization', text: '🔇 2025 TREND: Will people watch with sound OFF? (Optimize for silent viewing / Include captions / Visual storytelling focus / Assume sound is ON)' },
  { key: 'main_character', text: "Who should be the main character in your ad? (e.g., CEO, satisfied customer, everyday person, celebrity, animated character, etc. Type 'N/A' if no specific preference)" },
  { key: 'target_platform', text: '📱 2025 TREND: Primary platform for this ad? (TikTok/Instagram Reels / YouTube Shorts / Facebook/Instagram Feed / LinkedIn / Multiple platforms)' },
  { key: 'transformation_story', text: '✨ 2025 TREND: Show a transformation? (Before/after results / Problem to solution / Struggle to success / No transformation story)' },
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

  // Script preview state
  const [scriptGenerated, setScriptGenerated] = useState(false);
  const [currentScript, setCurrentScript] = useState(null);
  const [scriptAnalysis, setScriptAnalysis] = useState(null);
  const [companyInfo, setCompanyInfo] = useState(null);

  // Rating modal state
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [hasRated, setHasRated] = useState(false);

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
  }, [messages, result, currentScript]);

  // Handle product selection
  const handleProductSelect = (product) => {
    setMessages(msgs => [...msgs, { sender: 'user', text: product }]);
    const updatedAnswers = { ...answers, product };
    setAnswers(updatedAnswers);
    setProductSelected(true);
    maybeGenerateScript(updatedAnswers);
  };

  // Handle custom product input
  const handleCustomProduct = () => {
    setMessages(msgs => [...msgs, { sender: 'bot', text: 'Type your product or service:' }]);
    setProductAsked(true);
    setProductSelected(false);
  };

  // Updated send handler to generate script first
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
        setMessages(msgs => [
          ...msgs,
          { sender: 'bot', text: 'Research failed. Please check the URL and try again.' }
        ]);
        setLoading(false);
        setLoadingMessage('');
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
      setStep(1);
      return;
    }

    // If waiting for custom product input
    if (productAsked && !productSelected && !answers.product && step >= creativeQuestions.length) {
      handleProductSelect(input);
      setInput('');
      return;
    }

    // Handle other questions
    if (step <= creativeQuestions.length) {
      const currentQuestion = creativeQuestions[step - 1];
      const newAnswers = { ...answers, [currentQuestion.key]: input };
      setAnswers(newAnswers);
      setInput('');
      
      if (step < creativeQuestions.length) {
        setStep(step + 1);
        const nextQuestion = creativeQuestions[step];
        setMessages(msgs => [...msgs, { sender: 'bot', text: nextQuestion.text }]);
      } else {
        setStep(step + 1);
        // Show product selection instead of generating ad immediately
        if (!productAsked && productsList.length > 0) {
          setMessages(msgs => [...msgs, { sender: 'bot', text: 'Select a product or service to promote:' }]);
          setProductAsked(true);
        } else if (!productAsked) {
          setMessages(msgs => [...msgs, { sender: 'bot', text: 'Type your product or service:' }]);
          setProductAsked(true);
        }
      }
    } else if (productAsked && !productSelected) {
      // Handle custom product input
      const newAnswers = { ...answers, product: input };
      setAnswers(newAnswers);
      setProductSelected(true);
      setInput('');
      maybeGenerateScript(newAnswers);
    }
  };

  // Generate script first (instead of full ad)
  const maybeGenerateScript = async (finalAnswers) => {
    const answersToCheck = finalAnswers || answers;
    
    // Debug logging
    console.log('maybeGenerateScript called with:', {
      finalAnswers,
      currentAnswers: answers,
      answersToCheck,
      hasProduct: !!answersToCheck.product,
      creativeQuestionsStatus: creativeQuestions.map(q => ({
        key: q.key,
        value: answersToCheck[q.key],
        hasValue: !!answersToCheck[q.key]
      }))
    });
    
    // Check if all creative questions are answered and product is selected
    const allQuestionsAnswered = creativeQuestions.every(q => {
      const value = answersToCheck[q.key];
      return value && value.trim() !== '';
    });
    
    const hasProduct = answersToCheck.product && answersToCheck.product.trim() !== '';
    const hasCompanyUrl = answersToCheck.company_url && answersToCheck.company_url.trim() !== '';
    const hasIndustry = answersToCheck.industry && answersToCheck.industry.trim() !== '';
    
    console.log('Generation conditions:', {
      allQuestionsAnswered,
      hasProduct,
      hasCompanyUrl,
      hasIndustry,
      shouldGenerate: allQuestionsAnswered && hasProduct && hasCompanyUrl && hasIndustry,
      missingQuestions: creativeQuestions.filter(q => {
        const value = answersToCheck[q.key];
        return !(value && value.trim() !== '');
      }).map(q => q.key)
    });
    
    if (allQuestionsAnswered && hasProduct && hasCompanyUrl && hasIndustry) {
      setLoadingMessage('Generating your script...');
      setLoading(true);
      setMessages(msgs => [...msgs, { sender: 'bot', text: 'Generating your ad script, please wait...' }]);
      
      try {
        console.log('Calling generateScript API with:', answersToCheck);
        const data = await generateScript(answersToCheck);
        console.log('Script generation successful:', data);
        
        setCurrentScript(data.script);
        setScriptAnalysis(data.script_analysis);
        setCompanyInfo(data.company_info);
        setScriptGenerated(true);
        setMessages(msgs => [...msgs, { sender: 'bot', text: 'Your script is ready! Review it below and make any improvements you want before generating the video.' }]);
      } catch (err) {
        console.error('Script generation error:', err);
        setMessages(msgs => [...msgs, { sender: 'bot', text: `Sorry, something went wrong generating your script: ${err.message}. Please try again.` }]);
      }
      setLoading(false);
      setLoadingMessage('');
    } else {
      console.log('Not ready to generate script yet. Missing requirements.');
    }
  };

  // Handle script improvement
  const handleScriptImprovement = async (improvementRequest) => {
    setLoading(true);
    setLoadingMessage('Improving your script...');
    setMessages(msgs => [...msgs, { sender: 'bot', text: `Improving script: "${improvementRequest}"...` }]);
    
    try {
      const data = await improveScript({
        script: currentScript,
        company_info: companyInfo,
        user_answers: answers,
        improvement_request: improvementRequest
      });
      
      setCurrentScript(data.script);
      setScriptAnalysis(data.script_analysis);
      setMessages(msgs => [...msgs, { sender: 'bot', text: 'Script improved! Review the changes below.' }]);
    } catch (err) {
      console.error('Script improvement error:', err);
      setMessages(msgs => [...msgs, { sender: 'bot', text: 'Sorry, something went wrong improving your script. Please try again.' }]);
    }
    
    setLoading(false);
    setLoadingMessage('');
  };

  // Handle script approval and video generation
  const handleScriptApproval = async () => {
    setLoading(true);
    setLoadingMessage('Generating your video...');
    setMessages(msgs => [...msgs, { sender: 'bot', text: 'Great! Now generating your video from the approved script. This may take a few minutes...' }]);
    
    try {
      const data = await generateVideoFromScript({
        script: currentScript,
        company_info: companyInfo,
        user_answers: answers
      });
      
      setResult(data);
      setMessages(msgs => [...msgs, { sender: 'bot', text: 'Your AI video ad is ready! 🎉' }]);
      
      // Show rating modal after a short delay
        setTimeout(() => {
          if (!hasRated) {
            setShowRatingModal(true);
          }
        }, 3000);
      } catch (err) {
      console.error('Video generation error:', err);
      setMessages(msgs => [...msgs, { sender: 'bot', text: 'Sorry, something went wrong generating your video. Please try again or contact support.' }]);
      }
    
      setLoading(false);
      setLoadingMessage('');
  };

  // Handle rating submission
  const handleRatingSubmit = (ratingData) => {
    console.log('Rating submitted:', ratingData);
    setHasRated(true);
    setMessages(msgs => [...msgs, { 
      sender: 'bot', 
      text: `Thank you for rating the ad ${ratingData.rating}/5 stars! Your feedback helps us improve our AI.` 
    }]);
  };

  // Handle rating modal close
  const handleRatingClose = () => {
    setShowRatingModal(false);
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
          
          {/* Loading indicator */}
          {loading && (
            <div className="msg bot">
              <div className="bubble">
                {loadingMessage}
                <div style={{ 
                  display: 'inline-block', 
                  marginLeft: '0.5rem',
                  animation: 'spin 1s linear infinite' 
                }}>
                  ⚡
                </div>
              </div>
            </div>
          )}
          
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
                    onClick={() => {
                      setMessages(msgs => [...msgs, { sender: 'user', text: opt }]);
                      const updatedAnswers = { ...answers, product: opt };
                      setAnswers(updatedAnswers);
                      setProductSelected(true);
                      maybeGenerateScript(updatedAnswers);
                    }}
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
          
          {/* Script Preview */}
          {scriptGenerated && currentScript && (
            <ScriptPreview
              script={currentScript}
              scriptAnalysis={scriptAnalysis}
              companyInfo={companyInfo}
              userAnswers={answers}
              onImprove={handleScriptImprovement}
              onApprove={handleScriptApproval}
              loading={loading}
            />
          )}
          
          {/* Final Result */}
          {result && (
            <div>
              <div style={{ margin: '1em 0', padding: '1em', background: '#f0f0f0', borderRadius: '8px' }}>
                <h3 style={{ color: '#333', marginBottom: '1em' }}>🎉 Your AI Video Ad is Ready!</h3>
                
                <div style={{ margin: '1em 0' }}>
                  <a
                    href={`${API_BASE_URL}${result.video_url}`}
                    download
                    style={{ 
                      color: '#fff', 
                      backgroundColor: '#007bff', 
                      padding: '12px 24px', 
                      textDecoration: 'none', 
                      borderRadius: '8px',
                      display: 'inline-block',
                      marginRight: '1em',
                      fontSize: '16px',
                      fontWeight: 'bold'
                    }}
                  >
                    📹 Download Video
                  </a>
                  
                  <a
                    href={`${API_BASE_URL}${result.report_url}`}
                    download
                    style={{ 
                      color: '#fff', 
                      backgroundColor: '#28a745', 
                      padding: '12px 24px', 
                      textDecoration: 'none', 
                      borderRadius: '8px',
                      display: 'inline-block',
                      fontSize: '16px',
                      fontWeight: 'bold'
                    }}
                  >
                    📄 Download Report
                  </a>
                  
                  {!hasRated && (
                    <button
                      onClick={() => setShowRatingModal(true)}
                      style={{ 
                        color: '#fff', 
                        backgroundColor: '#ffc107', 
                        padding: '12px 24px', 
                        border: 'none',
                        borderRadius: '8px',
                        display: 'inline-block',
                        marginLeft: '1em',
                        fontSize: '16px',
                        fontWeight: 'bold',
                        cursor: 'pointer'
                      }}
                    >
                      ⭐ Rate This Ad
                    </button>
                  )}
                </div>
                
                <p style={{ color: '#666', fontSize: '14px', marginTop: '1em' }}>
                  Your video was generated from the script you approved. Download and share your AI-created ad!
                </p>
              </div>
            </div>
          )}
        </div>
        
        {/* Input form */}
        {!result && !loading && !scriptGenerated && (
          <form className="input-row" onSubmit={handleSend}>
            {!answers.company_url ? (
              <div>
                <div style={{ 
                  background: '#e3f2fd', 
                  border: '1px solid #2196f3', 
                  borderRadius: '8px', 
                  padding: '12px', 
                  marginBottom: '12px',
                  fontSize: '14px',
                  color: '#1976d2'
                }}>
                  💡 <strong>Tip:</strong> Just enter the website domain (e.g., "apple.com" or "nike.com"). 
                  Our AI will research your company automatically.
                </div>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Enter your company website URL..."
                  style={{
                    width: '100%',
                    padding: '1rem',
                    borderRadius: '12px',
                    border: '1px solid var(--teal-mid)',
                    background: 'var(--input-bg)',
                    color: 'var(--text-light)',
                    fontSize: '1rem'
                  }}
                />
              </div>
            ) : step === 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {industryOptions.map(opt => (
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
                      cursor: 'pointer'
                    }}
                    onClick={() => {
                      setMessages(msgs => [...msgs, { sender: 'user', text: opt }]);
                      setAnswers(ans => ({ ...ans, industry: opt }));
                      setStep(1);
                      setMessages(msgs => [...msgs, { sender: 'bot', text: creativeQuestions[0].text }]);
                    }}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            ) : step <= creativeQuestions.length && creativeQuestions[step - 1]?.options ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {creativeQuestions[step - 1].options.map(opt => (
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
                      cursor: 'pointer'
                    }}
                    onClick={() => {
                      console.log('Button clicked:', opt, 'Current step:', step, 'Question:', creativeQuestions[step - 1]);
                      setMessages(msgs => [...msgs, { sender: 'user', text: opt }]);
                      const currentQuestion = creativeQuestions[step - 1];
                      const updatedAnswers = { ...answers, [currentQuestion.key]: opt };
                      console.log('Updating answers:', updatedAnswers);
                      setAnswers(updatedAnswers);
                      
                      if (step < creativeQuestions.length) {
                        setStep(step + 1);
                        const nextQuestion = creativeQuestions[step];
                        setMessages(msgs => [...msgs, { sender: 'bot', text: nextQuestion.text }]);
                      } else {
                        setStep(step + 1);
                        if (!productAsked && productsList.length > 0) {
                          setMessages(msgs => [...msgs, { sender: 'bot', text: 'Select a product or service to promote:' }]);
                          setProductAsked(true);
                        } else if (!productAsked) {
                          setMessages(msgs => [...msgs, { sender: 'bot', text: 'Type your product or service:' }]);
                          setProductAsked(true);
                        }
                      }
                    }}
                  >
                    {opt}
                  </button>
                  ))}
              </div>
              ) : (
                <input
                  value={input}
                onChange={(e) => setInput(e.target.value)}
                  placeholder="Type your answer..."
                style={{
                  width: '100%',
                  padding: '1rem',
                  borderRadius: '12px',
                  border: '1px solid var(--teal-mid)',
                  background: 'var(--input-bg)',
                  color: 'var(--text-light)',
                  fontSize: '1rem'
                }}
                />
            )}
            
            {/* Only show submit button for text inputs */}
            {((answers.company_url && step === 0) || 
              (step > 0 && step <= creativeQuestions.length && !creativeQuestions[step - 1]?.options) ||
              (productAsked && !productSelected)) && (
              <button type="submit" className="send-btn">
                Send
              </button>
            )}
          </form>
        )}
      
        {/* Show rating modal */}
      <RatingModal
          show={showRatingModal}
        onClose={handleRatingClose}
        onSubmit={handleRatingSubmit}
        />
        
        <style jsx>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </div>
  );
}

export default Chatbot;

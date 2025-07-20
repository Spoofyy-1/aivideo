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
  'E-commerce',
  'Finance',
  'Education',
  'Food & Beverage',
  'Real Estate',
  'Other'
];

const durationOptions = [
  '16 seconds (2 segments - VEO-3 Optimized)' // Fixed to 16 seconds only
];

const creativeQuestions = [
  { key: 'ad_type', text: "What style of ad do you want?", options: adTypeOptions },
  { key: 'mood', text: 'What mood should your ad have? (e.g., energetic, trustworthy, fun, professional, emotional)' },
  { key: 'target_audience', text: 'Who is your target audience? (e.g., young professionals, parents, seniors, tech enthusiasts)' },
  { key: 'main_message', text: 'What is the main message you want to communicate? (e.g., "fastest delivery", "most affordable", "life-changing results")' },
  { key: 'cta', text: "What action should viewers take? (e.g., 'Visit our website', 'Download the app', 'Call now', or type 'Auto' for us to create one)" }
];

function Chatbot() {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: "Hi! I'm your VEO-3 AI Ad Generator. Upload images, answer questions, and I'll create seamless 16-second ads with frame continuation!" },
    { sender: 'bot', text: '📁 First, drag & drop any images you want in your ad (product photos, dashboards, logos, etc.) or skip to start with questions.' },
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

  // VEO-3 Image Upload State
  const [uploadedImages, setUploadedImages] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [imageContextOptions, setImageContextOptions] = useState({});

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

  // VEO-3 Image Upload Handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleImageUpload(e.dataTransfer.files[0]);
    }
  };

  const handleImageUpload = async (file) => {
    if (uploadedImages.length >= 5) {
      setMessages(msgs => [...msgs, {
        sender: 'bot',
        text: '❌ Maximum 5 images allowed. Please remove an image first.'
      }]);
      return;
    }

    const formData = new FormData();
    formData.append('image', file);
    
    try {
      setLoading(true);
      setLoadingMessage('Uploading image...');
      
      const response = await fetch(`${API_BASE_URL}/upload-image`, {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (result.success) {
        // Add uploaded image to state with context selection
        const newImage = {
          id: Date.now(),
          file_path: result.file_path,
          filename: result.filename,
          context: 'product',
          placement: 'in use',
          description: '',
          preview: URL.createObjectURL(file)
        };
        
        setUploadedImages(prev => [...prev, newImage]);
        
        setMessages(msgs => [...msgs, {
          sender: 'bot',
          text: `✅ Uploaded "${file.name}" successfully! Describe what this image shows for better AI integration.`
        }]);
      } else {
        setMessages(msgs => [...msgs, {
          sender: 'bot',
          text: '❌ Failed to upload image. Please try again.'
        }]);
      }
    } catch (error) {
      console.error('Image upload error:', error);
      setMessages(msgs => [...msgs, {
        sender: 'bot',
        text: '❌ Failed to upload image. Please try again.'
      }]);
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  };

  const updateImageContext = (imageIndex, field, value) => {
    setUploadedImages(prev => 
      prev.map((img, index) => 
        index === imageIndex 
          ? { ...img, [field]: value }
          : img
      )
    );
  };

  const updateImageDescription = (imageId, description) => {
    setUploadedImages(prev => 
      prev.map(img => 
        img.id === imageId 
          ? { ...img, description }
          : img
      )
    );
  };

  const removeImage = (imageIndex) => {
    setUploadedImages(prev => prev.filter((img, index) => index !== imageIndex));
    setMessages(msgs => [...msgs, {
      sender: 'bot',
      text: 'Image removed successfully!'
    }]);
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
      uploadedImages: uploadedImages.length,
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
      setLoadingMessage('Generating VEO-3 optimized script...');
      setLoading(true);
      
      const scriptMessage = uploadedImages.length > 0 
        ? `Generating your 16-second VEO-3 script with ${uploadedImages.length} uploaded assets...`
        : 'Generating your 16-second VEO-3 script with frame continuation...';
      
      setMessages(msgs => [...msgs, { sender: 'bot', text: scriptMessage }]);
      
      try {
        console.log('Calling VEO-3 script generation with:', {
          answers: answersToCheck,
          uploadedImages: uploadedImages.length
        });
        
        // Use new VEO-3 script generation endpoint
        const response = await fetch(`${API_BASE_URL}/generate-script-with-images`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            product_name: answersToCheck.product,
            product_description: `${answersToCheck.features || ''} ${answersToCheck.industry || ''}`.trim(),
            target_audience: answersToCheck.industry || 'general audience',
            answers: {
              ...answersToCheck,
              duration: '16' // Fixed to 16 seconds
            },
            uploaded_images: uploadedImages.map(img => ({
              file_path: img.file_path,
              context: img.context,
              placement: img.placement,
              description: img.description
            }))
          })
        });

        const data = await response.json();
        
        if (data.success) {
          console.log('VEO-3 script generation successful:', data);
          
          setCurrentScript(data.script);
          setScriptAnalysis({
            veo3_optimized: true,
            duration: 16,
            segments: 2,
            features: data.veo3_features,
            uploaded_assets: uploadedImages.length
          });
          setCompanyInfo({ company_url: answersToCheck.company_url });
          setScriptGenerated(true);
          
          const successMessage = uploadedImages.length > 0
            ? `🎬 VEO-3 script ready! Optimized for 16 seconds with ${uploadedImages.length} uploaded assets integrated. Frame continuation enabled for seamless transitions!`
            : '🎬 VEO-3 script ready! Optimized for 16 seconds with frame continuation for seamless transitions!';
            
          setMessages(msgs => [...msgs, { 
            sender: 'bot', 
            text: successMessage + '\n\nReview it below and make any improvements before generating the video.'
          }]);
      } else {
          throw new Error(data.error || 'VEO-3 script generation failed');
        }
      } catch (err) {
        console.error('VEO-3 script generation error:', err);
        setMessages(msgs => [...msgs, { 
          sender: 'bot', 
          text: `Sorry, something went wrong generating your VEO-3 script: ${err.message}. Please try again.` 
        }]);
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

  // Handle script approval
  const handleScriptApproval = async () => {
      setLoading(true);
    setLoadingMessage('Generating your VEO-3 video with frame continuation...');
    setMessages(msgs => [...msgs, { sender: 'bot', text: 'Perfect! Generating your VEO-3 video with seamless frame continuation...' }]);
    
    try {
      console.log('Starting VEO-3 video generation with:', {
        script: currentScript,
        uploadedImages: uploadedImages.length
      });
      
      const response = await fetch(`${API_BASE_URL}/generate-video-veo3-continuation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          script: currentScript,
          uploaded_images: uploadedImages.map(img => ({
            file_path: img.file_path,
            context: img.context,
            placement: img.placement
          }))
        })
      });

      const data = await response.json();
      
      if (data.success) {
        console.log('VEO-3 video generation successful:', data);
        
        setResult({
          ...data,
          veo3_features: data.veo3_features_used || [
            'frame_to_video_continuation',
            'uploaded_image_integration',
            'seamless_camera_movement',
            'enhanced_physics_and_realism'
          ]
        });
        
        const successMessage = `🎬 VEO-3 video generated successfully!

✨ Features used:
• Frame-to-video continuation for seamless transitions
• ${data.technical_details?.image_assets_integrated || 0} uploaded assets integrated
• Enhanced physics and realism
• Cinematic camera movements

🎥 Duration: ${data.duration} seconds (2 seamless segments)`;

        setMessages(msgs => [...msgs, { 
          sender: 'bot', 
          text: successMessage
        }]);
        
        // Show rating modal after successful generation
        setTimeout(() => {
          if (!hasRated) {
            setShowRatingModal(true);
          }
        }, 2000);
      } else {
        throw new Error(data.error || 'VEO-3 video generation failed');
      }
    } catch (err) {
      console.error('VEO-3 video generation error:', err);
      setMessages(msgs => [...msgs, { 
        sender: 'bot', 
        text: `❌ Error generating VEO-3 video: ${err.message}. Please try again.` 
      }]);
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
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

  // Handle option clicks for industry and ad type selection
  const handleOptionClick = (option) => {
    setMessages(msgs => [...msgs, { sender: 'user', text: option }]);
    
    // Handle industry selection
    if (!answers.industry) {
      setAnswers(ans => ({ ...ans, industry: option }));
      setMessages(msgs => [...msgs, { sender: 'bot', text: creativeQuestions[0].text }]);
      setStep(1);
      return;
    }
    
    // Handle creative questions with options (ad_type)
    if (step <= creativeQuestions.length) {
      const currentQuestion = creativeQuestions[step - 1];
      const newAnswers = { ...answers, [currentQuestion.key]: option };
      setAnswers(newAnswers);
      
      if (step < creativeQuestions.length) {
        setStep(step + 1);
        const nextQuestion = creativeQuestions[step];
        setMessages(msgs => [...msgs, { sender: 'bot', text: nextQuestion.text }]);
      } else {
        setStep(step + 1);
        // Show product selection after all questions
        if (!productAsked && productsList.length > 0) {
          setMessages(msgs => [...msgs, { sender: 'bot', text: 'Select a product or service to promote:' }]);
          setProductAsked(true);
        } else if (!productAsked) {
          setMessages(msgs => [...msgs, { sender: 'bot', text: 'Type your product or service:' }]);
          setProductAsked(true);
        }
      }
    }
  };

  return (
    <div className="chatbot-container">
      {/* Only show script preview when script is generated, hide everything else */}
      {scriptGenerated ? (
        <div className="script-only-container">
          <ScriptPreview
            script={currentScript}
            scriptAnalysis={scriptAnalysis}
            companyInfo={companyInfo}
            userAnswers={answers}
            onImprove={handleScriptImprovement}
            onApprove={handleScriptApproval}
            loading={loading}
          />
        </div>
      ) : (
        /* Main Content */
        <div className="main-layout">
          {/* Chat Panel */}
          <div className="chat-panel">
            <div className="panel-header">
              <h2>Chat</h2>
            </div>
            
            <div className="chat-messages" ref={chatRef}>
              {messages.map((msg, index) => (
                <div key={index} className={`message ${msg.sender}`}>
                  <div className="message-bubble">{msg.text}</div>
                </div>
              ))}
              
              {/* Loading indicator */}
              {loading && (
                <div className="message bot">
                  <div className="message-bubble">
                    {loadingMessage}
                    <div className="loading-spinner">⚡</div>
                  </div>
                </div>
              )}
              
              {/* Industry options */}
              {researchDone && !answers.industry && (
                <div className="message bot">
                  <div className="message-bubble">
                    <div className="options-grid">
                      {industryOptions.map((option, index) => (
                        <button
                          key={index}
                          onClick={() => handleOptionClick(option)}
                          className="option-btn"
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Product selection after industry */}
              {researchDone && answers.industry && !productAsked && !productSelected && step >= creativeQuestions.length && (
                <div className="message bot">
                  <div className="message-bubble">
                    <div className="options-grid">
                      {productsList.slice(0, 6).map((product, index) => (
                        <button
                          key={index}
                          onClick={() => handleProductSelect(product)}
                          className="option-btn"
                        >
                          {product}
                        </button>
                      ))}
                      <button onClick={handleCustomProduct} className="option-btn custom">
                        Type your product/service
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Creative question options */}
              {answers.industry && step < creativeQuestions.length && (
                <div className="message bot">
                  <div className="message-bubble">
                    <div className="options-grid">
                      {adTypeOptions.map((option, index) => (
                        <button
                          key={index}
                          onClick={() => handleOptionClick(option)}
                          className="option-btn"
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input form */}
            {!loading && !scriptGenerated && (
              <div className="chat-input">
                {!answers.company_url ? (
                  <div>
                    <div className="input-tip">
                      💡 <strong>Tip:</strong> Just enter the website domain (e.g., "apple.com" or "nike.com"). 
                      Our AI will research your company automatically.
                    </div>
                    <form onSubmit={handleSend} className="input-form">
                      <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Enter your company website URL..."
                        className="text-input"
                      />
                      <button type="submit" className="send-btn">Send</button>
                    </form>
                  </div>
                ) : (step <= creativeQuestions.length && !answers.industry) || 
                     (step <= creativeQuestions.length && creativeQuestions[step - 1] && !creativeQuestions[step - 1].options) ||
                     (productAsked && !productSelected) ? (
                  <form onSubmit={handleSend} className="input-form">
                    <input
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder={
                        productAsked && !productSelected ? "Type your product or service..." :
                        step <= creativeQuestions.length ? 
                          creativeQuestions[step - 1]?.placeholder || "Type your answer..." : 
                          "Type your answer..."
                      }
                      className="text-input"
                    />
                    <button type="submit" className="send-btn">Send</button>
                  </form>
                ) : null}
              </div>
            )}
          </div>
          
          {/* Image Drop Panel */}
          <div className="image-panel">
            <div className="panel-header">
              <h2>Image drop box</h2>
            </div>
            
            <div 
              className={`drop-zone ${dragActive ? 'drag-active' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <div className="drop-content">
                <div className="drop-icon">📁</div>
                <p>Drop images here</p>
                <button
                  className="browse-btn"
                  onClick={() => document.getElementById('file-input').click()}
                >
                  Browse Files
                </button>
                <input
                  id="file-input"
                  type="file"
                  accept="image/*"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleImageUpload(e.target.files[0]);
                    }
                  }}
                />
              </div>
            </div>

            {/* Uploaded Images */}
            {uploadedImages.length > 0 && (
              <div className="uploaded-images">
                <h3>Uploaded Images ({uploadedImages.length})</h3>
                <div className="images-list">
                  {uploadedImages.map((img, index) => (
                    <div key={index} className="image-item">
                      <div className="image-preview">
                        <img src={img.preview} alt={img.filename} />
                        <button
                          className="remove-btn"
                          onClick={() => removeImage(index)}
                        >
                          ✕
                        </button>
                      </div>
                      <div className="image-name">{img.filename}</div>
                      <div className="image-description">
                        <textarea
                          placeholder="Describe this image (e.g., 'Product dashboard showing analytics', 'CEO headshot for testimonial', etc.)"
                          value={img.description || ''}
                          onChange={(e) => updateImageContext(index, 'description', e.target.value)}
                          className="description-input"
                          rows="3"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Show result when video is generated */}
      {result && (
        <div className="result-section">
          <div className="result-card">
            <h3>🎉 Your VEO-3 AI Video Ad is Ready!</h3>
            
            {/* VEO-3 Features Display */}
            {result.veo3_features && (
              <div className="features-display">
                <h4>✨ VEO-3 Features Used:</h4>
                <ul>
                  {result.veo3_features.map((feature, index) => (
                    <li key={index}>
                      {feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* Technical Details */}
            {result.technical_details && (
              <div className="technical-details">
                <h4>🔧 Technical Details:</h4>
                <div>
                  <p><strong>Duration:</strong> {result.duration} seconds (2 seamless segments)</p>
                  <p><strong>Segments Generated:</strong> {result.segments_generated}</p>
                  <p><strong>Image Assets Integrated:</strong> {result.technical_details.image_assets_integrated}</p>
                  <p><strong>Frame Continuation:</strong> {result.technical_details.continuation_frame}</p>
                </div>
              </div>
            )}
            
            <div className="download-buttons">
              <a
                href={`${API_BASE_URL}${result.video_url}`}
                download
                className="download-btn primary"
              >
                🎬 Download VEO-3 Video
              </a>
              
              {result.report_url && (
                <a
                  href={`${API_BASE_URL}${result.report_url}`}
                  download
                  className="download-btn secondary"
                >
                  📄 Download Report
                </a>
              )}
              
              {!hasRated && (
                <button
                  onClick={() => setShowRatingModal(true)}
                  className="download-btn rating"
                >
                  ⭐ Rate This VEO-3 Ad
                </button>
              )}
            </div>
            
            <p className="result-description">
              🎯 Your video was generated using Google's VEO-3 with frame-to-video continuation for seamless transitions. 
              {uploadedImages.length > 0 && ` Your ${uploadedImages.length} uploaded assets were integrated into the scenes.`}
              {' '}Download and share your professional AI-created ad!
            </p>
          </div>
        </div>
      )}

      {/* Show rating modal */}
      {showRatingModal && (
        <RatingModal
          isOpen={showRatingModal}
          onClose={handleRatingClose}
          onSubmit={handleRatingSubmit}
          sessionId={result?.session_id}
          adType={answers.ad_type}
          industry={answers.industry}
          companyUrl={answers.company_url}
          adScript={JSON.stringify(currentScript)}
        />
      )}

      <style jsx>{`
        .chatbot-container {
          height: 100vh;
          background: linear-gradient(135deg, #D789D7 0%, #9C27B0 25%, #673AB7 50%, #3F51B5 75%, #1A237E 100%);
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
          display: flex;
          flex-direction: column;
        }

        .main-layout {
          flex: 1;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 2rem;
          padding: 2rem;
          min-height: 0;
        }

        .chat-panel,
        .image-panel {
          background: rgba(45, 55, 72, 0.95);
          border-radius: 24px;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
          backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .panel-header {
          background: rgba(26, 35, 126, 0.8);
          padding: 1.5rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .panel-header h2 {
          margin: 0;
          font-size: 1.5rem;
          font-weight: 600;
          color: white;
          text-align: center;
        }

        .chat-messages {
          flex: 1;
          overflow-y: auto;
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
          background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
          min-height: 300px;
          max-height: calc(100vh - 400px);
        }

        .message {
          display: flex;
          flex-direction: column;
        }

        .message.bot {
          align-items: flex-start;
        }

        .message.user {
          align-items: flex-end;
        }

        .message-bubble {
          max-width: 80%;
          padding: 1rem 1.5rem;
          border-radius: 18px;
          line-height: 1.6;
          font-weight: 500;
        }

        .message.bot .message-bubble {
          background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%);
          color: white;
        }

        .message.user .message-bubble {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .loading-spinner {
          display: inline-block;
          margin-left: 0.5rem;
          animation: spin 1s linear infinite;
        }

        .options-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 0.8rem;
          margin-top: 1rem;
          max-height: 300px;
          overflow-y: auto;
          overflow-x: hidden;
          scrollbar-width: thin;
          scrollbar-color: rgba(156, 39, 176, 0.6) rgba(45, 55, 72, 0.3);
          padding-right: 8px;
        }

        .options-grid::-webkit-scrollbar {
          width: 8px;
        }

        .options-grid::-webkit-scrollbar-track {
          background: rgba(45, 55, 72, 0.3);
          border-radius: 4px;
        }

        .options-grid::-webkit-scrollbar-thumb {
          background: rgba(156, 39, 176, 0.6);
          border-radius: 4px;
        }

        .options-grid::-webkit-scrollbar-thumb:hover {
          background: rgba(156, 39, 176, 0.8);
        }

        .option-btn {
          background: linear-gradient(135deg, #3F51B5 0%, #9C27B0 100%);
          color: white;
          border: none;
          padding: 0.8rem 1.2rem;
          border-radius: 12px;
          cursor: pointer;
          font-weight: 600;
          font-size: 0.9rem;
          transition: all 0.3s ease;
          box-shadow: 0 4px 15px rgba(63, 81, 181, 0.3);
          text-align: center;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .option-btn:hover {
          transform: translateY(-3px);
          box-shadow: 0 8px 25px rgba(63, 81, 181, 0.4);
        }

        .chat-input {
          padding: 1.5rem;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
          background: rgba(45, 55, 72, 0.8);
        }

        .input-tip {
          background: rgba(26, 35, 126, 0.3);
          border: 1px solid #3F51B5;
          border-radius: 12px;
          padding: 1rem;
          margin-bottom: 1rem;
          font-size: 0.9rem;
          color: white;
          font-weight: 500;
        }

        .input-form {
          display: flex;
          gap: 0.8rem;
        }

        .text-input {
          flex: 1;
          padding: 1rem 1.5rem;
          border: 2px solid rgba(255, 255, 255, 0.2);
          border-radius: 15px;
          font-size: 1rem;
          transition: all 0.3s ease;
          background: rgba(45, 55, 72, 0.8);
          color: white;
          font-family: inherit;
        }

        .text-input:focus {
          outline: none;
          border-color: #3F51B5;
          box-shadow: 0 0 0 4px rgba(63, 81, 181, 0.1);
          transform: translateY(-2px);
        }

        .text-input::placeholder {
          color: rgba(255, 255, 255, 0.5);
        }

        .send-btn {
          background: linear-gradient(135deg, #3F51B5 0%, #9C27B0 100%);
          color: white;
          border: none;
          padding: 1rem 2rem;
          border-radius: 15px;
          cursor: pointer;
          font-weight: 600;
          font-size: 1rem;
          transition: all 0.3s ease;
          box-shadow: 0 4px 15px rgba(63, 81, 181, 0.3);
        }

        .send-btn:hover {
          transform: translateY(-3px);
          box-shadow: 0 8px 25px rgba(63, 81, 181, 0.4);
        }

        .drop-zone {
          flex: 1;
          margin: 1.5rem;
          border: 3px dashed #9C27B0;
          border-radius: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
          cursor: pointer;
          background: rgba(45, 55, 72, 0.5);
        }

        .drop-zone.drag-active {
          border-color: #3F51B5;
          background: rgba(63, 81, 181, 0.2);
          transform: scale(1.02);
          box-shadow: 0 10px 30px rgba(63, 81, 181, 0.2);
        }

        .drop-zone:hover {
          border-color: #3F51B5;
          background: rgba(63, 81, 181, 0.1);
        }

        .drop-content {
          text-align: center;
          color: white;
        }

        .drop-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
          color: #9C27B0;
        }

        .drop-content p {
          font-size: 1.2rem;
          font-weight: 500;
          margin-bottom: 1.5rem;
          color: white;
        }

        .browse-btn {
          background: linear-gradient(135deg, #3F51B5 0%, #9C27B0 100%);
          color: white;
          border: none;
          padding: 1rem 2rem;
          border-radius: 12px;
          cursor: pointer;
          font-weight: 600;
          font-size: 1rem;
          transition: all 0.3s ease;
          box-shadow: 0 4px 15px rgba(63, 81, 181, 0.3);
        }

        .browse-btn:hover {
          transform: translateY(-3px);
          box-shadow: 0 8px 25px rgba(63, 81, 181, 0.4);
        }

        .uploaded-images {
          padding: 1.5rem;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
          background: rgba(45, 55, 72, 0.8);
          max-height: 400px;
          overflow-y: auto;
          overflow-x: hidden;
          scrollbar-width: thin;
          scrollbar-color: rgba(156, 39, 176, 0.6) rgba(45, 55, 72, 0.3);
        }

        .uploaded-images::-webkit-scrollbar {
          width: 8px;
        }

        .uploaded-images::-webkit-scrollbar-track {
          background: rgba(45, 55, 72, 0.3);
          border-radius: 4px;
        }

        .uploaded-images::-webkit-scrollbar-thumb {
          background: rgba(156, 39, 176, 0.6);
          border-radius: 4px;
        }

        .uploaded-images::-webkit-scrollbar-thumb:hover {
          background: rgba(156, 39, 176, 0.8);
        }

        .uploaded-images h3 {
          margin: 0 0 1rem 0;
          font-size: 1.1rem;
          color: white;
          font-weight: 600;
        }

        .images-list {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 1.5rem;
        }

        .image-item {
          position: relative;
          display: flex;
          flex-direction: column;
        }

        .image-preview {
          position: relative;
          aspect-ratio: 1;
          border-radius: 12px;
          overflow: hidden;
          background: rgba(45, 55, 72, 0.8);
        }

        .image-preview img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .remove-btn {
          position: absolute;
          top: 8px;
          right: 8px;
          background: rgba(239, 68, 68, 0.9);
          color: white;
          border: none;
          border-radius: 50%;
          width: 24px;
          height: 24px;
          cursor: pointer;
          font-size: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
        }

        .remove-btn:hover {
          background: #ef4444;
          transform: scale(1.1);
        }

        .image-name {
          margin-top: 0.5rem;
          font-size: 0.8rem;
          color: rgba(255, 255, 255, 0.7);
          text-align: center;
          word-break: break-word;
        }

        .image-description {
          margin-top: 0.5rem;
          display: flex;
          justify-content: center;
        }

        .description-input {
          flex: 1;
          padding: 0.5rem 0.8rem;
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 8px;
          font-size: 0.8rem;
          color: white;
          background: rgba(45, 55, 72, 0.8);
          font-family: inherit;
          resize: none;
          min-height: 40px;
          max-height: 80px;
          overflow-y: auto;
          width: 100%;
        }

        .description-input:focus {
          outline: none;
          border-color: #3F51B5;
          box-shadow: 0 0 0 4px rgba(63, 81, 181, 0.1);
          transform: translateY(-2px);
        }

        .description-input::placeholder {
          color: rgba(255, 255, 255, 0.5);
        }

        .result-section {
          margin-top: 1rem;
        }

        .result-card {
          background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(63, 81, 181, 0.2) 100%);
          border: 2px solid #10b981;
          border-radius: 16px;
          padding: 2rem;
        }

        .result-card h3 {
          color: white;
          margin-bottom: 1.5rem;
          font-size: 1.5rem;
        }

        .features-display {
          background: rgba(16, 185, 129, 0.2);
          padding: 1rem;
          border-radius: 8px;
          margin-bottom: 1rem;
          border: 1px solid #10b981;
        }

        .features-display h4 {
          color: #10b981;
          margin-bottom: 0.5rem;
          font-size: 1.1rem;
        }

        .features-display ul {
          margin: 0;
          padding-left: 1.2rem;
          color: white;
        }

        .features-display li {
          margin-bottom: 0.3rem;
        }

        .technical-details {
          background: rgba(251, 191, 36, 0.2);
          padding: 1rem;
          border-radius: 8px;
          margin-bottom: 1rem;
          border: 1px solid #fbbf24;
        }

        .technical-details h4 {
          color: #fbbf24;
          margin-bottom: 0.5rem;
          font-size: 1.1rem;
        }

        .technical-details div {
          color: white;
          font-size: 0.9rem;
        }

        .technical-details p {
          margin: 0.2rem 0;
        }

        .download-buttons {
          margin: 1.5rem 0;
          display: flex;
          gap: 1rem;
          flex-wrap: wrap;
        }

        .download-btn {
          color: white;
          padding: 1rem 2rem;
          text-decoration: none;
          border-radius: 12px;
          display: inline-block;
          font-size: 1rem;
          font-weight: 600;
          transition: all 0.3s ease;
          border: none;
          cursor: pointer;
        }

        .download-btn.primary {
          background: linear-gradient(135deg, #3F51B5 0%, #9C27B0 100%);
          box-shadow: 0 4px 15px rgba(63, 81, 181, 0.3);
        }

        .download-btn.secondary {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        }

        .download-btn.rating {
          background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
          box-shadow: 0 4px 15px rgba(251, 191, 36, 0.3);
        }

        .download-btn:hover {
          transform: translateY(-3px);
          box-shadow: 0 8px 25px rgba(63, 81, 181, 0.4);
        }

        .result-description {
          color: rgba(255, 255, 255, 0.8);
          font-size: 0.9rem;
          margin-top: 1rem;
          line-height: 1.5;
        }

        /* Mobile Responsive */
        @media (max-width: 768px) {
          .main-layout {
            grid-template-columns: 1fr;
            gap: 1rem;
            padding: 1rem;
          }

          .panel-header h2 {
            font-size: 1.2rem;
          }

          .options-grid {
            grid-template-columns: 1fr 1fr;
            max-height: 250px;
            gap: 0.6rem;
          }

          .option-btn {
            padding: 0.7rem 1rem;
            font-size: 0.85rem;
          }

          .chat-messages {
            min-height: 200px;
            max-height: calc(100vh - 350px);
          }

          .download-buttons {
            flex-direction: column;
          }

          .images-list {
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
          }

          .uploaded-images {
            max-height: 300px;
          }

          .logo-img {
            width: 100px;
            height: 100px;
          }

          .logo {
            font-size: 1.8rem;
          }
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default Chatbot;

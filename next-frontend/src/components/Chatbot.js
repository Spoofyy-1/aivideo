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
  '16 seconds (2 segments - VEO-3 Optimized)' // Fixed to 16 seconds only
];

const creativeQuestions = [
  // Removed duration question since it's fixed to 16 seconds
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
  const [showImageSidebar, setShowImageSidebar] = useState(true);

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
          suggested_contexts: result.suggested_contexts,
          context: result.suggested_contexts[0] || 'product',
          placement: 'in use', // Default placement
          description: '', // User can add custom description
          preview: URL.createObjectURL(file)
        };
        
        setUploadedImages(prev => [...prev, newImage]);
        setImageContextOptions(result.context_options);
        
        setMessages(msgs => [...msgs, {
          sender: 'bot',
          text: `✅ Uploaded "${file.name}" - Check the sidebar to add a description and adjust settings!`
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

  const updateImageContext = (imageId, context, placement) => {
    setUploadedImages(prev => 
      prev.map(img => 
        img.id === imageId 
          ? { ...img, context, placement }
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

  const removeImage = (imageId) => {
    setUploadedImages(prev => prev.filter(img => img.id !== imageId));
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

  return (
    <div className="chatbot-layout">
      {/* Image Sidebar */}
      <div className={`image-sidebar ${showImageSidebar ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h3>🎬 Visual Assets</h3>
          <button 
            className="toggle-sidebar"
            onClick={() => setShowImageSidebar(!showImageSidebar)}
          >
            {showImageSidebar ? '◀' : '▶'}
          </button>
        </div>

        {/* Upload Zone in Sidebar */}
        <div 
          className={`sidebar-upload-zone ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="upload-icon">📁</div>
          <p>Drop images here</p>
          <button 
            className="browse-btn"
            onClick={() => document.getElementById('sidebar-file-input').click()}
          >
            Browse Files
          </button>
          <input
            id="sidebar-file-input"
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => e.target.files[0] && handleImageUpload(e.target.files[0])}
          />
        </div>

        {/* Uploaded Images List */}
        <div className="uploaded-images-list">
          {uploadedImages.length === 0 ? (
            <div className="no-images">
              <p>No images uploaded yet</p>
              <span>Upload product photos, dashboards, logos, or any visuals you want in your ad!</span>
            </div>
          ) : (
            uploadedImages.map(img => (
              <div key={img.id} className="image-card">
                <div className="image-preview">
                  <img src={img.preview} alt={img.filename} />
                  <button 
                    className="remove-image-btn"
                    onClick={() => removeImage(img.id)}
                    title="Remove image"
                  >
                    ✕
                  </button>
                </div>
                
                <div className="image-details">
                  <div className="filename">{img.filename}</div>
                  
                  <div className="form-group">
                    <label>Description:</label>
                    <textarea
                      placeholder="Describe what this image shows..."
                      value={img.description}
                      onChange={(e) => updateImageDescription(img.id, e.target.value)}
                      rows="2"
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>Context:</label>
                    <select 
                      value={img.context} 
                      onChange={(e) => updateImageContext(img.id, e.target.value, img.placement)}
                    >
                      {Object.keys(imageContextOptions).map(context => (
                        <option key={context} value={context}>{context}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="form-group">
                    <label>How to show:</label>
                    <select 
                      value={img.placement}
                      onChange={(e) => updateImageContext(img.id, img.context, e.target.value)}
                    >
                      {imageContextOptions[img.context]?.map(placement => (
                        <option key={placement} value={placement}>{placement}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="main-chat-area">
    <div className="chatbot-outer">
      <div className="container">
            <h1>🎬 VEO-3 AI Ad Generator</h1>
            <p className="subtitle">
              Create seamless 16-second ads with frame continuation
              {uploadedImages.length > 0 && ` • ${uploadedImages.length} assets uploaded`}
            </p>
            
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
                  <div style={{ margin: '1em 0', padding: '1.5em', background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)', borderRadius: '12px', border: '2px solid #28a745' }}>
                    <h3 style={{ color: '#333', marginBottom: '1em', fontSize: '1.5rem' }}>
                      🎉 Your VEO-3 AI Video Ad is Ready!
                    </h3>
                    
                    {/* VEO-3 Features Display */}
                    {result.veo3_features && (
                      <div style={{ 
                        background: '#e8f5e8', 
                        padding: '1rem', 
                        borderRadius: '8px', 
                        marginBottom: '1rem',
                        border: '1px solid #28a745'
                      }}>
                        <h4 style={{ color: '#155724', marginBottom: '0.5rem', fontSize: '1.1rem' }}>
                          ✨ VEO-3 Features Used:
                        </h4>
                        <ul style={{ margin: '0', paddingLeft: '1.2rem', color: '#155724' }}>
                          {result.veo3_features.map((feature, index) => (
                            <li key={index} style={{ marginBottom: '0.3rem' }}>
                              {feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {/* Technical Details */}
                    {result.technical_details && (
                      <div style={{ 
                        background: '#fff3cd', 
                        padding: '1rem', 
                        borderRadius: '8px', 
                        marginBottom: '1rem',
                        border: '1px solid #ffc107'
                      }}>
                        <h4 style={{ color: '#856404', marginBottom: '0.5rem', fontSize: '1.1rem' }}>
                          🔧 Technical Details:
                        </h4>
                        <div style={{ color: '#856404', fontSize: '0.9rem' }}>
                          <p><strong>Duration:</strong> {result.duration} seconds (2 seamless segments)</p>
                          <p><strong>Segments Generated:</strong> {result.segments_generated}</p>
                          <p><strong>Image Assets Integrated:</strong> {result.technical_details.image_assets_integrated}</p>
                          <p><strong>Frame Continuation:</strong> {result.technical_details.continuation_frame}</p>
                        </div>
                      </div>
                    )}
                    
                    <div style={{ margin: '1.5em 0' }}>
                  <a
                    href={`${API_BASE_URL}${result.video_url}`}
                    download
                    style={{ 
                      color: '#fff', 
                      backgroundColor: '#007bff', 
                          padding: '14px 28px', 
                      textDecoration: 'none', 
                          borderRadius: '10px',
                      display: 'inline-block',
                      marginRight: '1em',
                          marginBottom: '0.5em',
                      fontSize: '16px',
                          fontWeight: 'bold',
                          boxShadow: '0 4px 8px rgba(0,123,255,0.3)'
                    }}
                  >
                        🎬 Download VEO-3 Video
                  </a>
                  
                      {result.report_url && (
                  <a
                    href={`${API_BASE_URL}${result.report_url}`}
                    download
                    style={{ 
                      color: '#fff', 
                      backgroundColor: '#28a745', 
                            padding: '14px 28px', 
                      textDecoration: 'none', 
                            borderRadius: '10px',
                      display: 'inline-block',
                            marginRight: '1em',
                            marginBottom: '0.5em',
                      fontSize: '16px',
                            fontWeight: 'bold',
                            boxShadow: '0 4px 8px rgba(40,167,69,0.3)'
                    }}
                  >
                    📄 Download Report
                  </a>
                      )}
                  
                  {!hasRated && (
                    <button
                      onClick={() => setShowRatingModal(true)}
                      style={{ 
                        color: '#fff', 
                        backgroundColor: '#ffc107', 
                            padding: '14px 28px', 
                        border: 'none',
                            borderRadius: '10px',
                        display: 'inline-block',
                            marginBottom: '0.5em',
                        fontSize: '16px',
                        fontWeight: 'bold',
                            cursor: 'pointer',
                            boxShadow: '0 4px 8px rgba(255,193,7,0.3)'
                      }}
                    >
                          ⭐ Rate This VEO-3 Ad
                    </button>
                  )}
                </div>
                
                    <p style={{ color: '#666', fontSize: '14px', marginTop: '1em', lineHeight: '1.5' }}>
                      🎯 Your video was generated using Google's VEO-3 with frame-to-video continuation for seamless transitions. 
                      {uploadedImages.length > 0 && ` Your ${uploadedImages.length} uploaded assets were integrated into the scenes.`}
                      {' '}Download and share your professional AI-created ad!
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
              .chatbot-layout {
                display: flex;
                height: 100vh;
                background: #f5f7fa;
              }

              .image-sidebar {
                width: 350px;
                background: white;
                border-right: 2px solid #e1e8ed;
                display: flex;
                flex-direction: column;
                transition: all 0.3s ease;
                overflow: hidden;
              }

              .image-sidebar.closed {
                width: 50px;
              }

              .sidebar-header {
                padding: 1rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #e1e8ed;
              }

              .sidebar-header h3 {
                margin: 0;
                font-size: 1.1rem;
                white-space: nowrap;
                overflow: hidden;
              }

              .toggle-sidebar {
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                padding: 0.5rem;
                border-radius: 4px;
                cursor: pointer;
                font-size: 1rem;
                transition: background 0.2s;
              }

              .toggle-sidebar:hover {
                background: rgba(255,255,255,0.3);
              }

              .sidebar-upload-zone {
                margin: 1rem;
                border: 2px dashed #ccc;
                border-radius: 12px;
                padding: 1.5rem;
                text-align: center;
                background: #f9f9f9;
                transition: all 0.3s ease;
                cursor: pointer;
              }

              .sidebar-upload-zone.drag-active {
                border-color: #2196f3;
                background: #f3f8ff;
                transform: scale(1.02);
              }

              .upload-icon {
                font-size: 2rem;
                margin-bottom: 0.5rem;
              }

              .browse-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 0.6rem 1.2rem;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                margin-top: 0.5rem;
                transition: transform 0.2s;
              }

              .browse-btn:hover {
                transform: translateY(-2px);
              }

              .uploaded-images-list {
                flex: 1;
                overflow-y: auto;
                padding: 0 1rem 1rem;
              }

              .no-images {
                text-align: center;
                padding: 2rem 1rem;
                color: #666;
              }

              .no-images p {
                font-weight: 600;
                margin-bottom: 0.5rem;
              }

              .no-images span {
                font-size: 0.9rem;
                line-height: 1.4;
              }

              .image-card {
                background: white;
                border: 1px solid #e1e8ed;
                border-radius: 12px;
                margin-bottom: 1rem;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                transition: transform 0.2s, box-shadow 0.2s;
              }

              .image-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 16px rgba(0,0,0,0.15);
              }

              .image-preview {
                position: relative;
                height: 120px;
                overflow: hidden;
              }

              .image-preview img {
                width: 100%;
                height: 100%;
                object-fit: cover;
              }

              .remove-image-btn {
                position: absolute;
                top: 8px;
                right: 8px;
                background: rgba(255,68,68,0.9);
                color: white;
                border: none;
                border-radius: 50%;
                width: 28px;
                height: 28px;
                cursor: pointer;
                font-size: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
              }

              .remove-image-btn:hover {
                background: #ff4444;
                transform: scale(1.1);
              }

              .image-details {
                padding: 1rem;
              }

              .filename {
                font-weight: 600;
                color: #333;
                margin-bottom: 0.8rem;
                font-size: 0.9rem;
                word-break: break-word;
              }

              .form-group {
                margin-bottom: 0.8rem;
              }

              .form-group label {
                display: block;
                font-weight: 600;
                color: #555;
                margin-bottom: 0.3rem;
                font-size: 0.85rem;
              }

              .form-group select,
              .form-group textarea {
                width: 100%;
                padding: 0.5rem;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 0.85rem;
                transition: border-color 0.2s;
              }

              .form-group select:focus,
              .form-group textarea:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
              }

              .form-group textarea {
                resize: vertical;
                min-height: 60px;
                font-family: inherit;
              }

              .main-chat-area {
                flex: 1;
                display: flex;
                flex-direction: column;
                background: #f5f7fa;
              }

              .chatbot-outer {
                flex: 1;
                display: flex;
                flex-direction: column;
                max-width: 100%;
              }

              .container {
                flex: 1;
                display: flex;
                flex-direction: column;
                padding: 1rem 2rem;
                max-width: 900px;
                margin: 0 auto;
                width: 100%;
              }

              .subtitle {
                color: #666;
                text-align: center;
                margin-bottom: 1rem;
                font-size: 1rem;
              }

              .chat {
                flex: 1;
                overflow-y: auto;
                padding: 1rem 0;
              }

              /* Mobile Responsive */
              @media (max-width: 768px) {
                .chatbot-layout {
                  flex-direction: column;
                  height: auto;
                  min-height: 100vh;
                }

                .image-sidebar {
                  width: 100%;
                  height: auto;
                  max-height: 40vh;
                  order: 2;
                }

                .image-sidebar.closed {
                  width: 100%;
                  height: 60px;
                }

                .main-chat-area {
                  order: 1;
                }

                .container {
                  padding: 1rem;
                }

                .sidebar-header h3 {
                  font-size: 1rem;
                }
              }

              @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
              }
            `}</style>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chatbot;

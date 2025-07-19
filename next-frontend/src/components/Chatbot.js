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
                <div className="info-tip">
                  💡 <strong>Tip:</strong> Just enter the website domain (e.g., "apple.com" or "nike.com"). 
                  Our AI will research your company automatically.
                </div>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Enter your company website URL..."
                />
              </div>
            ) : step === 0 ? (
              <div className="options-grid">
                {industryOptions.map(opt => (
                  <button
                    key={opt}
                    type="button"
                    className="option-btn"
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
              <div className="options-grid">
                {creativeQuestions[step - 1].options.map(opt => (
                  <button
                    key={opt}
                    type="button"
                    className="option-btn"
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
              <div>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={step <= creativeQuestions.length ? 
                    creativeQuestions[step - 1]?.placeholder || "Type your answer..." : 
                    "Type your product or service..."
                  }
                />
                <button type="submit">Send</button>
              </div>
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
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
              }

              .image-sidebar {
                width: 380px;
                background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
                border-right: none;
                display: flex;
                flex-direction: column;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                overflow: hidden;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
              }

              .image-sidebar.closed {
                width: 70px;
              }

              .sidebar-header {
                padding: 1.5rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 2px 20px rgba(102, 126, 234, 0.3);
              }

              .sidebar-header h3 {
                margin: 0;
                font-size: 1.2rem;
                font-weight: 700;
                white-space: nowrap;
                overflow: hidden;
                display: flex;
                align-items: center;
                gap: 0.5rem;
              }

              .toggle-sidebar {
                background: rgba(255,255,255,0.15);
                border: none;
                color: white;
                padding: 0.7rem;
                border-radius: 12px;
                cursor: pointer;
                font-size: 1.1rem;
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
              }

              .toggle-sidebar:hover {
                background: rgba(255,255,255,0.25);
                transform: scale(1.05);
              }

              .sidebar-upload-zone {
                margin: 1.5rem;
                border: 3px dashed #e2e8f0;
                border-radius: 16px;
                padding: 2rem 1rem;
                text-align: center;
                background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                cursor: pointer;
                position: relative;
                overflow: hidden;
              }

              .sidebar-upload-zone::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
                opacity: 0;
                transition: opacity 0.3s ease;
              }

              .sidebar-upload-zone:hover::before {
                opacity: 1;
              }

              .sidebar-upload-zone.drag-active {
                border-color: #667eea;
                background: linear-gradient(135deg, #eff6ff 0%, #f0f4ff 100%);
                transform: scale(1.02);
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2);
              }

              .sidebar-upload-zone:hover {
                border-color: #667eea;
                transform: translateY(-2px);
              }

              .upload-icon {
                font-size: 2.5rem;
                margin-bottom: 0.8rem;
                color: #667eea;
              }

              .sidebar-upload-zone p {
                margin: 0.5rem 0;
                color: #475569;
                font-weight: 500;
              }

              .browse-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 0.8rem 1.5rem;
                border-radius: 12px;
                cursor: pointer;
                font-weight: 600;
                margin-top: 0.8rem;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                font-size: 0.95rem;
              }

              .browse-btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
              }

              .uploaded-images-list {
                flex: 1;
                overflow-y: auto;
                padding: 0 1.5rem 1.5rem;
                scrollbar-width: thin;
                scrollbar-color: #cbd5e1 transparent;
              }

              .uploaded-images-list::-webkit-scrollbar {
                width: 6px;
              }

              .uploaded-images-list::-webkit-scrollbar-track {
                background: transparent;
              }

              .uploaded-images-list::-webkit-scrollbar-thumb {
                background: #cbd5e1;
                border-radius: 3px;
              }

              .no-images {
                text-align: center;
                padding: 3rem 1.5rem;
                color: #64748b;
              }

              .no-images p {
                font-weight: 600;
                margin-bottom: 0.8rem;
                font-size: 1.1rem;
                color: #475569;
              }

              .no-images span {
                font-size: 0.95rem;
                line-height: 1.6;
                color: #64748b;
              }

              .image-card {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 16px;
                margin-bottom: 1.5rem;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
              }

              .image-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 12px 40px rgba(0,0,0,0.15);
                border-color: #667eea;
              }

              .image-preview {
                position: relative;
                height: 140px;
                overflow: hidden;
                background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
              }

              .image-preview img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                transition: transform 0.3s ease;
              }

              .image-card:hover .image-preview img {
                transform: scale(1.05);
              }

              .remove-image-btn {
                position: absolute;
                top: 12px;
                right: 12px;
                background: rgba(239, 68, 68, 0.9);
                color: white;
                border: none;
                border-radius: 50%;
                width: 32px;
                height: 32px;
                cursor: pointer;
                font-size: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
              }

              .remove-image-btn:hover {
                background: #ef4444;
                transform: scale(1.1);
                box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
              }

              .image-details {
                padding: 1.5rem;
              }

              .filename {
                font-weight: 700;
                color: #1e293b;
                margin-bottom: 1rem;
                font-size: 0.95rem;
                word-break: break-word;
                display: flex;
                align-items: center;
                gap: 0.5rem;
              }

              .filename::before {
                content: '📄';
                font-size: 1.1rem;
              }

              .form-group {
                margin-bottom: 1rem;
              }

              .form-group label {
                display: block;
                font-weight: 600;
                color: #374151;
                margin-bottom: 0.5rem;
                font-size: 0.9rem;
              }

              .form-group select,
              .form-group textarea {
                width: 100%;
                padding: 0.75rem;
                border: 2px solid #e5e7eb;
                border-radius: 12px;
                font-size: 0.9rem;
                transition: all 0.3s ease;
                background: white;
                font-family: inherit;
              }

              .form-group select:focus,
              .form-group textarea:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
                transform: translateY(-1px);
              }

              .form-group textarea {
                resize: vertical;
                min-height: 70px;
                line-height: 1.5;
              }

              .main-chat-area {
                flex: 1;
                display: flex;
                flex-direction: column;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                position: relative;
                overflow: hidden;
              }

              .main-chat-area::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url('data:image/svg+xml,<svg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"><g fill="none" fill-rule="evenodd"><g fill="%23ffffff" fill-opacity="0.03"><circle cx="30" cy="30" r="2"/></g></svg>');
                opacity: 0.5;
              }

              .chatbot-outer {
                flex: 1;
                display: flex;
                flex-direction: column;
                max-width: 100%;
                position: relative;
                z-index: 1;
              }

              .container {
                flex: 1;
                display: flex;
                flex-direction: column;
                padding: 2rem;
                max-width: 1000px;
                margin: 0 auto;
                width: 100%;
              }

              .container h1 {
                font-size: 2.5rem;
                font-weight: 800;
                color: white;
                text-align: center;
                margin-bottom: 0.5rem;
                text-shadow: 0 2px 10px rgba(0,0,0,0.1);
              }

              .subtitle {
                color: rgba(255,255,255,0.9);
                text-align: center;
                margin-bottom: 2rem;
                font-size: 1.1rem;
                font-weight: 500;
                text-shadow: 0 1px 5px rgba(0,0,0,0.1);
              }

              .chat {
                flex: 1;
                overflow-y: auto;
                padding: 1rem 0;
                background: rgba(255,255,255,0.95);
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                backdrop-filter: blur(20px);
                margin-bottom: 1rem;
              }

              /* Enhanced message bubbles */
              .chat :global(.msg) {
                margin-bottom: 1rem;
                padding: 0 1.5rem;
              }

              .chat :global(.bubble) {
                max-width: 80%;
                padding: 1rem 1.5rem;
                border-radius: 18px;
                line-height: 1.6;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                font-weight: 500;
              }

              .chat :global(.msg.bot .bubble) {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                margin-right: auto;
              }

              .chat :global(.msg.user .bubble) {
                background: white;
                color: #1e293b;
                margin-left: auto;
                border: 1px solid #e2e8f0;
              }

              /* Enhanced form styling */
              .input-row {
                background: rgba(255,255,255,0.95);
                padding: 1.5rem;
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                backdrop-filter: blur(20px);
              }

              .input-row input {
                width: 100%;
                padding: 1rem 1.5rem;
                border: 2px solid #e5e7eb;
                border-radius: 15px;
                font-size: 1rem;
                transition: all 0.3s ease;
                background: white;
                font-family: inherit;
              }

              .input-row input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
                transform: translateY(-2px);
              }

              /* Enhanced button styling */
              .input-row button,
              .option-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 0.8rem 1.5rem;
                border-radius: 12px;
                cursor: pointer;
                font-weight: 600;
                font-size: 0.95rem;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                margin: 0.5rem;
              }

              .input-row button:hover,
              .option-btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
              }

              .option-btn.selected {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
              }

              /* Options grid */
              .options-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 0.8rem;
                margin-top: 1rem;
              }

              /* Info tip styling */
              .info-tip {
                background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
                border: 1px solid #3b82f6;
                border-radius: 12px;
                padding: 1rem;
                margin-bottom: 1rem;
                font-size: 0.9rem;
                color: #1e40af;
              }

              /* Script preview enhancements */
              .script-actions {
                background: rgba(255,255,255,0.95);
                padding: 1.5rem;
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                backdrop-filter: blur(20px);
                margin-top: 1rem;
              }

              .generate-video-btn {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
                border: none;
                padding: 1rem 2rem;
                border-radius: 15px;
                cursor: pointer;
                font-weight: 700;
                font-size: 1.1rem;
                transition: all 0.3s ease;
                box-shadow: 0 6px 20px rgba(16, 185, 129, 0.3);
                width: 100%;
              }

              .generate-video-btn:hover:not(:disabled) {
                transform: translateY(-3px);
                box-shadow: 0 10px 30px rgba(16, 185, 129, 0.4);
              }

              .generate-video-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
              }

              .veo3-features {
                margin-top: 1rem;
                text-align: center;
                color: #64748b;
                font-size: 0.9rem;
                font-weight: 500;
              }

              /* Loading indicator */
              .loading-indicator {
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 2rem;
                background: rgba(255,255,255,0.95);
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                backdrop-filter: blur(20px);
                margin-top: 1rem;
              }

              .loading-indicator .spinner {
                font-size: 2rem;
                margin-bottom: 1rem;
                animation: spin 1s linear infinite;
              }

              .loading-indicator p {
                color: #667eea;
                font-weight: 600;
                margin: 0;
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
                  max-height: 50vh;
                  order: 2;
                }

                .image-sidebar.closed {
                  width: 100%;
                  height: 80px;
                }

                .main-chat-area {
                  order: 1;
                  min-height: 50vh;
                }

                .container {
                  padding: 1.5rem;
                }

                .container h1 {
                  font-size: 2rem;
                }

                .sidebar-header h3 {
                  font-size: 1rem;
                }

                .image-sidebar {
                  width: 100%;
                }
              }

              @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
              }

              /* Loading animation */
              .chat :global(.spinner) {
                display: inline-block;
                animation: spin 1s linear infinite;
              }
            `}</style>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chatbot;

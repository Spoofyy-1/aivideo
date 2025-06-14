import React, { useState } from 'react';

const RatingModal = ({ isOpen, onClose, onSubmit, sessionId, adType, industry, companyUrl, adScript }) => {
  const [rating, setRating] = useState(0);
  const [feedback, setFeedback] = useState('');
  const [hoveredRating, setHoveredRating] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (rating === 0) {
      alert('Please select a rating');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch('/api/submit-rating', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          rating: rating,
          feedback_text: feedback,
          ad_type: adType,
          industry: industry,
          company_url: companyUrl,
          ad_script: adScript
        }),
      });

      if (response.ok) {
        onSubmit({ rating, feedback });
        onClose();
        // Reset form
        setRating(0);
        setFeedback('');
      } else {
        const error = await response.json();
        alert(`Error submitting rating: ${error.error}`);
      }
    } catch (error) {
      console.error('Error submitting rating:', error);
      alert('Error submitting rating. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setRating(0);
    setFeedback('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-md w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-800">Rate This Ad</h2>
          <button
            onClick={handleClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
            disabled={isSubmitting}
          >
            ×
          </button>
        </div>

        <div className="mb-6">
          <p className="text-gray-600 mb-4">
            How would you rate this ad? Your feedback helps us improve future ads!
          </p>

          {/* Star Rating */}
          <div className="flex justify-center mb-4">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                onClick={() => setRating(star)}
                onMouseEnter={() => setHoveredRating(star)}
                onMouseLeave={() => setHoveredRating(0)}
                className={`text-3xl mx-1 transition-colors ${
                  star <= (hoveredRating || rating)
                    ? 'text-yellow-400'
                    : 'text-gray-300'
                } hover:text-yellow-400`}
                disabled={isSubmitting}
              >
                ★
              </button>
            ))}
          </div>

          {/* Rating Labels */}
          <div className="text-center mb-4">
            {rating > 0 && (
              <span className="text-sm text-gray-600">
                {rating === 1 && "Poor - Didn't like it"}
                {rating === 2 && "Fair - Could be better"}
                {rating === 3 && "Good - It was okay"}
                {rating === 4 && "Very Good - Liked it"}
                {rating === 5 && "Excellent - Loved it!"}
              </span>
            )}
          </div>

          {/* Feedback Text Area */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tell us more (optional):
            </label>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder={
                rating <= 2
                  ? "What didn't you like? How could we improve it?"
                  : rating >= 4
                  ? "What did you love about this ad?"
                  : "Any thoughts or suggestions?"
              }
              className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows="4"
              disabled={isSubmitting}
            />
          </div>

          {/* Quick Feedback Buttons for Low Ratings */}
          {rating <= 2 && (
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">Common issues (click to add):</p>
              <div className="flex flex-wrap gap-2">
                {[
                  "Too fast/hard to follow",
                  "Audio quality issues", 
                  "Boring/not engaging",
                  "Doesn't explain the product well",
                  "Poor video quality",
                  "Too long",
                  "Confusing message"
                ].map((issue) => (
                  <button
                    key={issue}
                    onClick={() => {
                      if (!feedback.includes(issue)) {
                        setFeedback(prev => prev ? `${prev}, ${issue}` : issue);
                      }
                    }}
                    className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-full border"
                    disabled={isSubmitting}
                  >
                    {issue}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Quick Feedback Buttons for High Ratings */}
          {rating >= 4 && (
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">What worked well (click to add):</p>
              <div className="flex flex-wrap gap-2">
                {[
                  "Great hook/attention-grabbing",
                  "Clear product explanation",
                  "Good pacing",
                  "Engaging visuals",
                  "Memorable/catchy",
                  "Professional quality",
                  "Perfect length"
                ].map((positive) => (
                  <button
                    key={positive}
                    onClick={() => {
                      if (!feedback.includes(positive)) {
                        setFeedback(prev => prev ? `${prev}, ${positive}` : positive);
                      }
                    }}
                    className="px-3 py-1 text-xs bg-green-100 hover:bg-green-200 rounded-full border border-green-300"
                    disabled={isSubmitting}
                  >
                    {positive}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <button
            onClick={handleClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            disabled={isSubmitting}
          >
            Skip
          </button>
          <button
            onClick={handleSubmit}
            disabled={rating === 0 || isSubmitting}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Rating'}
          </button>
        </div>

        {/* Privacy Note */}
        <p className="text-xs text-gray-500 mt-3 text-center">
          Your feedback helps improve our AI. Ratings are anonymous and used to enhance future ad generation.
        </p>
      </div>
    </div>
  );
};

export default RatingModal; 
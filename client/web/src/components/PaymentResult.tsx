interface PaymentResultProps {
  status: 'success' | 'error';
  result?: unknown;
  error?: string;
  onReset: () => void;
}

export function PaymentResult({ status, result, error, onReset }: PaymentResultProps) {
  // Check if result contains media URL
  const getMediaUrl = () => {
    if (typeof result === 'object' && result !== null) {
      const data = result as Record<string, unknown>;
      console.log('PaymentResult - result data:', data);
      const url = (data.url || data.image || data.video || data.media) as string | undefined;
      console.log('PaymentResult - extracted URL:', url);
      return url;
    }
    return undefined;
  };

  const mediaUrl = getMediaUrl();
  // Check if it's a video based on extension or assume image if URL exists
  const isVideo = mediaUrl?.match(/\.(mp4|webm|ogg)$/i);
  const isImage = mediaUrl && !isVideo; // Assume image if not video

  console.log('PaymentResult - mediaUrl:', mediaUrl, 'isImage:', isImage, 'isVideo:', isVideo);

  return (
    <div className="border border-gray-200 rounded-2xl bg-white max-w-3xl mx-auto overflow-hidden">
      {status === 'success' ? (
        <>
          {/* Media Content */}
          {mediaUrl ? (
            <div className="relative w-full bg-gray-50">
              {isVideo ? (
                <video
                  src={mediaUrl}
                  controls
                  autoPlay
                  className="w-full h-auto max-h-[70vh] object-contain"
                >
                  Your browser does not support the video tag.
                </video>
              ) : (
                <img
                  src={mediaUrl}
                  alt="Protected content"
                  className="w-full h-auto max-h-[70vh] object-contain"
                  onError={(e) => {
                    // If image fails to load, hide it
                    e.currentTarget.style.display = 'none';
                  }}
                />
              )}
            </div>
          ) : (
            /* Fallback to text content */
            <div className="p-10">
              <div className="flex items-center justify-center mb-6">
                <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
              </div>
              <h2 className="text-3xl font-bold text-gray-900 text-center mb-3">
                Payment Successful
              </h2>
              <p className="text-gray-600 text-center mb-8 text-lg">
                You have successfully accessed the protected resource.
              </p>
              <div className="bg-gray-50 rounded-xl p-6 mb-6 border border-gray-200">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-3">Response</p>
                <pre className="text-sm text-gray-900 overflow-auto max-h-48 font-mono">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Action Button */}
          <div className="p-6 border-t border-gray-200">
            <button onClick={onReset} className="w-full btn-secondary">
              Try Again
            </button>
          </div>
        </>
      ) : (
        <div className="p-10">
          <div className="flex items-center justify-center mb-6">
            <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
          </div>
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-3">
            Payment Failed
          </h2>
          <p className="text-red-600 text-center mb-8">{error}</p>
          <button onClick={onReset} className="w-full btn-secondary">
            Try Again
          </button>
        </div>
      )}
    </div>
  );
}

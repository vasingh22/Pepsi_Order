const Hero = () => {
  return (
    <section className="min-h-screen flex items-center justify-center p-4 sm:p-6 md:p-8 bg-gradient-to-br from-[#667eea] to-[#764ba2] relative overflow-hidden">
      {/* Animated background pattern */}
      <div
        className="absolute w-[200%] h-[200%] opacity-10 animate-move-bg"
        style={{
          backgroundImage:
            "radial-gradient(circle, white 1px, transparent 1px)",
          backgroundSize: "50px 50px",
        }}
      ></div>

      <div className="max-w-6xl relative z-10">
        {/* Title */}
        <h1 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-4 sm:mb-5 md:mb-6 leading-tight">
          Transform Unstructured Orders into
          <span className="bg-gradient-to-r from-[#ffd89b] to-[#19547b] bg-clip-text text-transparent">
            {" "}
            Structured Data
          </span>
        </h1>

        {/* Description */}
        <p className="text-sm sm:text-base md:text-lg text-white/90 mb-8 sm:mb-10 md:mb-12 leading-relaxed max-w-3xl">
          PepsiCo receives thousands of unstructured order images and PDFs from
          customers with widely varying formats. Manual entry is slow,
          error-prone, and prevents near-real-time visibility into sales data.
        </p>

        {/* Problem & Solution Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 md:gap-8 mb-8 sm:mb-10 md:mb-12">
          {/* Problem Card */}
          <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl sm:rounded-3xl p-5 sm:p-6 md:p-8 text-white transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl">
            <div className="text-4xl sm:text-5xl mb-3 sm:mb-4">⚠️</div>
            <h3 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4">
              The Challenge
            </h3>
            <p className="text-sm sm:text-base leading-relaxed text-white/90">
              Existing OCR tools struggle with inconsistent layouts, while full
              vision-LLM pipelines are costly and complex to run at scale.
            </p>
          </div>

          {/* Solution Card */}
          <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl sm:rounded-3xl p-5 sm:p-6 md:p-8 text-white transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl">
            <div className="text-4xl sm:text-5xl mb-3 sm:mb-4">✨</div>
            <h3 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4">
              Our Solution
            </h3>
            <p className="text-sm sm:text-base leading-relaxed text-white/90">
              A managed OCR + LLM text-parsing workflow orchestrated through
              Temporal Cloud — delivering accurate, low-cost, and durable
              document ingestion without hosting custom models.
            </p>
          </div>
        </div>

        {/* Features */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <div className="flex items-center gap-2 sm:gap-3 px-3 py-2.5 sm:py-3 bg-white/15 backdrop-blur-md border border-white/20 rounded-xl sm:rounded-2xl text-white text-sm sm:text-base font-semibold transition-all duration-300 hover:bg-white/25 hover:scale-105">
            <span className="text-xl sm:text-2xl flex-shrink-0">⚡</span>
            <span>Near Real-Time Processing</span>
          </div>
          <div className="flex items-center gap-2 sm:gap-3 px-3 py-2.5 sm:py-3 bg-white/15 backdrop-blur-md border border-white/20 rounded-xl sm:rounded-2xl text-white text-sm sm:text-base font-semibold transition-all duration-300 hover:bg-white/25 hover:scale-105">
            <span className="text-xl sm:text-2xl flex-shrink-0">💰</span>
            <span>Cost-Effective</span>
          </div>
          <div className="flex items-center gap-2 sm:gap-3 px-3 py-2.5 sm:py-3 bg-white/15 backdrop-blur-md border border-white/20 rounded-xl sm:rounded-2xl text-white text-sm sm:text-base font-semibold transition-all duration-300 hover:bg-white/25 hover:scale-105">
            <span className="text-xl sm:text-2xl flex-shrink-0">🎯</span>
            <span>High Accuracy</span>
          </div>
          <div className="flex items-center gap-2 sm:gap-3 px-3 py-2.5 sm:py-3 bg-white/15 backdrop-blur-md border border-white/20 rounded-xl sm:rounded-2xl text-white text-sm sm:text-base font-semibold transition-all duration-300 hover:bg-white/25 hover:scale-105">
            <span className="text-xl sm:text-2xl flex-shrink-0">🔄</span>
            <span>Durable Workflows</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;

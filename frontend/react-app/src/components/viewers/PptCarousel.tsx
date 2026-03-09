/**
 * PPT slide carousel — displays slide images with prev/next navigation.
 * Supports keyboard arrow keys for slide navigation.
 * Fetches the slide list from the view API, then renders individual PNGs.
 */

import { useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchSlides, viewSlideUrl } from "@/api/jobs";

interface PptCarouselProps {
  jobId: string;
}

export default function PptCarousel({ jobId }: PptCarouselProps) {
  const [currentSlide, setCurrentSlide] = useState(1);

  const { data, isLoading, error } = useQuery({
    queryKey: ["slides", jobId],
    queryFn: () => fetchSlides(jobId),
  });

  const total = data?.total ?? 0;

  const goNext = useCallback(() => {
    setCurrentSlide((s) => Math.min(total, s + 1));
  }, [total]);

  const goPrev = useCallback(() => {
    setCurrentSlide((s) => Math.max(1, s - 1));
  }, []);

  // Keyboard navigation: arrow keys
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        goNext();
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        goPrev();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goNext, goPrev]);

  if (isLoading) {
    return <div className="text-center text-text-secondary">Loading slides...</div>;
  }

  if (error || !data || total === 0) {
    return <div className="text-center text-text-muted">No slides available</div>;
  }

  return (
    <div className="w-full" data-testid="ppt-carousel">
      {/* Slide image */}
      <div className="flex items-center justify-center rounded-lg bg-black/20 p-2">
        <img
          src={viewSlideUrl(jobId, currentSlide)}
          alt={`Slide ${currentSlide} of ${total}`}
          className="max-h-[500px] w-auto rounded"
        />
      </div>

      {/* Navigation controls */}
      <div className="mt-3 flex items-center justify-center gap-4">
        <button
          onClick={goPrev}
          disabled={currentSlide <= 1}
          className="glass rounded-lg px-4 py-2 text-sm font-medium transition hover:glass-hover disabled:opacity-40"
          aria-label="Previous slide"
        >
          Previous
        </button>

        <span className="text-sm text-text-secondary" data-testid="slide-counter">
          {currentSlide} / {total}
        </span>

        <button
          onClick={goNext}
          disabled={currentSlide >= total}
          className="glass rounded-lg px-4 py-2 text-sm font-medium transition hover:glass-hover disabled:opacity-40"
          aria-label="Next slide"
        >
          Next
        </button>
      </div>
    </div>
  );
}

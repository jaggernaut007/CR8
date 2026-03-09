/**
 * Video player — HTML5 video with topic selector for multiple videos.
 * Fetches the video list from the view API, shows a selector when multiple exist.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchVideos, viewVideoUrl } from "@/api/jobs";

interface VideoPlayerProps {
  jobId: string;
}

export default function VideoPlayer({ jobId }: VideoPlayerProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["videos", jobId],
    queryFn: () => fetchVideos(jobId),
  });

  if (isLoading) {
    return <div className="text-center text-text-secondary">Loading videos...</div>;
  }

  if (error || !data || data.videos.length === 0) {
    return <div className="text-center text-text-muted">No videos available</div>;
  }

  const videos = data.videos;

  return (
    <div className="w-full" data-testid="video-player">
      {/* Topic selector (only if multiple videos) */}
      {videos.length > 1 && (
        <div className="mb-3">
          <label htmlFor="video-topic" className="mb-1 block text-xs font-medium text-text-secondary">
            Topic
          </label>
          <select
            id="video-topic"
            value={selectedIndex}
            onChange={(e) => setSelectedIndex(Number(e.target.value))}
            className="glass w-full rounded-lg px-3 py-2 text-sm text-text-primary"
            data-testid="video-selector"
          >
            {videos.map((v, i) => (
              <option key={i} value={i}>
                {v.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Video element */}
      <video
        key={selectedIndex}
        controls
        className="w-full rounded-lg"
        src={viewVideoUrl(jobId, selectedIndex)}
      >
        Your browser does not support video playback.
      </video>

      {/* Video name (single video only) */}
      {videos.length === 1 && (
        <p className="mt-2 text-center text-sm text-text-secondary">{videos[0].name}</p>
      )}
    </div>
  );
}

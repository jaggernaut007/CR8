/**
 * Content tabs — switches between PDF, Slides, and Video viewers.
 * Only shows tabs for formats that were generated.
 */

interface ContentTabsProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  formats: string[];
}

const TAB_CONFIG = [
  { key: "pdf", label: "PDF Guide" },
  { key: "ppt", label: "Slides" },
  { key: "video", label: "Video" },
];

export default function ContentTabs({ activeTab, onTabChange, formats }: ContentTabsProps) {
  const visibleTabs = TAB_CONFIG.filter(({ key }) => {
    if (key === "pdf") return true; // Always generated
    if (key === "ppt") return formats.includes("ppt");
    if (key === "video") return formats.includes("video");
    return false;
  });

  return (
    <div className="flex gap-1 rounded-lg bg-bg-tertiary p-1" data-testid="content-tabs">
      {visibleTabs.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onTabChange(key)}
          className={`rounded-md px-4 py-2 text-sm font-medium transition ${
            activeTab === key
              ? "bg-accent-blue/20 text-accent-blue"
              : "text-text-secondary hover:text-text-primary"
          }`}
          aria-selected={activeTab === key}
          role="tab"
        >
          {label}
        </button>
      ))}
    </div>
  );
}

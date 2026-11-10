import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getNcertUnitNote } from "../api";
import type { NcertNoteDetail, NcertPage } from "../types";
import {
  CheckIcon,
  CopyIcon,
  DownloadIcon,
  WarningIcon,
} from "./icons";

interface PdfNotesViewerProps {
  initialUnit?: number;
  onClose?: () => void;
}

export function PdfNotesViewer({ initialUnit = 1 }: PdfNotesViewerProps) {
  const [currentUnit, setCurrentUnit] = useState<number>(initialUnit);
  const [noteData, setNoteData] = useState<NcertNoteDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [viewMode, setViewMode] = useState<"continuous" | "single">("continuous");
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [showSidebar, setShowSidebar] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);
  const [fullscreen, setFullscreen] = useState<boolean>(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<(HTMLElement | null)[]>([]);

  // Load Unit Notes
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    setCurrentPage(1);

    getNcertUnitNote(currentUnit)
      .then((data) => {
        if (active) {
          setNoteData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message || "Failed to load NCERT unit notes");
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [currentUnit]);

  // Trigger KaTeX auto-render on document body if KaTeX is loaded
  useEffect(() => {
    if (!loading && noteData && typeof window !== "undefined") {
      const renderMath = () => {
        const renderMathInElement = (window as any).renderMathInElement;
        if (renderMathInElement && containerRef.current) {
          try {
            renderMathInElement(containerRef.current, {
              delimiters: [
                { left: "$$", right: "$$", display: true },
                { left: "$", right: "$", display: false },
                { left: "\\[", right: "\\]", display: true },
                { left: "\\(", right: "\\)", display: false },
              ],
              throwOnError: false,
            });
          } catch {
            // KaTeX parsing warning ignored
          }
        }
      };
      const timer = setTimeout(renderMath, 100);
      return () => clearTimeout(timer);
    }
  }, [loading, noteData, currentPage, viewMode]);

  const scrollToPage = (pageNum: number) => {
    setCurrentPage(pageNum);
    if (viewMode === "continuous") {
      const target = pageRefs.current[pageNum - 1];
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  };

  const handleCopy = async () => {
    if (!noteData) return;
    try {
      await navigator.clipboard.writeText(noteData.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  const handleDownload = () => {
    if (!noteData) return;
    const blob = new Blob([noteData.markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `NCERT_Class10_Unit_${currentUnit}_Notes.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    window.print();
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.().catch(() => {});
      setFullscreen(true);
    } else {
      document.exitFullscreen?.().catch(() => {});
      setFullscreen(false);
    }
  };

  const pages = noteData?.pages || [];
  const totalPages = pages.length || 10;

  return (
    <div className={`pdf-viewer-root ${fullscreen ? "fullscreen-mode" : ""}`}>
      {/* Top PDF Controls Toolbar */}
      <header className="pdf-toolbar">
        {/* Left Section: Unit Selectors */}
        <div className="toolbar-group unit-selector-group">
          <span className="toolbar-label">NCERT Class 10:</span>
          <button
            type="button"
            className={`tab-pill ${currentUnit === 1 ? "active" : ""}`}
            onClick={() => setCurrentUnit(1)}
          >
            Unit 1: Real Numbers
          </button>
          <button
            type="button"
            className={`tab-pill ${currentUnit === 2 ? "active" : ""}`}
            onClick={() => setCurrentUnit(2)}
          >
            Unit 2: Polynomials
          </button>
          <button
            type="button"
            className={`tab-pill ${currentUnit === 3 ? "active" : ""}`}
            onClick={() => setCurrentUnit(3)}
          >
            Unit 3: Linear Equations
          </button>
        </div>

        {/* Center Section: Page Navigation & Zoom */}
        <div className="toolbar-group page-controls">
          <button
            type="button"
            className="icon-btn-pdf"
            onClick={() => setShowSidebar(!showSidebar)}
            title="Toggle Page Thumbnails Outline"
          >
            📑 Outline
          </button>

          <span className="divider" />

          <button
            type="button"
            className="icon-btn-pdf"
            disabled={currentPage <= 1}
            onClick={() => scrollToPage(Math.max(1, currentPage - 1))}
            title="Previous Page"
          >
            ◀
          </button>
          <div className="page-indicator">
            <select
              value={currentPage}
              onChange={(e) => scrollToPage(Number(e.target.value))}
              className="page-select"
            >
              {pages.map((p) => (
                <option key={p.page_number} value={p.page_number}>
                  Page {p.page_number}: {p.section_id}
                </option>
              ))}
            </select>
            <span className="total-pages-label">of {totalPages}</span>
          </div>
          <button
            type="button"
            className="icon-btn-pdf"
            disabled={currentPage >= totalPages}
            onClick={() => scrollToPage(Math.min(totalPages, currentPage + 1))}
            title="Next Page"
          >
            ▶
          </button>

          <span className="divider" />

          {/* View mode toggle */}
          <div className="mode-toggle">
            <button
              type="button"
              className={`toggle-btn ${viewMode === "continuous" ? "active" : ""}`}
              onClick={() => setViewMode("continuous")}
              title="Continuous Scroll Mode"
            >
              All 10 Pages
            </button>
            <button
              type="button"
              className={`toggle-btn ${viewMode === "single" ? "active" : ""}`}
              onClick={() => setViewMode("single")}
              title="Single Page Mode"
            >
              Single
            </button>
          </div>

          <span className="divider" />

          {/* Zoom controls */}
          <button
            type="button"
            className="icon-btn-pdf"
            onClick={() => setZoomLevel((z) => Math.max(60, z - 15))}
            title="Zoom Out"
          >
            🔍 -
          </button>
          <span className="zoom-text">{zoomLevel}%</span>
          <button
            type="button"
            className="icon-btn-pdf"
            onClick={() => setZoomLevel((z) => Math.min(160, z + 15))}
            title="Zoom In"
          >
            🔍 +
          </button>
          <button
            type="button"
            className="icon-btn-pdf"
            onClick={() => setZoomLevel(100)}
            title="Reset Zoom"
          >
            Reset
          </button>
        </div>

        {/* Right Section: Actions */}
        <div className="toolbar-group right-actions">
          <button
            type="button"
            className="pdf-action-btn print-btn"
            onClick={handlePrint}
            title="Print or Save as authentic PDF"
          >
            🖨️ Print / Save PDF
          </button>
          <button
            type="button"
            className="pdf-action-btn"
            onClick={handleCopy}
            title="Copy Markdown"
          >
            {copied ? <CheckIcon /> : <CopyIcon />}
            {copied ? "Copied" : "Copy"}
          </button>
          <button
            type="button"
            className="pdf-action-btn"
            onClick={handleDownload}
            title="Download Notes Markdown"
          >
            <DownloadIcon />
            Download
          </button>
          <button
            type="button"
            className="icon-btn-pdf"
            onClick={toggleFullscreen}
            title="Toggle Fullscreen"
          >
            ⛶
          </button>
        </div>
      </header>

      {/* Main Reader Layout */}
      <div className="pdf-workspace">
        {/* Left Thumbnails / Outline Sidebar */}
        {showSidebar && (
          <aside className="pdf-outline-sidebar">
            <div className="sidebar-header">
              <h3>{noteData?.title || `Unit ${currentUnit}`}</h3>
              <p className="sidebar-subtitle">10-Page Master Study Notes</p>
            </div>
            <div className="thumbnail-list">
              {pages.map((page: NcertPage) => (
                <div
                  key={page.page_number}
                  className={`thumbnail-card ${currentPage === page.page_number ? "active" : ""}`}
                  onClick={() => scrollToPage(page.page_number)}
                >
                  <div className="thumb-preview">
                    <span className="thumb-page-num">{page.page_number}</span>
                    <div className="thumb-mini-lines">
                      <div className="mini-line title-line" />
                      <div className="mini-line" />
                      <div className="mini-line" />
                      <div className="mini-line short" />
                    </div>
                  </div>
                  <div className="thumb-meta">
                    <span className="thumb-sec-id">Section {page.section_id}</span>
                    <span className="thumb-title">{page.title}</span>
                    <span className="thumb-words">{page.words} words</span>
                  </div>
                </div>
              ))}
            </div>
          </aside>
        )}

        {/* Central PDF Canvas Viewport */}
        <main className="pdf-canvas-viewport" ref={containerRef}>
          {loading ? (
            <div className="pdf-loading-state">
              <span className="spinner large" />
              <h3>Loading 10-Page Study Notes...</h3>
              <p>Fetching on-device generated notes for Unit {currentUnit} from local LLM storage.</p>
            </div>
          ) : error ? (
            <div className="pdf-error-state">
              <WarningIcon />
              <h3>Error loading notes</h3>
              <p>{error}</p>
              <button
                type="button"
                className="btn primary"
                onClick={() => setCurrentUnit((u) => u)}
              >
                Retry
              </button>
            </div>
          ) : (
            <div
              className={`pdf-pages-container zoom-${zoomLevel}`}
              style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: "top center" }}
            >
              {viewMode === "continuous"
                ? // Render all 10 pages stacked
                  pages.map((page: NcertPage, index: number) => (
                    <article
                      key={page.page_number}
                      className="pdf-a4-sheet"
                      ref={(el) => {
                        pageRefs.current[index] = el;
                      }}
                      id={`pdf-page-${page.page_number}`}
                    >
                      {/* Running A4 Page Header */}
                      <header className="a4-running-header">
                        <span className="header-subject">NCERT Class 10 Mathematics</span>
                        <span className="header-chapter">
                          {noteData?.title} • Section {page.section_id}
                        </span>
                        <span className="header-page">Page {page.page_number} of {totalPages}</span>
                      </header>

                      {/* A4 Page Content Area */}
                      <div className="a4-content-area">
                        <div className="section-title-badge">
                          <span className="badge-pill">Section {page.section_id}</span>
                          <h2 className="page-heading">{page.title}</h2>
                        </div>
                        <div className="a4-markdown-body">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {page.content}
                          </ReactMarkdown>
                        </div>
                      </div>

                      {/* Running A4 Page Footer */}
                      <footer className="a4-running-footer">
                        <span className="footer-org">Offline Intelligent Learning Assistant (ILA) · SDG 4</span>
                        <span className="footer-page-badge">
                          — Page {page.page_number} of {totalPages} —
                        </span>
                        <span className="footer-curriculum">CBSE / NCERT Standard</span>
                      </footer>
                    </article>
                  ))
                : // Render only current active page
                  pages
                    .filter((p) => p.page_number === currentPage)
                    .map((page: NcertPage) => (
                      <article
                        key={page.page_number}
                        className="pdf-a4-sheet"
                        id={`pdf-page-${page.page_number}`}
                      >
                        <header className="a4-running-header">
                          <span className="header-subject">NCERT Class 10 Mathematics</span>
                          <span className="header-chapter">
                            {noteData?.title} • Section {page.section_id}
                          </span>
                          <span className="header-page">Page {page.page_number} of {totalPages}</span>
                        </header>

                        <div className="a4-content-area">
                          <div className="section-title-badge">
                            <span className="badge-pill">Section {page.section_id}</span>
                            <h2 className="page-heading">{page.title}</h2>
                          </div>
                          <div className="a4-markdown-body">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {page.content}
                            </ReactMarkdown>
                          </div>
                        </div>

                        <footer className="a4-running-footer">
                          <span className="footer-org">Offline Intelligent Learning Assistant (ILA) · SDG 4</span>
                          <span className="footer-page-badge">
                            — Page {page.page_number} of {totalPages} —
                          </span>
                          <span className="footer-curriculum">CBSE / NCERT Standard</span>
                        </footer>
                      </article>
                    ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

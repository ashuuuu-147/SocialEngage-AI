import { Menu, PlusCircle } from 'lucide-react';

interface TopbarProps {
  title: string;
  subtitle?: string;
  onOpenMobileMenu: () => void;
  onOpenSubmitPost: () => void;
}

export function Topbar({
  title,
  subtitle,
  onOpenMobileMenu,
  onOpenSubmitPost,
}: TopbarProps) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="topbar-left">
          <button
            type="button"
            className="btn btn-secondary btn-icon mobile-menu-btn"
            onClick={onOpenMobileMenu}
            aria-label="Open navigation menu"
          >
            <Menu size={18} aria-hidden="true" />
          </button>
          <div style={{ minWidth: 0 }}>
            <h1 className="page-title">{title}</h1>
            {subtitle && <p className="page-subtitle">{subtitle}</p>}
          </div>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          onClick={onOpenSubmitPost}
        >
          <PlusCircle size={16} aria-hidden="true" />
          <span>Submit Post URL</span>
        </button>
      </div>
    </header>
  );
}

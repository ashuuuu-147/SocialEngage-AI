import React from 'react';

interface MetricCardProps {
  label: string;
  value: number | string;
  subtext?: string;
  icon: React.ReactNode;
  loading?: boolean;
  onClick?: () => void;
}

export function MetricCard({
  label,
  value,
  subtext,
  icon,
  loading = false,
  onClick,
}: MetricCardProps) {
  const content = (
    <div className="metric-card">
      <div className="metric-card-top">
        <span className="metric-label">{label}</span>
        <span className="metric-icon" aria-hidden="true">
          {icon}
        </span>
      </div>
      {loading ? (
        <>
          <div className="skeleton" style={{ height: 32, width: '48%' }} />
          <div className="skeleton" style={{ height: 14, width: '70%' }} />
        </>
      ) : (
        <>
          <div className="metric-value">{value}</div>
          {subtext && <div className="metric-subtext">{subtext}</div>}
        </>
      )}
    </div>
  );

  if (onClick) {
    return (
      <button
        type="button"
        className="card"
        style={{ textAlign: 'left', cursor: 'pointer', width: '100%' }}
        onClick={onClick}
      >
        {content}
      </button>
    );
  }

  return <div className="card">{content}</div>;
}

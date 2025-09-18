import React from 'react';

export const CutIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    strokeWidth={2}
    {...props}
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M8.25 4.5l7.5 7.5-7.5 7.5"
      transform="rotate(90 12 12)"
    />
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M8 8.25a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zm0 7.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z"
    />
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M19.5 8.25l-12 7.5"
    />
  </svg>
);

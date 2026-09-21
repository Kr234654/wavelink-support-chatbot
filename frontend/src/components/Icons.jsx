const base = {
  width: 22, height: 22, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
  strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true,
};

export const ChatIcon = (p) => (
  <svg {...base} {...p}><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" /></svg>
);
export const CloseIcon = (p) => (
  <svg {...base} {...p}><path d="M6 6l12 12M18 6 6 18" /></svg>
);
export const SendIcon = (p) => (
  <svg {...base} {...p}><path d="M22 2 11 13M22 2l-7 20-4-9-9-4z" /></svg>
);
export const WaveMark = (p) => (
  <svg {...base} width="30" height="30" {...p} strokeWidth="2.6"><path d="M2 9c2.5-3.5 5-3.5 7.5 0s5 3.5 7.5 0 3.5-2.5 5-1.5" /><path d="M2 16c2.5-3.5 5-3.5 7.5 0s5 3.5 7.5 0 3.5-2.5 5-1.5" /></svg>
);
export const UserIcon = (p) => (
  <svg {...base} {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></svg>
);
export const ThumbUpIcon = ({ filled, ...p }) => (
  <svg {...base} {...p} fill={filled ? 'currentColor' : 'none'}><path d="M7 11v9H4a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1zM7 11l4-8a2.5 2.5 0 0 1 2.5 2.7L13 9h5.6a2 2 0 0 1 2 2.4l-1.3 6.6A2 2 0 0 1 17.4 20H7" /></svg>
);
export const ThumbDownIcon = ({ filled, ...p }) => (
  <svg {...base} {...p} fill={filled ? 'currentColor' : 'none'}><path d="M17 13V4h3a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1zM17 13l-4 8a2.5 2.5 0 0 1-2.5-2.7L11 15H5.4a2 2 0 0 1-2-2.4l1.3-6.6A2 2 0 0 1 6.6 4H17" /></svg>
);
export const RefreshIcon = (p) => (
  <svg {...base} {...p}><path d="M21 12a9 9 0 1 1-2.6-6.4M21 4v5h-5" /></svg>
);
export const HeadsetIcon = (p) => (
  <svg {...base} {...p}><path d="M4 14v-2a8 8 0 0 1 16 0v2" /><rect x="3" y="14" width="4" height="6" rx="1.5" /><rect x="17" y="14" width="4" height="6" rx="1.5" /></svg>
);
